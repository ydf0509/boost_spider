import abc
import threading
import time
from typing import Type, TypeVar

T = TypeVar('T')


class BaseThreadLocalObjGetter(metaclass=abc.ABCMeta):
    thread_local = threading.local()

    def get_obj(self, obj_type: T,) -> T:
        obj_name = str(type(self))
        if not getattr(self.thread_local, obj_name, None):
            obj = self._get_obj()
            print(f'生成线程变量 {obj}')
            setattr(self.thread_local, obj_name, obj)
        return getattr(self.thread_local, obj_name)

    @abc.abstractmethod
    def _get_obj(self):
        raise NotImplemented


if __name__ == '__main__':
    import httpx
    from concurrent.futures import ThreadPoolExecutor


    class AsyncClientGetter(BaseThreadLocalObjGetter):
        def _get_obj(self):
            return httpx.AsyncClient()


    def t():
        for i in range(5):
            print(AsyncClientGetter().get_obj(httpx.AsyncClient))


    pool = ThreadPoolExecutor(20)
    for i in range(10):
        pool.submit(t)
