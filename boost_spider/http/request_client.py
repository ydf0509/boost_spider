# coding=utf-8
"""
改版包装requests的Session类，主要使用的是代理模式
1、支持一键设多种代理ip
2、支持3种类型的cookie添加
3、支持长会话，保持cookie状态, ss = RequestClient() , 一直用这个ss对象就可以自动保持cookie了
4、支持一键设置requests请求重试次数，确保请求成功，默认重试一次。
5、记录下当天的请求到文件，方便统计，同时开放了日志级别设置参数，用于禁止日志。
6、从使用requests修改为使用RequstClient门槛很低，三方包的request方法和此类的方法入参和返回完全100%保持了一致。
7、支持代理自动切换。需要将proxy_name设置为一个列表，指定多个代理的名字。
8、支持继承 RequestClient 来增加使用各种代理的请求方法，新增加代理商后，将请求方法名字加到 PROXYNAME__REQUEST_METHED_MAP 中。
"""
import json
import logging
import typing
from enum import Enum
from functools import lru_cache
from pathlib import Path

import nb_log
import copy
import time
from typing import Union
import requests
from requests.cookies import RequestsCookieJar
import urllib3.exceptions

from boost_spider.http.user_agent import rand_get_useragent

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from parsel import Selector
import re


class HttpStatusError(Exception):
    def __init__(self, http_status_code):
        super().__init__(f'请求返回的状态码不是200，是{http_status_code}')


request_logger = nb_log.get_logger('RequestClient', log_level_int=logging.DEBUG)


class SpiderResponse(requests.Response):  # 继承主要是方便代码补全提示，
    # noinspection PyMissingConstructor

    re_pattern_map = {}  # type: typing.Dict[str,re.Pattern]

    def __init__(self, resp: requests.Response):
        self.__dict__.update(resp.__dict__)  # 使 SpiderResponse 类具备requests.Response的所有属性

    @property
    @lru_cache()
    def selector(self) -> Selector:
        return Selector(self.text)

    @property
    @lru_cache()
    def resp_dict(self) -> typing.Dict:
        return json.loads(self.text)

    @property
    @lru_cache()
    def text(self) -> str:
        return super().text

    def re_search(self, pattern, flags=0):
        key = f'{pattern} {flags}'
        if key not in self.re_pattern_map:
            pa_obj = re.compile(pattern=pattern, flags=flags)
            self.re_pattern_map[key] = pa_obj
        return self.re_pattern_map[key].search(self.text)

    def re_findall(self, pattern, flags=0):
        # return re.findall(pattern, self.text, flags)
        key = f'{pattern} {flags}'
        if key not in self.re_pattern_map:
            pa_obj = re.compile(pattern=pattern, flags=flags)
            self.re_pattern_map[key] = pa_obj
        return self.re_pattern_map[key].findall(self.text)


# noinspection PyBroadException
class RequestClient:
    logger = request_logger

    def __init__(self, proxy_name_list=None,
                 ua=None, default_use_pc_ua=True, is_change_ua_every_request=False,
                 timeout: Union[tuple, float] = (30, 40),
                 verify=False, allow_redirects=True, is_close_session=True,
                 request_retry_times=2,
                 using_platfrom=''):
        """
        :param proxy_name_list: 轮流使用代理服务商名字，可设置为 None,'noproxy', 'kuai', 'abuyun', 'crawlera',为None不使用代理
        :param ua:  useragent，如果不设置就随机分配一个欺骗的
        :param is_change_ua_every_request: 为每次请求设置新的useragent
        :param timeout: 超时设置
        :param verify:  是否校验服务器证书
        :param allow_redirects
        :param is_close_session: 是否在请求后关闭会话，连续型的请求需要cookie保持的，请设置为False，并且一直使用RequestClient实例化后的对象
        :param logger_level:日志级别，10 20 30 40 50
        """
        if proxy_name_list is None:
            proxy_name_list = ['noproxy']
        if not isinstance(proxy_name_list, list):
            proxy_name_list = [proxy_name_list]
        if not set(proxy_name_list).issubset(set(self.PROXYNAME__REQUEST_METHED_MAP.keys())):
            raise Exception('设置的代理名称错误')
        self._proxy_name_list = proxy_name_list
        default_ua = (
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36' if default_use_pc_ua else
            'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Mobile Safari/537.36')
        self._ua = ua if ua else default_ua
        self._default_use_pc_ua = default_use_pc_ua
        self._is_change_ua_every_request = is_change_ua_every_request
        self._timeout = timeout
        self._verify = verify
        self._allow_redirects = allow_redirects
        self._is_close_session = is_close_session
        self.ss = requests.Session()
        self._max_request_retry_times = request_retry_times
        self._using_platfrom = using_platfrom

    def __add_ua_to_headers(self, headers):
        # noinspection PyDictCreation
        if not headers:
            headers = dict()
            headers['user-agent'] = self._ua
        else:
            if 'user-agent' not in headers and 'User-Agent' not in headers:
                headers['user-agent'] = self._ua
        if self._is_change_ua_every_request:
            if self._default_use_pc_ua:
                headers['user-agent'] = rand_get_useragent('chrome')
            else:
                headers['user-agent'] = rand_get_useragent('mobile')
        headers.update({'Accept-Language': 'zh-CN,zh;q=0.8'})
        return headers

    def get_cookie_jar(self):
        """返回cookiejar"""
        return self.ss.cookies

    def get_cookie_dict(self):
        """返回cookie字典"""
        return self.ss.cookies.get_dict()

    def get_cookie_str(self):
        """返回cookie字典"""
        cookie_str = ''
        for cookie_item in self.get_cookie_dict().items():
            cookie_str += cookie_item[0] + '=' + cookie_item[1] + ';'
        return cookie_str[:-1]

    def add_cookies(self, cookies: Union[str, dict, RequestsCookieJar]):
        """
        :param cookies: 浏览器复制的cookie字符串或字典类型或者CookieJar类型
        :return:
        """
        cookies_dict = dict()
        if not isinstance(cookies, (str, dict, RequestsCookieJar)):
            raise TypeError('传入的cookie类型错误')
        if isinstance(cookies, str):
            cookie_pairs = cookies.split('; ')
            for cookie_pair in cookie_pairs:
                k, v = cookie_pair.split('=', maxsplit=1)
                cookies_dict[k] = v
        if isinstance(cookies, (dict, RequestsCookieJar)):
            cookies_dict = cookies
        self.ss.cookies = requests.sessions.merge_cookies(self.ss.cookies, cookies_dict)

    def request(self, method: str, url: str, verify: bool = None,
                timeout: Union[int, float, tuple] = None, headers: dict = None,
                cookies: dict = None, **kwargs) -> typing.Optional[SpiderResponse]:
        """
        使用指定名字的代理请求,从_proxy_name读取,当请求出错时候轮流使用各种代理ip。
        :param method:
        :param url:
        :param verify:
        :param timeout:
        :param headers:
        :param cookies:
        :param kwargs:
        :param kwargs :可接受一切requests.request方法中的参数
        :return:
        """
        # self.logger.debug(locals())
        key_word_args = copy.copy(locals())
        key_word_args['headers'] = self.__add_ua_to_headers(headers)
        # key_word_args.pop('self')
        key_word_args.pop('kwargs')
        key_word_args.update(kwargs)
        if 'allow_redirects' not in key_word_args:
            key_word_args['allow_redirects'] = self._allow_redirects

        resp = None
        # self.logger.debug('starting {} this url -->  '.format(method) + url)
        # print(key_word_args)
        exception_request = None
        proxy_list = self._proxy_name_list * (self._max_request_retry_times + 1)
        for i in range(self._max_request_retry_times + 1):
            current_proxy_name = proxy_list[i]
            t_start = time.time()
            try:
                request_proxy_method = self.PROXYNAME__REQUEST_METHED_MAP[current_proxy_name]
                resp = request_proxy_method(**key_word_args)
                time_spend = round(time.time() - t_start, 2)
                resp.time_spend = time_spend
                resp.ts = time_spend  # 简写
                resp_log_dict = {
                    'time_spend': round(time_spend, 2),
                    'status_code': resp.status_code,
                    'method': method,
                    'current_retry_time': i,
                    'current_proxy_name': current_proxy_name,
                    'is_redirect': resp.is_redirect,
                    'resp_len': len(resp.text),
                    'resp_url': resp.url,
                }
                msg = f''' {self._using_platfrom}  request响应状态: {json.dumps(resp_log_dict, ensure_ascii=False)}'''
                self.logger.debug(msg, extra=resp_log_dict)
                if resp.status_code != 200 and i < self._max_request_retry_times + 1:
                    self.logger.warning(msg, extra=resp_log_dict)
                    raise HttpStatusError(resp.status_code)
                if i != 0:
                    pass
                    # self.logger.info(f'第 {i} 次重试请求成功')
                break
            except Exception as e:
                exception_request = e
                if i != self._max_request_retry_times:
                    self.logger.warning(
                        f'{self._using_platfrom} RequestClient内部第{i}次请求出错，此次使用的代理是{current_proxy_name},'
                        f'浪费时间[{round(time.time() - t_start, 2)}],再重试一次，原因是：{type(e)}    {e}')
        self.close_session()
        if resp is not None:  # 如<Response [404]>也是false,但不是none
            return SpiderResponse(resp)
        else:
            raise exception_request

    def get(self, url: str, verify: bool = None,
            timeout: Union[int, float, tuple] = None, headers: dict = None,
            cookies: dict = None, **kwargs):
        params = copy.copy(locals())
        params.pop('self')
        params.pop('kwargs')
        params.update(kwargs)
        params['method'] = 'get'
        return self.request(**params)

    def post(self, url: str, verify: bool = None,
             timeout: Union[int, float, tuple] = None, headers: dict = None,
             cookies: dict = None, **kwargs):
        params = copy.copy(locals())
        params.pop('self')
        params.pop('kwargs')
        params.update(kwargs)
        params['method'] = 'post'
        return self.request(**params)

    def close_session(self):
        if self._is_close_session:
            try:
                self.ss.close()
            except Exception:
                pass

    def save_picture(self, url, pic_path, pic_file=None, ):
        resp = self.get(url)
        if pic_file is None:
            pic_file = url.split('/')[-1]
        Path(pic_path).mkdir(exist_ok=True)
        full_path = Path(pic_path) / Path(pic_file)
        full_path.write_bytes(resp.content)

    def _request_with_no_proxy(self, method, url, verify=None, timeout=None, headers=None, cookies=None, **kwargs):
        """普通不使用代理"""

        return self.ss.request(method, url, verify=verify or self._verify, timeout=timeout or self._timeout,
                               headers=headers, cookies=cookies, **kwargs)

    def _request_with_abuyun_proxy(self, method, url, verify=None, timeout=None, headers=None, cookies=None, **kwargs):
        # 代理服务器
        proxy_host = "http-dyn.abuyun.com"
        proxy_port = "9020"

        # 代理隧道验证信息
        proxy_user = "HH65YN4C381XXXXX"
        proxy_pass = "7176BE32A00YYYYY"

        proxy_meta = "http://%(user)s:%(pass)s@%(host)s:%(port)s" % {
            "host": proxy_host,
            "port": proxy_port,
            "user": proxy_user,
            "pass": proxy_pass,
        }

        proxies = {
            "http": proxy_meta,
            "https": proxy_meta,
        }
        resp = self.ss.request(method, url, verify=verify or self._verify, timeout=timeout or self._timeout,
                               headers=headers, cookies=cookies,
                               proxies=proxies, **kwargs)
        if resp.status_code == 429 or "429 Too Many Requests'" in resp.text or "429 To Many Requests'" in resp.text:
            raise IOError(f'阿布云返回的状态是 {resp.status_code}')
        return resp

    def _request_with_kuai_proxy(self, method, url, verify=None, timeout=None, headers=None, cookies=None, **kwargs):
        """使用redis中的快代理池子,怎么从redis拿代理ip和requests怎么使用代理，用户自己写"""

        raise NotImplemented

    PROXY_NOPROXY = 'noproxy'  # 方便代理名称补全.
    PROXY_ABUYUN = 'abuyun'
    PROXY_KUAI = 'kuai'

    PROXYNAME__REQUEST_METHED_MAP = {'noproxy': _request_with_no_proxy,
                                     'abuyun': _request_with_abuyun_proxy,
                                     'kuai': _request_with_kuai_proxy
                                     }  # 用户新增了方法后，在这里添加代理名字和请求方法的映射映射


if __name__ == '__main__':
    rc = RequestClient(using_platfrom='爬百度的')
    resp = rc.get('https://www.baidu.com')
    print(resp.request.headers)
    print(resp.status_code)
    print(resp.selector)
    print(resp.selector)

    rc.save_picture('https://scarb-images.oss-cn-hangzhou.aliyuncs.com/img/202207142159934.png', '/pics')
