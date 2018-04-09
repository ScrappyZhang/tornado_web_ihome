"""房屋模块"""
'''
@Time    : 2018/4/9 上午8:59
@Author  : scrappy_zhang
@File    : house.py
'''
import logging

from handlers.BaseHandler import BaseHandler

from utils.response_code import RET

class AreaInfoHandler(BaseHandler):
    # 获取城区信息
    def get(self):
        # 1. 获取城区信息
        sql = "select ai_name,ai_area_id from ih_area_info"
        try:
            areas_info = self.db.query(sql)  # 返回的是列表
        except Exception as e:
            logging.error(e)
            return self.write(dict(errno=RET.DBERR, errmsg="数据库错误"))
        # 2. 返回数据 errno errmsg data
        self.write(dict(errno=RET.OK, errmsg="获取城区信息成功", data=areas_info))


class HouseIndexHandler(BaseHandler):
    # 获取首页房屋信息
    def get(self):
        pass
        # 1. 获取销量最好的5个房屋
        # 2. 返回数据 errno errmsg data