#coding:utf-8

from django.db import models

from django.contrib.auth.models import User

class Project(models.Model):
    name = models.CharField(max_length = 30)
    war_name = models.CharField(max_length = 30)
    
    def __unicode__(self):
        return '[' + self.name + ']';
    
    class Meta:
        db_table = 'dpl_project'


class DeployItem(models.Model):
    WAR = 'war'
    PATCH = 'patch'

    user = models.ForeignKey(User)
    project = models.ForeignKey(Project)
    version = models.CharField(max_length = 11)
    deploy_type = models.CharField(max_length=15)
    file_name = models.CharField(max_length = 100)
    folder_path = models.CharField(max_length = 512, null = True)
    create_time = models.DateTimeField()
    update_time = models.DateTimeField(null = True)
    
    def __unicode__(self):
        return '[' + self.file_name + '|' + self.version + ']'
    
    class Meta:
        db_table = 'dpl_deployitem'


class DeployRecord(models.Model):
    PREPARE = 'prepare'
    UPLOADED = 'uploaded'
    DEPLOYING = 'deploying'
    SUCCESS = 'success'
    FAILURE = 'failure'
    ROLLBACKING = 'rollbacking'
    ROLLBACK = 'rollback'
    
    user = models.ForeignKey(User)
    project = models.ForeignKey(Project)
    deploy_item = models.ForeignKey(DeployItem, null = True)
    create_time = models.DateTimeField()
    status = models.CharField(max_length = 15)
    conflict_detail = models.ForeignKey('ConflictDetail', null = True)
    
    class Meta:
        db_table = 'dpl_deployrecord'
    
    
class DeployLock(models.Model):
    user = models.ForeignKey(User)
    deploy_record = models.ForeignKey(DeployRecord)
    is_locked = models.BooleanField(default = False)
    locked_time = models.DateTimeField()
    
    class Meta:
        db_table = 'dpl_deploylock'
        

### 补丁分组，目前仅应用与网站
class PatchFile(models.Model):
    TYPE_DYNAMIC = "dynamic"
    TYPE_STATIC = "static"
    
    file_path = models.CharField(max_length = 196, unique = True)
    file_type = models.CharField(max_length = 10)        # 补丁文件的类型，发静态服务器的文件为static，其他均为dynamic
    
    class Meta:
        db_table = 'dpl_patch_file'

class PatchGroup(models.Model):
    STATUS_TEST = "test"
    STATUS_FINISH = "finish"
    STATUS_STOP = "stop"
    
    creator = models.ForeignKey(User)
    project = models.ForeignKey(Project)            # 目前只能是web
    name = models.CharField(max_length = 20)
    check_code = models.CharField(max_length = 10)  # 组内的补丁在目录名中必须包含相应的标识码
    status = models.CharField(max_length = 20)
    create_time = models.DateTimeField()
    finish_time = models.DateTimeField(null = True)
    patch_files = models.ManyToManyField(PatchFile, through='PatchFileRelGroup')
    
    class Meta:
        db_table = 'dpl_patch_group'

# 补丁文件与补丁组之间的关连
class PatchFileRelGroup(models.Model):
    patch_group = models.ForeignKey(PatchGroup)
    patch_file = models.ForeignKey(PatchFile)
    create_time = models.DateTimeField()
    is_conflict_excluded = models.BooleanField(default = False)
    
    class Meta:
        db_table = 'dpl_patch_file_rel_group'
        
class ConflictInfo(models.Model):
    conflict_patch_group = models.ForeignKey(PatchGroup)
    conflict_patch_file = models.ForeignKey(PatchFile)
    is_excluded_conflict = models.BooleanField(default = False) # 是否是与例外文件之间的冲突
    
    class Meta:
        db_table = 'dpl_conflict_info'

# DeployRecord与ConflictDetail之间1对0或1
class ConflictDetail(models.Model):
    conflict_infos = models.ManyToManyField(ConflictInfo)
    is_only_excluded_conflict = models.BooleanField(default = False) # 是否全是与例外文件之间的冲突
    
    class Meta:
        db_table = 'dpl_conflict_detail'

