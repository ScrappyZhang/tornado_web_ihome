"""用户个人中心模块"""
'''
@Time    : 2018/4/9 上午9:29
@Author  : scrappy_zhang
@File    : profile.py
'''
import logging

from handlers.BaseHandler import BaseHandler
from utils.commons import login_required
from utils.response_code import RET

import constants


class ProfileHandler(BaseHandler):
    # 个人信息
    @login_required
    def get(self):
        # 1. 获取用户id
        user_id = self.session.data['user_id']
        # 2. 获取用户信息
        try:
            ret = self.db.get("select up_name,up_mobile,up_avatar from ih_user_profile where up_user_id=%s", user_id)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errno=RET.DBERR, errmsg="获取用户数据失败"))
        # 2.1 用户头像url处理
        if ret["up_avatar"]:
            img_url = constants.QINIU_URL_PREFIX + ret["up_avatar"]
        else:
            img_url = None
        # 3. 返回数据
        self.write({"errno": RET.OK, "errmsg": "OK",
                    "data": {"user_id": user_id, "name": ret["up_name"], "mobile": ret["up_mobile"],
                             "avatar": img_url}})
