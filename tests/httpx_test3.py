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
