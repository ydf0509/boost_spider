# coding=utf-8
"""
boost_scrapy.pipeline - Pipeline 数据入库管道

类似 Scrapy 的 Pipeline，用于处理 Item 数据入库。
"""

from typing import TYPE_CHECKING
from boost_scrapy.log import logger
from boost_scrapy.item import Item


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
    

        
        return item
    
    def close_spider(self, spider: 'Spider'):
        """
        爬虫关闭时调用
        
        可在此处释放资源。
        
        Args:
            spider: 爬虫实例
        """
        pass


class ConsolePipeline(Pipeline):
    """
    打印 Pipeline - 仅打印 Item 用于调试
    """
    
    def process_item(self, item: 'Item', spider: 'Spider') -> 'Item':
        # 此时 item 已经是 boost_scrapy.Item (Engine 已处理)
        # 直接使用 Item 的方法获取漂亮打印的 JSON
        logger.info(f"  👀 [Console] {type(item).__name__}:\n{item.to_pretty_json()}")
        return item


class SQLModelPipeline(Pipeline):
    """
    SQLModel Pipeline - 自动保存 SQLModel Item 到数据库
    
    1. 自动根据 Item 定义创建表
    2. 自动保存数据 (Session.add / commit) ，不需要学scrapy那样，在pipeline手写insert语句。
    """
    
    def __init__(self, db_url: str):
        """
        Args:
            db_url: 数据库连接字符串 (必填)
        """
        try:
            from sqlmodel import create_engine
        except ImportError:
            raise ImportError("SQLModelPipeline requires 'sqlmodel' to be installed.")
        
        self.db_url = db_url
        self.engine = None
        self.item_count = {} # 统计每种 Item 的数量
    
    def open_spider(self, spider):
        """爬虫启动时创建数据库连接和表"""
        from boost_scrapy.item import Item
        from sqlmodel import create_engine
        
        logger.info(f"[SQLModelPipeline] 连接数据库: {self.db_url}")
        connect_args = {"check_same_thread": False} if "sqlite" in self.db_url else {}
        self.engine = create_engine(self.db_url, connect_args=connect_args)
        
        # 自动创建表
        logger.info("[SQLModelPipeline] 正在检查并创建数据库表...")
        Item.metadata.create_all(self.engine)
        logger.info("[SQLModelPipeline] 数据库表已就绪")
    
    def process_item(self, item, spider):
        """处理 Item，保存到数据库"""
        from sqlmodel import Session
        
        # 强制 Item 为 boost_scrapy.Item
        
        if not isinstance(item, Item):
             logger.warning(f"  ⚠️ [SQLModelPipeline] 忽略非 Item 对象: {type(item)}")
             return item

        with Session(self.engine) as session:
            item_json = item.to_json()
            session.add(item)
            session.commit()
            
            # 统计数量
            name = type(item).__name__
            self.item_count[name] = self.item_count.get(name, 0) + 1
            
            logger.info(f"  💾 [SQLModel] 保存 {name} {item_json}")
        
        return item
    
    def close_spider(self, spider):
        """爬虫关闭时操作"""
        logger.info("-" * 60)
        logger.info(f"[SQLModelPipeline] 数据保存统计")
        for name, count in self.item_count.items():
            logger.info(f"  {name}: {count} 条")
        logger.info(f"  数据库: {self.db_url}")
        logger.info("-" * 60)
