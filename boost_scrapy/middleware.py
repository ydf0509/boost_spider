# coding=utf-8
"""
boost_scrapy.middleware - 中间件

类似 Scrapy 的 Downloader Middleware，可以在请求发送前/响应返回后进行处理。
"""

import random
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from boost_scrapy.request import Request
    from boost_scrapy.response import Response
    from boost_scrapy.spider import Spider


# 预定义的 User-Agent 列表
USER_AGENTS = [
    # Chrome
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    # Firefox
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
    # Safari
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    # Edge
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
]


class Middleware:
    """
    中间件基类 - 类似 Scrapy Downloader Middleware
    
    使用示例:
        class MyMiddleware(Middleware):
            def process_request(self, request, spider):
                request.headers['X-Custom'] = 'value'
                return None  # 继续处理
            
            def process_response(self, request, response, spider):
                return response  # 返回响应
    """
    
    def process_request(self, request: 'Request', spider: 'Spider') -> Optional['Request']:
        """
        处理请求（请求发送前调用）
        
        Args:
            request: 请求对象
            spider: 爬虫实例
        
        Returns:
            - None: 继续处理，将请求传递给下一个中间件
            - Request: 返回新的 Request 对象
            - Response: 直接返回响应，不发送请求（用于缓存等场景）
        """
        return None
    
    def process_response(self, request: 'Request', response: 'Response', spider: 'Spider') -> 'Response':
        """
        处理响应（响应返回后调用）
        
        Args:
            request: 请求对象
            response: 响应对象
            spider: 爬虫实例
        
        Returns:
            Response 对象
        """
        return response
    
    def process_exception(self, request: 'Request', exception: Exception, spider: 'Spider'):
        """
        处理异常
        
        Args:
            request: 请求对象
            exception: 异常对象
            spider: 爬虫实例
        
        Returns:
            - None: 继续抛出异常
            - Response: 返回响应
            - Request: 重新发送请求
        """
        return None


class UserAgentMiddleware(Middleware):
    """
    随机 User-Agent 中间件
    
    每次请求自动随机切换 User-Agent。
    
    使用示例:
        engine = Engine(middlewares=[UserAgentMiddleware()])
    """
    
    def __init__(self, user_agents: list = None):
        """
        Args:
            user_agents: 自定义 UA 列表，默认使用内置列表
        """
        self.user_agents = user_agents or USER_AGENTS
    
    def process_request(self, request: 'Request', spider: 'Spider'):
        """为每个请求设置随机 User-Agent"""
        ua = random.choice(self.user_agents)
        request.headers['User-Agent'] = ua
        print(f"  🔄 [UserAgentMiddleware] UA: {ua[:50]}...")
        return None


class HeadersMiddleware(Middleware):
    """
    自定义请求头中间件
    
    使用示例:
        engine = Engine(middlewares=[
            HeadersMiddleware({
                'Referer': 'https://www.google.com',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            })
        ])
    """
    
    def __init__(self, headers: dict):
        """
        Args:
            headers: 要添加的请求头字典
        """
        self.headers = headers
    
    def process_request(self, request: 'Request', spider: 'Spider'):
        """为每个请求添加自定义请求头"""
        for key, value in self.headers.items():
            if key not in request.headers:
                request.headers[key] = value
        return None


class RetryMiddleware(Middleware):
    """
    重试中间件
    
    请求失败时自动重试。
    """
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
    
    def process_exception(self, request: 'Request', exception: Exception, spider: 'Spider'):
        """请求异常时重试"""
        retry_count = request.meta.get('_retry_count', 0)
        if retry_count < self.max_retries:
            print(f"  🔁 [RetryMiddleware] 重试 {retry_count + 1}/{self.max_retries}: {request.url}")
            new_request = request.copy()
            new_request.meta['_retry_count'] = retry_count + 1
            return new_request
        return None


class ProxyMiddleware(Middleware):
    """
    代理中间件 - 自动切换代理 IP
    
    使用示例:
        # 单个代理
        engine = Engine(middlewares=[
            ProxyMiddleware('http://127.0.0.1:8080')
        ])
        
        # 代理池（自动轮换）
        engine = Engine(middlewares=[
            ProxyMiddleware([
                'http://proxy1:8080',
                'http://proxy2:8080',
                'http://user:pass@proxy3:8080',  # 支持认证
            ])
        ])
    """
    
    def __init__(self, proxies):
        """
        Args:
            proxies: 代理配置，支持以下格式：
                - str: 单个代理，如 'http://127.0.0.1:8080'
                - list: 代理池列表，自动轮换
                - dict: requests 格式，如 {'http': 'http://proxy:8080', 'https': 'http://proxy:8080'}
        """
        if isinstance(proxies, str):
            self.proxy_list = [proxies]
        elif isinstance(proxies, list):
            self.proxy_list = proxies
        elif isinstance(proxies, dict):
            self.proxy_list = None
            self.proxy_dict = proxies
        else:
            raise ValueError("proxies must be str, list, or dict")
        
        self.index = 0
    
    def _get_proxy(self) -> dict:
        """获取代理配置（轮换）"""
        if hasattr(self, 'proxy_dict'):
            return self.proxy_dict
        
        if not self.proxy_list:
            return {}
        
        proxy = self.proxy_list[self.index % len(self.proxy_list)]
        self.index += 1
        return {'http': proxy, 'https': proxy}
    
    def process_request(self, request: 'Request', spider: 'Spider'):
        """为每个请求设置代理"""
        proxy = self._get_proxy()
        if proxy:
            request.kwargs['proxies'] = proxy
            proxy_str = list(proxy.values())[0] if proxy else 'None'
            print(f"  🌐 [ProxyMiddleware] Proxy: {proxy_str}")
        return None

