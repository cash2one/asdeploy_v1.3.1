#coding:utf-8

import os
import threading
import string

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
        status_key = 'log_is_writing_' + record_id_str
        deploy_result_key = 'deploy_result_' + record_id_str
        cache.set(status_key, True, 7200)
        if self.direct == 'deploy':
            flag = _deploy_item(self.item)
        elif self.direct == 'rollback':
            flag = _rollback_item(self.item)
        else:
            flag = False;
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

if __name__ == '__main__':
    pass
