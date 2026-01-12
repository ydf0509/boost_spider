# coding=utf-8
"""
boost_scrapy.response - Response 响应封装

独立实现，不依赖 boost_spider，提供 xpath/css/json 解析功能。
"""

import re
from typing import Dict, Any, Optional, TYPE_CHECKING

import requests
from parsel import Selector

if TYPE_CHECKING:
    from boost_scrapy.request import Request


class Response:
    """
    响应对象 - 独立实现，不依赖 boost_spider
    
    提供以下功能：
    - xpath(query): XPath 选择器
    - css(query): CSS 选择器
    - resp_dict: 自动解析 JSON
    - re_search(pattern): 正则搜索
    - re_findall(pattern): 正则查找全部
    - selector: parsel.Selector 对象
    - meta: 从 Request 传递的上下文数据
    - request: 关联的 Request 对象
    """
    
    # 正则模式缓存
    _re_pattern_cache = {}
    
    def __init__(
        self, 
        resp: requests.Response, 
        meta: Optional[Dict[str, Any]] = None,
        request: Optional['Request'] = None
    ):
        """
        初始化 Response 对象
        
        Args:
            resp: requests.Response 原始响应对象
            meta: 从 Request 传递的上下文数据
            request: 关联的 Request 对象
        """
        # 复制 requests.Response 的核心属性
        self._response = resp
        self.status_code = resp.status_code
        self.url = resp.url
        self.headers = resp.headers
        self.cookies = resp.cookies
        self.encoding = resp.encoding
        self.content = resp.content
        
        # boost_scrapy 扩展属性
        self._meta = meta or {}
        self._request = request
        
        # 延迟初始化
        self._selector = None
        self._text = None
        self._resp_dict = None
    
    @property
    def text(self) -> str:
        """获取响应文本"""
        if self._text is None:
            self._text = self._response.text
        return self._text
    
    @property
    def selector(self) -> Selector:
        """获取 parsel.Selector 对象"""
        if self._selector is None:
            self._selector = Selector(text=self.text)
        return self._selector
    
    @property
    def resp_dict(self) -> Any:
        """自动解析 JSON 响应"""
        if self._resp_dict is None:
            try:
                self._resp_dict = self._response.json()
            except Exception:
                self._resp_dict = {}
        return self._resp_dict
    
    @property
    def meta(self) -> Dict[str, Any]:
        """获取传递的上下文数据"""
        return self._meta
    
    @property
    def request(self) -> Optional['Request']:
        """获取关联的 Request 对象"""
        return self._request
    
    def xpath(self, query: str):
        """
        XPath 选择器
        
        Args:
            query: XPath 表达式
        
        Returns:
            SelectorList 对象
        """
        return self.selector.xpath(query)
    
    def css(self, query: str):
        """
        CSS 选择器
        
        Args:
            query: CSS 选择器表达式
        
        Returns:
            SelectorList 对象
        """
        return self.selector.css(query)
    
    def re_search(self, pattern: str, flags: int = 0):
        """
        正则搜索（返回第一个匹配）
        
        Args:
            pattern: 正则表达式
            flags: 正则标志
        
        Returns:
            Match 对象或 None
        """
        cache_key = (pattern, flags)
        if cache_key not in self._re_pattern_cache:
            self._re_pattern_cache[cache_key] = re.compile(pattern, flags)
        return self._re_pattern_cache[cache_key].search(self.text)
    
    def re_findall(self, pattern: str, flags: int = 0):
        """
        正则查找全部
        
        Args:
            pattern: 正则表达式
            flags: 正则标志
        
        Returns:
            匹配列表
        """
        cache_key = (pattern, flags)
        if cache_key not in self._re_pattern_cache:
            self._re_pattern_cache[cache_key] = re.compile(pattern, flags)
        return self._re_pattern_cache[cache_key].findall(self.text)
    
    def json(self) -> Any:
        """解析 JSON 响应（兼容 requests.Response.json()）"""
        return self._response.json()
    
    def __repr__(self):
        return f"<Response [{self.status_code}] {self.url}>"
