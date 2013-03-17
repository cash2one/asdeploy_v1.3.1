#coding:utf-8

import time
import threading

from django.core.cache import cache

from deployment.deploysetting import *


class LogReader(object):
    
    def __init__(self):
        self.file_pos = 0
        
    def read_lines(self):
        f = open(DEPLOY_LOG_PATH, 'r')
        f.seek(self.file_pos)
        result = f.readlines()
        self.file_pos = f.tell()
        f.close()
        return result
    
# 这个类只在测试时有用
#class LogWriter(threading.Thread):
#    
#    def __init__(self, record_id, filename, filepath):
#        threading.Thread.__init__(self)
#        if not filepath.endswith('/'):
#            filepath += '/'
#        self.file_name = filename
#        self.file_path = filepath
#        self.record_id = record_id
#    
#    def run(self):
#        status_key = 'log_is_writing_' + unicode(self.record_id)
#        cache.set(status_key, True, 7200)
#        f = open(self.file_path + self.file_name, 'w')
#        f.write('')
#        f.close()
#        for i in range(20):
#            f = open(self.file_path + self.file_name, 'a')
#            f.write(str(i) + ' content \r\n')
#            f.close()
#            time.sleep(2)
#        cache.delete('log_is_writing_' + unicode(self.record_id))
