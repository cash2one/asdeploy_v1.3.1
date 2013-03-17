#coding:utf-8

import os
import re
import logging

from deployment.deploysetting import *

logger = logging.getLogger(__name__)
disk_status_re = re.compile(r'.*?(?P<size>[\d\.]+\w)\s+(?P<used>[\d\.]+\w)\s+(?P<available>[\d\.]+\w)\s+(?P<used_percent>\d+%)')

def check_server_status(project_name):
    server_status = {
        'available': True,
        'servers': [],
    }
    try:
        target_servers = WEB_SERVER[project_name]
        if not target_servers or not isinstance(target_servers, list):
            server_status['available'] = False
            return server_status
        for server_name in target_servers:
            disk_info = check_content_disk(server_name)
            if disk_info['status'] == 'error':
                os.system("ssh " + server_name + " mount -a")
                logger.info("mount content disk for " + server_name)
                disk_info = check_content_disk(server_name)
            server_status['servers'].append(disk_info)
            if disk_info['status'] == 'error':
                server_status['available'] = False
        
        disk_info = check_content_disk(is_self = True)
        if disk_info['status'] == 'error':
            os.system('mount -a')
            logger.info("mount content disk for localhost")
            disk_info = check_content_disk(is_self = True)
        server_status['servers'].append(disk_info)
        if disk_info['status'] == 'error':
            server_status['available'] = False;
    except:
        server_status['available'] = False
    
    return server_status
    
# 检查指定服务器的硬盘的挂载情况
def check_content_disk(server_name = 'localhost', is_self = False):
    disk_info = {
        'status': 'error',
    }
    if is_self:
        server_name = 'localhost'
    if not server_name:
        return disk_info
    disk_info['server_name'] = server_name
    status_command = 'df -h'
    if not is_self:
        status_command = 'ssh ' + server_name + ' ' + status_command
    try:
        status_reader = os.popen(status_command)
        m = None
        while True:
            info = status_reader.readline()
            if not info:
                break;
            if info.find('/d/content') < 0:
                continue
            m = disk_status_re.match(info)
        status_reader.close()
        if not m:
            return disk_info
        disk_info['avail_space'] = m.group('available')
        try:
            avail_matcher = re.match(r'(?P<size>[\d\.]+)(?P<unit>\w)', disk_info['avail_space'])
            avail_size = float(avail_matcher.group('size'))
            avail_unit = avail_matcher.group('unit').upper()
        except:
            avail_size = 0
        
        if avail_size == 0:
            return disk_info
        
        # 检查下上传文件的临时目录。正常情况下如果访问不了，就说明挂载还是有问题
        folder_command = 'ls -d ' +  DPL_FILE_UPLOAD_TEMP_DIR
        if not is_self:
            folder_command = 'ssh ' + server_name + ' ' + folder_command
        flag = os.system(folder_command) == 0
        if not flag:
            return disk_info
        
        #--- 以上均为error的情形 ---#
        
        # 空间不足的情况
        
        if avail_unit in ['K', 'B'] or avail_size < 50 and avail_unit == 'M':
            disk_info['status'] = 'lackOfSpace'
            return disk_info
        
        disk_info['status'] = 'ok'
        return disk_info
    
    except:
        return disk_info