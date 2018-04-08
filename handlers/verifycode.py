"""图片验证码与短信验证码"""
'''
@Time    : 2018/4/8 下午3:48
@Author  : scrappy_zhang
@File    : verifycode.py
'''

import logging
import random
import re

from handlers.BaseHandler import BaseHandler
from utils.captcha.captcha import captcha
from utils.response_code import RET
from constants import PIC_CODE_EXPIRES_SECONDS, SMS_CODE_EXPIRES_SECONDS


class ImageCodeHandler(BaseHandler):
    """图片验证码"""

    def get(self):
        """获取图片验证码"""
        # 1. 获取uuid和last_uuid
        pre_code_id = self.get_argument("last_uuid", "")
        cur_code_id = self.get_argument("uuid")
        # 2. 生成图片验证码
        name, text, image = captcha.generate_captcha()
        # 3. 验证码缓存
        try:
            if pre_code_id:
                self.redis.delete("ImageCode_%s" % pre_code_id)
            self.redis.set("ImageCode_%s" % cur_code_id, text, PIC_CODE_EXPIRES_SECONDS)
        except Exception as e:
            logging.error(e)
            self.write("")
        else:
            self.set_header("Content-Type", "image/jpg")
            print(text)  # 打印出此次生成的图片验证码，以便调试
            self.write(image)


class SmsCodeHandler(BaseHandler):
    """短信验证码"""

    def post(self):
        # 1. 获取参数mobile、 text（图片验证码）、id
        mobile = self.json_args.get("mobile")
        image_code = self.json_args.get("text")
        uuid = self.json_args.get("id")
        # 2. 参数校验
        if not all((mobile, image_code, uuid)):
            return self.write(dict(errno=RET.PARAMERR, errmsg="参数缺失"))
        if not re.match(r"^1[34578][0-9]{9}$", mobile):
            return self.write(dict(errno=RET.PARAMERR, errmsg="手机号码错误"))
        # 3. 核对图片验证码
        # 3.1 获取redis中的图片验证码
        try:
            real_image_code = self.redis.get("ImageCode_%s" % uuid)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errno=RET.DBERR, errmsg="查询验证码错误"))

        # 3.2 判断取出的real_image_code是否为空，为空则过期
        if not real_image_code:
            return self.write(dict(errno=RET.NODATA, errmsg="验证码过期"))

        # 3.3 删除图片验证码
        try:
            self.redis.delete("ImageCode_%s" % image_code)
        except Exception as e:
            logging.error(e)
        # 3.4 比较用户输入与真实验证码
        if real_image_code.lower() != image_code.lower():
            return self.write(dict(errno=RET.DATAERR, errmsg="图片验证码错误"))

        # 4. 生成短信验证码并发送
        # 4.1 判断手机号是否存在， 以防用户篡改
        sql = "select count(*) counts from ih_user_profile where up_mobile=%s"
        try:
            ret = self.db.get(sql, mobile)
        except Exception as e:
            logging.error(e)
        else:
            if 0 != ret["counts"]:
                return self.write(dict(errno=RET.DATAEXIST, errmsg="手机号已注册"))

        # 4.2 生成短信验证码
        sms_code = "%04d" % random.randint(1, 10000)
        print(sms_code)  # 打印方便调试
        # 4.3 将验证码存入redis
        try:
            self.redis.set("SMS_CODE_%s" % mobile, sms_code, SMS_CODE_EXPIRES_SECONDS)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errno=RET.DBERR, errmsg="数据库错误"))
        # 4.4 发送短信验证码，由云通讯第三方完成，此处略过
        # 5. 返回成功结果
        self.write(dict(errno=RET.OK, errmsg="发送成功"))
