import nb_log

logger = nb_log.get_logger('boost_spider.sink',log_filename='boost_spider_sink.log')

def log_save_item(item, dbtype, db, table):
    logger.info(f'保存结果到 {dbtype} {db}.{table} 中成功,  {item} ')
