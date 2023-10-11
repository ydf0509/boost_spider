import asyncio
import httpx
from funboost import boost, BrokerEnum, ConcurrentModeEnum
import threading

thread_local = threading.local()


def get_client() -> httpx.AsyncClient:
    if not getattr(thread_local, 'httpx_async_client', None):
        # limits=httpx.Limits(max_connections=300,max_keepalive_connections=300)
        thread_local.httpx_async_client = httpx.AsyncClient()
    return thread_local.httpx_async_client


@boost('test_httpx_q2', broker_kind=BrokerEnum.REDIS, concurrent_mode=ConcurrentModeEnum.THREADING, concurrent_num=500)
async def f(url):
    # client= httpx.AsyncClient()
    r = await get_client().get(url)
    print(r.status_code, len(r.text))


if __name__ == '__main__':
    # asyncio.run(f())
    f.clear()
    f.multi_process_consume(1)
    for i in range(10):
        # http://group.yiai.me/_next/static/_5gZYR712KCYbr7mIlb3S/_ssgManifest.js   http://www.baidu.com/
        f.push('http://127.0.0.1:8000/')
