import os
from pymongo.collection import Collection
from pymongo import MongoClient
from boost_spider.sink.sink_helper import log_save_item

"""
此模块封装的pymongo是在linux上子进程安全的。
在win上无所谓都正常。
"""


class MongoSink:
    pid__col_map = {}

    def __init__(self, db: str, col: str, uniqu_key: str, mongo_connect_url='mongodb://127.0.0.1', ):
        self.db = db
        self.col = col
        self.uniqu_key = uniqu_key
        self.mongo_connect_url = mongo_connect_url

    def get_col(self, ) -> Collection:
        """封装一个函数，判断pid"""
        pid = os.getpid()
        key = (pid, self.mongo_connect_url, self.db, self.col)
        if key not in self.pid__col_map:
            self.pid__col_map[key] = MongoClient(self.mongo_connect_url).get_database(self.db).get_collection(self.col)
        return self.pid__col_map[key]

    def save(self, item):
        item['_id'] = item[self.uniqu_key]
        self.get_col().replace_one({'_id': item['_id']}, item, upsert=True)
        log_save_item(item, 'mongo', self.db, self.col)
