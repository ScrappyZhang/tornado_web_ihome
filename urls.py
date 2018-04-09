"""URl路由"""
'''
@Time    : 2018/4/8 下午2:43
@Author  : scrappy_zhang
@File    : urls.py
'''

import os
from handlers.BaseHandler import StaticFileBaseHandler as StaticFileHandler
from handlers import verifycode, passport

urls = [
    (r'^/register$', passport.RegisterHandler),  # 注册
    (r'/login$', passport.LoginHandler),  # 登录、退出、登录校验
    (r'^/image_code$',verifycode.ImageCodeHandler),  # 图片验证码
    (r'^/smscode$', verifycode.SmsCodeHandler),  # 短信验证码
    (r'/(.*)', StaticFileHandler,
     dict(path=os.path.join(os.path.dirname(__file__), "static/html"), default_filename="index.html")),

]
