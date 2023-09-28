import datetime
import json
import threading
import time
from pathlib import Path

from boost_spider.sink.sink_helper import log_save_item


class JsonFileSink:
    _lock = threading.Lock()
    # path__has_create_map = {}
    full_path__f_map = {}

    def __init__(self, path, file):
        self.full_path = Path(path) / Path(file)
        self._key = f'{path}{file}'
        if self._key not in self.full_path__f_map:
            Path(path).mkdir(exist_ok=True)
            self.full_path__f_map[self._key] = Path(self.full_path).open('a+', encoding='utf8')
        self.f = self.full_path__f_map[self._key]

    def save(self, item: dict):
        item['item_insert_time'] = str(datetime.datetime.now())
        with self._lock:
            self.f.write(json.dumps(item) + ',\n')
        # log_save_item(item,'jsonfile',self.full_path,'')

    def read_json(self):
        text = Path(self.full_path).read_text(encoding='utf8')
        json_text = f'[{text[:-2]}]'
        return json.loads(json_text)


if __name__ == '__main__':
    t1 = time.time()
    for i in range(1000):
        # JsonFileSink('/codedir', 'testjsonfile2.json').save({'a': i, 'b': f'{i*2}'})
        JsonFileSink('/codedir', 'testjsonfile.json').save({'a': 63, 'b': 4})
        pass
    print(time.time() - t1)
    # print(JsonFileSink('/codedir', 'testjsonfile2.json').read_json())
