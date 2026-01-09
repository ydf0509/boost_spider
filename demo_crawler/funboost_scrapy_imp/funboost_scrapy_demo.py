# coding=utf-8
"""
================================================================================
         新闻爬虫 Demo - 使用 funboost_scrapy 框架 (Scrapy 风格)
================================================================================

🎯 本文件目的：
   演示如何使用 funboost_scrapy 框架实现 Scrapy 风格的爬虫。
   爬取流程: 列表页 -> 详情页 -> 评论页

📊 使用方式：
   1. 先启动 news_server.py:
      cd demo_crawler
      python news_server.py
   
   2. 运行本爬虫:
      cd demo_crawler/funboost_scrapy_imp
      python funboost_scrapy_demo.py

================================================================================
"""

import sys
import os

# # 确保能够导入项目模块
# project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)

import sqlite3
import random

from funboost_scrapy import Spider, Request, Item, Engine, Pipeline, Middleware


# ================= 自定义 Middleware（演示代理切换） =================

class MyProxyMiddleware(Middleware):
    """
    自定义代理中间件 - 演示用户如何从 Redis/内存 获取代理 IP
    
    用户可以根据实际情况修改 get_proxy() 方法：
    - 从 Redis 代理池获取
    - 从内存代理列表获取
    - 从第三方代理 API 获取
    """
    
    def __init__(self):
        # 模拟内存代理池（实际项目中可以从 Redis 获取）
        self.proxy_pool = [
            'http://proxy1.example.com:8080',
            'http://proxy2.example.com:8080',
            'http://proxy3.example.com:8080',
        ]
        # 如果使用 Redis:
        # import redis
        # self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    def get_proxy(self) -> str:
        """
        获取代理 IP（用户可自定义实现）
        
        示例：
        - 从内存列表随机获取
        - 从 Redis 的 set/list 获取
        - 从代理服务商 API 获取
        """
        # 方式1：从内存列表随机选一个
        proxy = random.choice(self.proxy_pool)
        
        # 方式2：从 Redis 获取（示例）
        # proxy = self.redis_client.srandmember('proxy_pool').decode()
        
        # 方式3：从代理服务商 API 获取（示例）
        # resp = requests.get('http://proxy-api.com/get')
        # proxy = resp.json()['proxy']
        
        return proxy
    
    def process_request(self, request, spider):
        """每次请求时自动设置代理"""
        proxy = self.get_proxy()
        request.kwargs['proxies'] = {'http': proxy, 'https': proxy}
        print(f"  🌐 [MyProxyMiddleware] 使用代理: {proxy}")
        return None


class MyUserAgentMiddleware(Middleware):
    """
    自定义 UA 中间件 - 演示用户如何切换 UserAgent
    """
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]
    
    def process_request(self, request, spider):
        """每次请求时随机切换 UA"""
        ua = random.choice(self.USER_AGENTS)
        request.headers['User-Agent'] = ua
        print(f"  🔄 [MyUserAgentMiddleware] UA: {ua[:50]}...")
        return None


# ================= 定义 Item =================

class NewsItem(Item):
    """新闻详情数据项"""
    pass


class CommentItem(Item):
    """评论数据项"""
    pass


# ================= 定义 Pipeline =================

class SQLitePipeline(Pipeline):
    """
    SQLite Pipeline - 保存数据到 SQLite 数据库
    
    和其他爬虫实现一样，自动创建表并保存数据。
    """
    
    def __init__(self, db_path: str = None):
        """
        Args:
            db_path: 数据库文件路径，默认使用当前目录的 funboost_scrapy_data.db
        """
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), 'funboost_scrapy_data.db')
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.news_count = 0
        self.comment_count = 0
    
    def open_spider(self, spider):
        """爬虫启动时创建数据库连接和表"""
        print(f"[SQLitePipeline] 连接数据库: {self.db_path}")
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # 创建新闻表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_detail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_id INTEGER,
                title TEXT,
                author TEXT,
                publish_time TEXT,
                content TEXT
            )
        ''')
        
        # 创建评论表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_id INTEGER,
                comment_id TEXT,
                author TEXT,
                content TEXT,
                likes TEXT
            )
        ''')
        
        self.conn.commit()
        print(f"[SQLitePipeline] 数据库表已就绪: news_detail, comments")
    
    def process_item(self, item, spider):
        """处理 Item，保存到数据库"""
        if isinstance(item, NewsItem):
            self.cursor.execute('''
                INSERT INTO news_detail (news_id, title, author, publish_time, content)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                item.get('news_id'),
                item.get('title'),
                item.get('author'),
                item.get('publish_time'),
                item.get('content'),
            ))
            self.conn.commit()
            self.news_count += 1
            print(f"  💾 [SQLite] 保存新闻: {item.get('title')[:30]}...")
            
        elif isinstance(item, CommentItem):
            self.cursor.execute('''
                INSERT INTO comments (news_id, comment_id, author, content, likes)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                item.get('news_id'),
                item.get('comment_id'),
                item.get('author'),
                item.get('content'),
                item.get('likes'),
            ))
            self.conn.commit()
            self.comment_count += 1
            print(f"  💾 [SQLite] 保存评论: #{item.get('comment_id')}")
        
        return item
    
    def close_spider(self, spider):
        """爬虫关闭时关闭数据库连接"""
        if self.conn:
            self.conn.close()
        print()
        print("=" * 60)
        print(f"[SQLitePipeline] 数据库保存统计")
        print(f"  新闻: {self.news_count} 篇")
        print(f"  评论: {self.comment_count} 条")
        print(f"  数据库: {self.db_path}")
        print("=" * 60)


class ConsolePipeline(Pipeline):
    """控制台输出 Pipeline - 打印 Item 详情（用于调试）"""
    
    def process_item(self, item, spider):
        if isinstance(item, NewsItem):
            print("=" * 60)
            print(f"[新闻] ID: {item.get('news_id')}")
            print(f"  标题: {item.get('title')}")
            print(f"  作者: {item.get('author')}")
            print(f"  时间: {item.get('publish_time')}")
            preview = item.get('content', '')[:80]
            print(f"  内容: {preview}...")
            print("=" * 60)
        elif isinstance(item, CommentItem):
            print(f"  📝 评论#{item.get('comment_id')} | {item.get('author')} | 👍{item.get('likes')}")
            print(f"     {item.get('content')}")
        return item


# ================= 定义 Spider =================

class NewsSpider(Spider):
    """
    新闻爬虫 - 使用 funboost_scrapy 实现 (Scrapy 风格)
    
    爬取流程: 列表页(JSON) -> 详情页(JSON) -> 评论页(HTML/xpath)
    
    ⭐ 核心用法:
    1. yield Request(url, callback=self.xxx) - 发起请求并指定回调
    2. response.meta['key'] - 获取传递的上下文数据
    3. response.resp_dict - 解析 JSON 响应
    4. response.xpath() / response.css() - XPath/CSS 选择器
    5. yield Item(...) - 数据自动流经 Pipeline
    """
    
    name = "news_spider"
    
    # 自定义配置（可选）
    custom_settings = {
        'concurrent_num': 5,
        'qps': 10,
        'max_retry_times': 3,
    }
    
    BASE_URL = "http://127.0.0.1:7000"
    
    def start_requests(self):
        """
        初始请求入口 - 类似 Scrapy
        
        yield Request(url, callback=self.xxx) 指定回调函数
        """
        print()
        print("=" * 60)
        print("  funboost_scrapy 新闻爬虫 Demo")
        print("  Scrapy 风格: yield Request + callback")
        print("=" * 60)
        print()
        
        # 爬取前3页列表，每页5条
        for page in range(1, 4):
            url = f"{self.BASE_URL}/news/list?page={page}&size=5"
            print(f"[发布任务] 列表页 第{page}页")
            yield Request(url, callback=self.parse_list, meta={'page': page})
    
    def parse_list(self, response):
        """
        解析列表页 - JSON 响应
        
        - response.resp_dict: 自动解析 JSON
        - response.meta: 获取传递的上下文数据
        - yield Request(...): 发起新请求
        """
        page = response.meta.get('page', 1)
        news_list = response.resp_dict
        
        print(f"[列表页] 第{page}页 获取到 {len(news_list)} 条新闻")
        
        for news in news_list:
            news_id = news["id"]
            title = news["title"]
            print(f"  -> 发现新闻 [ID: {news_id}] {title}")
            
            # yield Request 发起详情页请求
            yield Request(
                f"{self.BASE_URL}/news/{news_id}",
                callback=self.parse_detail,
                meta={'news_id': news_id, 'title': title}
            )
    
    def parse_detail(self, response):
        """
        解析详情页 - 获取新闻内容并 yield Item 入库
        
        - yield Item: 数据自动流经 Pipeline
        """
        news_id = response.meta['news_id']
        title = response.meta['title']
        news = response.resp_dict
        
        print(f"[详情页] 新闻ID: {news_id} - {title}")
        
        # yield Item - 自动流经 Pipeline
        yield NewsItem(
            news_id=news_id,
            title=title,
            author=news.get("author", "未知"),
            publish_time=news.get("publish_time", ""),
            content=news.get("content", ""),
        )
        
        # 继续爬取评论页（前2页）
        for page in range(1, 3):
            yield Request(
                f"{self.BASE_URL}/news/{news_id}/comments?page={page}&size=10",
                callback=self.parse_comments,
                meta={'news_id': news_id, 'title': title, 'page': page}
            )
            print(f"  -> 已发布: 爬取新闻{news_id}的第{page}页评论")
    
    def parse_comments(self, response):
        """
        解析评论页 - 使用 XPath 解析 HTML
        
        - response.xpath(): XPath 选择器（和 Scrapy 一样）
        - response.css(): CSS 选择器
        """
        news_id = response.meta['news_id']
        page = response.meta['page']
        
        print(f"[评论页] 新闻{news_id} 第{page}页")
        
        # 使用 xpath 解析评论 (和 Scrapy 用法一致!)
        comments = response.xpath('//div[@class="comment-item"]')
        print(f"  找到 {len(comments)} 条评论")
        
        for item in comments:
            yield CommentItem(
                news_id=news_id,
                comment_id=item.xpath('./@data-id').get(),
                author=item.xpath('.//span[@class="author"]/text()').get(),
                content=item.xpath('.//p[@class="text"]/text()').get(),
                likes=item.xpath('.//span[@class="likes"]/text()').get(),
            )
    
    def closed(self, reason):
        """爬虫关闭时回调"""
        print(f"\n[Spider] 爬虫关闭: {reason}")


# ================= 启动爬虫 =================

if __name__ == "__main__":
    print()
    print("⚠️ 请先确保 news_server.py 正在运行:")
    print("   cd demo_crawler")
    print("   python news_server.py")
    print()
    
    # 创建引擎并运行爬虫
    # - pipelines: 数据入库管道
    # - middlewares: 中间件（用户自定义，演示 UA/代理 切换）
    engine = Engine(
        # Engine 里面的入参可以放在全局字典，多个spider共享，也可以放在你的Spider的custom_settings的字典中。
        pipelines=[SQLitePipeline()],
        middlewares=[
            MyUserAgentMiddleware(),   # 🔄 自定义 UA 中间件：每次请求随机切换 UA
            # MyProxyMiddleware(),     # 🌐 自定义代理中间件：从内存/Redis 获取代理（取消注释启用）
        ],
        use_funboost=True, # use_funboost为False就使用单线程顺序爬虫，可以用于调试。
    )
    engine.run(NewsSpider)


