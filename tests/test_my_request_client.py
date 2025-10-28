from boost_spider import RequestClient


class MyRequestClient(RequestClient):

    def _request_with_my_redis_ip_proxy(self, method, url, **kwargs):
        # 实现你自己的代理逻辑

        # proxies = {
        #     "http": $从你的redis ip代理池随机取一个ip,
        # "https": $从你的redis ip代理池随机取一个ip,
        # }
        proxies = None
        return self.ss.request(method, url, proxies=proxies, **kwargs)

        # 扩展代理映射

    RequestClient.PROXYNAME__REQUEST_METHED_MAP['my_proxy'] = _request_with_my_redis_ip_proxy



if __name__ == '__main__':
    MyRequestClient().get('https://www.baidu.com')