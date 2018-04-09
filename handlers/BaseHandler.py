"""
请求处理基类BaseHandler， 实现数据库对象、json数据处理、判断用户登录
自定义静态文件处理类
"""
import json

from tornado.web import RequestHandler, StaticFileHandler
from utils.session import Session

'''
@Time    : 2018/4/8 下午2:49
@Author  : scrappy_zhang
@File    : BaseHandler.py
'''


class BaseHandler(RequestHandler):
    """自定义基类"""

    @property
    def db(self):
        return self.application.db

    @property
    def redis(self):
        return self.application.redis

    def prepare(self):
        """预解析json"""
        if self.request.headers.get("Content-Type", "").startswith("application/json"):
            self.json_args = json.loads(self.request.body)
        else:
            self.json_args = {}

    def set_default_headers(self):
        """设置json头"""
        self.set_header("Content-Type", "application/json; charset=UTF-8")

    def get_current_user(self):
        """判断用户是否登录"""
        self.session = Session(self)
        return self.session.data


class StaticFileBaseHandler(StaticFileHandler):
    """自定义静态文件处理类, 在用户获取html页面的时候设置_xsrf的cookie"""

    def __init__(self, *args, **kwargs):
        super(StaticFileBaseHandler, self).__init__(*args, **kwargs)
        self.xsrf_token
