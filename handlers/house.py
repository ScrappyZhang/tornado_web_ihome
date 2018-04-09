"""房屋模块"""
'''
@Time    : 2018/4/9 上午8:59
@Author  : scrappy_zhang
@File    : house.py
'''
import logging
import datetime
import math

from handlers.BaseHandler import BaseHandler

from utils.response_code import RET
from utils.commons import login_required
from utils.qiniu_storage import storage
from utils.session import Session

import constants


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
        try:
            house_ret = self.db.query(
                "select hi_house_id,hi_title,hi_order_count,hi_index_image_url from ih_house_info " \
                "order by hi_order_count desc limit %s;" % constants.HOME_PAGE_MAX_HOUSES)
        except Exception as e:
            logging.error(e)
            return self.write({"errno": RET.DBERR, "errmsg": "get data error"})
        # 2. 返回数据 errno errmsg data
        # 2.1 判断是否有数据
        if not house_ret:
            return self.write({"errno": RET.NODATA, "errmsg": "no data"})
        # 2.2 整理数据
        houses = []
        for l in house_ret:
            if not l["hi_index_image_url"]:
                continue
            house = {
                "house_id": l["hi_house_id"],
                "title": l["hi_title"],
                "img_url": constants.QINIU_URL_PREFIX + l["hi_index_image_url"]
            }
            houses.append(house)
        # 2.3 返回数据data
        self.write(dict(errno=RET.OK, errmsg="OK", data=houses))


class NewHouseHandler(BaseHandler):
    def get(self):
        # 1. 获取前端参数aid sd ed sk p
        """
                传入参数说明
                start_date 用户查询的起始时间 sd     非必传   ""          "2017-02-28"
                end_date    用户查询的终止时间 ed    非必传   ""
                area_id     用户查询的区域条件   aid 非必传   ""
                sort_key    排序的关键词     sk     非必传   "new"      "new" "booking" "price-inc"  "price-des"
                page        返回的数据页数     p     非必传   1
        """
        start_date_str = self.get_argument("sd", "")
        end_date_str = self.get_argument("ed", "")
        area_id = self.get_argument("aid", "")
        # booking(订单量), price-inc(低到高), price-des(高到低),
        sort_key = self.get_argument("sk", "new")
        page = self.get_argument("p", "1")

        # 2. 前端参数校验——判断日期格式、sort_Key 字段的值、page的整数、区域area_id
        # 2.1 page整数化
        try:
            page = int(page)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errno=RET.PARAMERR, errmsg="页码参数错误"))
        # 2.2 排序方式校验
        if sort_key not in ("new", "booking", "price-inc", "price-des"):
            return self.write(dict(errno=RET.PARAMERR, errmsg="排序参数错误"))
        # 2.3 日期处理
        try:
            start_date = None
            end_date = None
            if start_date_str:
                start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
            if end_date_str:
                end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
            # 2.3.1若开始时间大于或等于结束时间就报错
            if start_date and end_date:
                assert start_date < end_date, Exception('开始时间大于结束时间')
        except Exception as e:
            logging.error(e)
            return self.write(dict(errno=RET.PARAMERR, errmsg='日期错误'))
        # TODO redis
        # 3. 查询房屋
        # 涉及到表： ih_house_info 房屋的基本信息  ih_user_profile 房东的用户信息 ih_order_info 房屋订单数据
        sql = "select distinct hi_title,hi_house_id,hi_price,hi_room_count,hi_address,hi_order_count,up_avatar,hi_index_image_url,hi_ctime" \
              " from ih_house_info inner join ih_user_profile on hi_user_id=up_user_id left join ih_order_info" \
              " on hi_house_id=oi_house_id"
        sql_total_count = "select count(distinct hi_house_id) count from ih_house_info inner join ih_user_profile on hi_user_id=up_user_id left join ih_order_info on hi_house_id=oi_house_id"
        sql_where = []  # 用来保存sql语句的where条件
        sql_params = {}  # 用来保存sql查询所需的动态数据
        # 3.1 日期过滤条件
        if start_date and end_date:
            sql_part = "((oi_begin_date>%(end_date)s or oi_end_date<%(start_date)s) " \
                       "or (oi_begin_date is null and oi_end_date is null))"
            sql_where.append(sql_part)
            sql_params["start_date"] = start_date
            sql_params["end_date"] = end_date
        elif start_date:
            sql_part = "(oi_end_date<%(start_date)s or (oi_begin_date is null and oi_end_date is null))"
            sql_where.append(sql_part)
            sql_params["start_date"] = start_date
        elif end_date:
            sql_part = "(oi_begin_date>%(end_date)s or (oi_begin_date is null and oi_end_date is null))"
            sql_where.append(sql_part)
            sql_params["end_date"] = end_date
        # 3.2 地区过滤条件
        if area_id:
            sql_part = "hi_area_id=%(area_id)s"
            sql_where.append(sql_part)
            sql_params["area_id"] = area_id
        # 3.3 sql增加where过滤条件
        if sql_where:
            sql += " where "
            sql += " and ".join(sql_where)
        # 3.4 查询结果总条目
        try:
            ret = self.db.get(sql_total_count, **sql_params)
        except Exception as e:
            logging.error(e)
            total_page = -1
        else:
            total_page = int(math.ceil(ret["count"] / float(constants.HOUSE_LIST_PAGE_CAPACITY)))
            if page > total_page:
                return self.write(dict(errno=RET.OK, errmsg="OK", data=[], total_page=total_page))
        # 3.5 sql语句增加排序
        if "new" == sort_key:  # 按最新上传时间排序
            sql += " order by hi_ctime desc"
        elif "booking" == sort_key:  # 最受欢迎
            sql += " order by hi_order_count desc"
        elif "price-inc" == sort_key:  # 价格由低到高
            sql += " order by hi_price asc"
        elif "price-des" == sort_key:  # 价格由高到低
            sql += " order by hi_price desc"
        # 3.6 sql语句查询第page页
        if 1 == page:
            sql += " limit %s" % constants.HOUSE_LIST_PAGE_CAPACITY
        else:
            sql += " limit %s,%s" % (
            (page - 1) * constants.HOUSE_LIST_PAGE_CAPACITY, constants.HOUSE_LIST_PAGE_CAPACITY)
        # 3.7 查询数据库
        try:
            ret = self.db.query(sql, **sql_params)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errno=RET.DBERR, errmsg="查询出错"))
        # 3.8 数据处理
        data = []
        if ret:
            for l in ret:
                house = dict(
                    house_id=l["hi_house_id"],
                    title=l["hi_title"],
                    price=l["hi_price"],
                    room_count=l["hi_room_count"],
                    address=l["hi_address"],
                    order_count=l["hi_order_count"],
                    user_avatar=constants.QINIU_URL_PREFIX + l["up_avatar"] if l.get("up_avatar") else "",
                    img_url=constants.QINIU_URL_PREFIX + l["hi_index_image_url"] if l.get(
                        "hi_index_image_url") else ""
                )
                data.append(house)
        # 4. 返回房屋列表信息
        self.write(dict(errno=RET.OK, errmsg="OK", data=data, total_page=total_page))

    @login_required
    def post(self):
        # 1. 获取输入参数
        """{
                    "title":"",
                    "price":"",
                    "area_id":"1",
                    "address":"",
                    "room_count":"",
                    "acreage":"",
                    "unit":"",
                    "capacity":"",
                    "beds":"",
                    "deposit":"",
                    "min_days":"",
                    "max_days":"",
                    "facility":["7","8"]
                }
        """
        title = self.json_args.get("title")
        price = self.json_args.get("price")
        area_id = self.json_args.get("area_id")
        address = self.json_args.get("address")
        room_count = self.json_args.get("room_count")
        acreage = self.json_args.get("acreage")
        unit = self.json_args.get("unit")
        capacity = self.json_args.get("capacity")
        beds = self.json_args.get("beds")
        deposit = self.json_args.get("deposit")
        min_days = self.json_args.get("min_days")
        max_days = self.json_args.get("max_days")
        facility = self.json_args.get("facility")  # 对一个房屋的设施，是列表类型
        # 2. 校验输入参数
        if not all((title, price, area_id, address, room_count, acreage, unit, capacity, beds, deposit, min_days,
                    max_days)):
            return self.write(dict(errno=RET.PARAMERR, errmsg="缺少参数"))
        # 3. 获取user_id
        user_id = self.session.data.get("user_id")
        # 4. 保存房源文字信息
        # 4.1 处理数据
        try:
            price = int(price) * 100
            deposit = int(deposit) * 100
        except Exception as e:
            return self.write(dict(errno=RET.PARAMERR, errmsg="参数错误"))
        # 4.2 写入房源信息
        try:
            sql = "insert into ih_house_info(hi_user_id,hi_title,hi_price,hi_area_id,hi_address,hi_room_count," \
                  "hi_acreage,hi_house_unit,hi_capacity,hi_beds,hi_deposit,hi_min_days,hi_max_days) " \
                  "values(%(user_id)s,%(title)s,%(price)s,%(area_id)s,%(address)s,%(room_count)s,%(acreage)s," \
                  "%(house_unit)s,%(capacity)s,%(beds)s,%(deposit)s,%(min_days)s,%(max_days)s)"
            # 对于insert语句，execute方法会返回最后一个自增id
            house_id = self.db.execute(sql, user_id=user_id, title=title, price=price, area_id=area_id, address=address,
                                       room_count=room_count, acreage=acreage, house_unit=unit, capacity=capacity,
                                       beds=beds, deposit=deposit, min_days=min_days, max_days=max_days)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errno=RET.DBERR, errmsg="save data error"))

        # 4.3 将房屋设施信息写入ih_house_facility
        try:
            # for fid in facility:
            #     sql = "insert into ih_house_facility(hf_house_id,hf_facility_id) values(%s,%s)"
            #     self.db.execute(sql, house_id, fid)
            sql = "insert into ih_house_facility(hf_house_id,hf_facility_id) values"
            sql_val = []  # 用来保存条目的(%s, %s)部分  最终的形式 ["(%s, %s)", "(%s, %s)"]
            vals = []  # 用来保存的具体的绑定变量值
            for facility_id in facility:
                # sql += "(%s, %s)," 采用此种方式，sql语句末尾会多出一个逗号
                sql_val.append("(%s, %s)")
                vals.append(house_id)
                vals.append(facility_id)

            sql += ",".join(sql_val)
            vals = tuple(vals)
            self.db.execute(sql, *vals)
        except Exception as e:
            logging.error(e)
            try:
                self.db.execute("delete from ih_house_info where hi_house_id=%s", house_id)
            except Exception as e:
                logging.error(e)
                return self.write(dict(errno=RET.DBERR, errmsg="delete fail"))
            else:
                return self.write(dict(errno=RET.DBERR, errmsg="no data save"))
        # 5. 返回房屋id
        self.write(dict(errno=RET.OK, errmsg="OK", data=dict(house_id=house_id)))


class NewHouseImageHandler(BaseHandler):
    @login_required
    def post(self, house_id):
        # 1. 获取参数 user_id house_id house_img
        user_id = self.session.data["user_id"]
        house_image = self.request.files["house_image"][0]["body"]
        # print(house_id)
        if not house_image:
            return self.write(dict(errno=RET.NODATA, errmsg="Invalid File"))
        # 2. 上传七牛云
        img_name = storage(house_image)
        # print(img_name)
        if not img_name:
            return self.write({"errno": RET.THIRDERR, "errmsg": "qiniu error"})
        # 3. 保存图片url
        # 保存图片路径到数据库ih_house_image表,并且设置房屋的主图片(ih_house_info中的hi_index_image_url）
        try:
            sql = 'insert into ih_house_image (hi_house_id,hi_url) value (%(house_id)s,%(img_name)s)'
            self.db.execute(sql, house_id=house_id, img_name=img_name)
            sql = "update ih_house_info set hi_index_image_url=%(img_name)s where hi_house_id=%(house_id)s and hi_index_image_url is null"
            self.db.execute(sql, img_name=img_name, house_id=house_id)
        except Exception as e:
            logging.error(e)
            return self.write({"errno": RET.DBERR, "errmsg": "upload failed"})
        img_url = constants.QINIU_URL_PREFIX + img_name
        self.write({"errno": RET.OK, "errmsg": "OK", "url": img_url})


class DetailHouseInfoHandler(BaseHandler):
    def get(self, house_id):
        # 前端在房屋详情页面展示时，如果浏览页面的用户不是该房屋的房东，则展示预定按钮，否则不展示，
        # 所以需要后端返回登录用户的user_id
        # 尝试获取用户登录的信息，若登录，则返回给前端登录用户的user_id，否则返回user_id=-1
        # 判断参数是否有值
        # 1. 获取session信息
        session = Session(self)
        user_id = session.data.get("user_id", "-1")
        # 2. 校验参数
        if not house_id:
            return self.write(dict(errno=RET.PARAMERR, errmsg="缺少参数"))
        # 3. 查询房屋信息
        sql = "select hi_title,hi_price,hi_address,hi_room_count,hi_acreage,hi_house_unit,hi_capacity,hi_beds," \
              "hi_deposit,hi_min_days,hi_max_days,up_name,up_avatar,hi_user_id " \
              "from ih_house_info inner join ih_user_profile on hi_user_id=up_user_id where hi_house_id=%s"

        try:
            ret = self.db.get(sql, house_id)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errno=RET.DBERR, errmsg="查询错误"))

        # 3.1 查询信息校验
        if not ret:
            return self.write(dict(errno=RET.NODATA, errmsg="查无此房"))
        # 3.2 组织信息
        data = {
            "hid": house_id,
            "user_id": ret["hi_user_id"],
            "title": ret["hi_title"],
            "price": ret["hi_price"],
            "address": ret["hi_address"],
            "room_count": ret["hi_room_count"],
            "acreage": ret["hi_acreage"],
            "unit": ret["hi_house_unit"],
            "capacity": ret["hi_capacity"],
            "beds": ret["hi_beds"],
            "deposit": ret["hi_deposit"],
            "min_days": ret["hi_min_days"],
            "max_days": ret["hi_max_days"],
            "user_name": ret["up_name"],
            "user_avatar": constants.QINIU_URL_PREFIX + ret["up_avatar"] if ret.get("up_avatar") else ""
        }

        # 3.1 查询房屋图片信息
        sql = "select hi_url from ih_house_image where hi_house_id=%s"
        try:
            ret = self.db.query(sql, house_id)
        except Exception as e:
            logging.error(e)
            ret = None

        # 如果查询到的图片
        images = []
        if ret:
            for image in ret:
                images.append(constants.QINIU_URL_PREFIX + image["hi_url"])
        data["images"] = images

        # 3.2 查询房屋的基本设施
        sql = "select hf_facility_id from ih_house_facility where hf_house_id=%s"
        try:
            ret = self.db.query(sql, house_id)
        except Exception as e:
            logging.error(e)
            ret = None

        # 如果查询到设施
        facilities = []
        if ret:
            for facility in ret:
                facilities.append(facility["hf_facility_id"])
        data["facilities"] = facilities

        # 3.3 查询评论信息
        sql = "select oi_comment,up_name,oi_utime,up_mobile from ih_order_info inner join ih_user_profile " \
              "on oi_user_id=up_user_id where oi_house_id=%s and oi_status=4 and oi_comment is not null"

        try:
            ret = self.db.query(sql, house_id)
        except Exception as e:
            logging.error(e)
            ret = None
        comments = []
        if ret:
            for comment in ret:
                comments.append(dict(
                    user_name=comment["up_name"] if comment["up_name"] != comment["up_mobile"] else "匿名用户",
                    content=comment["oi_comment"],
                    ctime=comment["oi_utime"].strftime("%Y-%m-%d %H:%M:%S")
                ))
        data["comments"] = comments

        # 4. 返回数据
        self.write(dict(errno=RET.OK, errmsg="OK", user_id=user_id, data=data))
