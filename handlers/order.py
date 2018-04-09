"""订单模块"""
'''
@Time    : 2018/4/9 下午3:33
@Author  : scrappy_zhang
@File    : order.py
'''

import logging
import datetime

from handlers.BaseHandler import BaseHandler

from utils.commons import login_required
from utils.response_code import RET


class OrderHandler(BaseHandler):
    @login_required
    def post(self):
        # 1. 获取参数  user_id house_id start_date end_date
        user_id = self.session.data["user_id"]
        house_id = self.json_args.get("house_id")
        start_date = self.json_args.get("start_date")
        end_date = self.json_args.get("end_date")
        # 2. 校验参数
        # 2.1 参数是否完全
        if not all((house_id, start_date, end_date)):
            return self.write({"errno": RET.PARAMERR, "errmsg": "params error"})
        # 2.2 判断日期
        order_days = (
        datetime.datetime.strptime(end_date, "%Y-%m-%d") - datetime.datetime.strptime(start_date, "%Y-%m-%d")).days
        if order_days < 0:
            return self.write({"errno": RET.PARAMERR, "errmsg": "date params error"})
        if order_days == 0:
            order_days = 1
        # 2.3 house_id必须为整数
        if house_id:
            try:
                house_id = int(house_id)
            except Exception as e:
                logging.error(e)
                return self.write(dict(errno=RET.PARAMERR, errmsg="参数错误"))
        # 3. 查询数据库

        # 3.1 房屋是否存在
        try:
            house_order = self.db.get("select hi_price,hi_user_id from ih_house_info where hi_house_id=%s", house_id)
        except Exception as e:
            logging.error(e)
            return self.write({"errno": RET.DBERR, "errmsg": "get house error"})
        if not house_order:
            return self.write({"errno": RET.NODATA, "errmsg": "no data"})

        # 3.2 判断是否为房东, 若是，则不能下单
        if user_id == house_order["hi_user_id"]:
            return self.write({"errno": RET.ROLEERR, "errmsg": "user is forbidden"})

        # 3.3 时间是否冲突
        try:
            ret = self.db.get("select count(*) counts from ih_order_info where oi_house_id=%(house_id)s "
                              "and oi_begin_date<%(end_date)s and oi_end_date>%(start_date)s",
                              house_id=house_id, end_date=end_date, start_date=start_date)
        except Exception as e:
            logging.error(e)
            return self.write({"errno": RET.DBERR, "errmsg": "get date error"})
        if ret["counts"] > 0:
            return self.write({"errno": RET.DATAERR, "errmsg": "serve date error"})
        # 4. 下单，生成订单order
        amount = order_days * house_order["hi_price"]
        try:
            # 保存订单数据ih_order_info，
            sql = "insert into ih_order_info(oi_user_id,oi_house_id,oi_begin_date,oi_end_date,oi_days,oi_house_price,oi_amount) values(%(user_id)s,%(house_id)s,%(begin_date)s,%(end_date)s,%(days)s,%(price)s,%(amount)s)"
            self.db.execute(sql, user_id=user_id, house_id=house_id, begin_date=start_date, end_date=end_date,
                            days=order_days, price=house_order["hi_price"], amount=amount)
            sql = "update ih_house_info set hi_order_count=hi_order_count+1 where hi_house_id=%(house_id)s"
            self.db.execute(sql, house_id=house_id)
        except Exception as e:
            logging.error(e)
            sql = "delete from ih_order_info where oi_user_id=%(user_id)s and oi_house_id=%(house_id)s and oi_begin_date=%(begin_date)s and oi_end_date=%(end_date)s"
            self.db.execute(sql, user_id=user_id, house_id=house_id, begin_date=start_date, end_date=end_date,
                            days=order_days, price=house_order["hi_price"], amount=amount)
            return self.write({"errno": RET.DBERR, "errmsg": "save data error"})
        # 返回结果
        self.write({"errno": RET.OK, "errmsg": "OK"})
