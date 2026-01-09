"""
================================================================================
            新闻爬虫 - 使用 Funboost + boost_spider 实现分布式爬取
================================================================================

🎯 本文件目的：
   演示如何使用 Funboost 框架实现列表页、详情页、评论页的三层爬取流程。
   使用 boost_spider 的 SpiderResponse 进行 xpath 解析（你羡慕的 Scrapy selector 功能）

================================================================================
                  ⭐ Funboost + boost_spider 核心优势对比表
================================================================================

📊 与 Scrapy 对比（详见 ../scrapy_imp/scrapy_spider_crawler.py）：
┌──────────────────────────┬────────────────────────────────────────────────────────┐
│       ⭐ 优势项           │              Funboost + boost_spider 实现              │
├──────────────────────────┼────────────────────────────────────────────────────────┤
│ 1. 单文件开箱即用        │ 无需创建项目结构，单个 .py 文件即可运行                │
│ 2. 40+ 中间件选择        │ Redis/RabbitMQ/Kafka/MongoDB/SQLite/NSQ/...           │
│ 3. 原生分布式            │ 改一个参数 broker_kind 立刻分布式，无需额外插件        │
│ 4. 精确 QPS 流控         │ qps=5 精确每秒5次，支持分布式统一流控                 │
│ 5. 一键任务去重          │ do_task_filtering=True 即可去重                       │
│ 6. 自动重试              │ max_retry_times=3 自动重试                            │
│ 7. 消息确认 ACK          │ REDIS_ACK_ABLE 确保任务不丢失，支持断点续爬           │
│ 8. 外部动态任务注入      │ ⭐ HTTP/API 随时注入二级任务（Scrapy 无法实现！）      │
│ 9. 分组启动消费          │ BoostersManager.consume_group("xxx") 一键启动一组     │
│ 10. RPC 获取结果         │ is_using_rpc_mode=True 支持获取消费结果               │
│ 11. XPath/CSS 解析       │ SpiderResponse.xpath()/css() 和 Scrapy 一样强大       │
│ 12. 代理/UA/Cookie管理   │ RequestClient 内置代理轮换、UA随机、Session管理       │
│ 13. 内置监控面板         │ funboost_web_manager 可视化监控                       │
│ 14. 定时任务             │ ApsJobAdder 内置 APScheduler                         │
│ 15. 平铺直叙的代码风格   │ 无 callback 地狱，函数之间直接 .push() 调用           │
└──────────────────────────┴────────────────────────────────────────────────────────┘

⭐ 核心优势：外部系统实时动态注入"二级任务"
───────────────────────────────────────────
场景：运营人员在后台发现某条新闻需要重新爬取
Funboost：直接调用 crawl_detail_page.push(news_id=12345)
Scrapy：❌ 无法实现，只能从 start_urls 开始爬取

这是 Funboost 对 Scrapy 的【降维打击】！
================================================================================
"""

import requests
from funboost import boost, BoosterParams, BrokerEnum, ctrl_c_recv, BoostersManager
from boost_spider import RequestClient
# RequestClient.get()/request() 返回 SpiderResponse 对象，支持 xpath/css 解析

# ⭐【boost_spider 优势 13】DatasetSink：一行代码保存到 SQLite/MySQL/PostgreSQL
# 💔  Scrapy 对比：需要定义 Item、配置 Pipeline、在 settings 中启用 Pipeline
from boost_spider.sink.dataset_sink import DatasetSink

import boost_spider
print(boost_spider.__file__)

# ================= 配置 =================
BASE_URL = "http://127.0.0.1:7000"

# ⭐ DatasetSink 初始化：一行代码，连接 SQLite 数据库
# 💔 Scrapy 对比：需要在 settings.py 配置 ITEM_PIPELINES，再定义 Pipeline 类
DB_URL = "sqlite:///demo_crawler/boost_spider_imp/boost_spider_crawled_data.db"  # SQLite 数据库文件
data_sink = DatasetSink(DB_URL)



# ================= 爬虫公共配置 =================
# ⭐【Funboost 优势 1】配置继承：子类继承 BoosterParams，避免重复配置
# 💔  Scrapy 对比：settings.py + custom_settings + 中间件，配置分散在多处
class BaseCrawlerParams(BoosterParams):
    """
    爬虫通用配置基类
    
    ⭐【Funboost 优势 2】配置集中：所有配置在装饰器一个地方
    ⭐【Funboost 优势 3】类型安全：BoosterParams 是 Pydantic 模型，IDE 可以自动补全和类型检查
    💔  Scrapy 对比：settings 是 Python 字典，没有类型检查，容易拼错键名
    
    - 统一使用 Redis ACK Able 中间件（增强数据安全性）
    - 统一归属到 news_crawler_group 分组
    """
    # ⭐【Funboost 优势 4】40+ 种中间件选择
    # 💔  Scrapy 对比：仅支持内存队列，分布式需要 scrapy-redis 插件
    broker_kind:str = BrokerEnum.REDIS_ACK_ABLE  # 使用Redis ACK模式，确保消息不丢失，支持断点续爬
    
    # ⭐【Funboost 优势 5】分组管理：一个参数即可分组
    # 💔  Scrapy 对比：无分组概念，需要手动管理多个 Spider
    booster_group:str = "news_crawler_group"     # 统一分组，BoostersManager.consume_group("xxx")一键启动
    
    # ⭐【Funboost 优势 6】自动重试：一个参数搞定
    # 💔  Scrapy 对比：需要配置 RETRY_ENABLED 和 RETRY_TIMES 等多个 settings
    max_retry_times :int= 3                      # 默认重试3次
  
  


# ================= 爬虫函数定义 =================
# ⭐【Funboost 优势 7】装饰器即分布式：普通函数 + @boost = 分布式消费函数
# 💔  Scrapy 对比：必须继承 Spider 类，遵循框架约定

@boost(BaseCrawlerParams(
    queue_name="news_crawler_list_page",
    # ⭐【Funboost 优势 8】精确 QPS 流控：qps=2 表示精确每秒2次
    # 💔  Scrapy 对比：DOWNLOAD_DELAY 是近似控制，不精确
    qps=2,  # 每秒最多请求2次列表页，支持分布式统一流控
    concurrent_num=5,  # 并发数5
))
def crawl_list_page(page: int = 1, size: int = 10):
    """
    爬取新闻列表页
    
    ⭐【Funboost 优势 9】平铺直叙的代码风格
    - 无需 callback 回调，直接 crawl_detail_page.push() 发起下一层任务
    - 代码逻辑清晰，如同编写普通脚本
    💔  Scrapy 对比：callback 回调地狱，parse_list -> parse_detail -> parse_comments
    
    ⭐【Funboost 优势 10】外部动态任务注入（核心降维打击优势！）
    - 运营人员可以随时调用 crawl_list_page.push(page=5) 注入新任务
    - 支持 HTTP API 注入（funboost.faas）
    💔  Scrapy 对比：❌ 无法从外部实时注入二级任务，只能从 start_urls 开始
    
    - 请求列表页API
    - 解析返回的新闻列表
    - 推送详情页爬取任务
    """
    url = f"{BASE_URL}/news/list?page={page}&size={size}"
    print(f"[列表页] 正在爬取: {url}")
    
    
    # ⭐【boost_spider 优势 14】动态请求头：RequestClient 内置 UA 随机化
    # 💔  Scrapy 对比：需要定义 Downloader Middleware 类，配置 settings
    client = RequestClient(
        proxy_name_list=None,        # 可设置代理列表，如 ['kuai', 'abuyun']
        request_retry_times=3,       # 请求重试次数
        is_change_ua_every_request=True,  # ⭐ 只需一行代码每次请求随机切换 UA！
    )
    # 可以设置自定义请求头
    custom_headers = {
        'Referer': 'https://news.example.com/',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    response = client.get(url, timeout=10, headers=custom_headers)
    news_list = response.resp_dict  # ⭐ SpiderResponse 自动解析 JSON
    
    print(f"[列表页] 获取到 {len(news_list)} 条新闻")
    
    # 遍历新闻列表，推送详情页爬取任务
    for news_item in news_list:
        news_id = news_item["id"]
        title = news_item["title"]
        print(f"  -> 发现新闻 [ID: {news_id}] {title}")
        # 推送详情页爬取任务
        crawl_detail_page.push(news_id=news_id, title=title)
    
    return {"status": "success", "page": page, "count": len(news_list)}
    

@boost(BaseCrawlerParams(
    queue_name="news_crawler_detail_page",
    qps=5,  # 每秒最多请求5次详情页
    concurrent_num=10,  # 并发数10,
    # ⭐【Funboost 优势 11】一键任务去重
    # 💔  Scrapy 对比：需要配置 DUPEFILTER_CLASS，可能还需要 BloomFilter 插件
    do_task_filtering=True, # 通过函数入参自动去重，无需任何配置
    task_filtering_expire_seconds = 600, # 仅在600秒之内去重，支持过期时间控制
    
))
def crawl_detail_page(news_id: int, title: str):
    """
    爬取新闻详情页
    
    ⭐【Funboost 优势 12】函数参数类型安全
    - news_id: int, title: str 有类型标注
    - IDE 可以检查类型，push 时参数错误会提示
    💔  Scrapy 对比：通过 response.meta 传参，容易出错
    
    - 请求详情页API
    - 解析并保存新闻内容
    - 推送评论页爬取任务
    """
    url = f"{BASE_URL}/news/{news_id}"
    print(f"[详情页] 正在爬取: {url}")
    
    
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    news_detail = response.json()
    
    # 提取新闻内容
    content = news_detail.get("content", "")
    author = news_detail.get("author", "未知")
    publish_time = news_detail.get("publish_time", "未知")
    
    # 输出爬取结果（实际项目中可以保存到数据库）
    print("=" * 60)
    print(f"[爬取成功] 新闻ID: {news_id}")
    print(f"标题: {title}")
    print(f"作者: {author}")
    print(f"发布时间: {publish_time}")
    print(f"正文预览: {content[:100]}...")
    print("=" * 60)
    
    # 推送评论页爬取任务（爬取前2页评论）
    for page in range(1, 3):
        crawl_comments_page.push(news_id=news_id, title=title, page=page)
        print(f"  -> 已发布: 爬取新闻{news_id}的第{page}页评论")
    
    # ⭐【boost_spider 优势】DatasetSink 一行代码保存到 SQLite！
    # 💔  Scrapy 对比：需要 yield item -> Pipeline -> 数据库
    news_data = {
        "news_id": news_id,
        "title": title,
        "author": author,
        "publish_time": publish_time,
        "content": content,
    }
    data_sink.save("news_detail", news_data)  # ⭐ 一行代码保存！
    print(f"  💾 [已保存到SQLite] news_detail 表")
    
    return {
        "status": "success",
        "news_id": news_id,
        "title": title,
        "content_length": len(content)
    }
    
 


@boost(BaseCrawlerParams(
    queue_name="news_crawler_comments_page",
    qps=10,  # 每秒最多请求10次评论页
    concurrent_num=15,  # 并发数15
    retry_interval=1,   # 这里可以覆盖基类的配置,
    do_task_filtering=True, # 通过函数入参自动去重
    # task_filtering_expire_seconds = 600, # 不配置有效期就是永久过滤。
))
def crawl_comments_page(news_id: int, title: str, page: int = 1, size: int = 10):
    """
    爬取新闻评论页 - 使用 boost_spider 的 SpiderResponse 进行 xpath 解析
    
    ⭐【boost_spider 优势】SpiderResponse 拥有你羡慕的 Scrapy selector 功能！
    - resp.xpath('//div[@class="xxx"]')  -> XPath 选择器
    - resp.css('div.xxx')                -> CSS 选择器  
    - resp.re_search(pattern)            -> 正则匹配
    - resp.resp_dict                     -> 自动解析 JSON
    - resp.selector                      -> parsel.Selector 对象
    
    同时 RequestClient 还内置了：
    - 代理管理（多代理商轮换）：proxy_name_list=['kuai', 'abuyun']
    - 请求自动重试：request_retry_times=3
    - UA 随机化：is_change_ua_every_request=True
    - Session/Cookie 管理：自动保持会话
    💔  Scrapy 对比：代理/重试/UA 都需要自己写中间件配置
    
    - 请求评论页HTML
    - 使用xpath解析评论列表
    - 提取评论信息
    """
    url = f"{BASE_URL}/news/{news_id}/comments?page={page}&size={size}"
    print(f"[评论页] 正在爬取: {url}")
    
    
    # 使用 boost_spider 的 RequestClient 发送请求
    # RequestClient.request() 返回 SpiderResponse 对象，支持 xpath/css 解析
    client = RequestClient(proxy_name_list=None,request_retry_times=3,is_change_ua_every_request=True)
    resp = client.get(url, timeout=10)
    
    # 使用 xpath 解析 HTML 页面
    # 通过 resp.selector 属性获取 parsel.Selector 对象
    print("[评论页] 使用 xpath 解析评论...")


    # 提取所有评论项
    # boost_spider的 resp是 SpiderResponse类型，自带你羡慕的scrapy那样的xpath css方法
    comment_items = resp.xpath('//div[@class="comment-item"]') 
    print(f"[评论页] 找到 {len(comment_items)} 条评论")
    
    comments = []
    for item in comment_items:
        # 提取评论ID
        comment_id = item.xpath('./@data-id').get()
        # 提取作者
        author = item.xpath('.//span[@class="author"]/text()').get()
        # 提取评论时间
        time_str = item.xpath('.//span[@class="time"]/text()').get()
        # 提取评论内容
        content = item.xpath('.//p[@class="text"]/text()').get()
        # 提取点赞数
        likes = item.xpath('.//span[@class="likes"]/text()').get()
        
        comment = {
            "comment_id": comment_id,
            "author": author,
            "time": time_str,
            "content": content,
            "likes": likes,
        }
        comments.append(comment)
        
        # 输出每条评论
        print(f"  📝 评论#{comment_id} | {author} | {time_str}")
        print(f"     内容: {content}")
        print(f"     点赞: {likes}")
    
    # 输出汇总
    print("=" * 60)
    print(f"[评论爬取成功] 新闻ID: {news_id}, 第{page}页")
    print(f"标题: {title}")
    print(f"共解析 {len(comments)} 条评论")
    print("=" * 60)
    
    # ⭐【boost_spider 优势】DatasetSink 批量保存评论到 SQLite！
    # 💔  Scrapy 对比：需要在 Pipeline 中处理 item
    for comment in comments:
        comment["news_id"] = news_id
        comment["news_title"] = title
        comment["page"] = page
        data_sink.save("comments", comment)  # ⭐ 一行代码保存！
    print(f"  💾 [已保存到SQLite] comments 表, {len(comments)} 条记录")
    
    return {
        "status": "success",
        "news_id": news_id,
        "page": page,
        "comments_count": len(comments),
        "comments": comments
    }
    



# ================= 入口 =================
if __name__ == "__main__":
    print("=" * 60)
    print("新闻爬虫 - Funboost 分布式爬取")
    print("支持：列表页 -> 详情页 -> 评论页(xpath解析)")
    print("=" * 60)
    print()
    
    # 1. 使用 BoostersManager.consume_group 分组启动所有消费者（非阻塞）
    # 只要装饰器中指定了 booster_group 参数，就可以通过该分组名称一次性启动所有相关消费者
    print("[启动] 分组启动所有爬虫消费者...")
    BoostersManager.consume_group("news_crawler_group")
    print("  -> 列表页/详情页/评论页爬虫消费者已启动 ✓")
    
    # 2. 发布初始任务：爬取前3页新闻列表
    print()
    print("[发布任务] 开始爬取前3页新闻列表...")
    for page in range(1, 4):
        crawl_list_page.push(page=page, size=5)
        print(f"  -> 已发布: 爬取第 {page} 页")
    
    print()
    print("爬虫已启动，按 Ctrl+C 停止...")
    print()
    
    # 3. 保持程序运行
    ctrl_c_recv()
