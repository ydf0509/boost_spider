import os
import sqlite3
import threading
from pathlib import Path

from pymongo.collection import Collection
from pymongo import MongoClient
from boost_spider.sink.sink_helper import log_save_item

"""
保存到sqlite
"""


class SqliteSink:
    def __init__(self, path, db, table):
        self.db = db
        self.table = table
        Path(path).mkdir(exist_ok=True)
        self.conn = sqlite3.connect( Path(path) /Path(f'{db}.db'))
        self.cursor = self.conn.cursor()
        self.__op_lock = threading.Lock()

    def save(self, item: dict):
        sql = self._build_sql(item)
        with self.__op_lock:
            self.cursor.execute(sql)
            self.conn.commit()
            log_save_item(item, 'sqlite', self.db, self.table)

    def _build_sql(self, item: dict):
        key_list = []
        value_list = []
        for k, v in item.items():
            key_list.append(k)
            value_list.append(v)
        # keys_str = str(tuple(key_list)).replace("'", "`")
        keys_str = ''
        for k in key_list:
            keys_str += f'`{k}`,'
        keys_str = f'( {keys_str[:-1]} )'

        values_str = ''
        for v in value_list:
            if isinstance(v,str):
                v = f"'{v}'"
            values_str += f'{v},'
        values_str = f'( {values_str[:-1]} )'
        sql = f"replace into {self.table} {keys_str} values {values_str}"
        return sql


if __name__ == '__main__':
    import sys

    # 遍历已导入的模块并打印自定义模块
    for module_name, module in sys.modules.items():
        if not module_name.startswith('built-in'):
            print(module_name)
    SqliteSink('/codedir/sqlite/','testdb','testtable').save({'a':'1','b':2})
    SqliteSink('/codedir/sqlite/', 'testdb', 'testtable').save({'a': '3', 'b': 4})