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
            print(text)
            self.write(image)
