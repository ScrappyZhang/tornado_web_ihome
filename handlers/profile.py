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
from utils.qiniu_storage import storage

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


class AvatarHandler(BaseHandler):
    # 上传用户头像
    @login_required
    def post(self):
        # 1. 获取图片文件 avatar
        file_image = self.request.files.get('avatar', None)
        if not file_image:
            return self.write(dict(errno=RET.NODATA, errmsg="Invalid File"))
        # 2. 获取文件体body
        # img有三个键值对可以通过img.keys()查看
        # 分别是 'filename', 'body', 'content_type' 很明显对应着文件名,内容(二进制)和文件类型
        image_body = file_image[0]['body']

        # 3. 上传到七牛云存储
        # 调用七牛上传图片
        try:
            file_name = storage(image_body)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errno=RET.THIRDERR, errmsg="上传失败"))

        # 4. 从session数据中取出user_id
        user_id = self.session.data["user_id"]

        # 5. 保存图片名（即图片url）到数据中
        sql = "update ih_user_profile set up_avatar=%(avatar)s where up_user_id=%(user_id)s"
        try:
            row_count = self.db.execute_rowcount(sql, avatar=file_name, user_id=user_id)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg="数据库图片保存错误"))
        # 6.返回数据 data
        self.write(
            dict(errno=RET.OK, errmsg="保存成功", data=dict(avatar_url="%s%s" % (constants.QINIU_URL_PREFIX, file_name))))
