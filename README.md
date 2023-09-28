# 1.分布式高速爬虫框架 boost_spider

## 简介：

boost_spider特点:
 ```
 boost_spider 是一款自由奔放写法的爬虫框架，无任何束缚，和用户手写平铺直叙的爬虫函数一样，
 是横冲直撞的思维写的,不需要callback回调解析方法,不需要继承BaseSpider类,没有BaseSpider类,大开大合自由奔放.
 
 绝对没有class MySpider(BaseSpider) 的写法
 
 绝对没有 yield Request(url=url, callback=self.my_parse) 的写法.
 
 绝对没有 yield item 的写法
 
 boost_spider在函数里面写的东西所见即所得,不需要在好几个文件中来回切换检查代码.
  
 函数去掉@boost装饰器仍然可以正常使用爬虫,加上和去掉都很容易,这就是自由.
 有的人喜欢纯手写无框架的使用线程池运行函数来爬虫,很容易替换成boost_spider
 
 仿scrapy api的爬虫框架,无论是去掉和加上框架,代码组织形式需要翻天覆地的大改特改,就是束缚框架.
 
 所写的爬虫代码可以直接去掉@boost装饰器,可以正常运行,所见即所得.
 
 只需要加上boost装饰器就可以自动加速并发，给函数和消息加上20控制功能,控制手段比传统爬虫框架多太多
 ```

scrapy和国内写的各种仿scrapy api用法的框架特点
```
需要在 spiders文件夹写继承BaseSpider, 
items文件夹定义item, 
pipleines文件夹写怎么保存爬虫数据,
settings.py写DOWNLOADER_MIDDLEWARES调用什么pipleline,ITEM_PIPELINES调用什么middlware优先级,各种配置
middlewares.py写怎么换代理 请求头,
以及命令行中写怎么启动爬虫运行. 
在各个代码文件中来回切换检查写代码,写法烦人程度非常的吓人.

国内的爬虫框架没有创新能力,都是模仿scrapy的 api用法,所以scrapy的写法烦人的缺点基本上都继承下来了.
和scrapy写法一样烦人的爬虫框架,这样的框架就没必要重复开发了.
```

boost_spider的qps作用远远的暴击所有爬虫框架的固定线程并发数量
```
国内的仿scrapy框架的,都只能做到固定并发数量,一般是固定开多少个线程.

比如我要求每秒精确完成爬10次接口或网页保存到数据库,你咋做到?
一般人就以为是开10个线程,这是错误的,我没讲过对方接口刚好是精确1秒的响应时间.

如果网站接口或网页耗时0.1秒,你开10线程那就每秒爬了100个网页了.
如果网站网页耗时20秒(特别是加上代理ip后经常可能响应时间大),你开10线程,每秒只能爬0.5次.
用线程数来决定每秒爬多少次就是非常的滑稽,只有请求耗时一直精确等于1秒,那么开多少个线程才等于每秒爬多少次,
否则每秒爬多少次和线程数量没有对应关系.

boost_spider不仅能设置并发数量,也可以设置qps,
boost_spider的qps参数无视任何网站的耗时是多少,不需要提前评估好接口的平均耗时,就能达到控频,
无视对方的响应耗时从0.01 0.07 0.3 0.7 3 7 13 19 37 秒 这些不规律的响应时间数字,
随意波动变化,都能一直保持恒定的爬虫次数.

保持恒定qps,这一点国产框架不行,国产框架需要提前评估好接口耗时,然后精确计算好开多少个线程来达到qps,
如果对方接口耗时变了,就要重新改代码的线程数量.
```


## 安装：

pip install boost_spider

# 2.代码例子：

```python

from boost_spider import boost, BrokerEnum, RequestClient, MongoSink, json, re, MysqlSink
from db_conn_kwargs import MONGO_CONNECT_URL, MYSQL_CONN_KWARGS  # 保密 密码

"""
非常经典的列表页-详情页 两层级爬虫调度,只要掌握了两层级爬虫,三层级多层级爬虫就很容易模仿

列表页负责翻页和提取详情页url,发送详情页任务到详情页消息队列中
"""

@boost('car_home_list', broker_kind=BrokerEnum.REDIS_ACK_ABLE, max_retry_times=5, qps=2,
       do_task_filtering=False) # boost 的控制手段很多.
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
    # MongoSink(db='test', col='car_home_news', uniqu_key='news_id', mongo_connect_url=MONGO_CONNECT_URL, ).save(item)
    MysqlSink(db='test', table='car_home_news', **MYSQL_CONN_KWARGS).save(item)  # 用户需要自己先创建mysql表


if __name__ == '__main__':
    # crawl_list_page('news',1) # 直接函数测试

    crawl_list_page.clear()  # 清空种子队列
    crawl_detail_page.clear()

    crawl_list_page.push('news', 1, do_page_turning=True)  # 发布新闻频道首页种子到列表页队列
    crawl_list_page.push('advice', page=1)  # 导购
    crawl_list_page.push(news_type='drive', page=1)  # 驾驶评测

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