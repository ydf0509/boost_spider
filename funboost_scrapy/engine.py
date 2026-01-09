# coding=utf-8
"""
funboost_scrapy.engine - 核心引擎

解析 Spider 的 yield 生成器，调度 funboost 任务。
这是 funboost_scrapy 框架的核心，负责协调请求、响应、回调和入库。
"""

import types
import requests
from typing import Type, List, Generator, Optional

from funboost import boost, BoosterParams, BrokerEnum, ctrl_c_recv

from funboost_scrapy.request import Request
from funboost_scrapy.response import Response
from funboost_scrapy.item import Item
from funboost_scrapy.spider import Spider
from funboost_scrapy.pipeline import Pipeline, PrintPipeline
from funboost_scrapy.middleware import Middleware


class Engine:
    """
    核心引擎 - 解析 Spider 的 yield 生成器，调度 funboost 任务
    
    工作流程:
    1. 实例化 Spider
    2. 初始化 Pipeline 列表
    3. 执行 spider.start_requests() 获取初始 Request
    4. 使用 boost_spider.RequestClient 发送请求
    5. 调用 Request.callback 处理响应
    6. 解析 callback 返回的生成器:
       - yield Request -> 递归处理新请求
       - yield Item -> 流经 Pipeline 入库
    7. 通过 funboost 队列实现分布式调度（可选）
    
    使用示例:
        engine = Engine()
        engine.run(MySpider)
    """
    
    def __init__(
        self,
        pipelines: Optional[List[Pipeline]] = None,
        middlewares: Optional[List[Middleware]] = None,  # 中间件列表
        use_funboost: bool = False,  # 是否使用 funboost 分布式调度
        broker_kind: str = BrokerEnum.PERSISTQUEUE,  # 消息队列类型
        concurrent_num: int = 5,
        qps: float = 0,  # 0 表示不限制
        max_retry_times: int = 3,
    ):
        """
        初始化引擎
        
        Args:
            pipelines: Pipeline 实例列表（如果为 None，默认使用 PrintPipeline）
            middlewares: Middleware 中间件列表（如 UserAgentMiddleware）
            use_funboost: 是否使用 funboost 分布式调度
            broker_kind: 消息队列类型（use_funboost=True 时有效）
            concurrent_num: 并发数
            qps: QPS 限制（0 表示不限制）
            max_retry_times: 最大重试次数
        """
        self.pipelines = pipelines if pipelines is not None else [PrintPipeline()]
        self.middlewares = middlewares or []  # 中间件列表
        self.use_funboost = use_funboost
        self.broker_kind = broker_kind
        self.concurrent_num = concurrent_num
        self.qps = qps
        self.max_retry_times = max_retry_times
        
        # HTTP 客户端 (requests.Session)
        self._session: Optional[requests.Session] = None
        
        # 当前爬虫实例
        self._spider: Optional[Spider] = None
        
        # funboost 消费函数（use_funboost=True 时使用）
        self._request_handler = None
    
    def run(self, spider_cls: Type[Spider], **kwargs):
        """
        运行爬虫
        
        Args:
            spider_cls: Spider 类（非实例）
            **kwargs: 传递给 Spider 构造函数的参数
        """
        # 1. 实例化 Spider
        self._spider = spider_cls.from_crawler(**kwargs)
        print(f"[Engine] 启动爬虫: {self._spider}")
        
        # 2. 合并配置
        settings = {
            'concurrent_num': self.concurrent_num,
            'qps': self.qps,
            'max_retry_times': self.max_retry_times,
        }
        settings.update(self._spider.custom_settings)
        self.concurrent_num = settings.get('concurrent_num', self.concurrent_num)
        self.qps = settings.get('qps', self.qps)
        self.max_retry_times = settings.get('max_retry_times', self.max_retry_times)
        
        # 3. 初始化 Pipeline
        spider_pipelines = []
        for pipeline_cls in self._spider.pipelines:
            if isinstance(pipeline_cls, type):
                spider_pipelines.append(pipeline_cls())
            else:
                spider_pipelines.append(pipeline_cls)
        all_pipelines = self.pipelines + spider_pipelines
        
        for pipeline in all_pipelines:
            pipeline.open_spider(self._spider)
        
        # 4. 初始化 HTTP 客户端 (requests.Session)
        self._session = requests.Session()
        
        try:
            if self.use_funboost:
                # 使用 funboost 分布式调度
                self._run_with_funboost(all_pipelines)
            else:
                # 简单模式：同步执行
                self._run_simple(all_pipelines)
        finally:
            # 5. 关闭 Pipeline
            for pipeline in all_pipelines:
                pipeline.close_spider(self._spider)
            
            # 6. 回调 spider.closed()
            self._spider.closed("finished")
            print(f"[Engine] 爬虫结束: {self._spider}")
    
    def _run_simple(self, pipelines: List[Pipeline]):
        """
        简单模式运行（同步执行，适合小规模爬取和调试）
        """
        print(f"[Engine] 运行模式: 简单模式（同步执行）")
        
        # 执行 start_requests
        start_gen = self._spider.start_requests()
        self._process_generator(start_gen, pipelines)
    
    def _run_with_funboost(self, pipelines: List[Pipeline]):
        """
        funboost 模式运行（分布式调度）
        """
        print(f"[Engine] 运行模式: funboost 分布式调度")
        print(f"[Engine] broker_kind={self.broker_kind}, concurrent_num={self.concurrent_num}, qps={self.qps}")
        
        # 创建 funboost 消费函数
        @boost(BoosterParams(
            queue_name=f"funboost_scrapy_{self._spider.name}",
            broker_kind=self.broker_kind,
            concurrent_num=self.concurrent_num,
            qps=self.qps,
            max_retry_times=self.max_retry_times,
        ))
        def process_request(request_data: dict):
            """处理单个请求"""
            request = self._deserialize_request(request_data)
            self._process_single_request(request, pipelines, process_request)
        
        self._request_handler = process_request
        
        # 启动消费者
        process_request.consume()
        
        # 发布初始任务
        for request in self._spider.start_requests():
            request_data = self._serialize_request(request)
            process_request.push(request_data=request_data)
        
        # 阻塞主线程
        print("[Engine] 爬虫已启动，按 Ctrl+C 停止...")
        ctrl_c_recv()
    
    def _process_generator(self, gen: Generator, pipelines: List[Pipeline]):
        """
        处理生成器：递归处理 yield 的 Request 和 Item
        """
        if gen is None:
            return
        
        if not isinstance(gen, types.GeneratorType):
            # 如果不是生成器，可能是单个 Request 或 Item
            self._process_yield_item(gen, pipelines)
            return
        
        for item in gen:
            self._process_yield_item(item, pipelines)
    
    def _process_yield_item(self, item, pipelines: List[Pipeline]):
        """
        处理单个 yield 产出的对象
        """
        if isinstance(item, Request):
            # yield Request -> 发送请求并处理响应
            self._process_single_request(item, pipelines)
        elif isinstance(item, Item):
            # yield Item -> 流经 Pipeline
            self._process_item(item, pipelines)
        elif isinstance(item, dict):
            # 字典也视为 Item
            self._process_item(Item(item), pipelines)
        elif item is not None:
            print(f"[Engine] 警告: 未知的 yield 类型: {type(item)}")
    
    def _process_single_request(
        self, 
        request: Request, 
        pipelines: List[Pipeline],
        push_func=None  # funboost 模式下用于推送新任务
    ):
        """
        处理单个请求：发送 HTTP 请求，调用 callback，处理返回的生成器
        """
        try:
            # 1. 执行中间件的 process_request（请求发送前）
            for middleware in self.middlewares:
                result = middleware.process_request(request, self._spider)
                if result is not None:
                    if isinstance(result, Request):
                        request = result  # 使用新的 Request
                    elif isinstance(result, Response):
                        # 中间件直接返回 Response，跳过实际请求
                        response = result
                        break
            else:
                # 2. 发送 HTTP 请求
                print(f"[Engine] 发送请求: {request}")
                
                # 使用 requests.Session 发送请求
                raw_resp = self._session.request(
                    method=request.method,
                    url=request.url,
                    headers=request.headers or None,
                    cookies=request.cookies or None,
                    **request.kwargs
                )
                
                # 3. 封装 Response
                response = Response(raw_resp, meta=request.meta, request=request)
            
            # 4. 执行中间件的 process_response（响应返回后）
            for middleware in reversed(self.middlewares):
                response = middleware.process_response(request, response, self._spider)
            
            # 5. 调用 callback
            callback = request.callback or self._spider.parse
            result = callback(response)
            
            # 6. 处理回调返回值
            if self.use_funboost and push_func:
                # funboost 模式：推送新任务到队列
                if isinstance(result, types.GeneratorType):
                    for item in result:
                        if isinstance(item, Request):
                            request_data = self._serialize_request(item)
                            push_func.push(request_data=request_data)
                        elif isinstance(item, (Item, dict)):
                            self._process_item(Item(item) if isinstance(item, dict) else item, pipelines)
            else:
                # 简单模式：递归处理
                self._process_generator(result, pipelines)
                
        except Exception as e:
            # 7. 执行中间件的 process_exception
            for middleware in self.middlewares:
                result = middleware.process_exception(request, e, self._spider)
                if result is not None:
                    if isinstance(result, Request):
                        # 重新处理请求
                        self._process_single_request(result, pipelines, push_func)
                        return
                    elif isinstance(result, Response):
                        # 使用返回的 Response
                        callback = request.callback or self._spider.parse
                        gen_result = callback(result)
                        self._process_generator(gen_result, pipelines)
                        return
            
            print(f"[Engine] 请求失败: {request.url}, 错误: {e}")
            import traceback
            traceback.print_exc()
    
    def _process_item(self, item: Item, pipelines: List[Pipeline]):
        """
        处理 Item：流经所有 Pipeline
        """
        for pipeline in pipelines:
            try:
                item = pipeline.process_item(item, self._spider)
                if item is None:
                    # Pipeline 返回 None 表示丢弃该 Item
                    break
            except Exception as e:
                print(f"[Engine] Pipeline 处理失败: {e}")
                import traceback
                traceback.print_exc()
    
    def _serialize_request(self, request: Request) -> dict:
        """
        序列化 Request 对象（用于 funboost 消息传递）
        """
        # 获取 callback 的方法名
        callback_name = None
        if request.callback:
            callback_name = request.callback.__name__
        
        return {
            'url': request.url,
            'method': request.method,
            'headers': request.headers,
            'cookies': request.cookies,
            'meta': request.meta,
            'dont_filter': request.dont_filter,
            'priority': request.priority,
            'callback_name': callback_name,
            'kwargs': request.kwargs,
        }
    
    def _deserialize_request(self, data: dict) -> Request:
        """
        反序列化 Request 对象
        """
        callback = None
        callback_name = data.get('callback_name')
        if callback_name and self._spider:
            callback = getattr(self._spider, callback_name, None)
        
        return Request(
            url=data['url'],
            callback=callback,
            method=data.get('method', 'GET'),
            headers=data.get('headers'),
            cookies=data.get('cookies'),
            meta=data.get('meta'),
            dont_filter=data.get('dont_filter', False),
            priority=data.get('priority', 0),
            **data.get('kwargs', {})
        )
