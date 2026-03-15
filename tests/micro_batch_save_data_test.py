# -*- coding: utf-8 -*-
"""
微批消费批量插入数据库测试
使用 funboost 自带的 MicroBatchBoosterParams 微批功能
使用 SQLAlchemy 和 SQLite - 支持动态多表插入
"""

import sys

sys.path.insert(2,'/codes/funboost')

import time
import threading
from pathlib import Path
from typing import Any, Dict, List
from collections import defaultdict
from sqlalchemy import create_engine, Table, Column, Integer, String, Float, Text, MetaData, text, inspect
from sqlalchemy.orm import sessionmaker
from funboost import boost, BrokerEnum, ctrl_c_recv
from funboost.contrib.override_publisher_consumer_cls.funboost_micro_batch_mixin import (
    MicroBatchConsumerMixin, MicroBatchBoosterParams
)

DB_PATH = Path(__file__).parent / 'micro_batch_test.db'
DATABASE_URL = f'sqlite:///{DB_PATH}'

engine = create_engine(
    DATABASE_URL, 
    echo=False,
    connect_args={'check_same_thread': False},
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()

_table_cache: Dict[str, float] = {}
_table_cache_lock = threading.Lock()
_db_write_lock = threading.RLock()
TABLE_CACHE_TTL = 60


def infer_column_type(value: Any):
    """根据值推断 SQLAlchemy 列类型"""
    if isinstance(value, int):
        return Integer
    elif isinstance(value, float):
        return Float
    elif isinstance(value, str):
        if len(value) > 200:
            return Text
        return String(500)
    else:
        return Text


def get_or_create_table(table_name: str, sample_data: Dict[str, Any]) -> Table:
    """获取或创建表，根据字典自动推断字段类型，带60秒缓存"""
    global _table_cache
    
    current_time = time.time()
    
    with _table_cache_lock:
        if table_name in _table_cache:
            if current_time - _table_cache[table_name] < TABLE_CACHE_TTL:
                return Table(table_name, metadata, autoload_with=engine, extend_existing=True)
    
    with _db_write_lock:
        inspector = inspect(engine)
        
        if table_name in inspector.get_table_names():
            with _table_cache_lock:
                _table_cache[table_name] = current_time
            return Table(table_name, metadata, autoload_with=engine, extend_existing=True)
        
        columns = [Column('id', Integer, primary_key=True, autoincrement=True)]
        
        for key, value in sample_data.items():
            col_type = infer_column_type(value)
            columns.append(Column(key, col_type))
        
        table = Table(table_name, metadata, *columns, extend_existing=True)
        metadata.create_all(bind=engine, tables=[table])
        
        with _table_cache_lock:
            _table_cache[table_name] = current_time
        
        print(f'✅ 自动创建表: {table_name}')
        
        return table


def init_db():
    """初始化数据库"""
    if DB_PATH.exists():
        DB_PATH.unlink()
        metadata.clear()
    print('✅ 数据库初始化完成')


@boost(MicroBatchBoosterParams(
    queue_name='micro_batch_sqlite_queue',
    broker_kind=BrokerEnum.MEMORY_QUEUE,
    user_options={
        'micro_batch_size': 10,
        'micro_batch_timeout': 3.0,
    },
))
def batch_insert_to_sqlite(items: list):
    """
    微批消费函数：接收消息列表，按表名分组批量插入
    
    :param items: 消息列表，格式如下:
        [
            {'table_name': 'table1', 'data': {'user_id': 1, 'username': 'user_1'}},
            {'table_name': 'table2', 'data': {'news_id': 1, 'title': 'news_1'}},
            {'table_name': 'table1', 'data': {'user_id': 2, 'username': 'user_2'}},
        ]
    """
    print(f'📦 收到批次，共 {len(items)} 条数据')
    
    if not items:
        return
    
    table_data_map: Dict[str, List[Dict]] = defaultdict(list)
    for item in items:
        table_name = item.get('table_name')
        data = item.get('data', {})
        if table_name and data:
            table_data_map[table_name].append(data)
    
    with _db_write_lock:
        db = SessionLocal()
        try:
            for table_name, data_list in table_data_map.items():
                sample_data = data_list[0]
                table = get_or_create_table(table_name, sample_data)
                
                insert_stmt = table.insert()
                db.execute(insert_stmt, data_list)
                print(f'✅ 表 {table_name} 批量插入 {len(data_list)} 条')
            
            db.commit()
            print(f'✅ 全部批量插入成功')
        except Exception as e:
            db.rollback()
            print(f'❌ 批量插入失败: {e}')
            raise
        finally:
            db.close()


if __name__ == '__main__':
    init_db()
    
    batch_insert_to_sqlite.consume()
    
    print('🚀 开始发布测试消息（多表）...')
    print('=' * 60)
    
    for i in range(15):
        batch_insert_to_sqlite.push(
            table_name='user_table',
            data={'user_id': i + 1, 'username': f'user_{i + 1}', 'age': 20 + i}
        )
        print(f'发布 user_table: user_id={i + 1}')
    
    for i in range(10):
        batch_insert_to_sqlite.push(
            table_name='news_table',
            data={'news_id': i + 1, 'title': f'新闻标题_{i + 1}', 'views': 100 * (i + 1)}
        )
        print(f'发布 news_table: news_id={i + 1}')
    
    print('\n' + '=' * 60)
    print('⏳ 等待微批消费处理...')
    
    time.sleep(8)
    
    print('\n' + '=' * 60)
    print('📊 验证插入结果:')
    db = SessionLocal()
    try:
        for table_name in ['user_table', 'news_table']:
            result = db.execute(text(f'SELECT COUNT(*) as cnt FROM {table_name}')).fetchone()
            print(f'✅ 表 {table_name} 共有 {result[0]} 条记录')
            
            rows = db.execute(text(f'SELECT * FROM {table_name} ORDER BY id LIMIT 3')).fetchall()
            print(f'  前 3 条记录:')
            for row in rows:
                print(f'    {dict(row._mapping)}')
    finally:
        db.close()
    
    ctrl_c_recv()
