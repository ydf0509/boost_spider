# -*- coding: utf-8 -*-
"""
================================================================================
                 Scrapy 新闻爬虫实现 —— 与 Funboost 爬虫的对比学习
================================================================================

🎯 本文件目的：
   使用 Scrapy 框架实现同样的新闻爬虫功能，与 boost_spider_imp/boost_spider_crawler.py 形成对比。
   通过大量注释说明两个框架在各方面的差异，帮助理解 Funboost + boost_spider 的优势。

📊 功能对比表（同样的爬取需求，不同的实现方式）：
   ┌──────────────────────┬──────────────────────────────┬──────────────────────────────┐
   │       对比项         │          Scrapy              │     Funboost + boost_spider  │
   ├──────────────────────┼──────────────────────────────┼──────────────────────────────┤
   │ 项目结构             │ 需要标准项目结构，多个文件   │ ⭐ 单文件即可运行            │
   │ 分布式能力           │ 需安装 scrapy-redis 插件     │ ⭐ 原生40+中间件分布式       │
   │ 中间件选择           │ 仅 Redis/Kafka(需插件)       │ ⭐ 40+种消息队列中间件       │
   │ 任务队列             │ 内存队列，进程结束任务丢失   │ ⭐ 持久化队列，断点续爬      │
   │ 动态任务注入         │ ❌ 不支持外部实时注入二级任务 │ ⭐ 天然支持HTTP/RPC动态注入  │
   │ 精确流控(QPS)        │ 近似控制(DOWNLOAD_DELAY)     │ ⭐ 精确到毫秒级QPS控制       │
   │ 分布式流控           │ 需自己实现                   │ ⭐ 内置分布式QPS控制         │
   │ 任务去重             │ 需配置+BloomFilter           │ ⭐ 一个参数do_task_filtering │
   │ 自动重试             │ 中间件配置                   │ ⭐ 装饰器参数max_retry_times │
   │ 消息确认(ACK)        │ 需scrapy-redis支持           │ ⭐ 原生ACK，消息不丢失       │
   │ 并发模型             │ Twisted异步                  │ ⭐ 多种:线程/协程/gevent/... │
   │ 监控面板             │ 需部署Scrapyd+第三方UI       │ ⭐ 内置Web管理面板           │
   │ RPC获取结果          │ 不支持                       │ ⭐ 原生RPC模式获取结果       │
   │ 定时任务             │ 需配合cron/celery-beat       │ ⭐ 内置APScheduler集成       │
   │ 学习曲线             │ 需学Twisted/中间件/settings  │ ⭐ 装饰器一行搞定            │
   │ 爬取路径追踪         │ 复杂 callback 链             │ ⭐ 直观的函数调用链          │
   │ XPath/CSS解析        │ 内置selector                 │ ⭐ SpiderResponse同样支持    │
   │ 代理管理             │ 需自己实现中间件             │ ⭐ RequestClient内置代理管理 │
   │ Session/Cookie管理   │ 需CookiesMiddleware配置      │ ⭐ RequestClient自动管理     │
   └──────────────────────┴──────────────────────────────┴──────────────────────────────┘

================================================================================
                          ⚠️ Scrapy 实现的局限性说明
================================================================================

1. 【外部动态任务注入】（Scrapy 无法实现）
   Scrapy的任务只能从start_urls或Spider内部yield产生，不能从外部系统实时注入任务。
   
   🌟 Funboost对比：
   - 天然支持 HTTP/API/RPC 任意时刻从外部注入"二级任务"
   - 例如：用户在后台点击"立即爬取此新闻"，马上可以 crawl_detail_page.push(news_id=xxx)
   - 这是 Scrapy 架构根本无法实现的功能，是 Funboost 降维打击 Scrapy 的核心优势！

2. 【分布式部署】（Scrapy 需要额外插件）
   需要安装配置 scrapy-redis，修改settings，配置Redis连接等。
   
   🌟 Funboost对比：
   - 只需把 broker_kind 改为 BrokerEnum.REDIS_ACK_ABLE
   - 无需任何额外配置，开箱即用分布式
   - 支持40+种消息队列作为分布式后端

3. 【任务去重】（Scrapy 需要配置）
   需要在 settings 中配置 DUPEFILTER_CLASS，可能还需要 BloomFilter
   
   🌟 Funboost对比：
   - 装饰器加一个参数：do_task_filtering=True
   - 可选配置过期时间：task_filtering_expire_seconds=600

4. 【精确流控】（Scrapy 近似控制）
   Scrapy 的 DOWNLOAD_DELAY 是近似控制，不是精确 QPS
   
   🌟 Funboost对比：
   - qps=5 表示精确每秒5次
   - 支持分布式场景下的统一流控

================================================================================
"""

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.http import Request
from scrapy import signals
import json
import sqlite3  # 用于 SQLite Pipeline
import os       # 用于路径处理
import random   # 用于动态 User-Agent

# ================= 配置 =================
BASE_URL = "http://127.0.0.1:7000"

# ==========================================
# 【Scrapy 痛点 11】数据持久化需要定义 Pipeline 类
# ==========================================
# 💔 Scrapy：需要下面这么多代码来保存数据到 SQLite
# 🌟 Funboost + boost_spider 对比：
#    from boost_spider.sink.dataset_sink import DatasetSink
#    sink = DatasetSink("sqlite:///data.db")
#    sink.save("table_name", data_dict)  # 就这一行！

class SQLitePipeline:
    """
    💔 Scrapy 需要定义这个 Pipeline 类来保存数据
    
    需要：
    1. 定义 Pipeline 类
    2. 实现 open_spider / close_spider / process_item 方法
    3. 在 settings 中配置 ITEM_PIPELINES 启用
    
    🌟 Funboost 对比：sink.save("table", data) 一行代码搞定！
    """
    
    def open_spider(self, spider):
        """爬虫启动时创建数据库连接"""
        db_path = os.path.join(os.path.dirname(__file__), 'scrapy_crawled_data.db')
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
        # 创建表
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
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_id INTEGER,
                news_title TEXT,
                page INTEGER,
                comment_id TEXT,
                author TEXT,
                time TEXT,
                content TEXT,
                likes TEXT
            )
        ''')
        self.conn.commit()
        print("💔 [Scrapy Pipeline] 数据库已连接")
    
    def close_spider(self, spider):
        """爬虫结束时关闭数据库连接"""
        self.conn.close()
        print("💔 [Scrapy Pipeline] 数据库已关闭")
    
    def process_item(self, item, spider):
        """处理每个 item"""
        if item.get('type') == 'news_detail':
            self.cursor.execute('''
                INSERT INTO news_detail (news_id, title, author, publish_time, content)
                VALUES (?, ?, ?, ?, ?)
            ''', (item['news_id'], item['title'], item['author'], 
                  item['publish_time'], item['content']))
            self.conn.commit()
            print(f"  💔 [Scrapy Pipeline] 保存新闻到 SQLite: {item['news_id']}")
        
        elif item.get('type') == 'comments':
            for comment in item.get('comments', []):
                self.cursor.execute('''
                    INSERT INTO comments (news_id, news_title, page, comment_id, author, time, content, likes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (item['news_id'], item.get('title', ''), item['page'],
                      comment.get('comment_id'), comment.get('author'),
                      comment.get('time'), comment.get('content'), comment.get('likes')))
            self.conn.commit()
            print(f"  💔 [Scrapy Pipeline] 保存 {len(item.get('comments', []))} 条评论到 SQLite")
        
        return item


# ==========================================
# 【Scrapy 痛点 13】动态请求头需要定义 Middleware 类
# ==========================================
# 💔 Scrapy：需要下面这么多代码来实现动态 User-Agent
# 🌟 Funboost + boost_spider 对比：
#    client = RequestClient(is_change_ua_every_request=True)  # 就这一个参数！

# 预定义的 User-Agent 列表
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

class RandomUserAgentMiddleware:
    """
    💔 Scrapy 需要定义这个 Middleware 类来实现动态 User-Agent
    
    需要：
    1. 定义 Middleware 类
    2. 实现 process_request 方法
    3. 在 settings 中配置 DOWNLOADER_MIDDLEWARES 启用
    4. 需要禁用默认的 UserAgentMiddleware
    
    🌟 Funboost + boost_spider 对比：
       client = RequestClient(is_change_ua_every_request=True)
       只需要这一个参数！RequestClient 内置了 100+ 种 UA 随机切换
    """
    
    def process_request(self, request, spider):
        """为每个请求随机设置 User-Agent"""
        ua = random.choice(USER_AGENTS)
        request.headers['User-Agent'] = ua
        # 添加其他常见请求头
        request.headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        request.headers['Accept-Language'] = 'zh-CN,zh;q=0.9,en;q=0.8'
        request.headers['Accept-Encoding'] = 'gzip, deflate'
        request.headers['Referer'] = 'https://news.example.com/'
        print(f"  💔 [Scrapy Middleware] 设置 UA: {ua[:50]}...")
        return None  # 继续处理请求

class NewsSpider(scrapy.Spider):
    """
    Scrapy 新闻爬虫
    
    ┌─────────────────────────────────────────────────────────────────┐
    │  💔 Scrapy 的痛点 1：必须继承 Spider 类                          │
    │                                                                 │
    │  🌟 Funboost 对比：                                              │
    │  - 任何普通函数加 @boost 装饰器即可变为分布式消费函数             │
    │  - 无需继承任何类，无需遵循任何框架约定                          │
    │  - 思维方式：横冲直撞，大开大合，自由奔放                        │
    └─────────────────────────────────────────────────────────────────┘
    """
    name = 'news_spider'
    
    # ==========================================
    # 【Scrapy 痛点 2】settings 配置分散在多个地方
    # ==========================================
    # 在 Scrapy 中，配置分散在：
    #   - settings.py（全局配置）
    #   - custom_settings（Spider级别配置）
    #   - 各种中间件配置
    #
    # 🌟 Funboost 对比：
    #   - 所有配置集中在 @boost(BoosterParams(...)) 一个地方
    #   - qps、concurrent_num、max_retry_times 等一目了然
    #   - 继承 BoosterParams 还可以复用配置
    custom_settings = {
        # 并发数设置
        # 💔 Scrapy：需要在 settings 中配置
        # 🌟 Funboost：concurrent_num=10 一个参数搞定
        'CONCURRENT_REQUESTS': 10,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 10,
        
        # 下载延迟（近似流控）
        # 💔 Scrapy：DOWNLOAD_DELAY 是近似控制，不精确
        # 🌟 Funboost：qps=5 表示精确每秒5次，支持分布式统一控频
        'DOWNLOAD_DELAY': 0.2,  # 每个请求间隔0.2秒，约 5 QPS
        
        # 重试配置
        # 💔 Scrapy：需要配置中间件
        # 🌟 Funboost：max_retry_times=3 一个参数搞定
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
        
        # 日志级别
        'LOG_LEVEL': 'INFO',
        
        # ==========================================
        # 【Scrapy 痛点 3】去重需要额外配置
        # ==========================================
        # 💔 Scrapy：需要配置 DUPEFILTER_CLASS
        # 🌟 Funboost：do_task_filtering=True 一个参数
        #            task_filtering_expire_seconds=600 控制过期时间
        # 'DUPEFILTER_CLASS': 'scrapy.dupefilters.RFPDupeFilter',
        
        # ==========================================
        # 【Scrapy 痛点 12】数据持久化需要配置 ITEM_PIPELINES
        # ==========================================
        # 💔 Scrapy：需要在 settings 中配置 Pipeline
        # 🌟 Funboost：sink.save("table", data) 一行代码！
        'ITEM_PIPELINES': {
            '__main__.SQLitePipeline': 300,  # 启用 SQLite Pipeline
        },
        
        # ==========================================
        # 【Scrapy 痛点 14】动态请求头需要配置 DOWNLOADER_MIDDLEWARES
        # ==========================================
        # 💔 Scrapy：需要定义 Middleware 类 + 下面的 settings 配置
        # 🌟 Funboost：RequestClient(is_change_ua_every_request=True) 一个参数！
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,  # 禁用默认 UA
            '__main__.RandomUserAgentMiddleware': 400,  # 启用自定义动态 UA
        },
    }
    
    # 统计数据
    crawled_count = {'list': 0, 'detail': 0, 'comment': 0}
    
    def start_requests(self):
        """
        ==========================================
        【Scrapy 痛点 4】任务起点固定
        ==========================================
        Scrapy 的任务只能从 start_requests 或 start_urls 开始
        无法从外部动态注入任务
        
        🌟 Funboost 对比：
        - 任务可以从任何地方发起：crawl_list_page.push(page=1)
        - 支持 HTTP API 动态注入任务（funboost.faas）
        - 支持 RPC 远程调用发布任务
        - 支持定时任务自动发布（ApsJobAdder）
        
        ⭐ 外部系统实时动态注入"二级任务"的需求：
        假设运营人员在后台看到一条新闻需要重新爬取，他可以直接调用：
           crawl_detail_page.push(news_id=12345)
        这个任务会立即进入消息队列，等待消费者处理。
        
        💔 Scrapy 完全无法实现这种外部动态注入！
        """
        print("=" * 60)
        print("新闻爬虫 - Scrapy 实现")
        print("☠️ 对比 Funboost，Scrapy 有诸多局限性，详见代码注释")
        print("=" * 60)
        print()
        
        # 爬取前3页新闻列表
        for page in range(1, 4):
            url = f"{BASE_URL}/news/list?page={page}&size=5"
            print(f"[列表页] 发起请求: {url}")
            yield Request(
                url=url,
                callback=self.parse_list_page,
                meta={'page': page},
                # ==========================================
                # 【Scrapy 痛点 5】错误处理需要配置 errback
                # ==========================================
                # 💔 Scrapy：需要分别配置 callback 和 errback
                # 🌟 Funboost：异常自动重试，max_retry_times=3
                errback=self.handle_error,
            )
    
    def parse_list_page(self, response):
        """
        解析新闻列表页
        
        ==========================================
        【Scrapy 痛点 6】callback 回调地狱
        ==========================================
        Scrapy 的解析流程必须通过 callback 链接：
          start_requests -> parse_list_page -> parse_detail_page -> ...
        
        这种写法的问题：
          - 代码逻辑被切割成多个回调函数
          - 难以追踪完整的爬取路径
          - 传递上下文数据需要通过 meta 字典
        
        🌟 Funboost 对比：
          - 直观的函数调用链：
            crawl_list_page 中直接 crawl_detail_page.push(news_id=xxx)
          - 每个函数独立，逻辑清晰
          - 上下文通过函数参数传递，类型安全
          - 思维方式：平铺直叙，如写普通脚本
        """
        page = response.meta.get('page', 1)
        
        try:
            news_list = json.loads(response.text)
            self.crawled_count['list'] += 1
            print(f"[列表页] 获取到 {len(news_list)} 条新闻 (第{page}页)")
            
            # 遍历新闻列表，发起详情页请求
            for news_item in news_list:
                news_id = news_item['id']
                title = news_item['title']
                print(f"  -> 发现新闻 [ID: {news_id}] {title}")
                
                # 请求详情页
                detail_url = f"{BASE_URL}/news/{news_id}"
                yield Request(
                    url=detail_url,
                    callback=self.parse_detail_page,
                    # ==========================================
                    # 【Scrapy 痛点 7】meta 传参容易出错
                    # ==========================================
                    # 💔 Scrapy：通过 meta 字典传递数据，没有类型检查
                    # 🌟 Funboost：函数参数直接传递，IDE 可以检查类型
                    #            crawl_detail_page.push(news_id=news_id, title=title)
                    meta={'news_id': news_id, 'title': title},
                    errback=self.handle_error,
                )
        except Exception as e:
            print(f"[列表页] 解析失败: {e}")
    
    def parse_detail_page(self, response):
        """
        解析新闻详情页
        
        ==========================================
        【boost_spider 的 SpiderResponse 优势】
        ==========================================
        在 Funboost 爬虫中，使用 boost_spider 的 RequestClient 发请求：
        
        from boost_spider import RequestClient
        client = RequestClient(proxy_name_list=None, request_retry_times=3)
        resp = client.get(url)  # 返回 SpiderResponse 对象
        
        SpiderResponse 兼具 requests.Response 的所有功能，同时增加：
        - resp.xpath('//div[@class="xxx"]')  -> 类似 Scrapy selector
        - resp.css('div.xxx')                -> CSS 选择器
        - resp.resp_dict                     -> 自动解析 JSON
        - resp.re_search / re_findall        -> 正则匹配
        - resp.selector                      -> parsel.Selector 对象
        
        🌟 你羡慕的 Scrapy selector 功能，boost_spider 全都有！
        🌟 而且 boost_spider 的 RequestClient 还内置了：
           - 代理管理（多代理商轮换）
           - Session 管理
           - 请求重试    
           - UA 随机化
        """
        news_id = response.meta.get('news_id')
        title = response.meta.get('title')
        
        try:
            news_detail = json.loads(response.text)
            self.crawled_count['detail'] += 1
            
            content = news_detail.get('content', '')
            author = news_detail.get('author', '未知')
            publish_time = news_detail.get('publish_time', '未知')
            
            print("=" * 60)
            print(f"[爬取成功] 新闻ID: {news_id}")
            print(f"标题: {title}")
            print(f"作者: {author}")
            print(f"发布时间: {publish_time}")
            print(f"正文预览: {content[:100]}...")
            print("=" * 60)
            
            # 💔 Scrapy 需要 yield item 给 Pipeline 处理
            # 🌟 Funboost 对比：sink.save("news_detail", data) 一行代码
            yield {
                'type': 'news_detail',
                'news_id': news_id,
                'title': title,
                'author': author,
                'publish_time': publish_time,
                'content': content,
            }
            
            # 请求评论页（前2页）
            for page in range(1, 3):
                comments_url = f"{BASE_URL}/news/{news_id}/comments?page={page}&size=10"
                yield Request(
                    url=comments_url,
                    callback=self.parse_comments_page,
                    meta={'news_id': news_id, 'title': title, 'page': page},
                    errback=self.handle_error,
                )
                print(f"  -> 已发起: 爬取新闻{news_id}的第{page}页评论")
                
        except Exception as e:
            print(f"[详情页] 解析失败 (ID: {news_id}): {e}")
    
    def parse_comments_page(self, response):
        """
        解析评论页（使用 XPath）
        
        ==========================================
        【XPath/CSS 解析对比】
        ==========================================
        
        Scrapy 内置强大的 Selector：
          response.xpath('//div[@class="comment-item"]')
          response.css('div.comment-item')
        
        🌟 boost_spider 的 SpiderResponse 同样支持：
          resp.xpath('//div[@class="comment-item"]')
          resp.css('div.comment-item')
        
        两者在解析能力上几乎一样强大！
        但 boost_spider 的优势在于：
          - 与 Funboost 分布式调度无缝集成
          - RequestClient 内置代理/重试/UA管理
          - 无需学习 Twisted 异步编程
        """
        news_id = response.meta.get('news_id')
        title = response.meta.get('title')
        page = response.meta.get('page')
        
        print(f"[评论页] 正在解析: 新闻{news_id} 第{page}页")
        
        # 使用 XPath 解析评论
        comment_items = response.xpath('//div[@class="comment-item"]')
        print(f"[评论页] 找到 {len(comment_items)} 条评论")
        
        comments = []
        for item in comment_items:
            comment_id = item.xpath('./@data-id').get()
            author = item.xpath('.//span[@class="author"]/text()').get()
            time_str = item.xpath('.//span[@class="time"]/text()').get()
            content = item.xpath('.//p[@class="text"]/text()').get()
            likes = item.xpath('.//span[@class="likes"]/text()').get()
            
            comment = {
                'comment_id': comment_id,
                'author': author,
                'time': time_str,
                'content': content,
                'likes': likes,
            }
            comments.append(comment)
            
            print(f"  📝 评论#{comment_id} | {author} | {time_str}")
            print(f"     内容: {content}")
            print(f"     点赞: {likes}")
        
        self.crawled_count['comment'] += 1
        
        print("=" * 60)
        print(f"[评论爬取成功] 新闻ID: {news_id}, 第{page}页")
        print(f"标题: {title}")
        print(f"共解析 {len(comments)} 条评论")
        print("=" * 60)
        
        # ==========================================
        # 【Scrapy 痛点 8】数据持久化需要 Pipeline
        # ==========================================
        # 💔 Scrapy：需要配置 ItemPipeline 处理数据
        # 🌟 boost_spider 对比：
        #    - DatasetSink：一行代码保存到 MySQL/PostgreSQL/SQLite
        #    - MongoSink：一行代码保存到 MongoDB
        #    - MysqlSink：直接保存到 MySQL
        #
        # 示例：
        #   from boost_spider import DatasetSink
        #   sink = DatasetSink('mysql://user:pass@host/db')
        #   sink.save('comments', comment_data)
        
        yield {
            'type': 'comments',
            'news_id': news_id,
            'page': page,
            'comments': comments,
        }
    
    def handle_error(self, failure):
        """
        错误处理
        
        ==========================================
        【Scrapy 痛点 9】错误处理复杂
        ==========================================
        💔 Scrapy：需要配置 errback，处理 Twisted Failure 对象
        🌟 Funboost：异常自动重试，max_retry_times=3
                   抛出 ExceptionForRetry 触发重试
                   抛出 ExceptionForRequeue 重新入队
                   抛出 ExceptionForPushToDlxqueue 推送到死信队列
        """
        print(f"[错误] 请求失败: {failure.request.url}")
        print(f"[错误] 原因: {failure.value}")
    
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider
    
    def spider_closed(self, spider):
        """爬虫关闭时输出统计"""
        print()
        print("=" * 60)
        print("爬虫运行结束 - 统计数据")
        print("=" * 60)
        print(f"列表页爬取: {self.crawled_count['list']} 页")
        print(f"详情页爬取: {self.crawled_count['detail']} 篇")
        print(f"评论页爬取: {self.crawled_count['comment']} 页")
        print()
        print("=" * 60)
        print("⚠️ Scrapy 的局限性总结：")
        print("=" * 60)
        print("1. ❌ 无法外部动态注入任务（Funboost ✅ 可以）")
        print("2. ❌ 分布式需要额外插件（Funboost ✅ 原生支持40+中间件）")
        print("3. ❌ 精确流控困难（Funboost ✅ qps=5 精确控制）")
        print("4. ❌ 任务不持久化（Funboost ✅ 支持断点续爬）")
        print("5. ❌ 配置分散（Funboost ✅ 装饰器一处配置）")
        print("6. ❌ callback 回调链复杂（Funboost ✅ 平铺直叙）")
        print("=" * 60)


# ========================================
# 【Scrapy 痛点 10】启动方式固定
# ========================================
# 💔 Scrapy：需要使用 scrapy crawl spider_name 命令
#           或者使用 CrawlerProcess 包装
#
# 🌟 Funboost 对比：
#   crawl_list_page.consume()  # 启动消费
#   BoostersManager.consume_group("news_crawler_group")  # 分组启动
#   ctrl_c_recv()  # 阻塞主线程
#
# Funboost 可以更灵活地：
#   - 单独启动某个消费函数
#   - 按分组启动一组消费函数
#   - 多进程启动提升性能

if __name__ == "__main__":
    print()
    print("=" * 60)
    print("         Scrapy 新闻爬虫 vs Funboost 爬虫")
    print("=" * 60)
    print()
    print("⚠️ 请先启动 news_server.py：")
    print("   cd demo_crawler")
    print("   python news_server.py")
    print()
    print("📖 对比 Funboost 实现请查看：")
    print("   funboost_imp/boost_spider_crawler.py")
    print()
    print("=" * 60)
    print()
    
    # 使用 CrawlerProcess 运行爬虫
    process = CrawlerProcess({
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    })
    
    process.crawl(NewsSpider)
    process.start()
