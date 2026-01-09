# -*- coding: utf-8 -*-
"""
================================================================================
        新闻爬虫 - 使用 ThreadPoolExecutor 原生线程池实现
================================================================================

🎯 本文件目的：
   使用 Python 原生的 ThreadPoolExecutor 实现新闻爬虫，
   与 Funboost + boost_spider 和 Scrapy 形成三方对比。

================================================================================
                    ⚠️ ThreadPoolExecutor 的局限性
================================================================================

📊 与 Funboost 对比：
┌─────────────────────────┬────────────────────────────────┬────────────────────────────────┐
│       对比项            │     ThreadPoolExecutor          │     Funboost + boost_spider    │
├─────────────────────────┼────────────────────────────────┼────────────────────────────────┤
│ 分布式能力              │ ❌ 仅单机，无法跨机器          │ ⭐ 40+ 中间件原生分布式         │
│ 任务持久化              │ ❌ 进程死亡任务全部丢失        │ ⭐ 消息队列持久化，断点续爬     │
│ 消息确认(ACK)           │ ❌ 不支持                      │ ⭐ 消息处理失败自动重新入队     │
│ 精确流控(QPS)           │ ❌ 需要自己手动实现            │ ⭐ qps=5 一个参数搞定          │
│ 分布式流控              │ ❌ 无法实现                    │ ⭐ 多机统一 QPS 限制           │
│ 任务去重                │ ❌ 需要自己维护 set/bloom      │ ⭐ do_task_filtering=True      │
│ 自动重试                │ ❌ 需要自己 try-except 封装    │ ⭐ max_retry_times=3           │
│ 外部动态任务注入        │ ❌ 无法从外部注入任务          │ ⭐ HTTP API / RPC 随时注入     │
│ 监控面板                │ ❌ 无                          │ ⭐ 内置 Web 管理面板           │
│ RPC 获取结果            │ ❌ 需要自己实现                │ ⭐ is_using_rpc_mode=True      │
│ 定时任务                │ ❌ 需要配合其他库              │ ⭐ 内置 APScheduler            │
│ 代理/UA管理             │ ❌ 完全手动实现                │ ⭐ RequestClient 一行代码      │
│ 数据保存                │ ❌ 完全手动实现                │ ⭐ DatasetSink 一行代码        │
└─────────────────────────┴────────────────────────────────┴────────────────────────────────┘

💔 ThreadPoolExecutor 的本质问题：
   - 它只是一个"线程池"，不是任务调度框架
   - 所有任务和状态都在内存中，进程一死全没了
   - 适合简单的并发场景，不适合生产级爬虫

================================================================================
"""

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import sqlite3
import os
import random
from threading import Lock

# ================= 配置 =================
BASE_URL = "http://127.0.0.1:7000"

# ==========================================
# 💔 ThreadPoolExecutor 痛点 1：需要自己创建和管理多个线程池
# ==========================================
# 每个爬取层级使用独立的线程池
# 🌟 Funboost 对比：@boost 装饰器自动管理，无需手动创建线程池
list_page_pool = ThreadPoolExecutor(max_workers=5, thread_name_prefix="list_page")
detail_page_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="detail_page")
comments_page_pool = ThreadPoolExecutor(max_workers=15, thread_name_prefix="comments_page")

# ==========================================
# 💔 ThreadPoolExecutor 痛点 2：需要自己维护任务去重
# ==========================================
# 🌟 Funboost 对比：do_task_filtering=True 一个参数搞定
crawled_detail_ids = set()
crawled_detail_lock = Lock()

crawled_comment_keys = set()
crawled_comment_lock = Lock()

# ==========================================
# 💔 ThreadPoolExecutor 痛点 3：需要自己实现数据保存
# ==========================================
# 🌟 Funboost 对比：DatasetSink("sqlite:///data.db").save("table", data) 一行代码
db_lock = Lock()
db_path = os.path.join(os.path.dirname(__file__), 'threadpool_crawled_data.db')

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
    print("💔 [ThreadPool] 数据库初始化完成（需要自己写 ~30 行建表代码）")

def save_news_to_db(news_data):
    """保存新闻到数据库"""
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
    """保存评论到数据库"""
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
# 💔 ThreadPoolExecutor 痛点 4：需要自己实现动态 UA
# ==========================================
# 🌟 Funboost 对比：RequestClient(is_change_ua_every_request=True) 一个参数
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
]

def get_random_headers():
    """获取随机请求头"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': 'https://news.example.com/',
    }

# ==========================================
# 💔 ThreadPoolExecutor 痛点 5：需要自己实现重试逻辑
# ==========================================
# 🌟 Funboost 对比：max_retry_times=3 一个参数搞定
def request_with_retry(url, max_retries=3):
    """带重试的请求函数"""
    for i in range(max_retries):
        try:
            response = requests.get(url, headers=get_random_headers(), timeout=10)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"  💔 [ThreadPool] 请求失败 (第{i+1}次): {e}")
            if i < max_retries - 1:
                time.sleep(1)
    return None


# ==========================================
# 爬虫函数定义
# ==========================================

def crawl_list_page(page: int = 1, size: int = 10):
    """
    爬取新闻列表页
    
    💔 ThreadPoolExecutor 痛点 6：无法从外部动态注入任务
    - 所有任务必须在代码中预先定义
    - 无法通过 HTTP API 实时添加任务
    
    🌟 Funboost 对比：
    - crawl_list_page.push(page=5) 随时注入
    - funboost.faas HTTP API 动态注入
    """
    url = f"{BASE_URL}/news/list?page={page}&size={size}"
    print(f"[列表页] 正在爬取: {url}")
    
    response = request_with_retry(url)
    if not response:
        print(f"[列表页] 爬取失败: {url}")
        return None
    
    news_list = response.json()
    print(f"[列表页] 获取到 {len(news_list)} 条新闻")
    
    # 💔 痛点 7：需要手动收集 Future 并等待
    # 🌟 Funboost 对比：crawl_detail_page.push(...) 自动进入队列
    futures = []
    for news_item in news_list:
        news_id = news_item["id"]
        title = news_item["title"]
        print(f"  -> 发现新闻 [ID: {news_id}] {title}")
        
        # 使用详情页线程池提交任务
        future = detail_page_pool.submit(crawl_detail_page, news_id, title)
        futures.append(future)
    
    return {"page": page, "count": len(news_list), "futures": futures}


def crawl_detail_page(news_id: int, title: str):
    """
    爬取新闻详情页
    
    💔 ThreadPoolExecutor 痛点 8：需要手动实现任务去重
    🌟 Funboost 对比：do_task_filtering=True 自动去重
    """
    # 手动去重逻辑
    with crawled_detail_lock:
        if news_id in crawled_detail_ids:
            print(f"  💔 [ThreadPool] 跳过已爬取: news_id={news_id}")
            return None
        crawled_detail_ids.add(news_id)
    
    url = f"{BASE_URL}/news/{news_id}"
    print(f"[详情页] 正在爬取: {url}")
    
    response = request_with_retry(url)
    if not response:
        print(f"[详情页] 爬取失败 (ID: {news_id})")
        return None
    
    news_detail = response.json()
    
    content = news_detail.get("content", "")
    author = news_detail.get("author", "未知")
    publish_time = news_detail.get("publish_time", "未知")
    
    print("=" * 60)
    print(f"[爬取成功] 新闻ID: {news_id}")
    print(f"标题: {title}")
    print(f"作者: {author}")
    print(f"发布时间: {publish_time}")
    print(f"正文预览: {content[:100]}...")
    print("=" * 60)
    
    # 保存到数据库
    news_data = {
        "news_id": news_id,
        "title": title,
        "author": author,
        "publish_time": publish_time,
        "content": content,
    }
    save_news_to_db(news_data)
    print(f"  💔 [ThreadPool] 保存新闻到 SQLite（需要自己写保存函数）")
    
    # 提交评论页爬取任务
    futures = []
    for page in range(1, 3):
        future = comments_page_pool.submit(crawl_comments_page, news_id, title, page)
        futures.append(future)
        print(f"  -> 已提交: 爬取新闻{news_id}的第{page}页评论")
    
    return {"news_id": news_id, "futures": futures}


def crawl_comments_page(news_id: int, title: str, page: int = 1, size: int = 10):
    """
    爬取新闻评论页
    
    💔 ThreadPoolExecutor 痛点 9：无法使用 xpath/css 解析
    - 需要自己安装 lxml/parsel 并手动处理
    
    🌟 Funboost 对比：SpiderResponse.xpath() 开箱即用
    """
    # 手动去重逻辑
    cache_key = f"{news_id}_{page}"
    with crawled_comment_lock:
        if cache_key in crawled_comment_keys:
            print(f"  💔 [ThreadPool] 跳过已爬取: {cache_key}")
            return None
        crawled_comment_keys.add(cache_key)
    
    url = f"{BASE_URL}/news/{news_id}/comments?page={page}&size={size}"
    print(f"[评论页] 正在爬取: {url}")
    
    response = request_with_retry(url)
    if not response:
        print(f"[评论页] 爬取失败 (新闻ID: {news_id}, 第{page}页)")
        return None
    
    # 💔 痛点 10：需要手动安装和使用 lxml/parsel 解析 HTML
    # 🌟 Funboost 对比：resp.xpath('//div[@class="xxx"]') 开箱即用
    from lxml import etree
    html = etree.HTML(response.text)
    comment_items = html.xpath('//div[@class="comment-item"]')
    
    print(f"[评论页] 找到 {len(comment_items)} 条评论")
    
    comments = []
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
        
        comment = {
            "news_id": news_id,
            "news_title": title,
            "page": page,
            "comment_id": comment_id,
            "author": author,
            "time": time_str,
            "content": content,
            "likes": likes,
        }
        comments.append(comment)
        save_comment_to_db(comment)
        
        print(f"  📝 评论#{comment_id} | {author} | {time_str}")
        print(f"     内容: {content}")
        print(f"     点赞: {likes}")
    
    print("=" * 60)
    print(f"[评论爬取成功] 新闻ID: {news_id}, 第{page}页")
    print(f"标题: {title}")
    print(f"共解析 {len(comments)} 条评论")
    print(f"  💔 [ThreadPool] 保存 {len(comments)} 条评论到 SQLite")
    print("=" * 60)
    
    return {"news_id": news_id, "page": page, "comments_count": len(comments)}


# ================= 入口 =================
if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  新闻爬虫 - ThreadPoolExecutor 原生线程池实现")
    print("=" * 60)
    print()
    print("⚠️ 请先启动 news_server.py：")
    print("   cd demo_crawler")
    print("   python news_server.py")
    print()
    print("💔 ThreadPoolExecutor 的局限性：")
    print("   - 仅单机，无法分布式")
    print("   - 进程死亡任务全部丢失")
    print("   - 需要手动实现：去重、重试、流控、数据保存...")
    print()
    print("=" * 60)
    print()
    
    # 初始化数据库
    init_database()
    
    start_time = time.time()
    
    # 💔 痛点 11：需要手动管理所有 Future
    # 🌟 Funboost 对比：ctrl_c_recv() 阻塞即可
    all_futures = []
    
    # 爬取前3页列表
    for page in range(1, 4):
        future = list_page_pool.submit(crawl_list_page, page, 5)
        all_futures.append(future)
    
    # 等待所有任务完成
    print("\n💔 [ThreadPool] 等待所有任务完成...")
    for future in as_completed(all_futures):
        try:
            result = future.result()
            if result and 'futures' in result:
                all_futures.extend(result.get('futures', []))
        except Exception as e:
            print(f"💔 [ThreadPool] 任务异常: {e}")
    
    # 💔 痛点 12：需要手动关闭线程池
    # 🌟 Funboost 对比：无需手动管理
    list_page_pool.shutdown(wait=True)
    detail_page_pool.shutdown(wait=True)
    comments_page_pool.shutdown(wait=True)
    
    elapsed = time.time() - start_time
    
    print()
    print("=" * 60)
    print("爬虫运行结束 - ThreadPoolExecutor")
    print("=" * 60)
    print(f"耗时: {elapsed:.2f} 秒")
    print()
    print("💔 ThreadPoolExecutor 需要手动实现的功能：")
    print("   1. 多个线程池的创建和管理")
    print("   2. 任务去重（set + Lock）")
    print("   3. 请求重试逻辑")
    print("   4. 动态 UA 随机")
    print("   5. 数据库保存（建表 + 写入）")
    print("   6. HTML 解析（安装 lxml）")
    print("   7. 等待所有 Future 完成")
    print("   8. 关闭线程池")
    print()
    print("🌟 Funboost 只需要：")
    print("   @boost(BoosterParams(...)) 装饰器 + .push() 调用")
    print("=" * 60)
