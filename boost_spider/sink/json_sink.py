import datetime
import json
import threading
from pathlib import Path


class JsonFileSink:
    _lock = threading.Lock()
    _has_mkdir = False

    def __init__(self, path, file):
        if not self._has_mkdir:
            self.__class__._has_mkdir = True
            Path(path).mkdir(exist_ok=True)
        self.full_path = Path(path) / Path(file)

    def save(self, item: dict):
        with self._lock:
            with Path(self.full_path).open('a+', encoding='utf8') as f:
                item['item_insert_time'] = str(datetime.datetime.now())
                f.write(json.dumps(item) + ',\n')

    def read_json(self):
        text = Path(self.full_path).read_text(encoding='utf8')
        json_text = f'[{text[:-2]}]'
        return json.loads(json_text)


if __name__ == '__main__':
    for i in range(100):
        # JsonFileSink('/codedir', 'testjsonfile2.json').save({'a': i, 'b': f'{i*2}'})
        # JsonFileSink('/codedir', 'testjsonfile.json').save({'a': 63, 'b': 4})
        pass
    print(JsonFileSink('/codedir', 'testjsonfile2.json').read_json())
