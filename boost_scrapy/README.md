# boost_scrapy - 基于 funboost 的 Scrapy 风格分布式爬虫框架

**boost_scrapy** 是一个巧妙的封装器，它将强大的 **[funboost](https://github.com/ydf0509/funboost)** 分布式调度框架包装成了大家熟悉的 **Scrapy** 风格。

如果你习惯了 Scrapy 的 `Spider`, `Request`, `Item` 写法，但又想极简地实现分布式、断点续爬、消息队列集成，**boost_scrapy 是你的最佳选择**。

---

## 🚀 核心特性

- **Scrapy 风格 API**：保留了 `start_requests`, `yield Request`, `yield Item`, `parse(response)` 等经典写法，零学习成本迁移。
- **天然分布式**：底层由 [funboost](https://github.com/ydf0509/funboost) 驱动，一行配置即可支持 Redis, RabbitMQ, Kafka 等 40+ 种消息队列。
- **极其轻量**：没有 Scrapy 复杂的 Twisted 依赖，基于 `requests` + `funboost`，代码简洁易读。
- **强大的控制力**：直接继承 funboost 的 QPS 控频、并发控制、自动重试、熔断降级等能力。
- **灵活的管道**：支持 Item Pipeline 机制，轻松实现数据清洗和入库。

## 📦 架构说明

`boost_scrapy` 的核心是将 Scrapy 的 `yield Request` 转换为 `funboost` 的任务发布。

1. **Engine**: 启动爬虫，将 `start_requests` 发布的请求推送到消息队列（通过 funboost）。
2. **Worker (Funboost)**: 从队列消费消息，执行 `Spider.parse` 等回调函数。
3. **Yield**:
    - `yield Request(...)` -> 序列化后推送新任务到队列（分布式递归）。
    - `yield Item(...)` -> 流经 Pipelines 处理数据。

## 🛠️ 快速上手

### 1. 安装

确保已经安装了 `funboost` 和依赖：

```bash
pip install funboost requests
```

### 2. 定义 Spider

像写 Scrapy 一样定义你的爬虫：

```python
from boost_scrapy import Spider, Request, Item, Engine

# 定义数据结构
class MyItem(Item):
    title: str
    url: str

# 定义爬虫
class MySpider(Spider):
    name = "demo_spider"
    
    # funboost 配置
    custom_settings = {
        'concurrent_num': 5,  # 并发数
        'qps': 2,            # QPS 限制
    }

    def start_requests(self):
        # 初始请求
        for i in range(5):
            yield Request(f"http://httpbin.org/get?a={i}", callback=self.parse)

    def parse(self, response):
        print(f"处理: {response.url}")
        # 解析数据
        yield MyItem(title="Example Title", url=response.url)
        
        # 继续爬取 (深度爬取)
        # yield Request("http://httpbin.org/get?b=1", callback=self.parse_next)

# 启动引擎
if __name__ == '__main__':
    # use_funboost=True 开启分布式模式
    # enable_filter=True 开启请求去重
    Engine(use_funboost=True).run(MySpider)
```

## ⚙️ 关键参数

在 `Spider.custom_settings` 或 `(kw)args` 中可以配置：

| 参数 | 说明 | 默认值 |
| :--- | :--- | :--- |
| `use_funboost` | 是否启用 funboost 分布式调度。设为 `False` 时为单线程同步调试模式。 | `False` |
| `broker_kind` | 消息队列类型 (Redis, RabbitMQ, Memory 等)。 | `PERSISTQUEUE` (本地持久化) |
| `concurrent_num` | 消费者并发线程/进程数。 | `5` |
| `qps` | 全局每秒请求数限制 (控频)。 | `0` (无限制) |
| `max_retry_times` | 任务失败/报错最大重试次数。 | `3` |
| `enable_filter` | 是否启用请求去重 (基于 URL+Method+Body 指纹)。 | `True` |

---

## 🆚 与 Scrapy 对比

| 维度 | Scrapy | Boost Scrapy |
| :--- | :--- | :--- |
| **底层核心** | Twisted (异步IO) | Funboost (多模式并发 + 消息队列) |
| **分布式支持** | 需配合 Scrapy-Redis | **原生支持** (40+种 Broker 任意选) |
| **部署难度** | 需配置 scrapyd 或其他守护进程 | 普通 Python 脚本，直接运行即可 |
| **去重机制** | RedisSet (Scrapy-Redis) | Funboost 任务去重  |
| **适用场景** | 纯异步高并发高性能 | 分布式、断点续爬、需要精细任务控制 |

## 📂 项目结构

- `engine.py`: 核心调度引擎，连接 Spider 和 Funboost。
- `spider.py`: 爬虫基类，定义了 pipeline 和 start_requests。
- `request.py` / `response.py`: 封装 HTTP 请求和响应。
- `item.py`: 数据模型基类。
- `pipeline.py`: 数据处理管道基类。
- `middleware.py`: 下载器中间件基类。

---

> **Note**: `boost_scrapy` 是 `funboost` 生态的一部分，旨在展示如何利用 `funboost` 的通用调度能力快速构建特定领域的框架。
