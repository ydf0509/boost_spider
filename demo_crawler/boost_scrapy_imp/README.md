

## boost_scrapy 是为了满足，部分闲得蛋疼的用户非要装封装成模仿 scrapy api ，yield Request 的框架

有些被 Scrapy 毒害太深的家伙极其的蛋疼，居然想把 funboost 二次封装成  类似scrapy的爬虫api 框架 。
人为制造一层类 Scrapy 的 API（Spider 类、Middleware、Pipeline）

那么就满足这种愿望，自带实现了一个 boost_scrapy 的包。  
用法见 demo_crawler/boost_scrapy_imp/boost_scrapy_demo.py。  


看这个redame `boost_scrapy/README.md` ,这种做法就是有强力发动机`funboost`  有汽车`boost_spider`了，
**你非要把汽车发动机安装到马车上,封装一个 `boost_scrapy` 这种开历史倒车的丑陋怪胎。**




## 这个boost_scrapy包证明， funboost 的通用性适用性很强

能用线程池的地方就一定能用 funboost，既然线程池可以封装为爬虫框架的并发运行核心，  
所以 funboost 也一定能 封装为爬虫框架的并发运行核心


### 1.2.1 🆚 对比：Funboost 取代传统线程池

以下两种方式均实现 **10并发** 运行函数 `f`。   
Funboost 更加简洁且具备扩展性，funboost 有30多种控制功能，例如重试 qps 消费确认 消息队列背压， ThreadpoolExecutor 没这些高级功能。

#### ❌ 方式 A：手动开启线程池 (传统)
```python
import time
from concurrent.futures import ThreadPoolExecutor

def f(x):
    time.sleep(3)
    print(x)

pool = ThreadPoolExecutor(10)

if __name__ == '__main__':
    for i in range(100):
        pool.submit(f, i)
```

#### ✅ 方式 B：Funboost 模式 (推荐)
```python
import time
from funboost import BoosterParams, BrokerEnum

# 仅需一行装饰器，即可获得 10 线程并发 + 消息队列能力
@BoosterParams(queue_name="test_insteda_thread_queue", 
               broker_kind=BrokerEnum.MEMORY_QUEUE, 
               concurrent_num=10, 
               is_auto_start_consuming_message=True)
def f(x):
    time.sleep(3)
    print(x)

if __name__ == '__main__':
    for i in range(100):
        f.push(i)
```