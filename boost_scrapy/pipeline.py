# coding=utf-8
"""
boost_scrapy.pipeline - Pipeline 数据入库管道

类似 Scrapy 的 Pipeline，用于处理 Item 数据入库。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from boost_scrapy.item import Item
    from boost_scrapy.spider import Spider


class Pipeline:
    """
    数据入库管道基类 - 类似 Scrapy Pipeline
    
    使用示例:
        class SQLitePipeline(Pipeline):
            def open_spider(self, spider):
                self.conn = sqlite3.connect('data.db')
            
            def process_item(self, item, spider):
                # 入库逻辑
                return item
            
            def close_spider(self, spider):
                self.conn.close()
    """
    
    def open_spider(self, spider: 'Spider'):
        """
        爬虫启动时调用
        
        可在此处初始化数据库连接等资源。
        
        Args:
            spider: 爬虫实例
        """
        pass
    
    def process_item(self, item: 'Item', spider: 'Spider') -> 'Item':
        """
        处理每个 Item
        
        可在此处进行数据清洗、入库等操作。
        
        Args:
            item: 数据项
            spider: 爬虫实例
        
        Returns:
            处理后的 Item（可返回 None 表示丢弃该 Item）
        """
        return item
    
    def close_spider(self, spider: 'Spider'):
        """
        爬虫关闭时调用
        
        可在此处释放资源。
        
        Args:
            spider: 爬虫实例
        """
        pass


class PrintPipeline(Pipeline):
    """
    打印 Pipeline - 仅打印 Item 用于调试
    """
    
    def process_item(self, item: 'Item', spider: 'Spider') -> 'Item':
        print(f"[Pipeline] {type(item).__name__}: {dict(item)}")
        return item
