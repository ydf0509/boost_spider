import os
import sqlite3
import threading
from pathlib import Path
import nb_log
from pymongo.collection import Collection
from pymongo import MongoClient
from boost_spider.sink.sink_helper import log_save_item

"""
保存到sqlite
"""


class SqliteSink:
    db__cusor_map = {}
    db__conn_map = {}
    _op_lock = threading.Lock()

    logger = nb_log.get_logger('SqliteSink')

    def __init__(self, path, db, table):
        self.db = db
        self.table = table
        self._key = f'{path} {db}'
        if self._key not in self.db__cusor_map:
            Path(path).mkdir(exist_ok=True)
            full_path = Path(path) / Path(f'{db}.db')
            conn = sqlite3.connect(full_path)
            cursor = conn.cursor()
            self.logger.debug(f'创建 {full_path} sqlite连接成功')
            self.db__cusor_map[self._key] = cursor
            self.db__conn_map[self._key] = conn
        self.cusror = self.db__cusor_map[self._key]
        self.conn = self.db__conn_map[self._key]

    def save(self, item: dict):
        sql = self._build_sql(item)
        with self._op_lock:
            self.cusror.execute(sql)
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
            if isinstance(v, str):
                v = f"'{v}'"
            values_str += f'{v},'
        values_str = f'( {values_str[:-1]} )'
        sql = f"replace into {self.table} {keys_str} values {values_str}"
        return sql


if __name__ == '__main__':
    SqliteSink('/codedir/sqlite/', 'testdb', 'testtable').save({'a': '1', 'b': 2})
    SqliteSink('/codedir/sqlite/', 'testdb', 'testtable').save({'a': '7', 'b': 8})
