"""
dataset 很适合保存一个字典到各种数据库 mysql postgre sqlite
"""
import dataset


class DatasetSink:
    # 类级别的实例缓存，按 db_url 存储
    _instances = {}
    _has__init_set = set()

    def __new__(cls, db_url):
        # 如果 db_url 已存在，直接返回已有实例
        if db_url not in cls._instances:
            # 创建新实例并存入缓存
            self = super(DatasetSink, cls).__new__(cls)
            cls._instances[db_url] = self
        return cls._instances[db_url]

    def __init__(self, db_url):
        if id(self) not in self.__class__._has__init_set:
            print(f'创建连接 {db_url}')
            self.db = dataset.connect(db_url, ensure_schema=True)
            self.__class__._has__init_set.add(id(self))

    def save(self, table_name: str, data: dict, ):
        # 使用已有的连接插入数据
        table = self.db[table_name]
        table.insert(data)

    # @classmethod
    # def get_instance(cls, db_url="mysql://root:pass@localhost/test"):
    #     # 提供一个显式的获取实例方法（可选）
    #     return cls(db_url)


if __name__ == '__main__':
    dataset_sink1 = DatasetSink("mysql+pymysql://root:123456@localhost/testdb2")
    DatasetSink("mysql+pymysql://root:123456@localhost/testdb2")
    data = {'user': 'user2', 'oderid': 222}
    dataset_sink1.save('your_table', data)  # 使用第一个数据库
