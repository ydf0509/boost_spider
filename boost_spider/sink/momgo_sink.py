from db_libs.mongo_fork_safe import get_col


class MongoSink:
    def __init__(self, db: str, col: str, uniqu_key: str, mongo_connect_url='mongodb://127.0.0.1', ):
        self.db = db
        self.col = col
        self.uniqu_key = uniqu_key
        self.mongo_connect_url = mongo_connect_url

    def save(self, item):
        item['_id'] = item[self.uniqu_key]
        get_col(self.db, self.col, self.mongo_connect_url).replace_one({'_id': item['_id']}, item, upsert=True)
