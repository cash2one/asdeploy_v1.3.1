#coding:utf-8

from django.contrib import admin
from deployment.models import *

admin.site.register(Project)
admin.site.register(DeployItem)