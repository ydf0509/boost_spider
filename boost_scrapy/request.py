# coding=utf-8
"""
boost_scrapy.request - Request 请求封装

类似 Scrapy 的 Request 对象，封装 URL、callback、method、headers、meta 等属性。
"""

from typing import Callable, Dict, Any, Optional


class Request:
    """
    请求对象 - 类似 Scrapy 的 Request
    
    使用示例:
        yield Request(
            url="http://example.com",
            callback=self.parse,
            method='GET',
            headers={'User-Agent': 'xxx'},
            meta={'page': 1},
        )
    """
    
    def __init__(
        self,
        url: str,
        callback: Callable = None,
        method: str = 'GET',
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        meta: Optional[Dict[str, Any]] = None,
        dont_filter: bool = False,
        priority: int = 0,
        **kwargs  # 额外参数: data, json, params, timeout 等
    ):
        """
        初始化 Request 对象
        
        Args:
            url: 请求 URL
            callback: 响应回调函数
            method: 请求方法 (GET, POST, PUT, DELETE 等)
            headers: 请求头
            cookies: Cookie
            meta: 传递给回调函数的上下文数据
            dont_filter: 是否跳过去重过滤
            priority: 优先级（数值越大优先级越高）
            **kwargs: 额外请求参数（如 data, json, params, timeout）
        """
        self.url = url
        self.callback = callback
        self.method = method.upper()
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.meta = meta or {}
        self.dont_filter = dont_filter
        self.priority = priority
        self.kwargs = kwargs  # data, json, params, timeout 等
        
        # 内部属性：关联的 Spider 实例（由 Engine 设置）
        self._spider = None
    
    def __repr__(self):
        return f"<Request [{self.method}] {self.url}>"
    
    def copy(self) -> 'Request':
        """创建请求的副本"""
        return Request(
            url=self.url,
            callback=self.callback,
            method=self.method,
            headers=self.headers.copy(),
            cookies=self.cookies.copy(),
            meta=self.meta.copy(),
            dont_filter=self.dont_filter,
            priority=self.priority,
            **self.kwargs
        )
    
    def replace(self, **kwargs) -> 'Request':
        """创建请求的副本并替换指定属性"""
        new_request = self.copy()
        for key, value in kwargs.items():
            if hasattr(new_request, key):
                setattr(new_request, key, value)
            else:
                new_request.kwargs[key] = value
        return new_request
