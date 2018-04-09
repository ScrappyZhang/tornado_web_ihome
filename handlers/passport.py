"""注册、登录、登出"""
'''
@Time    : 2018/4/8 下午4:51
@Author  : scrappy_zhang
@File    : passport.py
'''

import logging
import hashlib
import re
import config

from tornado.web import RequestHandler
from handlers.BaseHandler import BaseHandler

from utils.session import Session
from utils.response_code import RET
from utils.commons import login_required


class RegisterHandler(BaseHandler):
    def post(self):
        # 1. 获取参数 手机号、短信验证码、密码
        mobile = self.json_args.get("mobile")
        sms_code = self.json_args.get("phonecode")
        password = self.json_args.get("password")
        # 2. 校验参数
        if not all([mobile, sms_code, password]):
            return self.write(dict(errno=RET.PARAMERR, errmsg="参数不完整"))
        if not re.match(r"^1\d{10}$", mobile):
            return self.write(dict(errno=RET.DATAERR, errmsg="手机号格式错误"))
        # 3. 校验短信验证码
        # 3.1 获取服务器生成的短信验证码
        try:
            real_sms_code = self.redis.get("SMS_CODE_%s" % mobile)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errno=RET.DBERR, errmsg="查询验证码出错"))
        # 短信验证码是否过期
        if not real_sms_code:
            return self.write(dict(errno=RET.NODATA, errmsg="验证码过期"))
        # 3.2 对比验证码
        if real_sms_code != sms_code:
            return self.write(dict(errno=RET.DATAERR, errmsg="短信验证码错误"))

        # 4、保存注册数据
        # 4.1 删除缓存中的验证码
        try:
            self.redis.delete("SMS_CODE_%s" % mobile)
        except Exception as e:
            logging.error(e)
        # 4.2 保存
        passwd = hashlib.sha256((password + config.passwd_hash_key).encode("utf8")).hexdigest()  # 密码加密
        sql = "insert into ih_user_profile(up_name, up_mobile, up_passwd) values(%(name)s, %(mobile)s, %(passwd)s);"
        try:
            user_id = self.db.execute(sql, name=mobile, mobile=mobile, passwd=passwd)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errno=RET.DATAEXIST, errmsg="手机号已存在"))

        # 5、添加session记录用户登录状态
        session = Session(self)
        session.data["user_id"] = user_id
        session.data["mobile"] = mobile
        session.data["name"] = mobile
        try:
            session.save()
        except Exception as e:
            logging.error(e)

        # 6、返回成功信息
        self.write(dict(errno=RET.OK, errmsg="注册成功"))


class LoginHandler(BaseHandler):
    """登录"""
    def post(self):
        # 1.获取参数 mobile password
        mobile = self.json_args["mobile"]
        password = self.json_args["password"]
        # 2.参数校验
        if not all([mobile, password]):
            return self.write(dict(errno=RET.PARAMERR, errmsg="参数错误"))
        if not re.match(r"^1\d{10}$", mobile):
            return self.write(dict(errno=RET.DATAERR, errmsg="手机号错误"))
        # 3. 获取真实加密密码等
        real_password = self.db.get(
            "select up_user_id, up_name, up_passwd from ih_user_profile where up_mobile=%(mobile)s", mobile=mobile)
        # 3.1 加密用户输入密码
        password = hashlib.sha256((password + config.passwd_hash_key).encode()).hexdigest()
        # 3.2 进行比对，若ok则生成session
        if real_password and real_password["up_passwd"] == str(password):
            try:
                self.session = Session(self)
                self.session.data["user_id"] = real_password["up_user_id"]
                self.session.data["name"] = real_password["up_name"]
                self.session.data["mobile"] = mobile
                self.session.save()
            except Exception as e:
                logging.error(e)
            return self.write(dict(errno=RET.OK, errmsg="OK"))
        else:
            return self.write(dict(errno=RET.DATAERR, errmsg="手机号或密码错误！"))

    # 退出登录
    @login_required
    def delete(self):
        self.session.clear()
        self.write(dict(errno=RET.OK, errmsg="退出成功"))

    # 登录检查
    def get(self):
        if self.get_current_user():
            self.write(dict(errno=RET.OK, errmsg="true", data={"name":self.session.data.get("name")}))
        else:
            self.write((dict(errno=RET.SESSIONERR, errmsg="false")))

