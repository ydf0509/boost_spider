"""
boost_spider
是一款自由奔放写法的爬虫框架，无任何束缚，和用户手写平铺直叙的爬虫函数一样，
是横冲直撞的思维写的, 不需要callback回调解析方法, 不需要继承BaseSpider类, 没有BaseSpider类, 大开大合自由奔放.
只需要加上boost装饰器就可以自动加速并发，控制手段比传统爬虫框架多太多
"""

from boost_spider.http.request_client import RequestClient
from boost_spider.sink.momgo_sink import MongoSink
from boost_spider.sink.mysql_sink import MysqlSink
from funboost import *

import json
import re