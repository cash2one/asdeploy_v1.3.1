#coding:utf-8

import os
import json
import string
import urllib
import chardet
import cgi
from datetime import datetime, timedelta

from django.core.cache import cache
from django.db.models import Q

from django.http import HttpResponse, Http404
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response

from django.contrib.auth.models import User
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.core.servers.basehttp import FileWrapper
from django.db import connection

from deployment.deploysetting import *
from deployment.models import *
from deployment.forms import *
from deployment.logutil import *
from deployment.deployimpl import *
from deployment.sftpconn import *
from deployment.serverchecker import check_server_status

from django.utils import simplejson
from django.core.serializers import serialize,deserialize

import pdb

def check_version_and_env(request):
    params = {
        'version': VERSION,
        'environment': ENVIRONMENT,
    }
    return HttpResponse(json.dumps(params))

@login_required
def main_page(request):
    cur_lock = _check_lock()
    params = RequestContext(request, {
        'user': request.user,
        'curLock': cur_lock
    })
    return render_to_response('main_page.html', params)

@login_required
def user_page(request, username):
    try:
        user = User.objects.get(username = username)
    except:
        raise Http404('Requested user not found.')
    
    params = RequestContext(request, {
        'username': user.username,
    })
    return render_to_response('user_page.html', params)

@login_required
def logout_page(request):
    logout(request)
    return HttpResponseRedirect('/login/')

def register_page(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            User.objects.create_user(
                username = username, 
                password = password,
                email = form.cleaned_data.get('email')
            )
            user = authenticate(username = username, password = password)
            login(request, user)
            return HttpResponseRedirect('/')
    else:
        form = RegistrationForm()
    params = RequestContext(request, {
        'form': form,
    })
    return render_to_response('registration/register.html', params)

###检查/d/content挂载情况###
@login_required
def check_server_status_for_project(request, project_name = ''):
    server_status = check_server_status(project_name)
    return HttpResponse(json.dumps(server_status))

########业务相关########
@login_required
def deploy_init_option_page(request):
    error_msg = None
    if request.POST:
        deploy_type = request.POST.get('deployType')
        version = request.POST.get('version')
        proj_id = request.POST.get('projId') or 0
        patch_group_id = request.POST.get('patchGroupId') or 0    #补丁组id
        cur_lock = _check_lock()
        if not proj_id or not deploy_type or not version:
            error_msg = '输入参数有误'
        elif cur_lock:
            return HttpResponseRedirect('/')
        else:
            project = Project.objects.get(pk = proj_id)
            patch_group = patch_group_id \
                and PatchGroup.objects.get(pk = patch_group_id) \
                or None
            try:
                cur_server = WEB_SERVER[project.name][0]
            except:
                cur_server = 'NONE'
            _params = {
                'project': project,
                'deployType': deploy_type,
                'version': version,
                'curServer': cur_server,
                'patchGroup': patch_group,
                'patchGroupId': patch_group_id,
            }
            (record, lock) = _before_deploy_project(request, _params)
            _params['record'] = record
            _params['lock'] = lock
            #读取日志
            if deploy_type == DeployItem.WAR:
                folder_path = _generate_upload_folder_path(project.name, version);
                readme_content = _get_readme_content(folder_path)
                _params['readmeContent'] = cgi.escape(readme_content)
            params = RequestContext(request, _params)
            
            if deploy_type == DeployItem.RESET:
                new_backup_source_list = _get_new_backup_source_list()
                params['new_backup_source_list'] = new_backup_source_list
                return render_to_response('reset_project_page.html', params)
            else:
                return render_to_response('deploy_project_page.html', params)
        
    # 看下有没有新的backup source
    try:
        new_backup_source_list = _get_new_backup_source_list()
    except:
        new_backup_source_list = []
    
    params = RequestContext(request, {
        'error_msg': error_msg,
        'projects': Project.objects.all(),
        'ajaxableskyProject': Project.objects.get(war_name = 'ajaxablesky'),    # used for reset
        'has_new_backup_source': len(new_backup_source_list) > 0
    })
    return render_to_response('deploy_init_option_page.html', params)

def _check_lock():
    locks = DeployLock.objects.filter(is_locked = True)
    if len(locks) >= 1:
        lock = locks[0]
        period = datetime.now() - lock.locked_time
        if period.days * 24 * 3600 + period.seconds <= LOCK_TIMEOUT_PERIOD:
            return lock
        else:
            lock.is_locked = False
            lock.save()
    return None

def _before_deploy_project(request, params):
    # create DeployRecord
    # create DeployLock and build the relationship between it and DeployRecord
    project = params.get('project');
    record = DeployRecord(
        user = request.user,
        project = project,
        create_time = datetime.now(),
        status = DeployRecord.PREPARE
    )
    record.save()
    lock = DeployLock(
        user = request.user,
        deploy_record = record,
        is_locked = True,
        locked_time = datetime.now()
    )
    lock.save()
    return (record, lock)

@login_required
def unlock_deploy(request):
    curUser = request.user
    curLock = _check_lock()
    # 本人或者超级管理员有权解锁
    if curLock and (curUser.is_superuser or curUser.id == curLock.user.id):
        curLock.is_locked = False
        curLock.save()
    return HttpResponseRedirect('/')


@login_required
def deploy_record_list_page(request, page_num=1):
    projects = Project.objects.all()
    conditions = []
    query_params = {}
    num_per_page = 20
    
    if request.POST:
        username = request.POST.get('username')
        if username:
            query_params['username'] = username
            conditions.append(Q(user__username__icontains = username))
        print request.POST.get('project')
        proj_id = request.POST.get('project')
        if proj_id and proj_id != '0':
            query_params['project'] = proj_id
            conditions.append(Q(project__id = proj_id))
        version = request.POST.get('version')
        if version:
            query_params['version'] = version
            conditions.append(Q(deploy_item__version = version))
        deploy_type = request.POST.get('deployType')
        if deploy_type:
            query_params['deploy_type'] = deploy_type
            conditions.append(Q(deploy_item__deploy_type = deploy_type))
        start_time = request.POST.get('startTime')
        if start_time:
            query_params['start_time'] = start_time
            conditions.append(Q(create_time__gte = start_time))
        end_time = request.POST.get('endTime')
        if end_time:
            query_params['end_time'] = end_time
            conditions.append(Q(create_time__lte = end_time))
    query_result = DeployRecord.objects.filter(*conditions).order_by('-id')
    paged_records = Paginator(query_result, num_per_page);
    records = paged_records.page(page_num)
    for record in records:
        record.formated_create_time = record.create_time.strftime('%Y-%m-%d %H:%M:%S')
    
    query_params['curPage'] = page_num
    query_params['numPerPage'] = num_per_page
    query_params['totalPage'] = paged_records.num_pages
    params = RequestContext(request, {
        'projects': projects,
        'records': records,
        'query_params': query_params,
    })
    return render_to_response('deploy_record_list_page.html', params) 

@login_required
def deploy_record_detail_page(request, record_id):
    record = DeployRecord.objects.get(pk = record_id)
    item = record.deploy_item
    readme = ''
    #file_list_content = ''
    if item.deploy_type == DeployItem.PATCH:
        folder_path = item.folder_path + trim_compress_suffix(item.file_name) + '/'
        readme = _get_readme_content(folder_path)
        file_list = _get_file_list(folder_path)
        #file_list_content = '\r\n'.join(file_list)
    elif item.deploy_type == DeployItem.WAR or item.deploy_type == DeployItem.RESET:
        readme = _get_readme_content(item.folder_path)
        #file_list_content = item.file_name
        file_list = [item.file_name]
    
    conflict_detail = None
    if record.is_conflict_with_others:
        conflict_details = ConflictDetail.objects.filter(deploy_record__id = record.id)
        if len(conflict_details) > 0:
            conflict_detail = conflict_details[0]
        
    params = RequestContext(request, {
        'record': record,
        'readme': cgi.escape(readme),
        #'file_list_content': file_list_content,
        'file_list': file_list,
        'conflict_detail': conflict_detail,
    })
    
    return render_to_response('deploy_record_detail_page.html', params)

# 上传readme只限版本发布
@login_required
def upload_readme(request):
    params = {}
    if request.POST and request.FILES:
        proj_name = request.POST.get('projName')
        version =request.POST.get('version')
        folderpath = _generate_upload_folder_path(proj_name, version)
        if not os.path.isdir(folderpath):
            os.makedirs(folderpath)
        readme_file = request.FILES.get('readmeField')
        destination = open(folderpath + 'readme.txt', 'wb+')
        for chunk in readme_file.chunks():
            destination.write(chunk)
        destination.close()
        readme_content = _get_readme_content(folderpath)
        params['isSuccess'] = True
        params['readmeContent'] = cgi.escape(readme_content)
    else:
        params['isSuccess'] = False
    return HttpResponse(json.dumps(params))

@login_required
def upload_deploy_item(request):
    params = {}
    if request.POST and request.FILES:
        flag = True ##也许下面应该try一下
        proj_id = int(request.POST.get('projId'))
        record_id = int(request.POST.get('recordId'))
        version = string.strip(request.POST.get('version') or '')
        deploy_type = request.POST.get('deployType')
        patch_group_id = int(request.POST.get('patchGroupId') or 0)
        
        project = Project.objects.get(pk = proj_id)
        
        deploy_item_file = request.FILES.get('deployItemField')
        filename = deploy_item_file.name
        size = deploy_item_file.size
        
        if patch_group_id:
            patch_group = PatchGroup.objects.get(pk = patch_group_id)
            if patch_group and patch_group.check_code and filename.find(patch_group.check_code) == -1:
                return HttpResponse(json.dumps({
                    'isSuccess': False,
                    'errorMsg': '补丁名称与补丁组的标识号不匹配!'
                }))
        
        folderpath = _generate_upload_folder_path(project.name, version)
        if not os.path.isdir(folderpath):
            os.makedirs(folderpath)
        destination = open(folderpath + filename, 'wb+')
        for chunk in deploy_item_file.chunks():
            destination.write(chunk)
        destination.close()
        
        items = DeployItem.objects.filter(file_name__exact = filename, version__exact = version)
        item = (items and len(items) > 0) and items[0] or None
        now_time = datetime.now()
        if not item:
            item = DeployItem(
                user = request.user,
                project = project,
                version = version,
                deploy_type = deploy_type,
                file_name = filename,
                folder_path = folderpath,
                create_time = now_time,
                update_time = now_time)
        else:
            item.update_time = now_time
        item.save()
        
        record = DeployRecord.objects.get(pk = record_id)
        if record:
            record.status = DeployRecord.UPLOADED
            record.deploy_item = item;
            record.save()
            
        params['filename'] = filename
        params['size'] = size
        params['isSuccess'] = flag
    else:
        params['isSuccess'] = False
    return HttpResponse(json.dumps(params))

@login_required
def decompress_item(request):
    params = {}
    if request.POST and request.POST.get('recordId'):
        record_id = request.POST.get('recordId')
        patch_group_id = int(request.POST.get('patchGroupId') or 0)
        record = DeployRecord.objects.get(pk = record_id)
        item = record.deploy_item
        flag = False
        if item and item.file_name.endswith('.zip'):
            unziped_folder = item.folder_path + trim_compress_suffix(item.file_name) + '/'
            if os.path.isdir(unziped_folder):
                os.system('rm -rf ' + unziped_folder)
            flag = 0 == os.system('unzip -o ' + item.folder_path + item.file_name + ' -d ' + item.folder_path)
        if flag:
            file_list = _get_file_list(unziped_folder)
            params['isSuccess'] = True
            params['readme'] = cgi.escape(_get_readme_content(unziped_folder))
            params['fileList'] = file_list
        
        # 如果当前工程有配置关联的补丁组，则进行冲突检查
        # patch_group = patch_group_id > 0 and PatchGroup.objects.get(pk = patch_group_id) or None
        patch_groups = _query_patch_groups(record.project.id, PatchGroup.STATUS_TESTING)
        if patch_groups and len(patch_groups) > 0:
            # 这个数组里面不是ConflictInfo的实例，而是{file_path, conflict_patch_group_name}
            conflict_file_info_list = _check_conflict_of_file_path(patch_groups, patch_group_id, file_list)
            params['conflict_file_info_list'] = conflict_file_info_list
            
                
    if not params.has_key('isSuccess'):
        params['isSuccess'] = False
    return HttpResponse(json.dumps(params))

@login_required
def start_rollback(request):
    # 检查是否拥有当前的发布锁
    cur_lock = _check_lock()
    if not cur_lock or cur_lock.user.id != request.user.id:
        params = {
            'beginDeploy': False,
            'errorMsg': '在发布页面停留时间过长，发布锁已超时'
        }
        return HttpResponse(json.dumps(params))
    params = None
    error_msg = ''
    if request.POST and request.POST.get('recordId'):
        record_id_str = request.POST.get('recordId')
        record = DeployRecord.objects.get(pk = int(record_id_str))
        deploy_type = request.POST.get('deployType')
        server_group = request.POST.get('serverGroup')
        if deploy_type != DeployItem.PATCH:
            error_msg = '只有补丁的发布可以回滚'
        elif record.status != DeployRecord.SUCCESS \
            and record.status != DeployRecord.FAILURE \
            and record.status != DeployRecord.ROLLBACK:
            error_msg = '只有完成后的发布可以回滚'
        elif cache.get('log_is_writing_' + record_id_str):
            error_msg = '发布仍在继续中...'
        else:
            set_server_group(server_group=server_group)
            log_reader = LogReader()
            cache.set('log_reader_' + record_id_str, log_reader, 300)
            deployer = Deployer(record = record, direct = 'rollback')
            deployer.start()
            record.status = DeployRecord.ROLLBACKING
            record.save()
            params = {
                'beginDeploy': True,
            }
    if not params:
        params = {
            'beginDeploy': False,
            'errorMsg': error_msg
        }
    return HttpResponse(json.dumps(params))

def _check_backup_source_before_group_deploy():
    # 如果最新的backup源不是本环境产生的，则在发布补丁组之前，需要先进行重置发布
    latest_ajaxablesky_source, latest_static_source = _get_latest_new_backup_source_tuple()
    if latest_ajaxablesky_source is not None and latest_ajaxablesky_source.find(ENVIRONMENT) < 0 \
            or latest_static_source is not None and latest_static_source.find(ENVIRONMENT) < 0:
        return False
    return True

# 查看当前环境是否需要reset
def has_new_backup_source_for_current_env(request):
    return HttpResponse(json.dumps({
        'hasNew': not _check_backup_source_before_group_deploy()
    }))
    

@login_required
def start_deploy(request):
    # 检查是否拥有当前的发布锁
    cur_lock = _check_lock()
    if not cur_lock or cur_lock.user.id != request.user.id:
        params = {
            'beginDeploy': False,
            'errorMsg': '在发布页面停留时间过长，发布锁已超时'
        }
        return HttpResponse(json.dumps(params))
    # 发布前需要检查状态，至少为uploaded
    params = None
    error_msg = ''
    if request.POST and request.POST.get('recordId'):
        record_id_str = request.POST.get('recordId')
        record = DeployRecord.objects.get(pk = int(record_id_str))
        server_group = request.POST.get('serverGroup')
        patch_group_id = int(request.POST.get('patchGroupId') or 0)
        deploy_direct = request.POST.get('deployDirect') or 'deploy'
        
        # 版本发布需要web.xml
        if record.status == DeployRecord.PREPARE:
            error_msg = '尚未上传文件'
        elif cache.get('log_is_writing_' + record_id_str):
            error_msg = '发布仍在继续中...'
        elif deploy_direct == 'backup' and not _check_backup_source_before_group_deploy():
            error_msg = '需要先使用最新的备份源进行重置发布!'
        else:
            set_server_group(server_group=server_group)
            log_reader = LogReader()
            cache.set('log_reader_' + record_id_str, log_reader, 300)
            deployer = Deployer(record = record, direct = deploy_direct)
            deployer.start()
            record.status = DeployRecord.DEPLOYING
            record.save()
            # 如果是有组的补丁，且不是backup，则要生成冲突信息
            # backup的情形，只在上传时提示冲突，在发布时不记录冲突
            if patch_group_id != 0 and record.deploy_item.deploy_type == DeployItem.PATCH:
                # 先在item里存下patch_group的信息
                patch_group = patch_group_id and PatchGroup.objects.get(pk = patch_group_id) or None
                item = record.deploy_item
                if patch_group:
                    item.patch_group = patch_group
                    item.save() 
                # 如果是非backup的补丁发布，则生成冲突信息
                if deploy_direct != 'backup':
                    _generate_conflict_detail_for_deploy_record(record, patch_group)
                    
            params = {
                'beginDeploy': True,
            }
    if not params:
        params = {
            'beginDeploy': False,
            'errorMsg': error_msg
        }
    return HttpResponse(json.dumps(params))

# api for test
    
def test_raw_sql(request):
    patch_group_conflict_file_list = []
    related_patch_group_id = 1;
    sql = """
        SELECT 
            distinct ci.conflict_patch_group_id, 
            pg.name AS conflict_patch_group_name,
            ci.conflict_patch_file_id,
            pf.file_path AS conflict_patch_file_path
        FROM dpl_conflict_info AS ci,  
            dpl_patch_group AS pg,
            dpl_patch_file AS pf
        WHERE ci.related_patch_group_id = %d
            AND ci.conflict_patch_group_id = pg.id
            AND ci.conflict_patch_file_id = pf.id
            AND pg.status = 'testing'
    """ % (related_patch_group_id)
    cursor = connection.cursor()
    cursor.execute(sql)
    for row in cursor.fetchall():
        patch_group_conflict_file_list.append({
            'conflict_patch_group_id': row[0],
            'conflict_patch_group_name': row[1],
            'conflict_patch_file_id': row[2],
            'conflict_patch_file_patch': row[3],
        })
    print patch_group_conflict_file_list
    return HttpResponse('abc');

def test_add_patch_file_to_group(request, patch_group_id):
    file_list = [
        'com.ablesky.migration.controller.account.LoginController.class',
        'com.ablesky.migration.controller.organization.OrganizationRedirectController.class',
        'com.ablesky.migration.controller.course.PostCourseOneController.class',
    ]
    patch_group = PatchGroup.objects.get(pk = patch_group_id)
    unrelated_file_list, related_file_list = _distinguish_patch_file(patch_group, file_list)
    print unrelated_file_list
    print related_file_list
    _add_patch_file_to_group(patch_group, file_list)
    return HttpResponse('abc');

def test_generate_conflict_detial_for_deploy_record(request):
#    record_id = 29
#    patch_group_id = 2;
#    record = DeployRecord.objects.get(pk = record_id)
#    patch_group = PatchGroup.objects.get(pk = patch_group_id)
#    _generate_conflict_detail_for_deploy_record(record, patch_group_id)
    return HttpResponse('abc');

### 补丁组相关部分的代码 begin ###

# 为每次发布的deploy_record生成相应的conflict_detail
# record: 当前的发布记录
# patch_group_id: 当前发布记录所对应的补丁组
def _generate_conflict_detail_for_deploy_record(record = None, patch_group = None):
    if not record:
        return;
    item = record.deploy_item
    unziped_folder = item.folder_path + trim_compress_suffix(item.file_name) + '/'
    file_list = _get_file_list(unziped_folder)
    file_list = _exclude_readme_from_file_list(file_list)
    
    unrelated_file_list, related_file_list = _distinguish_patch_file(patch_group, file_list)
    patch_file_list = related_file_list + _add_patch_file_to_group(patch_group, unrelated_file_list)
    
    patch_groups = _query_patch_groups(record.project.id, PatchGroup.STATUS_TESTING)
    conflict_info_list = _check_conflict_of_patch_file(patch_groups, patch_group.id, patch_file_list)
    if len(conflict_info_list) > 0:
        conflict_detail = ConflictDetail(deploy_record = record)
        conflict_detail.save()
        record.is_conflict_with_others = True
        record.save()
        for conflict_info in conflict_info_list:
            conflict_info.save()
            conflict_detail.conflict_infos.add(conflict_info)

# file_list是文件路径的字符串数组
def _exclude_readme_from_file_list(file_list):
    new_file_list = []
    for file_path in file_list:
        if not file_path:
            continue
        if file_path.lower() == 'readme.txt':
            continue
        new_file_list.append(file_path)
    return new_file_list
    
            
# 检查冲突(用于上传文件时提醒)
# current_file_path_list
def _check_conflict_of_file_path(patch_groups, current_patch_group_id, current_file_path_list):
    conflict_file_path_list = []
    for path in current_file_path_list:
        for patch_group in patch_groups:
            if patch_group.id == current_patch_group_id:
                continue
            for pf in patch_group.patch_files.all():
                if pf.file_path == path:
                    conflict_file_path_list.append({
                        'file_path': path,
                        'conflict_patch_group_name': patch_group.name
                    })
    return conflict_file_path_list

# 检查冲突 (用于发布时)
# current_patch_file_list是PatchFile的数组
def _check_conflict_of_patch_file(patch_groups, current_patch_group_id, current_patch_file_list):
    conflict_info_list = []
    for cpf in current_patch_file_list:
        for patch_group in patch_groups:
            if patch_group.id == current_patch_group_id:
                continue
            for pf in patch_group.patch_files.all():
                if cpf.id == pf.id:
                    conflict_info_list.append(ConflictInfo(
                        related_patch_group_id = current_patch_group_id,
                        conflict_patch_group = patch_group,
                        conflict_patch_file = cpf
                    ))
    return conflict_info_list

# 区分已关联的file和未关联的file
# unrelated_file_list是路径数组
# related_file_list是PatchFile数组
def _distinguish_patch_file(patch_group, file_list):
    related_file_list = []
    unrelated_file_list = []
    for filepath in file_list:
        flag = True
        for related_patch_file in patch_group.patch_files.all():
            if filepath == related_patch_file.file_path:
                flag = False
                break
        if flag:
            unrelated_file_list.append(filepath)
        else:
            related_file_list.append(related_patch_file)
    return unrelated_file_list, related_file_list

# 为PatchGroup添加PatchFile信息        
# 只能输入未关联的文件路径
def _add_patch_file_to_group(patch_group, file_list):
    if not file_list:
        return []
    patch_file_list = []
    for file_path in file_list:
        files = PatchFile.objects.filter(file_path = file_path)
        patch_file = len(files) and files[0] or None
        if not patch_file:
            patch_file = PatchFile(file_path = file_path, file_type = _judge_patch_file_type(file_path))
            patch_file.save();
        patch_file_list.append(patch_file)
        
        rel = PatchFileRelGroup(
            patch_group = patch_group,
            patch_file = patch_file,
            create_time = datetime.now(),
        )
        rel.save()
    return patch_file_list
    

def _judge_patch_file_type(file_path):
    if not file_path:
        return PatchFile.TYPE_DYNAMIC
    ridx = file_path.rfind('.')
    if ridx < 0:
        return PatchFile.TYPE_DYNAMIC
    # 以上都是异常情形，默认返回dynamic
    # dynamic对应tomcat，static对应静态服务器
    suffix = file_path[ridx + 1: None]
    if suffix in ['class', 'xml', 'jsp', 'properties']:
        return PatchFile.TYPE_DYNAMIC
    else:
        return PatchFile.TYPE_STATIC
        
### 补丁组功能相关代码 end ###


@login_required
def read_deploy_log_on_realtime(request):
    record_id_str = request.GET.get('recordId')
    params = {}
    if record_id_str:
        # log_reader在start_deploy的时候生成并放入cache
        log_reader_key = 'log_reader_' + record_id_str
        log_reader = cache.get(log_reader_key)
        if log_reader:
            # 对读取的文件内容进行html转义
            logInfoArr = [];
            for line in log_reader.read_lines():
                logInfoArr.append(cgi.escape(line))
            params['logInfo'] = logInfoArr
            params['isFinished'] = False
            if cache.get('log_is_writing_' + record_id_str):
                cache.set(log_reader_key, log_reader, 300)
            else:
                cache.delete(log_reader_key)
            return HttpResponse(json.dumps(params))
    deploy_result_key = 'deploy_result_' + record_id_str
    deploy_result = cache.get(deploy_result_key)
    cache.delete(deploy_result_key)
    
    # 发布结束的状态修改操作不应该在这里进行
#    record = DeployRecord.objects.get(pk = int(record_id_str))
#    if deploy_result:
#        record.status = record.status == DeployRecord.ROLLBACKING and DeployRecord.ROLLBACK or DeployRecord.SUCCESS
#    else:
#        record.status = DeployRecord.FAILURE
##    record.status = deploy_result and DeployRecord.SUCCESS or DeployRecord.FAILURE
#    record.save()
    params['isFinished'] = True
    params['deployResult'] = deploy_result
    return HttpResponse(json.dumps(params))

def _generate_upload_folder_path(proj_name, version):
    return get_target_folder(proj_name, version)

def _get_readme_content(folder_path):
    readme_path = folder_path + 'readme.txt'
    if os.path.isfile(readme_path):
        readme_f = open(readme_path, 'r')
        lines = readme_f.readlines()
        readme_f.close()
        readme =  ''.join(lines)
    else:
        readme = ''
    return convert2utf8(readme)

def _get_file_list(root_path, depth = 0):
    if not os.path.isdir(root_path):
        return []
    f_list = []
    if not root_path.endswith('/'):
        root_path += '/'
    f_dirs = os.listdir(root_path)
    for f in f_dirs:
        f_path = root_path + f
        if os.path.isdir(f_path):
            f_list += _get_file_list(f_path, depth + 1)
        elif os.path.isfile(f_path):
            f_list.append(f_path)
    if depth == 0:
        for i in range(len(f_list)):
            s =  f_list[i][len(root_path):]
            s = string.replace(s, '/', '.')
            f_list[i] = s
        f_list.sort()
    return f_list

def convert2utf8(content):
    if not content:
        return content
    encode_manner = chardet.detect(content)
    if not encode_manner:
        return content
    if encode_manner['confidence'] < 0.6:
        return content
    if encode_manner['encoding'] == 'utf-8':
        return content
    try:
        result = content.decode(encode_manner['encoding']).encode('utf8')
    except:
        result = '内容解码失败'
    return result


# 线上文件远程下载
# folder_type: apps or conf
def file_node_cmp(n1, n2):
    if n1['isParent'] ^ n2['isParent']:
        return n1['isParent'] and -1 or 1
    elif n1['isParent'] and n2['isParent']:
        return cmp(n1['name'], n2['name'])
    else:
        suffix1 = n1['name'].split('.')[-1]
        suffix2 = n2['name'].split('.')[-1]
        suffix_cmp = cmp(suffix1, suffix2)
        if suffix_cmp:
            return suffix_cmp
        return cmp(n1['name'], n2['name'])

@login_required
def get_project_file_nodes(request, project_id = 0, server_idx = -1,  node_id = '0'):
    server_idx = int(server_idx)
    file_path = request.GET.get('file_path')
    folder_type = request.GET.get('folder_type') or FTP_DEFAULT_FOLDER_TYPE
    if not file_path:
        file_path = ''
    project = Project.objects.get(pk = project_id)
    filename_arr = get_dirlist_from_ftp(file_path = file_path, project = project, server_idx = server_idx, folder_type = folder_type)
    nodes = []
    if filename_arr is not None:
        index = 0
        suffix_regx = re.compile(r'\.\D+$')
        for name in filename_arr:
            node = {
                'id': node_id + '_' + unicode(index),
                'name': name,
                'file_path': file_path + '/' + name,
                'isParent': not suffix_regx.search(name)
            }
            index += 1
            nodes.append(node)
        nodes.sort(cmp=file_node_cmp, key=None, reverse=False)
    return HttpResponse(json.dumps(nodes))

@login_required
def download_project_file(request, project_id = 0, server_idx = 0):
    if request.GET:
        file_path = request.GET.get('file_path')
        file_name = request.GET.get('file_name')
        folder_type = request.GET.get('folder_type') or FTP_DEFAULT_FOLDER_TYPE
        project = Project.objects.get(pk = project_id)
        local_path = get_file_from_ftp(file_path = file_path, project = project, server_idx = server_idx, folder_type = folder_type)
        if local_path:
            wrapper = FileWrapper(file(local_path), blksize = 1048576)
            response = HttpResponse(wrapper, content_type='text/plain')
            response['Content-Length'] = os.path.getsize(local_path)
            response['Content-Disposition'] = 'attachment; filename=' + file_name
            return response
    return HttpResponse('')

# 编辑线上文件
@login_required
def show_online_file(request):
    
    params = RequestContext(request, {
        'projects': Project.objects.all(),
        'serverInfo': json.dumps(WEB_SERVER),
    });
    return render_to_response('show_online_file.html', params);

@login_required
def open_online_file(request, project_id = 0, server_idx_list = ''):
    params = {
        'isError': True
    }
    if project_id == 0 or server_idx_list.strip() == '':
        pass
    elif request.GET:
        file_path = request.GET.get('file_path')
        file_name = request.GET.get('file_name')
        folder_type = request.GET.get('folder_type') or FTP_DEFAULT_FOLDER_TYPE
        server_idx_arr = server_idx_list.split('_')
        project = Project.objects.get(pk = project_id)
        local_path = get_file_from_ftp(file_path = file_path, project = project, server_idx = server_idx_arr[0], folder_type = folder_type)
        f = open(local_path, 'r');
        lines = f.readlines();
        f.close()
        content = ''.join(lines);
        params['isError'] = False
        params['project'] = project
        params['content'] = content
        params['filePath'] = file_path
        params['fileName'] = file_name
        params['serverIdxList'] = server_idx_list
        params['serverInfo'] = json.dumps(WEB_SERVER);
        params['folderType'] = folder_type

    return render_to_response('edit_online_file.html', RequestContext(request, params));

@login_required
def rename_online_file(request, project_id = 0, server_idx_list = ''):
    params = {
        'isSuccess': False
    }
    if project_id == 0 or server_idx_list.strip() == '':
        pass
    elif request.POST:
        try:
            parent_folder_path = request.POST.get('parent_folder_path')
            old_file_name = request.POST.get('old_file_name')
            new_file_name = request.POST.get('new_file_name')
            folder_type = request.POST.get('folder_type') or FTP_DEFAULT_FOLDER_TYPE
            server_idx_arr = server_idx_list.split('_')
            project = Project.objects.get(pk = project_id)
            result_msg_arr = ['对文件 [ ' + str(old_file_name) + ' ] 的重命名结果:\n']
            for idx in server_idx_arr:
                flag = rename_file_on_ftp(
                    parent_folder_path = parent_folder_path, 
                    old_file_name = old_file_name, 
                    new_file_name = new_file_name,
                    project = project, server_idx = idx,
                    folder_type = folder_type)
                
                result_msg_arr.append(WEB_SERVER[project.name][int(idx)] + (flag and ' 重命名成功!' or ' 重命名失败!'))
            result_msg = '\n'.join(result_msg_arr)
            params['isSuccess'] = True
            params['resultMsg'] = result_msg
        except:
            pass
    
    return HttpResponse(json.dumps(params))

@login_required
def backup_online_file(request, project_id = 0, server_idx_list = ''):
    params = {
        'isSuccess': False
    }
    if project_id == 0 or server_idx_list.strip() == '':
        pass
    elif request.POST:
        try:
            parent_folder_path = request.POST.get('parent_folder_path')
            file_name = request.POST.get('file_name')
            folder_type = request.POST.get('folder_type') or FTP_DEFAULT_FOLDER_TYPE
            ts = unicode(int(time.time() * 1000))
            backup_file_name = file_name + '.' + ts + '.bak'
            server_idx_arr = server_idx_list.split('_')
            project = Project.objects.get(pk = project_id)
            result_msg_arr = ['对文件 [ ' + str(file_name) + ' ] 的备份结果:\n']
            for idx in server_idx_arr:
                flag = backup_file_on_ftp(parent_folder_path = parent_folder_path,
                    file_name = file_name,
                    backup_file_name = backup_file_name,
                    project = project,
                    server_idx = idx,
                    folder_type = folder_type)
                
                result_msg_arr.append(WEB_SERVER[project.name][int(idx)] + (flag and ' 备份成功!' or ' 备份失败!'))
            result_msg_arr.append('备份文件的文件名为 [' + str(backup_file_name) + ' ]')
            result_msg = '\n'.join(result_msg_arr)
            params['isSuccess'] = True
            params['resultMsg'] = result_msg
        except:
            pass
        
    return HttpResponse(json.dumps(params))

@login_required
def save_file_from_online_editor(request, project_id = 0, server_idx_list = ''):
    params = {
        'isSuccess': False
    }
    if project_id == 0 or server_idx_list.strip() == '':
        pass
    elif request.POST:
        try:
            file_path = request.POST.get('file_path')
            file_name = request.POST.get('file_name')
            folder_type = request.POST.get('folder_type') or FTP_DEFAULT_FOLDER_TYPE
            file_content = request.POST.get('file_content').encode('utf8')
            server_idx_arr = server_idx_list.split('_')
            project = Project.objects.get(pk = project_id)
            localpath = write_content_to_localfile(file_content = file_content, file_name = file_name)
            result_msg_arr = ['对文件 [ ' + str(file_name) + ' ] 的保存结果:\n']
            for idx in server_idx_arr:
                flag = upload_file_to_ftp(local_file_path = localpath, 
                    ftp_file_path = file_path, 
                    project = project, 
                    server_idx = idx, 
                    overwrite = True, 
                    folder_type = folder_type)
                
                result_msg_arr.append(WEB_SERVER[project.name][int(idx)] + (flag and ' 保存成功!' or ' 保存失败!'))
            result_msg = '\n'.join(result_msg_arr)
            params['isSuccess'] = True
            params['resultMsg'] = result_msg
        except:
            pass
    
    return HttpResponse(json.dumps(params));

###################
###-补丁组相关功能-###
###################

@login_required
def patch_group_list_page(request, page_num=1):
    projects = Project.objects.all()
    conditions = []
    query_params = {}
    num_per_page = 20
    
    if request.POST:
        creator_name = request.POST.get('creatorName')
        if creator_name:
            query_params['creatorName'] = creator_name
            conditions.append(Q(creator__username__icontains = creator_name))
        proj_id = request.POST.get('project')
        if proj_id and proj_id != '0':
            query_params['project'] = proj_id
            conditions.append(Q(project__id = proj_id))
        status = request.POST.get('status')
        if status:
            query_params['status'] = status
            conditions.append(Q(status = status))
        patch_group_name = request.POST.get('patchGroupName')
        if patch_group_name:
            query_params['patchGroupName'] = patch_group_name
            conditions.append(Q(name = patch_group_name))
    query_result = PatchGroup.objects.filter(*conditions).order_by('-id')
    paged_result = Paginator(query_result, num_per_page);
    patch_groups = paged_result.page(page_num)
    for patch_group in patch_groups:
        patch_group.formated_create_time = patch_group.create_time.strftime('%Y-%m-%d %H:%M:%S')
        if patch_group.finish_time:
            patch_group.formated_finish_time = patch_group.finish_time.strftime('%Y-%m-%d %H:%M:%S')
    
    query_params['curPage'] = page_num
    query_params['numPerPage'] = num_per_page
    query_params['totalPage'] = paged_result.num_pages
    params = RequestContext(request, {
        'projects': projects,
        'patch_groups': patch_groups,
        'query_params': query_params,
    })
    return render_to_response('patch_group_list_page.html', params) 

def patch_group_detail_page(request, patch_group_id):
    patch_group = PatchGroup.objects.get(pk = patch_group_id)
    patch_group.formated_create_time = patch_group.create_time \
        and patch_group.create_time.strftime('%Y-%m-%d %H:%M:%S') \
        or None
    patch_group.formated_finish_time = patch_group.finish_time \
        and patch_group.finish_time.strftime('%Y-%m-%d %H:%M:%S') \
        or None
    
    # 还要查询冲突信息
    patch_group_conflict_file_list = _find_patch_group_conflict_file_list(patch_group.id)
    
    params = RequestContext(request, {
        'patch_group': patch_group,
        'patch_group_conflict_file_list': patch_group_conflict_file_list,
    })
    return render_to_response('patch_group_detail_page.html', params)



def _find_patch_group_conflict_file_list(related_patch_group_id = 0):
    patch_group_conflict_file_list = []
    sql = """
        SELECT 
            distinct ci.conflict_patch_group_id, 
            pg.name AS conflict_patch_group_name,
            ci.conflict_patch_file_id,
            pf.file_path AS conflict_patch_file_path,
            pf.file_type AS conflict_patch_file_type
        FROM dpl_conflict_info AS ci,  
            dpl_patch_group AS pg,
            dpl_patch_file AS pf
        WHERE ci.related_patch_group_id = %d
            AND ci.conflict_patch_group_id = pg.id
            AND ci.conflict_patch_file_id = pf.id
            AND pg.status = 'testing'
    """ % (related_patch_group_id)
    cursor = connection.cursor()
    cursor.execute(sql)
    for row in cursor.fetchall():
        patch_group_conflict_file_list.append({
            'conflict_patch_group_id': row[0],
            'conflict_patch_group_name': row[1],
            'conflict_patch_file_id': row[2],
            'conflict_patch_file_path': row[3],
            'conflict_patch_file_type': row[4],
        })
    return patch_group_conflict_file_list

@login_required
def save_or_update_patch_group(request, patch_group_id = 0):
    patch_group_id = int(patch_group_id)
    patch_group = PatchGroup()
    has_authority = True
    if patch_group_id > 0:
        patch_group = PatchGroup.objects.get(pk = patch_group_id)
        ## 判断是否是本人或者管理员
        if patch_group.creator.id != request.user.id \
                and not request.user.is_superuser:
            has_authority = False
    if request.POST:
        if not has_authority:
            return HttpResponse(json.dumps({
                'isSuccess': False
            }))
        project_id = int(request.POST.get('project_id'))
        project = Project.objects.get(pk = project_id)
        if patch_group_id == 0:
            patch_group = PatchGroup(
                creator = request.user,
                project = project,
                create_time = datetime.now(),
            )
        patch_group.name = request.POST.get('name')
        patch_group.check_code = request.POST.get('check_code')
        patch_group.status = request.POST.get('status')
        patch_group.save()
        params = {
            'isSuccess': True,
        }
        return HttpResponse(json.dumps(params))
    ## get的情形
    params = RequestContext(request, {
        'patch_group': patch_group,
        'has_authority': has_authority,
    })
    return render_to_response('save_or_update_patch_group_page.html', params)

# 根据条件来获取补丁组
@login_required
def query_patch_groups(request):
    project_id = request.GET.get('project_id')
    status = request.GET.get('status')
    query_result = _query_patch_groups(project_id = project_id, status = status)
    patch_groups = [];
    for patch_group in query_result:
        patch_groups.append({
            'id': patch_group.id,
            'name': patch_group.name,
            'check_code': patch_group.check_code,
            'project_id': patch_group.project.id,
            'project_name': patch_group.project.name,
            'creator_id': patch_group.creator.id,
        })
    params = {
        'isSuccess': True,
        'count': len(patch_groups),
        'patchGroups': patch_groups,
    }
    return HttpResponse(json.dumps(params))

def _query_patch_groups(project_id, status):
    conditions = []
    if project_id is not None:
        conditions.append(Q(project__id = project_id))
    if status is not None:
        conditions.append(Q(status = status))
    return PatchGroup.objects.filter(*conditions).order_by('-id')

# 查看backup服务器上是否有新的备份源
@login_required
def get_new_backup_source_list(request):
    try:
        return HttpResponse(json.dumps({
            'isSuccess': True,
            'new_backup_source_list': _get_new_backup_source_list(),
        }))
    except:
        return  HttpResponse(json.dumps({
            'isSuccess': False,
            'errorMsg': '未能成功链接备份源的服务器!',
        }))
        
def _get_latest_new_backup_source_tuple():
    source_list = _get_new_backup_source_list()
    latest_ajaxablesky_source = None
    latest_static_source = None
    # 从已排序的文件名中找出最新的源
    for filename in source_list:
        if latest_ajaxablesky_source and latest_static_source:
            break
        if latest_ajaxablesky_source is None and filename.find('ajaxablesky') >= 0:
            latest_ajaxablesky_source = filename
            continue
        if latest_static_source is None and filename.find('static') >= 0:
            latest_static_source = filename
            continue
    return (latest_ajaxablesky_source, latest_static_source)
            
        

def _get_new_backup_source_list():
    conn = SimpleConnector(server_address = BACKUP_SERVER_IP)
    if not conn.connect():
        raise Exception('failed to connect the backup source server!')
    conn.sftp.chdir(path = BACKUP_ROOT_PATH + 'www-baseline/compress/')
    try:
        file_list = conn.sftp.listdir(path = '.')
    finally:
        conn.disconnect()
    new_backup_source_list = []
    cur_static_ts, cur_ajaxablesky_ts = _get_reset_ts_tuple()
    if file_list and len(file_list):
        for file_name in file_list:
            cur_ts = file_name.find(ResetInfo.TYPE_STATIC) >= 0 and cur_static_ts or cur_ajaxablesky_ts
            if not _is_new_backup_source(file_name, cur_ts, '.tar.gz'):
                continue
            new_backup_source_list.append(file_name)
    start_pos, end_pos = -21, -7 # 时间戳在文件名中的位置
    new_backup_source_list.sort(
        cmp = lambda n1, n2: cmp(n1[start_pos: end_pos], n2[start_pos: end_pos]), 
        key = None, 
        reverse = True
    )
    return new_backup_source_list

def _get_reset_ts_tuple():
    default_ts = '19000101235959'
    try:
        # 一个也没有的时候会报错，实在不清楚django下这种情况怎么处理
        cur_static_ts = ResetInfo.objects.filter(reset_type__exact = ResetInfo.TYPE_STATIC, is_ignored = 0).order_by('-reset_time')[0].reset_source_ts
    except:
        cur_static_ts = default_ts
    try:
        cur_ajaxablesky_ts = ResetInfo.objects.filter(reset_type__exact = ResetInfo.TYPE_AJAXABLESKY, is_ignored = 0).order_by('-reset_time')[0].reset_source_ts
    except:
        cur_ajaxablesky_ts = default_ts
    return (cur_static_ts, cur_ajaxablesky_ts)

def _is_new_backup_source(file_name, cur_ts, file_suffix):
    if not file_name or not cur_ts or not file_suffix:
        return False
    ts_len = len(cur_ts)
    end_pos = file_name.rfind(file_suffix)
    if end_pos < ts_len:
        return False
    ts = file_name[end_pos - ts_len: end_pos]
    if ts <= cur_ts:
        return False
    return True

# 从公共本分源所在的服务器上向当前测试环境拷贝备份源
@login_required
def obtain_reset_item(request):
    if not request.POST:
        return HttpResponse(json.dumps({
            'isSuccess': False,
            'errorMsg': '必须用表单提交',
        }))
    proj_id = request.POST.get('projId')
    record_id = request.POST.get('recordId')
    version = string.strip(request.POST.get('version') or '')
    source_filename = request.POST.get('sourceFilename')

    cur_static_ts, cur_ajaxablesky_ts = _get_reset_ts_tuple()
    cur_ts = source_filename.find(ResetInfo.TYPE_STATIC) >= 0 and cur_static_ts or cur_ajaxablesky_ts
    if not _is_new_backup_source(source_filename, cur_ts, '.tar.gz'):
        return HttpResponse(json.dumps({
            'isSuccess': False,
            'errorMsg': '备份源 [ ' + source_filename  + ' ] 版本过旧!',
        }))
    
    conn = SimpleConnector(server_address = BACKUP_SERVER_IP)
    if not conn.connect():
        return HttpResponse(json.dump({
            'isSuccess': False,
            'errorMsg': '未能成功连接备份源的服务器!',
        }))
    
    local_folderpath = DPL_BACKUP_SOURCE_LOCAL_DIR
    local_source_path = local_folderpath + source_filename  # 本地文件源路径
    if not os.path.isdir(local_folderpath):
        os.makedirs(local_folderpath)
    # 清除文件夹中的原有内容
    for filename in os.listdir(local_folderpath):
        try:
            os.remove(local_folderpath + filename)
        except:
            pass    # 理论上不会沦落到这一行
        
    conn.sftp.chdir(path = BACKUP_ROOT_PATH + 'www-baseline/compress/')
    try: 
        conn.sftp.get(source_filename, local_source_path)
    except: 
        return HttpResponse(json.dumps({
            'isSuccess': False,
            'errorMsg': '未能成功获取备份源!'
        }))
    finally: 
        conn.disconnect()
    
    project = Project.objects.get(pk = proj_id)
    
    items = DeployItem.objects.filter(file_name__exact = source_filename, version__exact = version)
    item = (items and len(items) > 0) and items[0] or None
    now_time = datetime.now()
    if not item: 
        item = DeployItem(
            user = request.user,
            project = project,
            version = version,
            deploy_type = DeployItem.RESET,
            file_name = source_filename,
            folder_path = local_folderpath,
            create_time = now_time,
            update_time = now_time,
        )
    else: 
        item.updte_time = now_time
    item.save()
    
    record = DeployRecord.objects.get(pk = record_id)
    if record:
        record.status = DeployRecord.UPLOADED
        record.deploy_item = item
        record.save()
        
    return HttpResponse(json.dumps({
        'isSuccess': True,
        'message': '源文件获取成功!',
        'filename': source_filename,
        'size': os.path.getsize(local_source_path),
    }))

@login_required
def read_file_size(request):
    filepath = request.GET.get('filepath')
    if not filepath or not os.path.exists(filepath):
        return HttpResponse(json.dumps({
            'isSuccess': False,
            'errorMsg': '文件路径有误或文件不存在!'
        }))
    return HttpResponse(json.dumps({
        'isSuccess': True,
        'filepath': filepath,
        'size': os.path.getsize(filepath)
    }))

@login_required
def ignore_reset_record(request):    
    record_id = int(request.POST.get('recordId')) or 0
    if not record_id:
        return HttpResponse(json.dumps({
            'isSuccess': False,
            'errorMsg': 'record_id有误!',
        }))
    try: 
        record = DeployRecord.objects.get(id = record_id)
        record.status = DeployRecord.RESET_IGNORED
        reset_info = ResetInfo.objects.get(deploy_record__id = record_id)
        reset_info.is_ignored = True
        reset_info.save()
        record.save()
    except:
        return HttpResponse(json.dumps({
            'isSuccess': False,
            'errorMsg': '相关数据有误!',
        }))
    
    return HttpResponse(json.dumps({
        'isSuccess': True
    }))
