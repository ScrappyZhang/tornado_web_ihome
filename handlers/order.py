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

import constants


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


class OrderListHandler(BaseHandler):
    @login_required
    def get(self):
        # 1. 获取用户角色 role
        role = self.get_argument("role", "")
        user_id = self.session.data['user_id']
        # 2. 校验参数
        if not role:
            return self.write(dict(errno=RET.PARAMERR, errmsg="参数错误"))
        # 3. 查询数据库
        # 3.1 角色判断
        try:
            if role == "custom":
                # 3.1 若为客户
                ret = self.db.query("select oi_order_id,hi_title,hi_index_image_url,oi_begin_date,oi_end_date,oi_ctime,"
                                    "oi_days,oi_amount,oi_status,oi_comment from ih_order_info inner join ih_house_info"
                                    " on oi_house_id=hi_house_id where oi_user_id=%s order by oi_ctime desc", user_id)
            else:
                # 3.2 若为房东
                ret = self.db.query("select oi_order_id,hi_title,hi_index_image_url,oi_begin_date,oi_end_date,oi_ctime,"
                                    "oi_days,oi_amount,oi_status,oi_comment from ih_order_info inner join ih_house_info "
                                    "on oi_house_id=hi_house_id where hi_user_id=%s order by oi_ctime desc", user_id)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errno=RET.DBERR, errmsg="数据库查询错误"))
        # 3.2 查询结果整理
        orders = []
        if ret:
            for l in ret:
                order = {
                    "order_id": l["oi_order_id"],
                    "title": l["hi_title"],
                    "img_url": constants.QINIU_URL_PREFIX + l["hi_index_image_url"] if l["hi_index_image_url"] else "",
                    "start_date": l["oi_begin_date"].strftime("%Y-%m-%d"),
                    "end_date": l["oi_end_date"].strftime("%Y-%m-%d"),
                    "ctime": l["oi_ctime"].strftime("%Y-%m-%d"),
                    "days": l["oi_days"],
                    "amount": l["oi_amount"],
                    "status": l["oi_status"],
                    "comment": l["oi_comment"] if l["oi_comment"] else ""
                }
                orders.append(order)
        # 4. 返回数据
        self.write({"errno": RET.OK, "errmsg": "OK", "data": {"orders": orders}})


class OrderStatusHandler(BaseHandler):
    @login_required
    def put(self, order_id):
        # 0. 获取当前用户id
        user_id = self.session.data["user_id"]
        # 1. 获取动作参数action
        action = self.json_args.get("action")
        if action not in ("accept", "reject"):
            return self.write(dict(errno=RET.PARAMERR, errmsg="参数错误"))
        # 2.  校验order_id
        try:
            order_id = int(order_id)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errno=RET.PARAMERR, errmsg="参数错误"))

        if action == "accept":
            #  3. 接单
            # 修改status为"WAIT_COMMENT"
            try:
                # 确保房东只能修改属于自己房子的订单
                sql="update ih_order_info set oi_status=%(status)s " \
                    "where oi_order_id=%(order_id)s and oi_house_id in " \
                    "(select hi_house_id from ih_house_info where hi_user_id=%(user_id)s) and oi_status=%(status_o)s"
                self.db.execute(sql, status="WAIT_COMMENT", order_id=order_id, user_id=user_id, status_o="WAIT_ACCEPT")
            except Exception as e:
                logging.error(e)
                return self.write(dict(errno=RET.DBERR, errmsg="数据库错误"))
        else:
            # 4. 拒单
            reason = self.json_args.get("reason")
            # 4.1 判断reason是否为空
            if not reason:
                return self.write(dict(errno=RET.PARAMERR, errmsg="未填写拒单原因"))
            try:
                self.db.execute("update ih_order_info set oi_status=6,oi_comment=%(reject_reason)s "
                                "where oi_order_id=%(order_id)s and oi_house_id in (select hi_house_id from ih_house_info "
                                "where hi_user_id=%(user_id)s) and oi_status=%(status)s",
                                reject_reason=reason, order_id=order_id, user_id=user_id, status="REJECTED")
            except Exception as e:
                logging.error(e)
                return self.write({"errno": RET.DBERR, "errmsg": "DB error"})

        # 5. ok
        self.write(dict(errno=RET.OK, errmsg="ok"))


class OrderCommentHandler(BaseHandler):
    @login_required
    def put(self, order_id):
        # 1. 获取参数
        user_id = self.session.data["user_id"]
        comment = self.json_args.get("comment")
        # 2. 校验参数
        if not comment:
            return self.write({"errno": RET.PARAMERR, "errmsg": "params error"})
        try:
            order_id = int(order_id)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errno=RET.PARAMERR, errmsg="参数错误"))
        # 3. 更新数据库中评论信息
        try:
            # 需要确保只能评论自己下的订单
            self.db.execute(
                "update ih_order_info set oi_status=%(oi_status)s,oi_comment=%(comment)s where oi_order_id=%(order_id)s "
                "and oi_status=%(status)s and oi_user_id=%(user_id)s", oi_status="COMPLETE", comment=comment, status="WAIT_COMMENT", order_id=order_id, user_id=user_id)
        except Exception as e:
            logging.error(e)
            return self.write({"errno": RET.DBERR, "errmsg": "DB error"})
        # 4.返回数据
        self.write({"errno": RET.OK, "errmsg": "OK"})