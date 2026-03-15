# -*- coding: utf-8 -*-
"""
微批消费批量插入数据库测试
使用 SQLAlchemy 和 SQLite - 简化版，自动停止
"""
import time
import threading
from pathlib import Path
from sqlalchemy import create_engine, Table, Column, Integer, String, DateTime, MetaData, text
from sqlalchemy.orm import sessionmaker
from funboost import boost, BrokerEnum, ctrl_c_recv
from funboost.contrib.override_publisher_consumer_cls.funboost_micro_batch_mixin import (
    MicroBatchConsumerMixin, MicroBatchBoosterParams
)

DB_PATH = Path(__file__).parent / 'micro_batch_test.db'
DATABASE_URL = f'sqlite:///{DB_PATH}'

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()

user_data = Table(
    'user_data',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('user_id', Integer, nullable=False, unique=True),
    Column('username', String(100), nullable=False),
    Column('age', Integer),
    Column('email', String(200)),
    Column('create_time', DateTime, server_default=text('CURRENT_TIMESTAMP'))
)


def init_table():
    """初始化测试表"""
    if DB_PATH.exists():
        DB_PATH.unlink()
    
    metadata.create_all(bind=engine)
    print('✅ 数据库表初始化完成')


@boost(MicroBatchBoosterParams(
    queue_name='micro_batch_sqlite_queue',
    broker_kind=BrokerEnum.MEMORY_QUEUE,
    concurrent_num=1,
    user_options={
        'micro_batch_size': 10,
        'micro_batch_timeout': 2.0,
    },
))
def batch_insert_to_sqlite(items: list):
    """
    微批消费函数：批量插入 SQLite
    
    :param items: 消息列表，每个元素是一个字典
    """
    print(f'📦 收到批次，共 {len(items)} 条数据')
    
    if not items:
        return
    
    db = SessionLocal()
    try:
        insert_stmt = user_data.insert()
        db.execute(insert_stmt, items)
        db.commit()
        
        print(f'✅ 批量插入成功')
        
    except Exception as e:
        db.rollback()
        print(f'❌ 批量插入失败: {e}')
        raise
    finally:
        db.close()


if __name__ == '__main__':
    init_table()
    
    print('🚀 开始发布 25 条测试消息...')
    print('=' * 60)
    
    for i in range(25):
        user_dict = {
            'user_id': i + 1,
            'username': f'user_{i + 1}',
            'age': 20 + (i % 30),
            'email': f'user_{i + 1}@example.com'
        }
        batch_insert_to_sqlite.push(**user_dict)
        print(f'发布消息: user_id={i + 1}')
    
    print('\n' + '=' * 60)
    print('⏳ 启动消费...')
    
    batch_insert_to_sqlite.consume()
    
    print('⏳ 等待微批消费处理 (8秒)...')
    time.sleep(8)
    
    print('\n' + '=' * 60)
    print('📊 验证插入结果:')
    db = SessionLocal()
    try:
        result = db.execute(text('SELECT COUNT(*) as cnt FROM user_data')).fetchone()
        print(f'✅ 数据库中共有 {result[0]} 条记录')
        
        rows = db.execute(text('SELECT * FROM user_data ORDER BY user_id LIMIT 5')).fetchall()
        print('前 5 条记录:')
        for row in rows:
            print(dict(row._mapping))
    finally:
        db.close()
    
    print('\n✅ 测试完成！')
