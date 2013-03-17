#coding:utf-8

import re
from django import forms

from django.contrib.auth.models import User

class RegistrationForm(forms.Form):
    username = forms.CharField(label = '用户名', max_length = 30, min_length = 3)
    email = forms.EmailField(label = '邮箱')
    password1 = forms.CharField(
        label = '输入密码',
        widget = forms.PasswordInput()
    )
    password2 = forms.CharField(
        label = '确认密码',
        widget = forms.PasswordInput()
    )
    
    def clean_username(self):
        if 'username' in self.cleaned_data:
            username = self.cleaned_data.get('username')
            if not re.search(r'^[a-zA-Z0-9]{3,30}$', username):
                raise forms.ValidationError('用户名只能使用字符，数字和下划线')
            try:
                User.objects.get(username = username)
            except:
                return username
            raise forms.ValidationError('用户已存在!')
        raise forms.ValidationError('用户名的长度必须在3到30之间')

    def clean_password2(self):
        if 'password1' in self.cleaned_data:
            password1 = self.cleaned_data.get('password1')
            password2 = self.cleaned_data.get('password2')
            if password1 == password2:
                return password2
        raise forms.ValidationError('两次输入的密码不相同!')
