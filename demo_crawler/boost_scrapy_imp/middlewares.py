
from boost_scrapy import Middleware
import random


# ================= 自定义 Middleware（演示代理切换） =================

class MyProxyMiddleware(Middleware):
    """
    自定义代理中间件 - 演示用户如何从 Redis/内存 获取代理 IP
    
    用户可以根据实际情况修改 get_proxy() 方法：
    - 从 Redis 代理池获取
    - 从内存代理列表获取
    - 从第三方代理 API 获取
    """
    
    def __init__(self):
        # 模拟内存代理池（实际项目中可以从 Redis 获取）
        self.proxy_pool = [
            'http://proxy1.example.com:8080',
            'http://proxy2.example.com:8080',
            'http://proxy3.example.com:8080',
        ]
        # 如果使用 Redis:
        # import redis
        # self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    def get_proxy(self) -> str:
        """
        获取代理 IP（用户可自定义实现）
        
        示例：
        - 从内存列表随机获取
        - 从 Redis 的 set/list 获取
        - 从代理服务商 API 获取
        """
        # 方式1：从内存列表随机选一个
        proxy = random.choice(self.proxy_pool)
        
        # 方式2：从 Redis 获取（示例）
        # proxy = self.redis_client.srandmember('proxy_pool').decode()
        
        # 方式3：从代理服务商 API 获取（示例）
        # resp = requests.get('http://proxy-api.com/get')
        # proxy = resp.json()['proxy']
        
        return proxy
    
    def process_request(self, request, spider):
        """每次请求时自动设置代理"""
        proxy = self.get_proxy()
        request.kwargs['proxies'] = {'http': proxy, 'https': proxy}
        print(f"  🌐 [MyProxyMiddleware] 使用代理: {proxy}")
        return None


class MyUserAgentMiddleware(Middleware):
    """
    自定义 UA 中间件 - 演示用户如何切换 UserAgent
    """
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]
    
    def process_request(self, request, spider):
        """每次请求时随机切换 UA"""
        ua = random.choice(self.USER_AGENTS)
        request.headers['User-Agent'] = ua
        print(f"  🔄 [MyUserAgentMiddleware] UA: {ua[:50]}...")
        return None