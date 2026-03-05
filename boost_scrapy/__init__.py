# coding=utf-8
"""
boost_scrapy - 基于 funboost 的 Scrapy 风格爬虫框架

将 funboost 封装成类似 Scrapy 的 yield Request 框架，
让习惯 Scrapy 写法的用户能够快速上手。

核心组件:
- Request: 请求对象，封装 URL、callback、meta 等
- Response: 响应对象，继承 SpiderResponse，支持 xpath/css
- Item: 数据项，用于定义爬取的数据结构
- Spider: 爬虫基类，提供 start_requests 和 parse 方法
- Pipeline: 数据入库管道
- Engine: 核心引擎，解析 yield 生成器并调度任务

使用示例:
    from boost_scrapy import Spider, Request, Item, Engine
    
    class NewsItem(Item):
        pass
    
    class NewsSpider(Spider):
        name = "news_spider"
        
        def start_requests(self):
            yield Request("http://example.com/list", callback=self.parse_list)
        
        def parse_list(self, response):
            for news in response.resp_dict:
                yield Request(
                    f"/detail/{news['id']}", 
                    callback=self.parse_detail,
                    meta={'id': news['id']}
                )
        
        def parse_detail(self, response):
            yield NewsItem(
                id=response.meta['id'],
                title=response.xpath('//h1/text()').get()
            )
    
    if __name__ == "__main__":
        engine = Engine()
        engine.run(NewsSpider)
"""

from boost_scrapy.request import Request
from boost_scrapy.response import Response
from boost_scrapy.item import Item
from boost_scrapy.spider import Spider
from boost_scrapy.pipeline import Pipeline, ConsolePipeline, SQLModelPipeline
from boost_scrapy.middleware import Middleware, UserAgentMiddleware, HeadersMiddleware, RetryMiddleware, ProxyMiddleware
from boost_scrapy.engine import Engine
from boost_scrapy.log import logger

__all__ = [
    'Request',
    'Response', 
    'Item',
    'Spider',
    'Pipeline',
    'SQLModelPipeline',
    'ConsolePipeline',
    'Middleware',
    'UserAgentMiddleware',
    'HeadersMiddleware',
    'RetryMiddleware',
    'ProxyMiddleware',
    'Engine',
    'logger',
]

__version__ = '0.1.0'
