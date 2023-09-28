import datetime
import json
import threading
from pathlib import Path


class JsonFileSink:
    _lock = threading.Lock()

    def __init__(self, path, file):
        Path(path).mkdir(exist_ok=True)
        self.full_path = Path(path) / Path(file)

    def save(self, item: dict):
        with self._lock:
            with Path(self.full_path).open('a+', encoding='utf8') as f:
                item['item_insert_time'] = str(datetime.datetime.now())
                f.write(json.dumps(item) + '\n')


if __name__ == '__main__':
    JsonFileSink('/codedir', 'testjsonfile.json').save({'a': 1, 'b': '44'})
    # JsonFileSink('/codedir', 'testjsonfile.json').save({'a': 63, 'b': 4})
