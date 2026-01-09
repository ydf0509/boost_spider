# -*- coding: utf-8 -*-
"""
================================================================================
     新闻爬虫 - 使用 Redis + ThreadPoolExecutor 手动实现分布式
================================================================================

🎯 本文件目的：
   使用 Redis blpop + ThreadPoolExecutor 手动实现一个"分布式"爬虫，
   展示如果不使用 Funboost，自己实现分布式调度有多麻烦。

================================================================================
                    ⚠️ 手动实现分布式的痛点
================================================================================

这个实现需要自己手动处理：
1. Redis 连接管理
2. 3 个 while True 循环监听队列
3. 3 个独立的线程池
4. JSON 序列化/反序列化
5. 异常处理和重试逻辑
6. 任务去重
7. 数据保存
8. 优雅退出

💔 代码量：~400 行
🌟 Funboost 相同功能：~100 行（3 个 @boost 装饰的函数）

================================================================================
"""

import json
import time
import threading

import sys
import requests
import sqlite3
import os
import random
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

# ==========================================
# 💔 痛点 1：需要自己安装和管理 Redis 连接
# ==========================================
# 🌟 Funboost 对比：broker_kind=BrokerEnum.REDIS_ACK_ABLE 一个参数搞定
try:
    import redis
except ImportError:
    print("请安装 redis: pip install redis")
    sys.exit(1)

# ================= 配置 =================
BASE_URL = "http://127.0.0.1:7000"
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_DB = 0

# Redis 队列名称
QUEUE_LIST_PAGE = "crawler:list_page"
QUEUE_DETAIL_PAGE = "crawler:detail_page"
QUEUE_COMMENTS_PAGE = "crawler:comments_page"

# ==========================================
# 💔 痛点 2：需要自己创建 Redis 连接池
# ==========================================
# 🌟 Funboost 对比：自动管理连接池
redis_pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)

def get_redis_client():
    return redis.Redis(connection_pool=redis_pool)

# ==========================================
# 💔 痛点 3：需要自己创建和管理多个线程池
# ==========================================
# 🌟 Funboost 对比：@boost 装饰器自动管理
list_page_pool = ThreadPoolExecutor(max_workers=5, thread_name_prefix="list_page")
detail_page_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="detail_page")
comments_page_pool = ThreadPoolExecutor(max_workers=15, thread_name_prefix="comments_page")



# ==========================================
# 💔 痛点 5：需要自己维护任务去重
# ==========================================
# 🌟 Funboost 对比：do_task_filtering=True 一个参数
crawled_detail_ids = set()
crawled_detail_lock = Lock()
crawled_comment_keys = set()
crawled_comment_lock = Lock()

# ==========================================
# 💔 痛点 6：需要自己实现数据保存
# ==========================================
# 🌟 Funboost 对比：DatasetSink.save() 一行代码
db_lock = Lock()
db_path = os.path.join(os.path.dirname(__file__), 'redis_threadpool_data.db')

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
    print("💔 [Redis+Pool] 数据库初始化完成")

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
# 💔 痛点 7：需要自己实现动态 UA
# ==========================================
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
# 💔 痛点 8：需要自己实现请求重试
# ==========================================
def request_with_retry(url, max_retries=3):
    for i in range(max_retries):
        try:
            response = requests.get(url, headers=get_random_headers(), timeout=10)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"  💔 请求失败 (第{i+1}次): {e}")
            if i < max_retries - 1:
                time.sleep(1)
    return None


# ==========================================
# 爬虫处理函数
# ==========================================

def process_list_page(msg_data):
    """处理列表页任务"""
    page = msg_data.get('page', 1)
    size = msg_data.get('size', 10)
    
    url = f"{BASE_URL}/news/list?page={page}&size={size}"
    print(f"[列表页] 正在爬取: {url}")
    
    response = request_with_retry(url)
    if not response:
        print(f"[列表页] 爬取失败: {url}")
        return
    
    news_list = response.json()
    print(f"[列表页] 获取到 {len(news_list)} 条新闻")
    
    # 💔 痛点 9：需要手动序列化并推送到 Redis
    # 🌟 Funboost 对比：crawl_detail_page.push(news_id=xxx)
    r = get_redis_client()
    for news_item in news_list:
        news_id = news_item["id"]
        title = news_item["title"]
        print(f"  -> 发现新闻 [ID: {news_id}] {title}")
        
        # 手动 JSON 序列化并推送
        task_data = json.dumps({"news_id": news_id, "title": title})
        r.rpush(QUEUE_DETAIL_PAGE, task_data)


def process_detail_page(msg_data):
    """处理详情页任务"""
    news_id = msg_data.get('news_id')
    title = msg_data.get('title', '')
    
    # 手动去重
    with crawled_detail_lock:
        if news_id in crawled_detail_ids:
            print(f"  💔 跳过已爬取: news_id={news_id}")
            return
        crawled_detail_ids.add(news_id)
    
    url = f"{BASE_URL}/news/{news_id}"
    print(f"[详情页] 正在爬取: {url}")
    
    response = request_with_retry(url)
    if not response:
        print(f"[详情页] 爬取失败 (ID: {news_id})")
        return
    
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
    
    # 推送评论页任务到 Redis
    r = get_redis_client()
    for page in range(1, 3):
        task_data = json.dumps({"news_id": news_id, "title": title, "page": page})
        r.rpush(QUEUE_COMMENTS_PAGE, task_data)
        print(f"  -> 已推送: 爬取新闻{news_id}的第{page}页评论")


def process_comments_page(msg_data):
    """处理评论页任务"""
    news_id = msg_data.get('news_id')
    title = msg_data.get('title', '')
    page = msg_data.get('page', 1)
    
    # 手动去重
    cache_key = f"{news_id}_{page}"
    with crawled_comment_lock:
        if cache_key in crawled_comment_keys:
            print(f"  💔 跳过已爬取: {cache_key}")
            return
        crawled_comment_keys.add(cache_key)
    
    url = f"{BASE_URL}/news/{news_id}/comments?page={page}&size=10"
    print(f"[评论页] 正在爬取: {url}")
    
    response = request_with_retry(url)
    if not response:
        print(f"[评论页] 爬取失败")
        return
    
    # 解析 HTML
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


# ==========================================
# 💔 痛点 10：需要自己实现 3 个消费者循环
# ==========================================
# 🌟 Funboost 对比：
#    crawl_list_page.consume()
#    crawl_detail_page.consume()
#    crawl_comments_page.consume()
#    只需要 3 行！

def consume_list_page():
    """消费列表页队列"""
    r = get_redis_client()
    print(f"💔 [消费者] 开始监听队列: {QUEUE_LIST_PAGE}")
    
    while True:
        try:
            # blpop 阻塞等待，超时 1 秒
            result = r.blpop(QUEUE_LIST_PAGE, timeout=1)
            if result:
                _, msg = result
                msg_data = json.loads(msg)
                # 提交到线程池
                list_page_pool.submit(process_list_page, msg_data)
        except Exception as e:
            print(f"💔 [消费者] 列表页队列异常: {e}")
            time.sleep(1)


def consume_detail_page():
    """消费详情页队列"""
    r = get_redis_client()
    print(f"💔 [消费者] 开始监听队列: {QUEUE_DETAIL_PAGE}")
    
    while True:
        try:
            result = r.blpop(QUEUE_DETAIL_PAGE, timeout=1)
            if result:
                _, msg = result
                msg_data = json.loads(msg)
                detail_page_pool.submit(process_detail_page, msg_data)
        except Exception as e:
            print(f"💔 [消费者] 详情页队列异常: {e}")
            time.sleep(1)


def consume_comments_page():
    """消费评论页队列"""
    r = get_redis_client()
    print(f"💔 [消费者] 开始监听队列: {QUEUE_COMMENTS_PAGE}")
    
    while True:
        try:
            result = r.blpop(QUEUE_COMMENTS_PAGE, timeout=1)
            if result:
                _, msg = result
                msg_data = json.loads(msg)
                comments_page_pool.submit(process_comments_page, msg_data)
        except Exception as e:
            print(f"💔 [消费者] 评论页队列异常: {e}")
            time.sleep(1)


# ==========================================
# 💔 痛点 11：需要自己发布初始任务
# ==========================================
# 🌟 Funboost 对比：crawl_list_page.push(page=1) 一行代码

def publish_initial_tasks():
    """发布初始的列表页任务"""
    r = get_redis_client()
    print("💔 [发布] 发布初始任务...")
    
    for page in range(1, 4):
        task_data = json.dumps({"page": page, "size": 5})
        r.rpush(QUEUE_LIST_PAGE, task_data)
        print(f"  -> 已发布: 爬取第 {page} 页列表")


# ================= 入口 =================
if __name__ == "__main__":
    print()
    print("=" * 70)
    print("  新闻爬虫 - Redis blpop + ThreadPoolExecutor 手动分布式实现")
    print("=" * 70)
    print()
    print("⚠️ 请先启动：")
    print("   1. Redis 服务器")
    print("   2. news_server.py")
    print()
    print("💔 这个实现需要自己手动处理：")
    print("   - Redis 连接管理")
    print("   - 3 个 while True 消费者循环（永远等待消息）")
    print("   - 3 个独立的线程池")
    print("   - JSON 序列化/反序列化")
    print("   - 异常处理、重试、去重、数据保存...")
    print()
    print("🌟 Funboost 对比：")
    print("   @boost(BoosterParams(queue_name='xxx', broker_kind=BrokerEnum.REDIS_ACK_ABLE))")
    print("   def crawl_page(...): ...")
    print("   crawl_page.consume()  # 自动处理一切！永远等待消息！")
    print()
    print("=" * 70)
    print()
    
    # 初始化数据库
    init_database()
    
    # 💔 痛点 12：需要手动启动多个消费者线程
    # 🌟 Funboost 对比：BoostersManager.consume_group("xxx") 一行代码
    # 
    # 注意：这里使用 daemon=False，让消费者线程永远运行
    # 直到收到 Ctrl+C 信号才退出
    consumer_threads = [
        threading.Thread(target=consume_list_page, name="consumer_list", daemon=True),
        threading.Thread(target=consume_detail_page, name="consumer_detail", daemon=True),
        threading.Thread(target=consume_comments_page, name="consumer_comments", daemon=True),
    ]
    
    for t in consumer_threads:
        t.start()
        print(f"💔 [启动] 消费者线程: {t.name}")
    
    time.sleep(1)
    
    # 发布初始任务（仅作为示例，实际生产环境可以通过其他方式发布任务）
    publish_initial_tasks()
    
    print()
    print("=" * 70)
    print("� [永久运行模式] 消费者正在等待消息...")
    print("   - 3 个 while True 循环持续监听 Redis 队列")
    print("   - 随时可以从外部推送新任务到 Redis 队列")
    print("   - 按 Ctrl+C 退出")
    print("=" * 70)
    print()
    
    # 永久等待
    while True:
        time.sleep(3600)

    # ==========================================
    # 以下为说明
    # ==========================================
    """
    💔 手动实现分布式需要处理的痛点：
       1. Redis 连接池管理
       2. 多个线程池创建和管理
       3. 多个 while True 消费者循环（永远等待）
       4. JSON 序列化/反序列化
       5. 任务去重（set + Lock）
       6. 请求重试
       7. 动态 UA
       8. 数据库保存
       9. HTML 解析
       10. 初始任务发布
       11. 消费者线程启动
       12. 永久等待实现
    """
    print()
    print("🌟 Funboost 只需要：")
    print("   @boost(BoosterParams(...)) + .consume() + .push()")
    print("   所有痛点自动处理！永远等待消息！")
    print("=" * 70)
