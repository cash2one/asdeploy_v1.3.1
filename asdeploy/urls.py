#coding:utf-8

import os.path

from django.conf.urls import patterns, include, url
from django.views.generic.simple import direct_to_template
from deployment.views import *


# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

static_files = os.path.join(
    os.path.dirname(__file__), '../deployment/static_files'
)

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    
    #静态文件路径
    (r'^static_files/(?P<path>.*)$', 'django.views.static.serve', {'document_root': static_files}),
    
    #页面路径
    (r'^checkVersionAndEnv/$', check_version_and_env),
    (r'^login/$', 'django.contrib.auth.views.login'),
    (r'^logout/$', logout_page),
    (r'^register/$', register_page),
    (r'^register/success/$', direct_to_template,
         {'template': 'registration/register_success.html'}),
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    
    (r'^$', main_page),
    (r'^user/(\w+)/$', user_page),
    (r'^unlockDeploy/$', unlock_deploy),
    
    (r'^deployInitOption/$', deploy_init_option_page),
    (r'^uploadDeployItem/$', upload_deploy_item),
    (r'^uploadReadme/$', upload_readme),
    
    (r'^decompressItem/$', decompress_item),    #解压补丁
    (r'^startDeploy/$', start_deploy),          #发布按钮
    (r'^startRollback/$', start_rollback),       #回滚按钮
    (r'^readDeployLogOnRealtime/$', read_deploy_log_on_realtime), #发布过程中实时查询日志文件
    
    (r'^deployRecordList/(?P<page_num>\d+)/$', deploy_record_list_page),
    (r'^deployRecordDetail/(?P<record_id>\d+)/$', deploy_record_detail_page),
    
    # 补丁组相关功能
    (r'^patchGroupList/(?P<page_num>\d+)/$', patch_group_list_page),
    (r'^patchGroupDetail/(?P<patch_group_id>\d+)/$', patch_group_detail_page),
    
    (r'^saveOrUpdatePatchGroup/(?P<patch_group_id>\d+)/$', save_or_update_patch_group),
    (r'^queryPatchGroups/', query_patch_groups),
    
    #检查硬盘挂载情况
    (r'^checkServerStatusForProject/(?P<project_name>[\w-]+)/$', check_server_status_for_project),
    
    #展示和下载线上文件
    (r'^getProjectFileNodes/(?P<project_id>\d+)/(?P<server_idx>\d+)/(?P<node_id>\w+)/$', get_project_file_nodes),
    (r'^downloadProjectFile/(?P<project_id>\d+)/(?P<server_idx>\d+)/$', download_project_file),
    #在线编辑文件
    (r'^showOnlineFile/$', show_online_file),
    (r'^openOnlineFile/(?P<project_id>\d+)/(?P<server_idx_list>[\d_]+)/$', open_online_file),
    (r'^renameOnlineFile/(?P<project_id>\d+)/(?P<server_idx_list>[\d_]+)/$', rename_online_file),
    (r'^backupOnlineFile/(?P<project_id>\d+)/(?P<server_idx_list>[\d_]+)/$', backup_online_file),
    (r'^saveFileFromOnlineEditor/(?P<project_id>\d+)/(?P<server_idx_list>[\d_]+)/$', save_file_from_online_editor),

)
