"""URl路由"""
'''
@Time    : 2018/4/8 下午2:43
@Author  : scrappy_zhang
@File    : urls.py
'''

import os
from handlers.BaseHandler import StaticFileBaseHandler as StaticFileHandler
from handlers import verifycode

urls = [
    (r'/image_code',verifycode.ImageCodeHandler),  # 图片验证码
    (r'/(.*)', StaticFileHandler,
     dict(path=os.path.join(os.path.dirname(__file__), "static/html"), default_filename="index.html")),

]
