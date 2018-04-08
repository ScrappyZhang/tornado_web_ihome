"""session"""
'''
@Time    : 2018/4/8 下午3:32
@Author  : scrappy_zhang
@File    : session.py
'''

import uuid
import json
import logging

from constants import SESSION_EXPIRES_SECONDS


class Session(object):
    def __init__(self, request_handler_obj):
        # 1.尝试获取session_id
        self._request_handler = request_handler_obj
        self.session_id = request_handler_obj.get_secure_cookie("session_id")

        # 2. 若不存在session_id ，生成session_id
        if not self.session_id:
            self.session_id = uuid.uuid4().hex
            self.data = {}
            request_handler_obj.set_secure_cookie("session_id", self.session_id)

        # 3. 若存在session_id， 从redis中取出data
        else:
            try:
                json_data = request_handler_obj.redis.get("sess_%s" % self.session_id)
            except Exception as e:
                logging.error(e)
                raise e
            if not json_data:
                self.data = {}
            else:
                self.data = json.loads(json_data)

    def save(self):
        json_data = json.dumps(self.data)
        try:
            self._request_handler.redis.set("sess_%s" % self.session_id, json_data, SESSION_EXPIRES_SECONDS)
        except Exception as e:
            logging.error(e)
            raise e

    def clear(self):
        # 1. 删除redis中的session信息
        try:
            self._request_handler.redis.delete("sess_%s" % self.session_id)
        except Exception as e:
            logging.error(e)
        # 2. 清楚session值
        self._request_handler.clear_cookie("session_id")