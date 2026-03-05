# coding=utf-8
"""
boost_scrapy.engine - 核心引擎

解析 Spider 的 yield 生成器，调度 funboost 任务。
这是 boost_scrapy 框架的核心，负责协调请求、响应、回调和入库。
"""
import traceback
import time
import types
import requests
import logging
import hashlib
from typing import Type, List, Generator, Optional, Callable, Any
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
import json

from funboost import boost, BoosterParams, BrokerEnum, ctrl_c_recv, TaskOptions

from boost_scrapy.request import Request
from boost_scrapy.response import Response
from boost_scrapy.item import Item
from boost_scrapy.spider import Spider
from boost_scrapy.pipeline import Pipeline, ConsolePipeline
from boost_scrapy.middleware import Middleware
from boost_scrapy.log import logger




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
        middlewares: Optional[List[Middleware]] = None,
        use_funboost: bool = False,
        broker_kind: str = BrokerEnum.PERSISTQUEUE,
        concurrent_num: int = 5,
        qps: float = 0,
        max_retry_times: int = 3,
        request_timeout: float = 30,
        queue_name_prefix: str = "boost_scrapy",
        enable_filter: bool = True,
        log_level: int = logging.DEBUG,
    ):
        """
        初始化引擎
        
        Args:
            pipelines: Pipeline 实例列表（如果为 None，默认使用 ConsolePipeline）
            middlewares: Middleware 中间件列表（如 UserAgentMiddleware）
            use_funboost: 是否使用 funboost 分布式调度
            broker_kind: 消息队列类型（use_funboost=True 时有效）
            concurrent_num: 并发数
            qps: QPS 限制（0 表示不限制）
            max_retry_times: 最大重试次数
            request_timeout: 请求超时秒数
            queue_name_prefix: funboost 队列名称前缀
            enable_filter: 是否启用请求去重
            log_level: 日志级别
        """
        self.pipelines = pipelines if pipelines is not None else [ConsolePipeline()]
        self.middlewares = middlewares or []
        self.use_funboost = use_funboost
        self.broker_kind = broker_kind
        self.concurrent_num = concurrent_num
        self.qps = qps
        self.max_retry_times = max_retry_times
        self.request_timeout = request_timeout
        self.queue_name_prefix = queue_name_prefix
        self.enable_filter = enable_filter
        logger.setLevel(log_level)


        
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
        logger.info(f"启动爬虫: {self._spider}")
        
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
            # 5. 关闭 HTTP Session
            if self._session:
                self._session.close()
                self._session = None
            
            # 6. 关闭 Pipeline
            for pipeline in all_pipelines:
                pipeline.close_spider(self._spider)
            
            # 7. 回调 spider.closed()
            self._spider.closed("finished")
            
            # 8. 打印结束日志
            logger.info(f"爬虫结束: {self._spider}")
    
    def _run_simple(self, pipelines: List[Pipeline]):
        """
        简单模式运行（同步执行，适合小规模爬取和调试）
        """
        logger.info("运行模式: 简单模式（同步执行）")
        
        # 执行 start_requests
        start_gen = self._spider.start_requests()
        # 简单模式下 push_func=None
        self._process_generator(start_gen, pipelines, push_func=None)
    
    def _run_with_funboost(self, pipelines: List[Pipeline]):
        """
        funboost 模式运行（分布式调度）
        """

        logger.info("运行模式: funboost 分布式调度")
        logger.info(f"broker_kind={self.broker_kind}, concurrent_num={self.concurrent_num}, qps={self.qps}")
        
        queue_name = f"{self.queue_name_prefix}_{self._spider.name}"
        
        # 创建 funboost 消费函数
        @boost(BoosterParams(
            queue_name=queue_name,
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
            
            task_options = None
            if self.enable_filter and not request.dont_filter:
                fingerprint = self._get_request_fingerprint(request)
                # logger.info(f"请求指纹: {fingerprint},request={request}")
                # print(f"请求指纹: {fingerprint},request={request}")
                task_options = TaskOptions(filter_str=fingerprint, do_task_filtering=True)
            
            process_request.publish({'request_data': request_data}, task_options=task_options)
        
        # 阻塞主线程

        logger.info("爬虫已启动，按 Ctrl+C 停止...")
        ctrl_c_recv()
    
    def _get_request_fingerprint(self, request: Request) -> str:
        """
        计算请求指纹（用于去重）
        
        逻辑升级：
        1. 规范化 URL 参数（排序）
        2. 包含 Request Body (data/json)
        3. 包含 Method
        
        Args:
            request: 请求对象
            
        Returns:
            请求指纹（MD5 哈希）
        """
        # 1. 规范化 URL (参数排序，合并 query 和 params)
        parsed = urlparse(request.url)
        query_items = []
        
        # 1.1 从原始 URL 中提取 query
        if parsed.query:
            query_items.extend(parse_qsl(parsed.query))
            
        # 1.2 从 kwargs['params'] 中提取
        req_params = request.kwargs.get('params')
        if req_params:
            if isinstance(req_params, dict):
                query_items.extend(req_params.items())
            elif isinstance(req_params, (list, tuple)):
                query_items.extend(req_params)
        
        # 1.3 排序并重组
        if query_items:
            # 排序确保顺序一致
            # 注意：将所有元素转为字符串再排序，防止类型不一致报错 (如 int 和 str)
            query_items.sort(key=lambda x: (str(x[0]), str(x[1])))
            normalized_query = urlencode(query_items)
        else:
            normalized_query = ""
            
        # 重组 URL
        normalized_url = urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, normalized_query, parsed.fragment
        ))

        # 2. 收集 Body 数据 (json/data)
        body_str = ""
        
        # 处理 json 参数 (kwargs['json'])
        req_json = request.kwargs.get('json')
        if req_json:
            # JSON 键排序，确保 {a:1, b:2} 和 {b:2, a:1} 指纹一致
            body_str += json.dumps(req_json, sort_keys=True, separators=(',', ':'))
            
        # 处理 data 参数 (kwargs['data'])
        req_data = request.kwargs.get('data')
        if req_data:
            if isinstance(req_data, dict):
                # 字典类型 data，排序键
                # 注意：request data 为字典时通常是 form-data，顺序可能不敏感，排序更稳健
                sorted_data = dict(sorted(req_data.items()))
                body_str += str(sorted_data)
            else:
                # 字符串或 bytes，直接拼接
                body_str += str(req_data)

        # 3. 拼接指纹字符串
        # 格式: METHOD:URL:BODY
        fp_string = f"{request.method}:{normalized_url}:{body_str}"
        
        # print(f"原始指纹串: {fp_string}") # debug用
        return hashlib.md5(fp_string.encode('utf-8')).hexdigest()
    
    def _process_generator(self, gen: Generator, pipelines: List[Pipeline], push_func: Callable = None):
        """
        处理生成器：递归处理 yield 的 Request 和 Item
        """
        if gen is None:
            return
        
        # 兼容 list/tuple 返回值 (Scrapy 允许 return [Request(...), Item(...)])
        if isinstance(gen, (list, tuple)):
            for item in gen:
                self._process_yield_item(item, pipelines, push_func)
            return
        
        if not isinstance(gen, types.GeneratorType):
            # 如果不是生成器也不是列表，可能是单个 Request 或 Item
            self._process_yield_item(gen, pipelines, push_func)
            return
        
        for item in gen:
            self._process_yield_item(item, pipelines, push_func)
    
    def _process_yield_item(self, item: Any, pipelines: List[Pipeline], push_func: Callable = None):
        """
        处理单个 yield 产出的对象
        
        Args:
            item: yield 产出的对象
            pipelines: Pipeline 列表
            push_func: funboost 模式下用于推送新任务的函数
        """
        if isinstance(item, Request):
            # yield Request -> 发送请求并处理响应
            if push_func:
                # funboost 模式：推送到队列
                request_data = self._serialize_request(item)
                
                task_options = None
                if self.enable_filter and not item.dont_filter:
                    fingerprint = self._get_request_fingerprint(item)
                    task_options = TaskOptions(filter_str=fingerprint, do_task_filtering=True)
                
                push_func.publish(msg={'request_data': request_data}, task_options=task_options)
            else:
                # 简单模式：直接处理 (无去重)
                self._process_single_request(item, pipelines)
                
        elif isinstance(item, Item):
            # yield Item -> 流经 Pipeline
            self._process_item(item, pipelines)
            
        else:
             logger.warning(f"  ⚠️ [Engine] 忽略非 Item 对象: {type(item)} (请继承 boost_scrapy.Item)")
    
    def _process_single_request(
        self, 
        request: Request, 
        pipelines: List[Pipeline],
        push_func: Callable = None
    ):
        """
        处理单个请求：发送 HTTP 请求，调用 callback，处理返回的生成器
        
        Args:
            request: 请求对象
            pipelines: Pipeline 列表
            push_func: funboost 模式下用于推送新任务的函数
        """
        response = None
        
        try:
            # 1. 执行中间件的 process_request（请求发送前）
            for middleware in self.middlewares:
                result = middleware.process_request(request, self._spider)
                if result is not None:
                    if isinstance(result, Request):
                        request = result
                    elif isinstance(result, Response):
                        response = result
                        break
            
            if response is None:
                # 2. 发送 HTTP 请求
                logger.debug(f"发送请求: {request.method} {request.url}")
                
                # 优先使用 request.kwargs 中的 timeout，否则使用 engine 默认配置
                request_timeout = request.kwargs.pop('timeout', self.request_timeout)
                
                
                start_time = time.time()
                raw_resp = self._session.request(
                    method=request.method,
                    url=request.url,
                    headers=request.headers or None,
                    cookies=request.cookies or None,
                    timeout=request_timeout,
                    **request.kwargs
                )
                time_cost = time.time() - start_time
                
                # 3. 封装 Response
                response = Response(raw_resp, meta=request.meta, request=request)
                logger.debug(f"收到响应: {request.method} {request.url} 状态码:{response.status_code} "
                                  f"耗时:{time_cost:.3f}s 长度:{len(response.content)} 内容预览:{response.text[:200].replace(chr(10), '')}")
            
            # 4. 执行中间件的 process_response（响应返回后）
            for middleware in reversed(self.middlewares):
                response = middleware.process_response(request, response, self._spider)
            
            # 5. 调用 callback
            callback = request.callback or self._spider.parse
            result = callback(response)
            
            # 6. 处理回调返回值
            if isinstance(result, types.GeneratorType):
                for item in result:
                    self._process_yield_item(item, pipelines, push_func)
            elif result is not None:
                self._process_yield_item(result, pipelines, push_func)
                
        except Exception as e:
            # 7. 执行中间件的 process_exception
            for middleware in self.middlewares:
                result = middleware.process_exception(request, e, self._spider)
                if result is not None:
                    if isinstance(result, Request):
                        self._process_single_request(result, pipelines, push_func)
                        return
                    elif isinstance(result, Response):
                        callback = request.callback or self._spider.parse
                        gen_result = callback(result)
                        # 修复: 异常重试产生的任务必须走 push_func 入队
                        self._process_generator(gen_result, pipelines, push_func)
                        return
            
            logger.error(f"请求失败: {request.url}, 错误: {e}")
            
            logger.debug(traceback.format_exc())
    
    def _process_item(self, item: Item, pipelines: List[Pipeline]):
        """
        处理 Item：流经所有 Pipeline
        """
        for pipeline in pipelines:
            try:
                item = pipeline.process_item(item, self._spider)
                if item is None:
                    break
            except Exception as e:
                logger.error(f"Pipeline 处理失败: {e}")
                logger.debug(traceback.format_exc())
    
    def _serialize_request(self, request: Request) -> dict:
        """
        序列化 Request 对象（用于 funboost 消息传递）
        """
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
