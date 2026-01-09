# -*- coding: utf-8 -*-
"""
================================================================================
            新闻爬虫 - 使用 Feapder Spider 实现分布式爬取
================================================================================

🎯 本文件目的：
   演示如何使用 Feapder 框架的 Spider（分布式爬虫）实现列表页、详情页、评论页的三层爬取。
   符合 Feapder 最佳实践。

================================================================================
                        ⭐ Feapder 核心特性
================================================================================

📊 Feapder Spider 特点：
┌──────────────────────────┬────────────────────────────────────────────────────────┐
│       ⭐ 特性             │              说明                                      │
├──────────────────────────┼────────────────────────────────────────────────────────┤
│ 1. 基于Redis分布式        │ 任务存储在Redis，支持多进程/多机器分布式采集            │
│ 2. 断点续爬              │ 爬虫中断后重启，自动从上次中断处继续                    │
│ 3. 任务防丢              │ 任务做完才删除，异常退出10分钟后任务自动重新可用        │
│ 4. RANDOM_HEADERS        │ 内置1000+ User-Agent，自动随机切换                      │
│ 5. Item自动入库          │ yield Item() 自动批量入库，无需手动处理                 │
│ 6. 自定义Pipeline        │ 支持MySQL/MongoDB/自定义Pipeline                       │
│ 7. callback回调链        │ parse_list -> parse_detail -> parse_comments           │
│ 8. Request携带参数       │ Request(url, news_id=xxx) 直接携带，无需meta           │
│ 9. 内置去重              │ REQUEST_FILTER_ENABLE / ITEM_FILTER_ENABLE             │
│ 10. xpath/css/re解析     │ response.xpath/css/re 类似Scrapy                       │
└──────────────────────────┴────────────────────────────────────────────────────────┘

================================================================================
"""

import os
import sqlite3
from typing import Dict, List, Tuple

import feapder
from feapder import Item
from feapder.pipelines import BasePipeline


# ================= SQLite Pipeline =================

class SQLitePipeline(BasePipeline):
    """
    SQLite Pipeline - 自动创建表并批量入库
    
    feapder的Item会自动流经此Pipeline:
    - Item类名去掉Item后缀作为表名（如NewsDetailItem -> news_detail）
    - 自动根据Item字段创建表
    - 批量插入数据
    """
    
    def __init__(self):
        db_path = os.path.join(os.path.dirname(__file__), 'feapder_crawled_data.db')
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._created_tables = set()
        print(f"[SQLitePipeline] 数据库已连接: {db_path}")
    
    def _ensure_table(self, table: str, item: Dict):
        """确保表存在，不存在则创建"""
        if table in self._created_tables:
            return
        
        # 根据item的字段动态创建表
        columns = ', '.join([f"{k} TEXT" for k in item.keys()])
        sql = f"CREATE TABLE IF NOT EXISTS {table} (id INTEGER PRIMARY KEY AUTOINCREMENT, {columns})"
        
        cursor = self.conn.cursor()
        cursor.execute(sql)
        self.conn.commit()
        self._created_tables.add(table)
        print(f"[SQLitePipeline] 表 {table} 已就绪")
    
    def save_items(self, table: str, items: List[Dict]) -> bool:
        """批量保存数据"""
        if not items:
            return True
        
        self._ensure_table(table, items[0])
        
        cursor = self.conn.cursor()
        for item in items:
            columns = ', '.join(item.keys())
            placeholders = ', '.join(['?' for _ in item])
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            try:
                cursor.execute(sql, list(item.values()))
            except Exception as e:
                print(f"[SQLitePipeline] 插入失败: {e}")
        
        self.conn.commit()
        print(f"[SQLitePipeline] ✓ 保存 {len(items)} 条到 {table} 表")
        return True
    
    def update_items(self, table: str, items: List[Dict], update_keys: Tuple = ()) -> bool:
        """更新数据（暂不实现）"""
        return True
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            print("[SQLitePipeline] 数据库连接已关闭")


# 创建全局Pipeline实例，供Item使用
_sqlite_pipeline = SQLitePipeline()


# ================= Item 定义 =================
# Item类名去掉Item后缀 = 表名 (news_detail, comments)
# 使用 __pipelines__ 指定Pipeline实例（feapder语法）

class NewsDetailItem(Item):
    """
    新闻详情 Item - 自动入库到 news_detail 表
    
    Feapder 最佳实践：
    - 定义Item类，yield item 自动批量入库
    - __pipelines__ 指定Pipeline实例
    - __unique_key__ 可指定去重字段
    """
    __pipelines__ = [_sqlite_pipeline]  # ⭐ 使用Item的__pipelines__指定Pipeline
    __unique_key__ = ["news_id"]  # 根据 news_id 去重
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.news_id = None
        self.title = None
        self.author = None
        self.publish_time = None
        self.content = None


class CommentsItem(Item):
    """
    评论 Item - 自动入库到 comments 表
    """
    __pipelines__ = [_sqlite_pipeline]  # ⭐ 使用Item的__pipelines__指定Pipeline
    __unique_key__ = ["comment_id"]  # 根据 comment_id 去重
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.news_id = None
        self.news_title = None
        self.page = None
        self.comment_id = None
        self.author = None
        self.time = None
        self.content = None
        self.likes = None


# ================= Spider 爬虫 =================

class NewsCrawler(feapder.Spider):
    """
    Feapder 分布式新闻爬虫
    
    爬取流程: 列表页(JSON) -> 详情页(JSON) -> 评论页(HTML/xpath)
    
    ⭐ Feapder 最佳实践：
    1. 使用 Spider 类（基于Redis的分布式爬虫）
    2. 使用 __custom_setting__ 配置爬虫参数
    3. 使用 callback 指定解析函数
    4. 使用 Request(url, param=value) 携带参数
    5. 使用 yield Item() 自动入库
    """
    
    # ⭐ 爬虫配置 - 使用 __custom_setting__ 覆盖默认配置
    __custom_setting__ = dict(
        # Redis 配置（Spider必须）
        REDISDB_IP_PORTS="localhost:6379",
        REDISDB_USER_PASS="",
        REDISDB_DB=0,
        
        # 并发配置
        SPIDER_THREAD_COUNT=5,          # 并发线程数
        SPIDER_MAX_RETRY_TIMES=3,       # 最大重试次数
        SPIDER_SLEEP_TIME=0,            # 下载间隔（秒）
        
        # ⭐ 随机 User-Agent（feapder内置功能，无需自己实现！）
        RANDOM_HEADERS=True,            # 开启随机UA
        USER_AGENT_TYPE="chrome",       # UA类型：chrome/firefox/safari/mobile
        
        # 注意：Pipeline已在Item类中通过 __pipelines__ 指定，无需在这里配置
        
        # 日志
        LOG_LEVEL="INFO",
    )
    
    BASE_URL = "http://127.0.0.1:7000"
    
    def start_requests(self):
        """
        初始任务入口 - 下发列表页任务
        
        ⭐ Feapder 最佳实践：
        - yield feapder.Request(url, callback=self.xxx) 指定回调函数
        - 可以携带自定义参数：feapder.Request(url, page=1)
        """
        print("=" * 60)
        print("新闻爬虫 - Feapder Spider 分布式爬取")
        print("爬取流程: 列表页 -> 详情页 -> 评论页(xpath解析)")
        print("=" * 60)
        
        # 爬取前3页列表，每页5条
        for page in range(1, 4):
            url = f"{self.BASE_URL}/news/list?page={page}&size=5"
            print(f"[下发任务] 列表页 第{page}页: {url}")
            yield feapder.Request(url, callback=self.parse_list, page=page)
    
    def parse_list(self, request, response):
        """
        解析列表页 - JSON响应
        
        ⭐ Feapder 特性：
        - response.json 直接获取JSON数据（类似 response.json()）
        - 通过 request.page 取出携带的参数
        
        💔 Scrapy 对比：需要 response.meta['page'] 传递参数
        ✅ Funboost 对比：response.resp_dict 获取JSON
        """
        page = request.page
        
        # ⭐【Feapder 特性 1】response.json 属性直接获取JSON
        # 💔 Scrapy 对比：json.loads(response.text)
        news_list = response.json
        
        print(f"[列表页] 第{page}页 获取到 {len(news_list)} 条新闻")
        
        for news in news_list:
            news_id = news["id"]
            title = news["title"]
            print(f"  -> 发现新闻 [ID: {news_id}] {title}")
            
            # ⭐【Feapder 特性 2】Request直接携带参数，无需meta
            # 💔 Scrapy 对比：需要 meta={'news_id': news_id, 'title': title}
            # ✅ Funboost 对比：函数参数直接传递
            yield feapder.Request(
                f"{self.BASE_URL}/news/{news_id}",
                callback=self.parse_detail,
                news_id=news_id,
                title=title,
            )
    
    def parse_detail(self, request, response):
        """
        解析详情页 - JSON响应，yield Item 自动入库
        
        ⭐ Feapder 最佳实践：
        - request.news_id 取出携带的参数
        - yield Item() 自动批量入库
        
        💔 Scrapy 对比：需要定义 Item 类 + Pipeline + settings 配置
        ✅ Funboost 对比：DatasetSink.save() 一行代码入库
        """
        news_id = request.news_id
        title = request.title
        news = response.json
        
        # ⭐【Feapder 特性 3】创建 Item 并赋值
        # 💔 Scrapy 对比：同样需要定义 Item 类
        # ✅ Funboost 对比：直接使用 dict 即可
        item = NewsDetailItem()
        item.news_id = news_id
        item.title = title
        item.author = news.get("author", "未知")
        item.publish_time = news.get("publish_time", "")
        item.content = news.get("content", "")
        
        print("=" * 60)
        print(f"[详情页] 新闻ID: {news_id}")
        print(f"标题: {title}")
        print(f"作者: {item.author}")
        print(f"发布时间: {item.publish_time}")
        print(f"正文预览: {item.content[:80]}...")
        print("=" * 60)
        
        # ⭐【Feapder 特性 4】yield Item，自动批量入库到 news_detail 表
        # 💔 Scrapy 对比：需要配置 ITEM_PIPELINES，在 Pipeline 中手写 SQL
        # ✅ Funboost 对比：DatasetSink("sqlite:///data.db").save("news", data)
        yield item
        print(f"  💾 [yield Item] 将自动入库到 news_detail 表")
        
        # ⭐【Feapder 特性 5】下发评论页任务（前2页）
        # 💔 Scrapy 对比：同样使用 yield Request
        # ✅ Funboost 对比：crawl_comments_page.push()
        for page in range(1, 3):
            yield feapder.Request(
                f"{self.BASE_URL}/news/{news_id}/comments?page={page}&size=10",
                callback=self.parse_comments,
                news_id=news_id,
                title=title,
                comment_page=page,
            )
            print(f"  -> 已发布: 爬取新闻{news_id}的第{page}页评论")
    
    def parse_comments(self, request, response):
        """
        解析评论页 - HTML响应，使用 xpath 解析
        
        ⭐ Feapder 特性：
        - response.xpath() 返回 SelectorList，与 Scrapy 用法一致
        - .extract_first() 获取第一个匹配的文本
        - .extract() 获取所有匹配的文本列表
        
        💔 Scrapy 对比：用法相同
        ✅ Funboost 对比：SpiderResponse.xpath() 用法相同
        """
        news_id = request.news_id
        title = request.title
        page = request.comment_page
        
        print(f"[评论页] 正在解析: 新闻{news_id} 第{page}页")
        
        # ⭐【Feapder 特性 6】使用 xpath 解析 HTML
        # 💔 Scrapy 对比：用法完全相同
        # ✅ Funboost 对比：SpiderResponse.xpath() 同样支持
        comment_items = response.xpath('//div[@class="comment-item"]')
        print(f"[评论页] 找到 {len(comment_items)} 条评论")
        
        for elem in comment_items:
            # ⭐【Feapder 特性 7】创建 Item 并使用 xpath 提取数据
            item = CommentsItem()
            item.news_id = news_id
            item.news_title = title
            item.page = page
            
            # 提取评论ID
            item.comment_id = elem.xpath('./@data-id').extract_first()
            # 提取作者
            item.author = elem.xpath('.//span[@class="author"]/text()').extract_first()
            # 提取评论时间
            item.time = elem.xpath('.//span[@class="time"]/text()').extract_first()
            # 提取评论内容
            item.content = elem.xpath('.//p[@class="text"]/text()').extract_first()
            # 提取点赞数
            item.likes = elem.xpath('.//span[@class="likes"]/text()').extract_first()
            
            print(f"  📝 评论#{item.comment_id} | {item.author} | {item.time}")
            print(f"     内容: {item.content}")
            print(f"     点赞: {item.likes}")
            
            # ⭐【Feapder 特性 8】yield Item，自动批量入库到 comments 表
            yield item
        
        # 输出汇总
        print("=" * 60)
        print(f"[评论爬取成功] 新闻ID: {news_id}, 第{page}页")
        print(f"标题: {title}")
        print(f"共解析 {len(comment_items)} 条评论")
        print(f"  💾 [yield Item] 将自动入库到 comments 表")
        print("=" * 60)


# ================= 入口 =================
if __name__ == "__main__":
    """
    运行说明：
    
    1. 先启动 Redis:
       redis-server
    
    2. 启动 news_server.py:
       cd demo_crawler
       python news_server.py
    
    3. 运行爬虫:
       cd demo_crawler/feapder_imp
       python feapder_news_crawler.py
    
    4. 验证数据:
       sqlite3 feapder_crawled_data.db
       .tables
       SELECT COUNT(*) FROM news_detail;
       SELECT COUNT(*) FROM comments;
    """
    print("=" * 60)
    print("新闻爬虫 - Feapder Spider 分布式爬取")
    print("支持：列表页 -> 详情页 -> 评论页(xpath解析)")
    print("=" * 60)
    print()
    
    # ⭐【Feapder 特性】Spider 基于 Redis 分布式
    # 💔 Scrapy 对比：需要 scrapy-redis 插件才能分布式
    # ✅ Funboost 对比：支持 40+ 种中间件
    print("[启动] 创建 Feapder Spider 实例...")
    print("[配置] Redis: localhost:6379")
    print("[配置] 并发线程: 5")
    print("[配置] 随机UA: 开启")
    print()
    
    # delete_keys="*" 清空任务队列，重新爬取（开发调试时使用）
    # 正式环境去掉 delete_keys 参数，支持断点续爬
    spider = NewsCrawler(
        redis_key="news:feapder",  # Redis中的key前缀
        delete_keys="*",           # 开发模式：每次清空重新爬取
    )
    
    print("[启动] 开始爬取...")
    print()
    spider.start()

