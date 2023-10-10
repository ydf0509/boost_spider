import asyncio
import httpx
from funboost import boost, BrokerEnum, ConcurrentModeEnum
import threading

thread_local = threading.local()


def get_client():
    if not getattr(thread_local, 'httpx_async_client', None):
        thread_local.httpx_async_client = httpx.AsyncClient()
    return thread_local.httpx_async_client


@boost('test_httpx_q2', broker_kind=BrokerEnum.REDIS, concurrent_mode=ConcurrentModeEnum.ASYNC, concurrent_num=500)
async def f(url):
    # client= httpx.AsyncClient()
    client = get_client()
    r = await client.get(url)
    print(r.status_code, len(r.text))


if __name__ == '__main__':
    # asyncio.run(f())
    f.consume()
    for i in range(10000):
        f.push('https://www.baidu.com/')
