# coding=utf-8
"""
================================================================================
         新闻爬虫 Demo - 使用 boost_scrapy 框架 (Scrapy 风格)
================================================================================

🎯 本文件目的：
   演示如何使用 boost_scrapy 框架实现 Scrapy 风格的爬虫。
   爬取流程: 列表页 -> 详情页 -> 评论页

📊 使用方式：
   1. 先启动 news_server.py:
      cd demo_crawler
      python news_server.py
   
   2. 运行本爬虫:
      cd demo_crawler/boost_scrapy_imp
      python boost_scrapy_demo.py

================================================================================
"""

import sys
import os

# # 确保能够导入项目模块
# project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)



from boost_scrapy import Spider, Request, Engine
from items import NewsItem, CommentItem
from middlewares import MyProxyMiddleware, MyUserAgentMiddleware
from boost_scrapy import SQLModelPipeline, ConsolePipeline

# ================= 定义 Spider =================

class NewsSpider(Spider):
    """
    新闻爬虫 - 使用 boost_scrapy 实现 (Scrapy 风格)
    
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
        print("  boost_scrapy 新闻爬虫 Demo")
        print("  Scrapy 风格: yield Request + callback")
        print("=" * 60)
        print()
        
        # 爬取前3页列表，每页5条
        for page in range(1, 4):
            url = f"{self.BASE_URL}/news/list?page={page}&size=5"
            print(f"[发布任务] 列表页 第{page}页")
            yield Request(url, callback=self.parse_list, meta={'page': page},
                        #    dont_filter=True
                          )
    
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
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boost_scrapy_data.db')
    
    engine = Engine(
        # Engine 里面的入参可以放在全局字典，多个spider共享，也可以放在你的Spider的custom_settings的字典中。
        pipelines=[ConsolePipeline(),SQLModelPipeline(db_url=f'sqlite:///{db_path}'), ],  
        middlewares=[
            MyUserAgentMiddleware(),   # 🔄 自定义 UA 中间件：每次请求随机切换 UA
            # MyProxyMiddleware(),     # 🌐 自定义代理中间件：从内存/Redis 获取代理（取消注释启用）
        ],
        use_funboost=True, # use_funboost为False就使用单线程顺序爬虫，可以用于调试。
        enable_filter=False, # 默认是否启动过滤，也可以在 yield Request 的 dont_filter=True 来禁用
    )
    engine.run(NewsSpider)


