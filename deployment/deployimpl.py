#coding:utf-8

import os
import threading
import string
from datetime import datetime

from django.core.cache import cache

from deployment.models import *
from deployment.deploysetting import *

class Deployer(threading.Thread):
    def __init__(self, record, direct='deploy'):
        threading.Thread.__init__(self)
        self.record = record
        self.item = record.deploy_item
        self.direct = direct
    
    def run(self):
        record_id_str = unicode(self.record.id)
        # 向缓存中添加本次发布的信息
        status_key = 'log_is_writing_' + record_id_str
        deploy_result_key = 'deploy_result_' + record_id_str
        cache.set(status_key, True, 7200)
        
        #执行发布操作 
        flag = ({
            'deploy': _deploy_item,
            'rollback': _rollback_item,
            'backup': _backup_item,
            'reset': _reset_item,
         }.get(self.direct) or (lambda x: False) )(self.item)
        
        # 更新DeployRecord的状态字段
        self.record.status = ({
            'deploy': flag and DeployRecord.SUCCESS or DeployRecord.FAILURE,
            'rollback': flag and DeployRecord.ROLLBACK or DeployRecord.ROLLBACK_FAILURE,
            'backup': flag and DeployRecord.BACKUP_SUCCESS or DeployRecord.BACKUP_FAILURE,
            'reset': flag and DeployRecord.RESET_SUCCESS or DeployRecord.RESET_FAILURE,
        }.get(self.direct) or 'unknown')
        self.record.save()
        
        # 从缓存中删除此次的发布信息
        cache.set(deploy_result_key, flag)
        cache.delete(status_key)
        set_server_group(None)
        

# 标识当前发布的无宕机服务器分组
cur_server_group = None

def set_server_group(server_group=None):
    global cur_server_group
    cur_server_group = server_group
    
def get_server_group():
    return cur_server_group

# 获取文件上传存储的路径
def get_target_folder(proj_name, version):
    return ITEM_ROOT_PATH + proj_name + '-' + version + '/'

def _rollback_item(item):
    if item.deploy_type != DeployItem.PATCH:
        return False;
    return _rollback_patch(item)

def _rollback_patch(item):
    item_name = trim_compress_suffix(item.file_name)
    item_name = string.replace(item_name, '-todo', '-bakup')
    sh_path = _get_patch_sh_path_by_item(item)
    sh_param = ITEM_ROOT_PATH + item.project.name + '-' + item.version + '/' + item_name
    sh_param += NEED_SEND_EMAIL and ' y ' or ' n '
    if get_server_group():
        sh_param += ' ' + get_server_group() + ' '
    sh_command = 'sh ' + sh_path + ' ' + sh_param + ' > ' + DEPLOY_LOG_PATH
    flag = os.system(sh_command)
    return flag == 0


# 本质上reset的item会是空的，所以有可能需要单写
def _reset_item(item):
    if item.deploy_type != DeployItem.WAR:
        return False
    flag = _reset_war(item)
    return flag

def _reset_war(item):   # 其实是tar包
    shell_path = _get_reset_shell_path()
    remote_temp_dir = FOLDER_ROOT + '/reset-temp/'
    if not os.path.exists(remote_temp_dir) :
        os.makedirs(remote_temp_dir)
    shell_params = [
        LANIP,
        _get_war_sh_path_by_item(item),
        remote_temp_dir,
    ]
    sh_command = 'ssh ' + BACKUP_SERVER_IP + ' ' + shell_path + ' ' + ' '.join(shell_params) + ' > ' + DEPLOY_LOG_PATH
    flag = os.system(sh_command)
    return flag == 0
    

def _backup_item(item):
    if item.deploy_type != DeployItem.PATCH:
        return False
    flag = _backup_patch(item)
    if flag and item.patch_group:
        patch_group = item.patch_group
        patch_group.status = PatchGroup.STATUS_FINISHED
        patch_group.finish_time = datetime.now()
        patch_group.save()  # 发布成功后修改patch_group的状态为finish
    return flag

def _backup_patch(item):
    item_name = trim_compress_suffix(item.file_name)
    shell_path = _get_backup_shell_path()
    # shell脚本的参数为 ip 补丁路径 发布环境
    shell_params = [
        LANIP,
        ITEM_ROOT_PATH + item.project.name + '-' + item.version + '/' + item_name,
        ENVIRONMENT,
    ]
    sh_command = 'ssh ' + BACKUP_SERVER_IP + ' ' + shell_path + ' ' + ' '.join(shell_params) + ' > ' + DEPLOY_LOG_PATH
    flag = os.system(sh_command)
    return flag == 0

# backup和reset的发布本质上可以跟以前的代码整合在一起的
# 但是需要以前的代码改为ssh访问脚本，需要重构
# 目前暂时先不改了，等需求进一步稳定后再重构吧
def _deploy_item(item):
    flag = False
    if not item:
        return False;
    
    if item.deploy_type == DeployItem.WAR:
        flag = _deploy_war(item)
    elif item.deploy_type == DeployItem.PATCH:
        flag = _deploy_patch(item)
    else:
        return False
    return flag

def _deploy_war(item):
    sh_path = _get_war_sh_path_by_item(item);
    sh_param = item.project.name + '-' + item.version
    #sh_param += NEED_SEND_EMAIL and ' y ' or ' n '
    # fix the bad logic in the future
    if get_server_group():
        if 'ab' == get_server_group():
            sh_command = 'sh ' + sh_path + ' ' + sh_param + ' a > ' + DEPLOY_LOG_PATH
            sh_command += '; sh ' + sh_path + ' ' + sh_param + ' b > ' + DEPLOY_LOG_PATH
        else:
            sh_param += ' ' + get_server_group() + ' '
            sh_command = 'sh ' + sh_path + ' ' + sh_param + ' > ' + DEPLOY_LOG_PATH
    else:
        sh_command = 'sh ' + sh_path + ' ' + sh_param + ' > ' + DEPLOY_LOG_PATH
    flag = os.system(sh_command)
    return flag == 0

def _get_war_sh_path_by_item(item):
    name = item.project.name + '-deploy'
    return SHELL_ROOT_PATH + name + '/' + name + '.sh'

def _deploy_patch(item):
    item_name = item.file_name
    item_name = trim_compress_suffix(item_name)
    sh_path = _get_patch_sh_path_by_item(item)
    sh_param = ITEM_ROOT_PATH + item.project.name + '-' + item.version + '/' + item_name
    sh_param += NEED_SEND_EMAIL and ' y ' or ' n '
    if get_server_group():
        sh_param += ' ' + get_server_group() + ' '
    sh_command = 'sh ' + sh_path + ' ' + sh_param + ' > ' + DEPLOY_LOG_PATH
    flag = os.system(sh_command)
    return flag == 0

def _get_patch_sh_path_by_item(item):
    return SHELL_ROOT_PATH + 'patch-shell/start_patch_main.sh'

def trim_compress_suffix(filename):
    if not filename or len(filename) == 0:
        return filename
    filename = filename.lower()
    rindex = filename.rindex('.zip')
    if rindex > 0:
        filename = filename[:rindex]
    return filename

def _get_backup_shell_path():
    return BACKUP_ROOT_PATH + 'shell/main.sh'

def _get_reset_shell_path():
    return BACKUP_ROOT_PATH + 'shell/reset.sh'

if __name__ == '__main__':
    pass
