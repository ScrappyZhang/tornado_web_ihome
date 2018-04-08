"""登录状态校验装饰器"""
'''
@Time    : 2018/4/8 下午4:54
@Author  : scrappy_zhang
@File    : commons.py
'''

import functools

from utils.session import Session
from utils.response_code import RET


def login_required(f):
    @functools.wraps(f)
    def wrapper(request_handler_obj, *args, **kwargs):
        if not request_handler_obj.get_current_user():
            request_handler_obj.write(dict(errno=RET.SESSIONERR, errmsg="用户未登录"))
        else:
            f(request_handler_obj, *args, **kwargs)

    return wrapper
