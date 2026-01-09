# -*- coding: utf-8 -*-
"""
================================================================================
                新闻爬虫 - 使用 Celery 分布式任务队列实现
================================================================================

🎯 本文件目的：
   使用 Celery 框架实现新闻爬虫，与 Funboost + boost_spider 形成对比。
   展示 Celery 作为分布式任务队列在爬虫场景下与 Funboost 的差异。

================================================================================
                    ⚠️ Celery 实现的痛点对比
================================================================================

📊 与 Funboost 对比：
┌─────────────────────────┬────────────────────────────────┬────────────────────────────────┐
│       对比项            │           Celery               │     Funboost + boost_spider    │
├─────────────────────────┼────────────────────────────────┼────────────────────────────────┤
│ 项目结构                │ 需要多个文件(app/tasks/config) │ ⭐ 单文件即可运行              │
│ 启动方式                │ 需要单独启动 worker 进程       │ ⭐ .consume() 一行代码         │
│ 中间件选择              │ 主要 Redis/RabbitMQ            │ ⭐ 40+ 种中间件               │
│ 精确流控(QPS)           │ rate_limit 近似控制            │ ⭐ qps=5 精确到毫秒            │
│ 分布式流控              │ 需要自己实现                   │ ⭐ 内置分布式 QPS 控制         │
│ 任务去重                │ 需要自己实现                   │ ⭐ do_task_filtering=True     │
│ 分组启动                │ 需要配置 queue 路由            │ ⭐ booster_group 一个参数     │
│ 外部动态注入            │ ⚠️ 可以但需 apply_async       │ ⭐ .push() 更简洁             │
│ 监控面板                │ 需要单独部署 Flower            │ ⭐ 内置 Web 管理面板           │
│ RPC 获取结果            │ AsyncResult 异步获取           │ ⭐ 原生 RPC 模式更简洁         │
│ 定时任务                │ celery-beat 单独进程           │ ⭐ 内置 APScheduler           │
│ 消息确认机制            │ ack_late 配置                  │ ⭐ ACK_ABLE 中间件原生支持    │
│ 代理/UA管理             │ 需要自己实现                   │ ⭐ RequestClient 一行代码     │
│ 数据保存                │ 需要自己实现                   │ ⭐ DatasetSink 一行代码       │
│ 配置复杂度              │ 需要单独配置文件               │ ⭐ 装饰器参数集中配置          │
└─────────────────────────┴────────────────────────────────┴────────────────────────────────┘

💔 Celery 的主要问题：
   1. 需要单独的 worker 进程（celery -A tasks worker）
   2. 需要单独的配置文件
   3. 没有内置的精确 QPS 控制
   4. 没有内置的任务去重
   5. 监控需要额外部署 Flower

================================================================================
"""

# ==========================================
# 💔 Celery 痛点 1：需要创建 Celery 应用实例
# ==========================================
# 🌟 Funboost 对比：直接使用 @boost 装饰器，无需创建应用实例
from celery import Celery
import requests
import sqlite3
import os
import random
from threading import Lock
import json

# ==========================================
# 💔 Celery 痛点 2：需要配置 broker 和 backend
# ==========================================
# 🌟 Funboost 对比：broker_kind=BrokerEnum.REDIS_ACK_ABLE 一个参数
app = Celery(
    'news_crawler',
    broker='redis://localhost:6379/1',      # 消息代理
    backend='redis://localhost:6379/2',     # 结果存储
)

# ==========================================
# 💔 Celery 痛点 3：需要单独的配置
# ==========================================
# 🌟 Funboost 对比：所有配置在 @boost(BoosterParams(...)) 一个地方
app.conf.update(
    # 任务序列化格式
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # 时区
    timezone='Asia/Shanghai',
    enable_utc=True,
    
    # 重试配置
    # 💔 Celery：需要在任务中手动处理重试
    # 🌟 Funboost：max_retry_times=3 一个参数
    task_acks_late=True,  # 任务完成后才确认
    task_reject_on_worker_lost=True,
    
    # 并发配置
    # 💔 Celery：启动 worker 时用 -c 参数指定
    # 🌟 Funboost：concurrent_num=10 一个参数
    worker_concurrency=10,
    
    # 💔 Celery 痛点 4：rate_limit 是近似控制，不精确
    # 🌟 Funboost：qps=5 精确到毫秒级
    # task_default_rate_limit='5/s',  # 近似每秒5个
    
    # 队列路由
    # 💔 Celery 痛点 5：需要配置复杂的队列路由
    # 🌟 Funboost：queue_name 直接指定
    task_routes={
        'celery_crawler.crawl_list_page': {'queue': 'list_page'},
        'celery_crawler.crawl_detail_page': {'queue': 'detail_page'},
        'celery_crawler.crawl_comments_page': {'queue': 'comments_page'},
    },
)

# ================= 配置 =================
BASE_URL = "http://127.0.0.1:7000"

# ==========================================
# 💔 Celery 痛点 6：需要自己实现任务去重
# ==========================================
# 🌟 Funboost 对比：do_task_filtering=True 一个参数
crawled_detail_ids = set()
crawled_detail_lock = Lock()
crawled_comment_keys = set()
crawled_comment_lock = Lock()

# ==========================================
# 💔 Celery 痛点 7：需要自己实现数据保存
# ==========================================
# 🌟 Funboost 对比：DatasetSink.save() 一行代码
db_lock = Lock()
db_path = os.path.join(os.path.dirname(__file__), 'celery_crawled_data.db')

def init_database():
    """初始化数据库"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news_detail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id INTEGER,
            title TEXT,
            author TEXT,
            publish_time TEXT,
            content TEXT
        )
    ''')
    cursor.execute('''
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
    conn.commit()
    conn.close()
    print("💔 [Celery] 数据库初始化完成")

def save_news_to_db(news_data):
    with db_lock:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO news_detail (news_id, title, author, publish_time, content)
            VALUES (?, ?, ?, ?, ?)
        ''', (news_data['news_id'], news_data['title'], news_data['author'],
              news_data['publish_time'], news_data['content']))
        conn.commit()
        conn.close()

def save_comment_to_db(comment_data):
    with db_lock:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO comments (news_id, news_title, page, comment_id, author, time, content, likes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (comment_data['news_id'], comment_data['news_title'], comment_data['page'],
              comment_data['comment_id'], comment_data['author'], comment_data['time'],
              comment_data['content'], comment_data['likes']))
        conn.commit()
        conn.close()

# ==========================================
# 💔 Celery 痛点 8：需要自己实现动态 UA
# ==========================================
# 🌟 Funboost 对比：RequestClient(is_change_ua_every_request=True)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

def get_random_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }


# ==========================================
# Celery 任务定义
# ==========================================

@app.task(
    bind=True,              # 绑定任务实例
    max_retries=3,          # 最大重试次数
    default_retry_delay=1,  # 重试延迟
    # 💔 Celery 痛点 9：rate_limit 是近似控制
    # 🌟 Funboost：qps=2 精确每秒2次
    rate_limit='2/s',
)
def crawl_list_page(self, page: int = 1, size: int = 10):
    """
    爬取新闻列表页
    
    💔 Celery 痛点 10：任务定义需要 @app.task 装饰器 + 各种参数
    🌟 Funboost 对比：
       @boost(BoosterParams(
           queue_name="list_page",
           qps=2,
           concurrent_num=5,
       ))
       def crawl_list_page(page, size): ...
       
       配置更简洁，参数更直观！
    
    💔 Celery 痛点 11：bind=True + self 才能访问任务上下文
    🌟 Funboost 对比：fct (Funboost Current Task) 上下文直接可用
    """
    url = f"{BASE_URL}/news/list?page={page}&size={size}"
    print(f"[列表页] 正在爬取: {url}")
    
    try:
        response = requests.get(url, headers=get_random_headers(), timeout=10)
        response.raise_for_status()
        news_list = response.json()
        
        print(f"[列表页] 获取到 {len(news_list)} 条新闻")
        
        # 💔 Celery 痛点 12：推送子任务需要 .delay() 或 .apply_async()
        # 🌟 Funboost 对比：crawl_detail_page.push(news_id=xxx) 更直观
        for news_item in news_list:
            news_id = news_item["id"]
            title = news_item["title"]
            print(f"  -> 发现新闻 [ID: {news_id}] {title}")
            
            # 使用 delay 推送任务
            crawl_detail_page.delay(news_id=news_id, title=title)
        
        return {"status": "success", "page": page, "count": len(news_list)}
    
    except Exception as e:
        print(f"[列表页] 爬取失败: {e}")
        # 💔 Celery 痛点 13：需要手动调用 retry
        # 🌟 Funboost 对比：抛出异常自动重试
        raise self.retry(exc=e)


@app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=1,
    rate_limit='5/s',
)
def crawl_detail_page(self, news_id: int, title: str):
    """
    爬取新闻详情页
    
    💔 Celery 痛点 14：没有内置的任务去重功能
    🌟 Funboost 对比：
       do_task_filtering=True,              # 开启去重
       task_filtering_expire_seconds=600,   # 过期时间
    """
    # 手动去重逻辑
    with crawled_detail_lock:
        if news_id in crawled_detail_ids:
            print(f"  💔 [Celery] 跳过已爬取: news_id={news_id}")
            return None
        crawled_detail_ids.add(news_id)
    
    url = f"{BASE_URL}/news/{news_id}"
    print(f"[详情页] 正在爬取: {url}")
    
    try:
        response = requests.get(url, headers=get_random_headers(), timeout=10)
        response.raise_for_status()
        news_detail = response.json()
        
        content = news_detail.get("content", "")
        author = news_detail.get("author", "未知")
        publish_time = news_detail.get("publish_time", "未知")
        
        print("=" * 60)
        print(f"[爬取成功] 新闻ID: {news_id}")
        print(f"标题: {title}")
        print(f"作者: {author}")
        print("=" * 60)
        
        # 保存到数据库
        save_news_to_db({
            "news_id": news_id,
            "title": title,
            "author": author,
            "publish_time": publish_time,
            "content": content,
        })
        print("  💔 [Celery] 保存新闻到 SQLite（需自己写保存函数）")
        
        # 推送评论页任务
        for page in range(1, 3):
            crawl_comments_page.delay(news_id=news_id, title=title, page=page)
            print(f"  -> 已推送: 爬取新闻{news_id}的第{page}页评论")
        
        return {"status": "success", "news_id": news_id}
    
    except Exception as e:
        print(f"[详情页] 爬取失败 (ID: {news_id}): {e}")
        raise self.retry(exc=e)


@app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=1,
    rate_limit='10/s',
)
def crawl_comments_page(self, news_id: int, title: str, page: int = 1, size: int = 10):
    """
    爬取新闻评论页
    
    💔 Celery 痛点 15：没有内置的 XPath/CSS 解析
    🌟 Funboost 对比：SpiderResponse.xpath() 开箱即用
    """
    # 手动去重
    cache_key = f"{news_id}_{page}"
    with crawled_comment_lock:
        if cache_key in crawled_comment_keys:
            print(f"  💔 [Celery] 跳过已爬取: {cache_key}")
            return None
        crawled_comment_keys.add(cache_key)
    
    url = f"{BASE_URL}/news/{news_id}/comments?page={page}&size={size}"
    print(f"[评论页] 正在爬取: {url}")
    
    try:
        response = requests.get(url, headers=get_random_headers(), timeout=10)
        response.raise_for_status()
        
        # 需要手动安装和使用 lxml 解析
        from lxml import etree
        html = etree.HTML(response.text)
        comment_items = html.xpath('//div[@class="comment-item"]')
        
        print(f"[评论页] 找到 {len(comment_items)} 条评论")
        
        for item in comment_items:
            comment_id = item.get('data-id')
            author = item.xpath('.//span[@class="author"]/text()')
            author = author[0] if author else None
            time_str = item.xpath('.//span[@class="time"]/text()')
            time_str = time_str[0] if time_str else None
            content = item.xpath('.//p[@class="text"]/text()')
            content = content[0] if content else None
            likes = item.xpath('.//span[@class="likes"]/text()')
            likes = likes[0] if likes else None
            
            save_comment_to_db({
                "news_id": news_id,
                "news_title": title,
                "page": page,
                "comment_id": comment_id,
                "author": author,
                "time": time_str,
                "content": content,
                "likes": likes,
            })
            
            print(f"  📝 评论#{comment_id} | {author}")
        
        print(f"[评论爬取成功] 新闻ID: {news_id}, 第{page}页, 共 {len(comment_items)} 条")
        return {"status": "success", "news_id": news_id, "page": page}
    
    except Exception as e:
        print(f"[评论页] 爬取失败: {e}")
        raise self.retry(exc=e)


# ================= 入口 =================
if __name__ == "__main__":
    print()
    print("=" * 70)
    print("            新闻爬虫 - Celery 分布式任务队列实现")
    print("=" * 70)
    print()
    print("⚠️ Celery 的使用步骤（比 Funboost 复杂得多）：")
    print()
    print("💔 步骤 1：启动 Redis")
    print("   redis-server")
    print()
    print("💔 步骤 2：启动 news_server.py")
    print("   python news_server.py")
    print()
    print("💔 步骤 3：启动 Celery Worker（需要单独的终端）")
    print("   celery -A celery_crawler worker -l info -Q list_page,detail_page,comments_page")
    print()
    print("💔 步骤 4：发布初始任务（又一个终端）")
    print("   python -c \"from celery_crawler import *; [crawl_list_page.delay(page=i) for i in range(1,4)]\"")
    print()
    print("💔 步骤 5：（可选）启动 Flower 监控")
    print("   celery -A celery_crawler flower")
    print()
    print("=" * 70)
    print()
    print("🌟 Funboost 对比（简洁得多）：")
    print()
    print("   # 只需要一个文件，运行一次即可：")
    print("   python boost_spider_crawler.py")
    print()
    print("   # 内部代码也更简洁：")
    print("   from funboost import boost, BoosterParams, BrokerEnum")
    print()
    print("   @boost(BoosterParams(")
    print("       queue_name='list_page',")
    print("       broker_kind=BrokerEnum.REDIS_ACK_ABLE,")
    print("       qps=2,")
    print("       concurrent_num=5,")
    print("       do_task_filtering=True,")
    print("   ))")
    print("   def crawl_list_page(page, size): ...")
    print()
    print("   crawl_list_page.consume()  # 启动消费")
    print("   crawl_list_page.push(page=1)  # 发布任务")
    print()
    print("=" * 70)
    print()
    print("💔 Celery 的 15 个痛点总结：")
    print("   1. 需要创建 Celery 应用实例")
    print("   2. 需要配置 broker 和 backend")
    print("   3. 需要单独的配置文件/配置项")
    print("   4. rate_limit 是近似控制，不精确")
    print("   5. 需要配置复杂的队列路由")
    print("   6. 需要自己实现任务去重")
    print("   7. 需要自己实现数据保存")
    print("   8. 需要自己实现动态 UA")
    print("   9. rate_limit 近似 QPS 控制")
    print("   10. 任务装饰器参数繁多")
    print("   11. bind=True + self 才能访问上下文")
    print("   12. 推送子任务需要 .delay()/.apply_async()")
    print("   13. 需要手动调用 retry")
    print("   14. 没有内置任务去重")
    print("   15. 没有内置 XPath/CSS 解析")
    print()
    print("🌟 Funboost 只需要：")
    print("   @boost(BoosterParams(...)) + .consume() + .push()")
    print("   一切自动处理！")
    print("=" * 70)
    
    # 初始化数据库
    init_database()
    
    print()
    print("请按照上述步骤在多个终端中启动 Celery Worker...")
