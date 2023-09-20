# 1.分布式高速爬虫框架 boost_spider

## 简介：

 ```
 boost_spider 是一款自由奔放写法的爬虫框架，无任何束缚，和用户手写平铺直叙的爬虫函数一样，
 是横冲直撞的思维写的,不需要callback回调解析方法,不需要继承BaseSpider类,没有BaseSpider类,大开大合自由奔放.
 
 绝对没有class MySpider(BaseSpider) 的写法
 
 绝对没有 yield Request(url=url, callback=self.my_parse) 的写法.
 
 函数去掉@boost装饰器仍然可以正常使用爬虫,加上和去掉都很容易,这就是自由.
 有的人喜欢纯手写无框架的使用线程池运行函数来爬虫,很容易替换成boost_spider
 
 仿scrapy api的爬虫框架,无论是去掉和加上框架,代码组织形式需要翻天覆地的大改特改,就是束缚框架.
 
 所写的爬虫代码可以直接去掉@boost装饰器,可以正常运行,所见即所得.
 
 只需要加上boost装饰器就可以自动加速并发，给函数和消息加上20控制功能,控制手段比传统爬虫框架多太多
 ```

## 安装：

pip install boost_spider

# 2.代码例子：

```python
from boost_spider import boost, BrokerEnum, RequestClient, MongoSink, json, re, MysqlSink
from db_conn_kwargs import MONGO_CONNECT_URL, MYSQL_CONN_KWARGS  # 保密 密码


@boost('car_home_list', broker_kind=BrokerEnum.REDIS_ACK_ABLE, max_retry_times=5, qps=2,
       do_task_filtering=False)
def crawl_list_page(news_type, page, do_page_turning=False):
    """ 函数这里面的代码是用户想写什么就写什么，函数里面的代码和框架没有任何绑定关系
    例如用户可以用 urllib3请求 用正则表达式解析，没有强迫你用requests请求和parsel包解析。
    """
    url = f'https://www.autohome.com.cn/{news_type}/{page}/#liststart'
    sel = RequestClient(proxy_name_list=['noproxy'], request_retry_times=3,
                        using_platfrom='汽车之家爬虫新闻列表页').get(url).selector
    for li in sel.css('ul.article > li'):
        if len(li.extract()) > 100:  # 有的是这样的去掉。 <li id="ad_tw_04" style="display: none;">
            url_detail = 'https:' + li.xpath('./a/@href').extract_first()
            title = li.xpath('./a/h3/text()').extract_first()
            crawl_detail_page.push(url_detail, title=title, news_type=news_type)  # 发布详情页任务
    if do_page_turning:
        last_page = int(sel.css('#channelPage > a:nth-child(12)::text').extract_first())
        for p in range(2, last_page + 1):
            crawl_list_page.push(news_type, p)  # 列表页翻页。


@boost('car_home_detail', broker_kind=BrokerEnum.REDIS_ACK_ABLE, qps=5,
       do_task_filtering=True, is_using_distributed_frequency_control=True)
def crawl_detail_page(url: str, title: str, news_type: str):
    sel = RequestClient(using_platfrom='汽车之家爬虫新闻详情页').get(url).selector
    author = sel.css('#articlewrap > div.article-info > div > a::text').extract_first() or sel.css(
        '#articlewrap > div.article-info > div::text').extract_first() or ''
    author = author.replace("\n", "").strip()
    news_id = re.search('/(\d+).html', url).group(1)
    item = {'news_type': news_type, 'title': title, 'author': author, 'news_id': news_id, 'url': url}
    # 也提供了 MysqlSink类,都是自动连接池操作数据库
    MongoSink(db='test', col='car_home_news', uniqu_key='news_id', mongo_connect_url=MONGO_CONNECT_URL, ).save(item)
    MysqlSink(db='test', table='car_home_news', **MYSQL_CONN_KWARGS).save(item) # 用户需要自己先创建mysql表


if __name__ == '__main__':
    # crawl_list_page('news',1) # 直接函数测试

    crawl_list_page.clear()  # 清空种子队列
    crawl_detail_page.clear()

    crawl_list_page.push('news', 1, do_page_turning=True)  # 发布新闻频道首页种子到列表页队列

    crawl_list_page.consume()  # 启动列表页消费
    crawl_detail_page.consume()  # 启动详情页新闻内容消费

    # 这样速度更猛，叠加多进程
    # crawl_detail_page.multi_process_consume(4)


```

## 代码说明：

```
1.
RequestClient 类的方法入参和返回与requests包一模一样，方便用户切换
response在requests.Response基础上增加了适合爬虫解析的属性和方法。

RequestClient支持继承,用户自定义增加爬虫使用代理的方法,在 PROXYNAME__REQUEST_METHED_MAP 声明增加的方法就可以.

2. 
爬虫函数的入参随意，加上@ boost装饰器就可以自动并发

3.
爬虫种子保存，支持30种消息队列

4.
qps是规定爬虫每秒爬几个网页，qps的控制比指定固定的并发数量，控制强太多太多了
```