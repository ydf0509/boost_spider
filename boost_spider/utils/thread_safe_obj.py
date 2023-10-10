import abc
import threading
import time


class BaseThreadSafeObjGetter(metaclass=abc.ABCMeta):
    thread_local = threading.local()

    def get_obj(self):
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


    class AsyncClientGetter(BaseThreadSafeObjGetter):
        def _get_obj(self):
            return httpx.AsyncClient()


    def t():
        for i in range(5):
            print(AsyncClientGetter().get_obj())


    pool = ThreadPoolExecutor(20)
    for i in range(10):
        pool.submit(t)
