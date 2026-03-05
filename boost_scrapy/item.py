# coding=utf-8
"""
boost_scrapy.item - Item 数据项

类似 Scrapy 的 Item，用于定义爬取的数据结构。
"""

from sqlmodel import SQLModel


class Item(SQLModel):
    """
    数据项基类 - 继承自 SQLModel
    
    终端用户定义的 Item 应继承此类，例如:
        class NewsItem(Item, table=True):
            ...
    
    提供了方便的序列化方法:
    - to_dict()
    - to_json()
    - to_pretty_json()
    """
    
    def to_dict(self) -> dict:
        """转换为字典 (兼容 Pydantic v1/v2)"""
        # Pydantic v2 / SQLModel forward compatible
        if hasattr(self, 'model_dump'):
            return self.model_dump()
        # Pydantic v1 / Old SQLModel
        return self.dict()
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    def to_pretty_json(self) -> str:
        """转换为格式化的 JSON 字符串"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=4)
    
    def __getitem__(self, key):
        """兼容字典式访问 item['key']"""
        return getattr(self, key)
    
    def __setitem__(self, key, value):
        """兼容字典式赋值 item['key'] = value"""
        setattr(self, key, value)
    
    def get(self, key, default=None):
        """兼容 dict.get()"""
        return getattr(self, key, default)
