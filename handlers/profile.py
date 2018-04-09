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


class NameHandler(BaseHandler):
    @login_required
    def post(self):
        # 1. 获取session中的user_id
        user_id = self.session.data["user_id"]
        # 2. 获取用户设置的用户名
        name = self.json_args["name"]
        # 2.1 校验设置用户名
        if name in (None, ""):
            return self.write(dict(errno=RET.PARAMERR, errmsg="用户名输入错误"))

        # 3. 保存name
        try:
            self.db.execute_rowcount("update ih_user_profile set up_name=%s where up_user_id=%s", name, user_id)
        except Exception as e:
            logging.error(e)
            return self.write({"errcode": RET.DBERR, "errmsg": "用户名未修改"})

        # 4. 修改session数据中的name字段，并保存到redis中
        self.session.data["name"] = name
        try:
            self.session.save()
        except Exception as e:
            logging.error(e)
        self.write({"errcode": RET.OK, "errmsg": "OK"})


class AuthHandler(BaseHandler):
    @login_required
    def get(self):
        # 获取实名认证信息
        # 1、获取session的user_id
        user_id = self.session.data["user_id"]
        # 2、查询实名认证信息up_real_name 、up_id_card
        sql = "select up_real_name, up_id_card from ih_user_profile where up_user_id=%(user_id)s"
        try:
            user_auth_info = self.db.get(sql, user_id=user_id)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errno=RET.DBERR, errmsg="数据库错误"))
        # 3、返回结果
        self.write(dict(errno=RET.OK, errmsg="OK", data=user_auth_info))

    @login_required
    def post(self):
        # 修改实名认证信息
        # 1、获取user_id
        user_id = self.session.data["user_id"]
        # 2、获取输入参数
        real_name_input = self.json_args["real_name"]
        id_card_input = self.json_args["id_card"]
        # 3、校验输入参数
        if not all((real_name_input, id_card_input)):
            return self.write(dict(errno=RET.PARAMERR, errmsg="输入数据不全"))
        # 3.1身份证格式校验（略过）
        # 4、修改数据库信息
        try:
            self.db.execute_rowcount("update ih_user_profile set up_real_name=%s,up_id_card=%s where up_user_id=%s",
                                     real_name_input, id_card_input, user_id)
        except Exception as e:
            logging.error(e)
            return self.write({"errcode": RET.DBERR, "errmsg": "update failed"})

        # 5、返回结果
        self.write(dict(errno=RET.OK, errmsg="OK"))


class HouseSourceHandler(BaseHandler):
    @login_required
    def get(self):
        # 1、获取user_id
        user_id = self.session.data["user_id"]
        # 2、查询用户房源
        try:
            sql = "select a.hi_house_id,a.hi_title,a.hi_price,a.hi_ctime,b.ai_name,a.hi_index_image_url " \
                  "from ih_house_info a inner join ih_area_info b on a.hi_area_id=b.ai_area_id where a.hi_user_id=%s;"
            ret = self.db.query(sql, user_id)
        except Exception as e:
            logging.error(e)
            return self.write({"errcode": RET.DBERR, "errmsg": "get data erro"})
        # 3、返回数据errno errmsg data
        houses = []
        if ret:
            for l in ret:
                house_info = {
                    "house_id": l["hi_house_id"],
                    "title": l["hi_title"],
                    "price": l["hi_price"],
                    "ctime": l["hi_ctime"].strftime("%Y-%m-%d"),  # 将返回的Datatime类型格式化为字符串
                    "area_name": l["ai_name"],
                    "img_url": constants.QINIU_URL_PREFIX + l["hi_index_image_url"] if l["hi_index_image_url"] else ""
                }
                houses.append(house_info)
        self.write(dict(errno=RET.OK, errmsg="OK", data=houses))
