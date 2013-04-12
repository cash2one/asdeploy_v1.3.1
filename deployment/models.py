#coding:utf-8

from django.db import models

from django.contrib.auth.models import User

#------ 表结构需要手工修改的地方 ------#
# dpl_deployrecord.status要扩容到varchar(30)
# dpl_deployrecord添加is_conflict_with_others字段
# dpl_deployitem添加patch_group_id字段

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
    RESET = 'reset'

    user = models.ForeignKey(User)
    project = models.ForeignKey(Project)
    version = models.CharField(max_length = 11)
    deploy_type = models.CharField(max_length=15)
    file_name = models.CharField(max_length = 100)
    folder_path = models.CharField(max_length = 512, null = True)
    create_time = models.DateTimeField()
    update_time = models.DateTimeField(null = True)
    patch_group = models.ForeignKey('PatchGroup')
    
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
    ROLLBACK_FAILURE = 'rollback_failure'
    BACKUP_DEPLOYING = 'backup_deploying'  # 补丁组完结发布  
    BACKUP_SUCCESS = 'backup_success'
    BACKUP_FAILURE = 'backup_failure'
    RESET_DEPLOYING = 'reset_deploying'  # 版本接收发布
    RESET_SUCCESS = 'reset_success'
    RESET_FAILURE = 'reset_failure'
    RESET_IGNORED = 'reset_ignored'     # 忽略成功的reset发布
    
    user = models.ForeignKey(User)
    project = models.ForeignKey(Project)
    deploy_item = models.ForeignKey(DeployItem, null = True)
    create_time = models.DateTimeField()
    status = models.CharField(max_length = 30)
    is_conflict_with_others = models.BooleanField(default = False)
    
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
    STATUS_CREATED = 'created'
    STATUS_TESTING = "testing"
    STATUS_FINISHED = "finished"                        # 通过上线后的更新发布，方可将状态置为finish
    STATUS_STOPED = "stoped"
    STATUS_DELETED = "deleted"
    
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
    related_patch_group_id = models.IntegerField()
    conflict_patch_group = models.ForeignKey(PatchGroup)
    conflict_patch_file = models.ForeignKey(PatchFile)
    is_excluded_conflict = models.BooleanField(default = False) # 是否是与例外文件之间的冲突
    
    class Meta:
        db_table = 'dpl_conflict_info'

# DeployRecord与ConflictDetail之间1对0或1
class ConflictDetail(models.Model):
    deploy_record = models.ForeignKey(DeployRecord)
    conflict_infos = models.ManyToManyField(ConflictInfo)
    is_only_excluded_conflict = models.BooleanField(default = False) # 是否全是与例外文件之间的冲突
    
    class Meta:
        db_table = 'dpl_conflict_detail'

# 依据此表中的信息来判断是否有新的备份源
# 里面的信息除了reset_source_ts以外，其他的基本都是做冗余，并且目前还没有用到
# 只有reset发布成功的时候，才会记录此信息
class ResetInfo(models.Model):
    
    TYPE_STATIC = 'static'
    TYPE_AJAXABLESKY = 'ajaxablesky'
    
    operator = models.ForeignKey(User)                      # 操作者
    reset_source_ts = models.TextField(max_length = 14)    # reset源的时间戳，省得每次都去翻DeployItem
    reset_time = models.DateTimeField()
    deploy_record = models.ForeignKey(DeployRecord)
    deploy_item = models.ForeignKey(DeployItem)
    reset_type = models.TextField(max_length = 30)
    is_ignored = models.BooleanField(default = False)
    class Meta:
        db_table = 'dpl_reset_info'
        
