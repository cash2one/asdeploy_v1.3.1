#coding:utf-8

import os
import re

def get_hostname():
    syst = os.name
    if syst == 'nt':
        return os.getenv('computername')
    elif syst == 'posix':
        host = os.popen('echo $HOSTNAME')
        try:
            hostname = host.read().replace('\n', '')
            return hostname
        finally:
            host.close()
    else:
        return 'Unknown Hostname'

def get_lan_ip_address():
    lan_info = os.popen("ifconfig").read()
    ip_re = re.compile(r'inet.*?\:(192.168(?:\.\d{1,3}){2})')
    m = ip_re.search(lan_info)
    if not m or not len(m.groups()):
        return ''
    return m.groups()[0]

# 主机名称
HOSTNAME = get_hostname()
# 局域网IP
LANIP = get_lan_ip_address()

# 环境参数(重要) 依靠hostname来自动判断
# 点击logo，可弹出此文件配置的真实的环境信息。
ENVIRONMENT = 'error'
if HOSTNAME.find('.at1.') > 0:
    ENVIRONMENT = 'alpha'
elif HOSTNAME.find('.bt1.') > 0:
    ENVIRONMENT = 'beta'
elif HOSTNAME.find('.ot1.') > 0:
    ENVIRONMENT = 'omega'
else:
    ENVIRONMENT = 'localhost'

# 版本
VERSION = '1.3'

# 数据库信息
DB_PARAMS = {
    'alpha': {
        'host': '192.168.150.7',
        'username': 'root',
        'password': 'mysqlpwd1',
    },
    'beta': {
        'host': '192.168.3.50',
        'username': 'root',
        'password': 'mysqlpwd1',
    },
    'omega': {
        'host': '192.168.190.25',
        'username': 'root',
        'password': 'mysqlpwd1',
    },
    'localhost': {
        'host': '127.0.0.1',
        'username': 'root',
        'password': 'mysqlpwd1',
    },
}

DB_PARAM = DB_PARAMS[ENVIRONMENT]

# 服务器 信息，每个工程至少配置一个，localhost的server暂时先配成alpha的
WEB_SERVERS = {
    'alpha': {
        'as-web': ['web0.at1.ablesky.com'],
        'as-passport': ['passport0.at1.ablesky.com', 'passport1.at1.ablesky.com'],
        'as-search': ['se0.at1.ablesky.com'],
        'as-ad': ['ad0.at1.ablesky.com'],
        'as-im': ['im0.at1.ablesky.com'],
        'as-cms': ['memcms0.at1.ablesky.com'],
        'as-liveservice': ['liveservice0.at1.ablesky.com'],
    },
    'beta': {
        'as-web': ['web0.bt1.ablesky.com', 'web1.bt1.ablesky.com'],
        'as-passport': ['passport0.bt1.ablesky.com', 'passport1.bt1.ablesky.com'],
        'as-search': ['se0.bt1.ablesky.com', 'se1.bt1.ablesky.com'],
        'as-ad': ['ad0.bt1.ablesky.com'],
        'as-im': ['im0.bt1.ablesky.com', 'im1.bt1.ablesky.com'],
        'as-cms': ['memcms0.bt1.ablesky.com'],
        'as-liveservice': ['liveservice0.bt1.ablesky.com', 'liveservice1.bt1.ablesky.com'],
        'as-mobile': ['mobile1.bt1.ablesky.com'],
    },
    'omega': {
        'as-web': ['web0.ot1.ablesky.com', 'web1.ot1.ablesky.com'],
        'as-passport': ['passport0.ot1.ablesky.com', 'passport1.ot1.ablesky.com'],
        'as-search': ['se0.ot1.ablesky.com', 'se1.ot1.ablesky.com'],
        'as-ad': ['ad0.ot1.ablesky.com', 'ad1.ot1.ablesky.com'],
        'as-im': ['im0.ot1.ablesky.com', 'im1.ot1.ablesky.com'],
        'as-cms': ['memcms0.ot1.ablesky.com'],
        'as-liveservice': ['liveservice0.ot1.ablesky.com', 'liveservice1.ot1.ablesky.com'],
        'as-mobile': ['mobile1.ot1.ablesky.com']
    },    
    'localhost': {
        'as-web': ['web0.at1.ablesky.com'],
        'as-passport': ['passport0.at1.ablesky.com', 'passport1.at1.ablesky.com'],
        'as-search': ['se0.at1.ablesky.com'],
        'as-ad': ['ad0.at1.ablesky.com'],
        'as-im': ['im0.at1.ablesky.com'],
        'as-cms': ['cms0.at1.ablesky.com'],
    },
}

WEB_SERVER = WEB_SERVERS[ENVIRONMENT]

BACKUP_SERVER_IP = '192.168.190.18' # 公共备份发布脚本所在的服务器IP(目前omega的任意一台服务器都可以)

# 发布超时解锁时间(秒)，调用 _check_lock()的时候会去判断超时和解锁
LOCK_TIMEOUT_PERIOD = 3600 * 1.5

# 发布后是否发邮件
NEED_SEND_EMAIL = False

# 目录

FOLDER_ROOT = '/d/content/web-app-bak/'

ITEM_ROOT_PATH = FOLDER_ROOT + 'ableskyapps/'

SHELL_ROOT_PATH = FOLDER_ROOT + 'deployment/'

BACKUP_ROOT_PATH = FOLDER_ROOT + 'backup/'   # 补丁组完结的公共备份发布

BACKUP_SERVER_IP = '192.168.190.18'

DEPLOY_LOG_NAME = 'deploy.log'

DEPLOY_LOG_PATH = SHELL_ROOT_PATH + DEPLOY_LOG_NAME

# 文件上传的临时目录
DPL_FILE_UPLOAD_TEMP_DIR = '/d/content/web-app-bak/ableskyapps/tempuploads/'


# ftp运行目录

FPT_APACHE_ROOT_PATH = '/usr/share/apache-tomcat-7.0.11/'

FTP_APACHE_APPS_PATH = os.path.join(FPT_APACHE_ROOT_PATH, './ableskyapps/')

FTP_APACHE_CONF_PATH = os.path.join(FPT_APACHE_ROOT_PATH, './conf/')

FTP_LOCAL_DOWNLOAD_FILE_PATH = os.path.join(os.path.dirname(__file__), './download_file_folder/')

FTP_LOCAL_TEMP_FILE_PATH = os.path.join(os.path.dirname(__file__), './temp_file_folder/')

FTP_PORT = 22

FTP_USERNAME = 'root'

FTP_PASSWORD = 'ASdiyi'

FTP_DEFAULT_FOLDER_TYPE = FTP_APPS_FOLDER_TYPE = 'apps'    # apps or conf

FTP_CONF_FOLDER_TYPE = 'conf'
