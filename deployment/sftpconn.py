#coding:utf-8

import os
import shutil
import time
import paramiko

from deployment.deploysetting import *

class SftpConnector(object):
    def __init__(self, project = None):
        if not project:
            return None
        self.project = project
        self.ssh = None
        self.sftp = None
        
    def connect(self, server_idx = 0):
        try:
            server_idx = int(server_idx)
        except:
            return False
        if not self.project:
            return False
        try:
            hostname = WEB_SERVER[self.project.name][server_idx]
            socks = (hostname,FTP_PORT)
            self.ssh = paramiko.Transport(socks)
            self.ssh.connect(username = FTP_USERNAME, password = FTP_PASSWORD)
            self.sftp = paramiko.SFTPClient.from_transport(self.ssh)
            return True
        except:
            return False
    
    def disconnect(self):
        try:
            self.sftp.close()
            self.ssh.close()
            return True
        except:
            return False

def get_dirlist_from_ftp(file_path = None, project = None, server_idx = -1, folder_type = FTP_DEFAULT_FOLDER_TYPE):
    if not project or server_idx == -1:
        return None
    if not file_path:
        file_path = ''
    conn = SftpConnector(project)
    if not conn:
        return None
    if not conn.connect(server_idx):
        return None
    root_dir = _get_root_dir(project = project, folder_type = folder_type)
    conn.sftp.chdir(path = root_dir + file_path)
    file_list = conn.sftp.listdir(path = '.')
    conn.disconnect()
    return file_list

def get_file_from_ftp(file_path = None, project = None, server_idx = -1, folder_type = FTP_DEFAULT_FOLDER_TYPE):
    if not file_path or not project or server_idx == -1:
        return None
    conn = SftpConnector(project)
    if not conn:
        return None
    if not conn.connect(server_idx):
        return None
    root_dir = _get_root_dir(project = project, folder_type = folder_type)
    
    # 当日下载目录
    sub_folder_name = time.strftime('%Y%m%d') + '/'
    local_download_file_folder = FTP_LOCAL_DOWNLOAD_FILE_PATH + sub_folder_name
    if not os.path.isdir(local_download_file_folder):
        os.makedirs(local_download_file_folder)
    
    # 清除掉非当日的目录及文件
    sub_folder_list = os.listdir(FTP_LOCAL_DOWNLOAD_FILE_PATH)
    for f in sub_folder_list:
        if f == sub_folder_name[:-1]:
            continue
        shutil.rmtree(FTP_LOCAL_DOWNLOAD_FILE_PATH + f)
    
    # 带时间戳的文件名
    file_name = file_path.split('/')[-1]
    ts = unicode(int(time.time() * 1000))
    localpath = os.path.join(local_download_file_folder, ts + '_' + file_name)
    
    conn.sftp.get(remotepath = root_dir + file_path, localpath = localpath)
    conn.disconnect()
    return localpath

def write_content_to_localfile(file_content = None, file_name = None):
    sub_folder_name = time.strftime('%Y%m%d') + '/'
    local_temp_file_folder = FTP_LOCAL_TEMP_FILE_PATH + sub_folder_name
    if not os.path.isdir(local_temp_file_folder):
        os.makedirs(local_temp_file_folder)
        
    # 清除掉非当日的目录及文件, so don't use this at 24 clock
    sub_folder_list = os.listdir(FTP_LOCAL_DOWNLOAD_FILE_PATH)
    for f in sub_folder_list:
        if f == sub_folder_name[:-1]:
            continue
        shutil.rmtree(FTP_LOCAL_TEMP_FILE_PATH + f)
        
    ts = unicode(int(time.time() * 1000))
    localpath = os.path.join(local_temp_file_folder, ts + '_' + file_name)
    f = open(localpath, 'w')
    f.write(file_content)
    f.close()
    return localpath

def upload_file_to_ftp(local_file_path = None, 
        ftp_file_path = None, 
        project = None, 
        server_idx = -1, 
        overwrite = False, 
        folder_type = FTP_DEFAULT_FOLDER_TYPE):
    
    if not local_file_path or not ftp_file_path or not project or server_idx == -1:
        return False
    if not os.path.isfile(local_file_path):
        return False
    conn = SftpConnector(project)
    if not conn.connect(server_idx):
        return False
    try:
        root_dir = _get_root_dir(project = project, folder_type = folder_type)
        conn.sftp.put(localpath = local_file_path, remotepath = root_dir + ftp_file_path, confirm = False)
        return True
    except:
        return False
    finally:
        conn.disconnect()

def rename_file_on_ftp(parent_folder_path = None, 
        old_file_name = None, 
        new_file_name = None, 
        project = None, 
        server_idx = -1, 
        folder_type = FTP_DEFAULT_FOLDER_TYPE):
    
    if not old_file_name or not new_file_name or parent_folder_path == None or not project or server_idx == -1:
        return False;
    
    conn = SftpConnector(project)
    if not conn.connect(server_idx):
        return False
    try:
        root_dir = _get_root_dir(project = project, folder_type = folder_type)
        parent_full_path = root_dir + parent_folder_path + '/'
        oldpath = parent_full_path + old_file_name
        newpath = parent_full_path + new_file_name
        # 是否与现有文件重名
        file_list = conn.sftp.listdir(path = parent_full_path)
        if new_file_name in file_list:
            return False
        conn.sftp.rename(oldpath = oldpath, newpath = newpath)
        return True
    except:
        return False
    finally:
        conn.disconnect()

# 备份文件
def backup_file_on_ftp(parent_folder_path = None, 
        file_name = None, 
        backup_file_name = None, 
        project = None, 
        server_idx = -1, 
        folder_type = FTP_DEFAULT_FOLDER_TYPE):
    
    if not file_name or not backup_file_name or parent_folder_path == None or not project or server_idx == -1:
        return False;
    conn = SftpConnector(project)
    if not conn.connect(server_idx):
        return False
    try:
        root_dir = _get_root_dir(project = project, folder_type = folder_type)
        parent_full_path = root_dir + parent_folder_path + '/'
        file_full_path = parent_full_path + file_name
        backup_file_full_path = parent_full_path + backup_file_name
        file_list = conn.sftp.listdir(path = parent_full_path)
        if backup_file_name in file_list:
            return False
        sub_folder_name = time.strftime('%Y%m%d') + '/'
        
        # donwload online file
        local_download_file_folder = FTP_LOCAL_DOWNLOAD_FILE_PATH + sub_folder_name
        if not os.path.isdir(local_download_file_folder):
            os.makedirs(local_download_file_folder)
        
        ts = unicode(int(time.time() * 1000))
        localpath = os.path.join(local_download_file_folder, ts + '_' + file_name)
        conn.sftp.get(remotepath = file_full_path, localpath = localpath)
        
        # upload the file with its backup name
        conn.sftp.put(localpath = localpath, remotepath = backup_file_full_path)
        return True
    except:
        return False
    finally:
        conn.disconnect()

def _get_root_dir(project = None, folder_type = FTP_DEFAULT_FOLDER_TYPE):
    if folder_type == FTP_CONF_FOLDER_TYPE:
        return FTP_APACHE_CONF_PATH
    elif folder_type == FTP_APPS_FOLDER_TYPE:
        if project is None:
            return FTP_APACHE_APPS_PATH
        else:
            return FTP_APACHE_APPS_PATH + project.war_name