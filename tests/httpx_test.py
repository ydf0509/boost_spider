import asyncio
import httpx
from funboost import boost, BrokerEnum, ConcurrentModeEnum


@boost('test_queue', broker_kind=BrokerEnum.REDIS, concurrent_mode=ConcurrentModeEnum.ASYNC, concurrent_num=500)
async def f(url):
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        print(r.status_code, len(r.text))


if __name__ == '__main__':
    # asyncio.run(f())
    for i in range(1000):
        f.push('https://www.baidu.com/')
    f.consume()
