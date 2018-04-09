"""URl路由"""
'''
@Time    : 2018/4/8 下午2:43
@Author  : scrappy_zhang
@File    : urls.py
'''

import os
from handlers.BaseHandler import StaticFileBaseHandler as StaticFileHandler
from handlers import verifycode, passport, house, profile

urls = [
    (r'^/register$', passport.RegisterHandler),  # 注册
    (r'/login$', passport.LoginHandler),  # 登录、退出、登录校验
    (r'^/users$', profile.ProfileHandler),  # 获取个人信息
    (r'^/user/avatar$', profile.AvatarHandler),  # 用户头像
    (r'^/user/name$', profile.NameHandler),  # 用户名修改
    (r'^/user/auth$', profile.AuthHandler),  # 实名认证
    (r'^/user/houses$', profile.HouseSourceHandler),  # 房东房源
    (r'/house/areas', house.AreaInfoHandler),  # 获取城区信息
    (r'/house/index', house.HouseIndexHandler),  # 获取首页展示的房源
    (r'^/image_code$', verifycode.ImageCodeHandler),  # 图片验证码
    (r'^/smscode$', verifycode.SmsCodeHandler),  # 短信验证码
    (r'/(.*)', StaticFileHandler,
     dict(path=os.path.join(os.path.dirname(__file__), "static/html"), default_filename="index.html")),
]
