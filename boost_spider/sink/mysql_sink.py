import typing

import pymysql.cursors
from universal_object_pool import ObjectPool
from universal_object_pool.contrib.pymysql_pool import PyMysqlOperator


class MysqlSink:
    _key__pool_map = {}

    def _get_pool(self):
        if self._pool_key not in self._key__pool_map:
            self._key__pool_map[self._pool_key] = ObjectPool(object_type=PyMysqlOperator,
                                                             object_pool_size=100,
                                                             object_init_kwargs=self._mysql_conn_kwargs)
        return self._key__pool_map[self._pool_key]

    def __init__(self, host='192.168.6.130', port=3306, user='root', password='123456', db=None, table=None):
        self._mysql_conn_kwargs = {'host': host, 'user': user, 'password': password, 'port': port}
        self._pool_key = f'{host} {port} {user} {password}'
        self.db = db
        self.table = table

    def save(self, item: dict):
        mysql_pool = self._get_pool()
        sql = self._build_sql(item)
        print(sql)
        with mysql_pool.get() as operator:  # type: typing.Union[PyMysqlOperator,pymysql.cursors.DictCursor] #利于补全
            operator.execute(sql)

    def _build_sql(self, item: dict):
        key_list = []
        value_list = []
        for k, v in item.items():
            key_list.append(k)
            value_list.append(v)
        keys_str = str(tuple(key_list)).replace("'", "`")
        sql = f"replace into {self.db}.{self.table} {keys_str} values {tuple(value_list)}"
        return sql


if __name__ == '__main__':
    MysqlSink(db='testdb', table='test_table').save({'a': 1, 'b': 2})
