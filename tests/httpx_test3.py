import httpx
from funboost import boost, BrokerEnum, ConcurrentModeEnum, ctrl_c_recv

client = httpx.AsyncClient()


@boost('test_httpx_q3', broker_kind=BrokerEnum.REDIS, concurrent_mode=ConcurrentModeEnum.ASYNC, concurrent_num=500)
async def f(url):
    # client= httpx.AsyncClient()
    r = await client.get(url)
    print(r.status_code, len(r.text))


if __name__ == '__main__':
    # asyncio.run(f())
    f.clear()
    f.consume()
    for i in range(10):
        f.push('https://www.baidu.com/')
    ctrl_c_recv()
