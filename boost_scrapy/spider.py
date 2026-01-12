# coding=utf-8
"""
boost_scrapy.spider - Spider 爬虫基类

类似 Scrapy 的 Spider，用户继承此类定义爬虫逻辑。
"""

from typing import Dict, Any, Generator, List, TYPE_CHECKING, Type

if TYPE_CHECKING:
    from boost_scrapy.request import Request
    from boost_scrapy.response import Response
    from boost_scrapy.pipeline import Pipeline


class Spider:
    """
    爬虫基类 - 类似 Scrapy Spider
    
    使用示例:
        class NewsSpider(Spider):
            name = "news_spider"
            custom_settings = {'concurrent_num': 5}
            
            def start_requests(self):
                yield Request("http://example.com", callback=self.parse)
            
            def parse(self, response):
                for item in response.xpath('//div'):
                    yield Request(item.xpath('./@href').get(), callback=self.parse_detail)
            
            def parse_detail(self, response):
                yield Item(title=response.xpath('//h1/text()').get())
    """
    
    # 爬虫名称（子类必须定义）
    name: str = "base_spider"
    
    # 自定义配置（可选）
    # 可配置项: concurrent_num, qps, max_retry_times, broker_kind 等
    custom_settings: Dict[str, Any] = {}
    
    # Pipeline 列表（可选）
    pipelines: List[Type['Pipeline']] = []
    
    def __init__(self):
        """初始化爬虫"""
        self._closed = False
    
    def start_requests(self) -> Generator['Request', None, None]:
        """
        初始请求生成器 - 子类必须实现
        
        yield Request 对象发起初始请求。
        
        Returns:
            Request 生成器
        
        示例:
            def start_requests(self):
                for page in range(1, 10):
                    yield Request(f"http://example.com?page={page}", callback=self.parse)
        """
        raise NotImplementedError(f"{type(self).__name__}.start_requests() must be implemented")
    
    def parse(self, response: 'Response'):
        """
        默认解析方法
        
        如果 Request 没有指定 callback，则使用此方法。
        
        Args:
            response: 响应对象
        
        Returns:
            可 yield Request 或 Item
        """
        pass
    
    def closed(self, reason: str):
        """
        爬虫关闭时回调
        
        Args:
            reason: 关闭原因
        """
        pass
    
    @classmethod
    def from_crawler(cls, **kwargs) -> 'Spider':
        """
        工厂方法 - 创建爬虫实例
        
        Args:
            **kwargs: 初始化参数
        
        Returns:
            爬虫实例
        """
        return cls(**kwargs)
    
    def __repr__(self):
        return f"<{type(self).__name__} '{self.name}'>"
