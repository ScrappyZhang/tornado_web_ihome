"""URl路由"""
'''
@Time    : 2018/4/8 下午2:43
@Author  : scrappy_zhang
@File    : urls.py
'''

import os
from handlers.BaseHandler import StaticFileBaseHandler as StaticFileHandler
from handlers import verifycode, passport, house, profile, order

urls = [
    (r'^/register$', passport.RegisterHandler),  # 注册
    (r'/login$', passport.LoginHandler),  # 登录、退出、登录校验
    (r'^/users$', profile.ProfileHandler),  # 获取个人信息
    (r'^/user/avatar$', profile.AvatarHandler),  # 用户头像
    (r'^/user/name$', profile.NameHandler),  # 用户名修改
    (r'^/user/auth$', profile.AuthHandler),  # 实名认证
    (r'^/user/houses$', profile.HouseSourceHandler),  # 房东房源
    (r"^/house$", house.NewHouseHandler),  # 发布新房源之文字信息
    (r"^/house/(?P<house_id>\d+)/images$", house.NewHouseImageHandler),  # 发布新房源之图片信息
    (r'^/house/areas$', house.AreaInfoHandler),  # 获取城区信息
    (r'^/house/index$', house.HouseIndexHandler),  # 获取首页展示的房源
    (r'^/house/(?P<house_id>\d+)$', house.DetailHouseInfoHandler),  # 房屋详情页
    (r'^/order$', order.OrderHandler),  # 下单
    (r'^/order/list$',order.OrderListHandler), # 订单页 房东与客户
    (r'^/order/(?P<order_id>\d+)/status$', order.OrderStatusHandler),  # 接单与拒单
    (r'^/image_code$', verifycode.ImageCodeHandler),  # 图片验证码
    (r'^/smscode$', verifycode.SmsCodeHandler),  # 短信验证码
    (r'/(.*)', StaticFileHandler,
     dict(path=os.path.join(os.path.dirname(__file__), "static/html"), default_filename="index.html")),
]
