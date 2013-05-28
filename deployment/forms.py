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
            if not re.search(r'^[a-zA-Z0-9_]{3,30}$', username):
                raise forms.ValidationError('用户名只能使用字符，数字和下划线！')
            try:
                User.objects.get(username = username)
            except:
                return username
            raise forms.ValidationError('用户已存在!')
        raise forms.ValidationError('用户名的长度必须在3到30之间！')
    
    def clean_password1(self):
        if 'password1' in self.cleaned_data:
            password1 = self.cleaned_data.get('password1')
            pwd_len = len(password1)
            if pwd_len < 4 or pwd_len >= 30:
                raise forms.ValidationError('密码长度需大于3并小于30！')
            if not re.search(r'^[a-zA-Z0-9_]{4,30}$', password1):
                raise forms.ValidationError('密码只能使用字符和数字！')
            else: 
                return password1
        raise forms.ValidationError('密码不能为空！')
        

    def clean_password2(self):
        if 'password1' in self.cleaned_data:
            password1 = self.cleaned_data.get('password1')
            password2 = self.cleaned_data.get('password2')
            if password1 == password2:
                return password2
        raise forms.ValidationError('两次输入的密码不相同！')
