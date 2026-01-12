# coding=utf-8
"""
boost_scrapy.item - Item 数据项

类似 Scrapy 的 Item，用于定义爬取的数据结构。
"""

from typing import Any


class Item(dict):
    """
    数据项基类 - 类似 Scrapy Item
    
    继承自 dict，支持字典式访问和属性式访问。
    
    使用示例:
        class NewsItem(Item):
            pass
        
        item = NewsItem(title="新闻标题", content="内容")
        print(item['title'])    # 字典式访问
        print(item.title)       # 属性式访问（只读）
    """
    
    def __getattr__(self, name: str) -> Any:
        """支持属性式访问"""
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name: str, value: Any):
        """支持属性式赋值"""
        self[name] = value
    
    def __delattr__(self, name: str):
        """支持属性式删除"""
        try:
            del self[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    def __repr__(self):
        class_name = type(self).__name__
        items_str = ', '.join(f'{k}={v!r}' for k, v in self.items())
        return f"{class_name}({items_str})"
    
    def copy(self) -> 'Item':
        """创建 Item 的副本"""
        return type(self)(self)
