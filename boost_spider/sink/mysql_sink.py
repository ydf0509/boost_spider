import typing

import pymysql.cursors
from universal_object_pool import ObjectPool
from universal_object_pool.contrib.pymysql_pool import PyMysqlOperator

from boost_spider.sink.sink_helper import log_save_item


class MysqlSink:
    _key__pool_map = {}

    def _get_pool(self):
        if self._pool_key not in self._key__pool_map:
            self._key__pool_map[self._pool_key] = ObjectPool(object_type=PyMysqlOperator,
                                                             object_pool_size=100,
                                                             object_init_kwargs=self._mysql_conn_kwargs)
        return self._key__pool_map[self._pool_key]

    def __init__(self, host='127.0.0.1', port=3306, user='root', password='123456', db=None, table=None):
        self._mysql_conn_kwargs = {'host': host, 'user': user, 'password': password, 'port': port,'database':db}
        self._pool_key = f'{host} {port} {user} {password} {db}'
        self.db = db
        self.table = table

    def save(self, item: dict):
        mysql_pool = self._get_pool()
        sql = self._build_sql(item)
        with mysql_pool.get() as operator:  # type: typing.Union[PyMysqlOperator,pymysql.cursors.DictCursor] #利于补全
            operator.execute(sql,args=None)
        log_save_item(item, 'mysql', self.db, self.table)

    def _build_sql(self, item: dict):
        """
        这段字典转sql代码是复制网上的，可以使用dataset_sink来直接保存字典。
        :param item:
        :return:
        """
        key_list = []
        value_list = []
        for k, v in item.items():
            key_list.append(k)
            value_list.append(v)
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
    print(MysqlSink(db='testdb', table='test_table')._build_sql({'a': 1, 'b': 2}))
    MysqlSink(db='testdb', table='t2').save({'uname': 'uname1', 'age': 1})
