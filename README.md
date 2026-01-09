
**欢迎来到爬虫的未来，这里没有回调地域，只有自由世界。**

`pip install boost_spider`

**`boost_spider` = `funboost` 的超跑引擎 + 一套为爬虫量身打造的瑞士军刀。所有仿scrapy api爬虫框架都还是处在变花样造一辆马车**

对于爬虫场景:       
用户怕麻烦,要求天生就爬虫全套方便，就使用 `funboost` + `boost_spider`(内置了便利的 请求 解析 入库3个类)     
用户要绝对自由，就使用 `funboost` + 用户自己项目的 `utils/` 或 `commons/` 文件夹下已经封装好的 各种工具类和函数     

### funboost/boost_spider 对仿scrapy api框架最大优势是 复用用户自己的 utils文件夹下的 宝贵资产
- 复用用户自己的 utils 宝贵资产，正是 `funboost`  区别于 `Scrapy/Feapder` 等传统框架的**根本性优势**，是战略层面的胜利。   
*   **`utils` 是开发者的“内功心法”**：一个开发者的 `utils` 文件夹，是他/她多年经验的结晶，是解决特定领域问题的最佳实践沉淀。它包含了对业务逻辑的深刻理解，是**不可替代的、高度定制化的“私有武器库”**。
*   **“复用 `utils`” = 复用经验和智慧**：一个框架如果能让开发者无缝地复用自己的 `utils`，就意味着它尊重并放大了开发者的个人能力和历史积累。开发者可以用最熟悉、最高效的方式解决问题。
*   **“无法复用 `utils`” = 废掉武功，重练套路**：`Scrapy/Feapder` 的插件和中间件机制，本质上是让你放弃自己的“内功”，去学习并练习一套它们规定好的“套路招式”。你的 `my_request` 函数再精妙，也得改成 `Downloader Middleware` 的形状；你的 `save_to_mysql` 再高效，也得塞进 `Item Pipeline` 的模子里。这是一个**巨大的、隐性的成本**。

### **Funboost/boost_spider 天然就是 FaaS 微服务，而 Scrapy 只是数据孤岛,架构模式战略级碾压**  
`funboost/boost_spider` 支持高实时爬虫，scrapy只能封闭离线爬虫，架构模式战略级碾压。  
`funboost/boost_spider`不仅支持别的部门通过原生消息队列客户端发布函数入参对应的纯净json到对应的queue_name  
也支持 `funboost.faas` 快速给你的web服务增加多个funboost路由，一键实现`FaaS(Function as a Service)`     
自动发现注册爬虫函数，在实时爬虫上对`scrapy-redis`是战略级碾压。   

# 1.分布式光速python爬虫框架 boost_spider

boost_spider是从框架理念和本质上降维打击,任何仿 scrapy api 用法框架的爬虫框架,如同星际战舰对抗中世纪的蒸汽机车.    
碾压任何需要用户 yield Request(url=url, callback=self.my_parse,meta={'field1':'xxx','field2':'yyy'}) 的爬虫框架20年以上.  


## 安装：

pip install boost_spider

## boost_spider框架的更详细用法要看funboost文档

boost_spider是基于funboost驱动,增加了对爬虫更方便的常规反爬请求类和 方便爬虫解析的响应类 和 一行代码快捷保存字典入库 3个类.    
RequestClient  和  SpiderResponse  和 DatasetSink

[查看分布式函数调度框架完整文档 https://funboost.readthedocs.io/zh-cn/latest/index.html](https://funboost.readthedocs.io/zh-cn/latest/index.html)


## 简介：

boost_spider 是powerd by funboost,加了一个方便爬虫的请求类(用户可以不使用这个请求类,可以用任意包自己发送http请求)

本质上,funboost是函数调度框架,scrapy和国产仿scrapy api用法的爬虫框架是一个url请求调度框架,

函数里面用户可以写任何逻辑,所以boost_spider适应范围和用户自由度暴击写死了替发送一个http请求的仿scrapy框架.

函数调度框架暴击url请求调度框架,这是降维打击.

### boost_spider 理念:

- funboost/boost_spider 和 scrapy 难度差异: 【对于一个刚刚掌握了 Python 基础语法（变量、列表、元组、if/else、for循环）的新手来说】
  - **boost_spider**： 难度要低很多,就和小学生练手手写requests单个小脚本的思路一样，最后加一行@boost装饰器一键起飞。
  - **仿scrapy框架**： 巨大的框架压迫感，和刚学的基础语法对比，差异鸿沟太大,无限懵逼以至于自我怀疑，刚学的python语法是不是白学了。   
                      直接上手 Scrapy，就像 **一个刚学会骑自行车的人，突然被要求去驾驶一架波音747**。


- `boost_spider` 理念 是框架永远不要自作主动,在框架内部自动替用户执行http请求 
要自动调度一个函数而不是自动调度一个url/Request对象    
函数里面用户自己自由选择任何 httpx  requests aiohttp urllib3 selenium  playwright, 或者使用自己封装的一个my_request请求函数 来发送http请求.

- **boost_spider 不替用户自动发请求**, 意味上限很高,对于怎么换headers redis代理池的ip 代理商的隧道ip ,  
怎么在浏览器多步骤交互 输入 点击 等待,再解析网页, 用户非常容易按自己的内心想法搞定,    
对于执行http请求,`boost_spider` 只提供好用的 `RequestClient`, 但不强迫用户必须使用 `RequestClient`   

- **仿scrapy api 的框架内部自己去替用户执行http请求**,意味用户控制能力很弱,只能在`yield Request` 传递请求的 method url request_body 等等,   
对于复杂的需要写一段python代码逻辑来换ip和请求头的,用户需要写 download_middleware 钩子,怎么实现middleware需要和框架规则高度耦合, 导致用户实现难度太高     
以及多步骤浏览器交互会阻塞parse函数,短时效token 多个url必须短时间内连续请求, 由于不自由,导致用户无法实现.  

- **对于简单爬虫,boost_spider代码更简单更少,思维更直观平铺直叙,无需任何仪式感模板代码**  
**对于复杂爬虫,boost_spider除了代码更直观,用户还更容易实现自己奇葩想法,多机器+多进程+多线程/协程 性能强得多**   

- **🚀 boost_spider 作为微服务和 FaaS (Function as a Service) 使用，能高实时爬虫，scrapy只能离线循环爬虫，boost_spider在实时场景吊打scrapy**


### boost_spider 对 funboost 的 爬虫场景增强,3个重要类, RequestClient 和 SpiderResponse 和 DatasetSink
```
RequestClient：
一个为爬虫而生的请求客户端。封装了自动重试、随机User-Agent、代理商轮换、保持Cookie会话等所有反爬基础操作。
比 Scrapy 复杂的 Downloader Middleware 易用百倍。

SpiderResponse：
请求返回的响应对象，直接自带 .xpath(), .css(), .re_search() 等方法，让你无需额外导入 parsel 就能方便地解析页面。

DatasetSink：
一行代码将爬取到的字典数据存入MySQL、PostgreSQL、SQLite等多种数据库，并且自动处理建表。
完爆任何仿 Scrapy api 爬虫框架 繁琐的 定义Item -> yield item -> 定义 Pipeline -> Settings+ITEM_PIPELINES配置,来实现数据存储流程。
```

### boost_spider特点:

 ```
 boost_spider支持同步爬虫也支持asyncio异步爬虫
 boost_spider 是一款自由奔放写法的爬虫框架，无任何束缚，和用户手写平铺直叙的爬虫函数一样
 是横冲直撞的思维写的,不需要callback回调解析方法,不需要继承BaseSpider类,没有BaseSpider类,大开大合自由奔放,代码阅读所见即所得
 
 绝对没有class MySpider(BaseSpider) 的写法
 
 绝对没有 yield Request(url=url, callback=self.my_parse,meta={'field1':'xxx','field2':'yyy'}) 的写法.
 
 绝对没有 yield item 的写法
 
 boost_spider在函数里面写的东西所见即所得,不需要在好几个文件中来回切换检查代码.
  
 函数去掉@boost装饰器仍然可以正常使用爬虫,加上和去掉都很容易,这就是自由.
 有的人喜欢纯手写无框架的使用线程池运行函数来爬虫,很容易替换成boost_spider
 
 仿scrapy api的爬虫框架,无论是去掉和加上框架,代码组织形式需要翻天覆地的大改特改,这样就是束缚框架.
 
 boost_spider所写的爬虫代码可以直接去掉@boost装饰器,可以正常运行,所见即所得.
 
 只需要加上boost装饰器就可以自动加速并发，给函数和消息加上20控制功能,控制手段比传统爬虫框架多太多,
 boost_spider 支持多线程 gvent eventlet asyncio 并且能叠加多进程消费,运行速度远远的暴击国产爬虫框架.
 国产框架大部分是只能支持多线程同步语法爬虫,不能支持asyncio编程写法,而boost_spider能够同时兼容用户使用requests和aiohttp任意写法
 
 ```

### scrapy和国内写的各种仿scrapy api用法的框架特点
```
funboost函数调度框架,用户完全自由,

仿scrapy框架,只是个url调度框架,仿scrapy api 框架里面写死了怎么帮用户请求一个url,
有时候为了支持用户复杂的请求逻辑,例如换代理ip逻辑,框架还不得不暴露出用户自定义请求的所谓middware,用户要掌握在这些爬虫框架中自定义发送请求,框架又变难了.
因为爬虫框架难的是替自动并发 替用户自动重试 自动断点续爬,发送一个请求并不难,用户导入requests发一个http请求,只需要一行代码,
用户对requests封装一个请求http函数也很简单,反而替用户自作主张怎么发送请求,用户奇葩方式发请求反而满足不了,所以爬虫框架不需要内置替用户自动发送请求.
```

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

### boost_spider的qps作用远远的暴击所有爬虫框架的固定线程并发数量

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

# 2.代码例子：

```python

from boost_spider import boost, BrokerEnum, RequestClient, MongoSink, json, re, MysqlSink, BoosterParams
from boost_spider.sink.dataset_sink import DatasetSink
from db_conn_kwargs import MONGO_CONNECT_URL, MYSQL_CONN_KWARGS  # 保密 密码

"""
非常经典的列表页-详情页 两层级爬虫调度,只要掌握了两层级爬虫,三层级多层级爬虫就很容易模仿

列表页负责翻页和提取详情页url,发送详情页任务到详情页消息队列中
"""

dataset_sink1 = DatasetSink("mysql+pymysql://root:123456@localhost/testdb2")

@boost(BoosterParams(queue_name='car_home_list', broker_kind=BrokerEnum.REDIS_ACK_ABLE, max_retry_times=5, qps=2,
       do_task_filtering=False))  # boost 的控制手段很多.
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


@boost(BoosterParams(queue_name='car_home_detail', broker_kind=BrokerEnum.REDIS_ACK_ABLE, qps=5,
       do_task_filtering=True, is_using_distributed_frequency_control=True))
def crawl_detail_page(url: str, title: str, news_type: str):
    sel = RequestClient(using_platfrom='汽车之家爬虫新闻详情页').get(url).selector
    author = sel.css('#articlewrap > div.article-info > div > a::text').extract_first() or sel.css(
        '#articlewrap > div.article-info > div::text').extract_first() or ''
    author = author.replace("\n", "").strip()
    news_id = re.search('/(\d+).html', url).group(1)
    item = {'news_type': news_type, 'title': title, 'author': author, 'news_id': news_id, 'url': url}
    # 也提供了 MysqlSink类,都是自动连接池操作数据库
    # MongoSink(db='test', col='car_home_news', uniqu_key='news_id', mongo_connect_url=MONGO_CONNECT_URL, ).save(item)
    # MysqlSink(db='test', table='car_home_news', **MYSQL_CONN_KWARGS).save(item)  # 用户需要自己先创建mysql表
    dataset_sink1.save('car_home_news', item)  # 使用知名dataset三方包,一行代码能自动建表和保存字典到5种数据库类型.


if __name__ == '__main__':
    # crawl_list_page('news',1) # 直接函数测试

    crawl_list_page.clear()  # 清空种子队列
    crawl_detail_page.clear()

    crawl_list_page.push('news', 1, do_page_turning=True)  # 发布新闻频道首页种子到列表页队列
    crawl_list_page.push('advice', page=1,do_page_turning=True)  # 导购
    crawl_list_page.push(news_type='drive', page=1,do_page_turning=True)  # 驾驶评测

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
爬虫函数的入参随意，加上@boost装饰器就可以自动并发

3.
爬虫种子保存，支持40种消息队列

4.
qps是规定爬虫每秒爬几个网页，qps的控制比指定固定的并发数量，控制强太多太多了

```

## boost_spider 支持用户使用asyncio编程生态

国产爬虫框架大部分只能支持同步编程语法生态,无法兼容用户原有的asyncio编程方式.

boost_spider是同步编程和asyncio编程双支持.(boost_spider 还能支持gevent eventlet),还能和多进程叠加性能炸裂.

```python
import httpx
from funboost import boost, BrokerEnum, ConcurrentModeEnum, ctrl_c_recv, BoosterParams

client = httpx.AsyncClient()


@boost(
    BoosterParams(queue_name='test_httpx_q3a', broker_kind=BrokerEnum.REDIS, concurrent_mode=ConcurrentModeEnum.ASYNC,
                  concurrent_num=500))
async def f(url):
    # client= httpx.AsyncClient()
    r = await client.get(url)
    print(r.status_code, len(r.text))

    # 发布url到第二层级
    f2.push('新浪', 'https://www.sina.com')
    f2.push('搜狐', 'https://www.sohu.com')
    f2.push('qq', 'https://www.qq.com')


@boost(
    BoosterParams(queue_name='test_httpx_q3b', broker_kind=BrokerEnum.REDIS, concurrent_mode=ConcurrentModeEnum.ASYNC,
                  concurrent_num=500))
async def f2(site_name, url):
    # client= httpx.AsyncClient()
    r = await client.get(url)
    print(site_name, r.status_code, len(r.text))


if __name__ == '__main__':
    # asyncio.run(f())
    f.clear()  # 清空队列
    f2.clear()

    f.consume()  # 启动消费
    f2.consume()

    for i in range(5):
        f.push('https://www.baidu.com/')
    ctrl_c_recv()


```

## 为什么任何 yield Request(url=url, callback=self.my_parse,meta={'field1':'xxx','field2':'yyy'} 是过气爬虫框架?

在2025年还在模仿2007年的scrapy 框架的api,没有必要。如果真需要异步，就使用真异步asyncio。twisted 早就过气了。

```
1. 逻辑割裂与“回调地狱”：代码可读性的噩梦,  思维跳跃,上下文丢失

2. meta 字典：一个“无法无天”的“黑魔法”容器, 它是一个无类型、无结构、无约束的“垃圾桶”

3. 可测试性的毁灭:
   请求解析,无法独立测试,必须随着框架整体运行起来才能验证

4. 自由度的剥夺：
   你只是流水线上的工人. 你只能通过 yield Request 指定url get还是post 请求体 ,
   如果你是奇葩发请求,例如爬取的时候要从你自己的reids ip代理池获取ip,必须搞个 download middware 来适配框架.
   
5.时序之罪:
   yield Request,不能精准控制请求时机,如果要爬取url2,先必须从url1获取token加密,假设token有效期只有10秒,你分两次yield Request,
   因为请求是被框架自动调度的,你无法自己掌控两个请求的真正被调度时机,url2它可能在url1 1 毫秒后被执行，也可能在 10 分钟后被执行，你完全无法预测。
   只要是种子堆积了,就算是你设置优先级也没用,如果同一个优先级有几万个request种子,无法按优先级精准控制请求时序.
   而函数调度框架,一个函数里面天然可以写if /else/ for /try ,也能连续写发送多次请求
```

**用过 `funboost` 的pythoner都说相见恨晚,连连称奇,醍醐灌顶,豁然开朗,和传统作茧自缚的爬虫框架简直不在一个级别**


## 仿 scrapy api 爬虫框架，作者会疲于奔命
```
所有仿scrapy api 爬虫框架的 作者会疲于奔命需要持续改框架，
作者需要内置很多pipeline  ，例如mysql mongo sqlite jsonfile redis，
作者需要担心用户不会在自己框架扩展pipeline ，作者需要内置 怎么换ip代理 怎么换请求头， 怎么指纹反扒， 
怎么集成各种浏览器包，例如怎么集成 selneium  playwright ，因为作者如果不内置这些middware，用户很难自己扩展适配他的框架。 
  
funboost 不变应万变，funboost 始终不用改代码，以逸待劳，以不变应万变
因为用户在消费函数里面很 直观、自由、容易 地调用自己的 utils/ 或者 commons/ 文件夹下的工具类，
完全不需要考虑怎么和 funboost 进行精细化高度耦合适配
```

## 你的 utils文件夹 是黄金还是废铁？取决于你用什么哲学的框架

- **funboost/boost_spider 对仿scrapy api框架最大优势是 自由编程暴击框架奴役， 能复用用户自己的 utils 宝贵资产**

- scrapy的三方包插件，各种 scrapy-xx 插件，例如 scrapy-redis scrapy-playwright scrapy-selenium scrapy-user-agents scrapy-splash 等等，三方包插件总量不会超过1000个.
  只有pypi的三方包才是星辰大海，100万多个pypi三方包都是你的工具。  
  **最重要的是，只有用户自己项目下utils文件夹下积累的工具类和函数才是最符合用户自己实际需求的工具，而不是 scrapy-xx 插件。**

- Python pypi生态就是funboost的生态，你的python项目下的 utils/ 或者 helpers/ 文件夹下日积月累的各种工具类和函数都是 funboost的生态,   
  例如你的爬虫项目 utils 文件夹下日积月累，99%的概率已经存在如下，好用的经过实战检验的工具类和函数： 
  
```python
def anti_request(method,url,...retry_times=3,is_change_ua=True,is_change_proxy)：
   """自动重试 换代理ip  user-agent 的http请求函数""" 

def save_to_mysql(data:dict)：   
    """保存字典到数据库的函数"""

class RedisBloomFilter:
    """redis 布隆过滤器"""
    def is_exists(self, key):
        ...
    def add(self, key):
        ...

def extract_all_with_join(selector, separator=' '):
    """提取选择器所有结果并用指定分隔符连接成字符串。"""
    return separator.join(selector.getall()).strip()

class WebsiteAuthenticator:  
    """对于需要登录的网站，一个管理会话、Cookie 和 Token 的类是无价之宝。"""
    def login(self):
        ...
    def get_session(self):
        ...

def send_email_notification(subject, body, recipient):
    """发送爬虫邮件通知。"""

def download_and_upload_to_s3(url, bucket_name, object_name):
    """下载文件并直接流式上传到 S3。"""
    s3 = boto3.client('s3')
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        s3.upload_fileobj(r.raw, bucket_name, object_name)
    return f"s3://{bucket_name}/{object_name}"
    
```

**在 funboost中**，你utils文件夹下的宝贵资产，黄金任然是黄金，可以直接import 复用使用： 
```python
from funboost import boost, BrokerEnum
from utils.http_client import anti_request  # 你日积月累的工具
from utils.db import save_to_mysql        # 你日积月累的工具
from utils.redis_dedup import RedisBloomFilter   # 你日积月累的工具
from utils.website_authenticator import WebsiteAuthenticator   # 你日积月累的工具
from utils.send_notification import send_email_notification   # 你日积月累的工具
from utils.download_and_upload import download_and_upload_to_s3   # 你日积月累的工具
```
**而在`scrapy` `feapder`面前**，你曾经引以为豪在`utils`文件夹下积累的宝贵资产，他不是黄金，只是一堆破铜烂铁而已，不能被导入复用。    
你没有按照他们框架的`Downloader Middleware` 和 `Pipeline`规范写的`utils`文件夹下的工具类，都是废铁一文不值。  
`scrapy`的扩展插件机制 被 `funboost` 的自由import复用吊打。

- 复用用户自己的 utils 宝贵资产，正是 `funboost`  区别于 `Scrapy/Feapder` 等传统框架的**根本性优势**，是战略层面的胜利。

*   **`utils` 是开发者的“内功心法”**：一个开发者的 `utils` 文件夹，是他/她多年经验的结晶，是解决特定领域问题的最佳实践沉淀。它包含了对业务逻辑的深刻理解，是**不可替代的、高度定制化的“私有武器库”**。
*   **“复用 `utils`” = 复用经验和智慧**：一个框架如果能让开发者无缝地复用自己的 `utils`，就意味着它尊重并放大了开发者的个人能力和历史积累。开发者可以用最熟悉、最高效的方式解决问题。
*   **“无法复用 `utils`” = 废掉武功，重练套路**：`Scrapy/Feapder` 的插件和中间件机制，本质上是让你放弃自己的“内功”，去学习并练习一套它们规定好的“套路招式”。你的 `my_request` 函数再精妙，也得改成 `Downloader Middleware` 的形状；你的 `save_to_mysql` 再高效，也得塞进 `Item Pipeline` 的模子里。这是一个**巨大的、隐性的成本**。



## 🚀 boost_spider 作为微服务和 FaaS (Function as a Service) 使用，能高实时爬虫，scrapy只能离线批量爬虫，boost_spider在实时场景吊打scrapy

> **告别“数据孤岛”，让爬虫成为可被实时调用的“原子能力”。**

- 传统爬虫框架（如 Scrapy）的设计初衷是 **离线批处理**：启动 -> 跑完所有种子 -> 结束。这使得它们像一座座孤岛，外部系统（如 Java/Go 后端、Web 管理台）很难与正在运行的爬虫进行**实时交互**。

- 而 **boost_spider** 基于 **funboost** 的函数调度哲学，天然具备 **FaaS (Function as a Service)** 基因。每一个被 `@boost` 装饰的爬虫函数，瞬间就可以变成一个 **微服务接口**。

-  **Funboost/boost_spider 天然就是 FaaS 微服务，而 Scrapy 只是数据孤岛,架构模式战略级碾压**
  `funboost/boost_spider`不仅支持别的部门通过原生消息队列客户端发布函数入参对应的纯净json到对应的queue_name
   也支持 `funboost.faas` 快速给你的web服务增加多个funboost路由，一键实现`FaaS(Function as a Service)`    
   自动发现注册爬虫函数，在实时爬虫上对`scrapy-redis`是战略级碾压。 

### ⚔️ 核心差异对比：实时性与架构

| 维度 | 🐢 Scrapy (离线批处理) | ⚡ boost_spider (实时微服务) |
| :--- | :--- | :--- |
| **运行模式** | **主动轮询/跑批**。适合每天凌晨跑全量数据。 | **事件驱动/按需触发**。适合用户点一下按钮，立马抓取数据。 |
| **外部调用** | **难**。外部系统很难向正在运行的 Spider 插入任务并等待结果，通常需要通过数据库中转，延迟极高。 | **极简**。通过自动生成的 HTTP 接口直接触发，支持 **RPC 模式** 同步等待并获取爬取结果。 |
| **架构定位** | **脚本/任务**。是一个独立的进程，跑完即焚。 | **服务/组件**。是一个常驻的微服务，随时响应来自 Web 前端或后端 API 的抓取请求。 |
| **适用场景** | 全网爬取、搜索引擎索引、历史数据回溯。 | **接口实时代理解析**、**用户触发式采集**、**竞对价格实时监控**。 |

### scrapy是封闭循环系统，  scrapy-redis一旦启动后，再去人为从程序外部手动注入一个深层级的爬虫种子/任务 非常难。

**Scrapy 难以实现深层任务动态注入。**

有人不服气的，你可以试试对 `scrapy-redis`的 深层级爬虫动态增加一个任务， 例如从web接口给第二层级的 `detail_parse` 动态实时新增 `yield` 一个`Request` 请求调度对象，
这个简单的需求，对 scrapy 小白来说完全不可能，对scrapy大神来神实现非常麻烦。因为在程序外部你脱离了spider对象自身，就很难给深层级爬虫实时动态新增爬虫种子了。
如果是动态新增第一层级的爬虫种子，你可以简单的 `redis.lpush('start_urls','my_list_page_url1')`，这勉强能做到，但对深层级的爬虫`xx_parse`方法去动态实时加一个爬虫种子就太难了。


## funboost/booost_spider 比 scrapy框架的 战略优势和战术优势
### 一、 战略优势 (Strategic Advantages)
*—— 架构理念、生态整合与长远价值*

#### 1. 核心哲学：赋能 vs 奴役
*   **Funboost**: 是**“函数调度器”**。它不关心你的函数里写的是爬虫、数据清洗还是发邮件。它对代码**零侵入**，只负责为函数提供分布式、并发和高可靠的能力。你的代码依然是标准的 Python 代码。
*   **Scrapy**: 是**“URL调度器”**。它强迫开发者按照框架的规则（Spider, Item, Pipeline, Middleware）来拆解业务逻辑。开发者被框架“奴役”，必须削足适履。

#### 2. 架构模式：FaaS 微服务 vs 数据孤岛
*   **Funboost**: 天然具备 **FaaS (Function as a Service)** 基因。
    *   每一个爬虫函数瞬间变成一个**微服务接口**。
    *   **打破孤岛**：Java/Go/PHP 等外部系统可以直接往消息队列推 JSON 数据来实时触发特定的爬虫任务（如立即抓取某详情页），实现**实时交互**。
    *   **Funboost.faas**: 提供开箱即用的 HTTP 接口，实现自动服务发现。
*   **Scrapy**: 设计初衷是**离线批处理**。
    *   是一个封闭的黑盒循环。外部系统很难在爬虫运行时动态插入一个深层级的任务（如直接触发 `parse_detail`）。

#### 3. 资产复用：黄金 vs 废铁
*   **Funboost**: 直接复用你项目 `utils/` 文件夹下积累多年的工具类（如 `requests` 封装、数据库操作类）。这些代码是**黄金**，拿来即用。
*   **Scrapy**: 你积累的通用 Python 工具类在这里往往是**废铁**。你必须把它们改写成 Scrapy 特有的 `Middleware` 或 `Pipeline` 格式才能使用，造成巨大的重复劳动和维护成本。

#### 4. 生态兼容：Python 生态 vs 插件生态
*   **Funboost**: **无需插件**。整个 PyPI 都是你的插件库。想用 `Playwright`？直接 import 用。想用 `SQLAlchemy`？直接 import 用。
*   **Scrapy**: **严重依赖插件**。想用 Redis？得装 `scrapy-redis`。想用 Selenium？得找 `scrapy-selenium`。开发者被限制在 Scrapy 的小生态圈里，一旦没有对应的适配插件，寸步难行。

---

### 二、 战术优势 (Tactical Advantages)
*—— 开发效率、性能表现与具体功能*

#### 1. 并发性能：四重叠加 vs 单核异步
*   **Funboost**: 支持 **多机器 + 多进程 + (多线程/协程)** 的四重叠加并发。能轻松榨干多核 CPU 性能，QPS 极其炸裂。
*   **Scrapy**: 基于 Twisted 单进程事件循环。难以利用多核 CPU，一旦在回调中出现阻塞操作（如复杂的解密计算或浏览器渲染），整个爬虫就会卡死。

#### 2. 流程控制：线性直观 vs 回调地狱
*   **Funboost**: **平铺直叙**。在一个函数内完成 “请求 -> 逻辑判断 -> 再次请求 -> 解析 -> 入库” 的完整闭环。代码逻辑连贯，支持 `while`/`for` 等复杂流程控制。
*   **Scrapy**: **回调地狱**。逻辑被强行拆分到 `start_requests`, `parse`, `parse_detail` 等多个回调函数中，状态传递（`meta`）繁琐且易错，代码阅读极其跳跃。
    *   *场景举例*：**短时效 Token**。Funboost 可以在函数内获取 Token 后立即发起下一次请求，确保不过期；Scrapy 无法保证两个 Request 之间的执行间隔。

#### 3. 可靠性：万无一失 vs 随机丢包
*   **Funboost**: 拥有 **ACK 消费确认机制**。即使爬虫进程被强制 kill、断电或崩溃，未执行完的任务会重新回到队列，数据**一条不丢**。
*   **Scrapy (scrapy-redis)**: 使用 `BLPOP` 模式。任务一旦从 Redis 弹出，如果进程崩溃，内存中的任务就**永久丢失**了。断点续爬不可靠。

#### 4. 控频能力：精准 QPS vs 模糊并发
*   **Funboost**: 支持 **精准 QPS 控频**（如每秒 5.5 次）。无论网络响应快慢，框架会自动调节并发度来维持稳定的请求速率。支持**分布式全局控频**。
*   **Scrapy**: 只能控制**并发数**（Concurrent Requests）。无法保证稳定的抓取速率，容易因请求过快触发反爬，或因响应变慢导致效率低下。

#### 5. 反爬应对：简单函数 vs 复杂中间件
*   **Funboost**: 写一个普通的 Python 函数（如 `my_request`）来封装换 IP、换 UA 的逻辑，简单直观，容易测试。
*   **Scrapy**: 必须深入理解框架生命周期，编写复杂的 `Downloader Middleware`，配置优先级，调试困难。

#### 6. 任务去重：智能入参 vs 笨拙 URL
*   **Funboost**: 基于**函数入参**去重。天然忽略 URL 中的时间戳、随机数等噪音参数。支持设置**去重有效期**（如7天后可重爬）。
*   **Scrapy**: 基于 **URL 指纹**去重。对 URL 中的噪音参数敏感，需要编写复杂的正则或自定义去重器来清洗 URL。默认不支持有效期去重。

### 总结
**Scrapy** 适合处理结构简单、无需复杂交互、离线式的全网爬取任务。
**Funboost/BoostSpider** 则适合现代互联网环境下，高并发、强反爬、逻辑复杂、需要实时交互和微服务化的采集业务。