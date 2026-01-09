# -*- coding: utf-8 -*-
"""
SQLite Pipeline - Feapder自定义数据管道

将Item自动批量入库到SQLite数据库
"""

import os
import sqlite3
from typing import Dict, List, Tuple
from feapder.pipelines import BasePipeline


class SQLitePipeline(BasePipeline):
    """
    SQLite Pipeline - 自动创建表并批量入库
    
    feapder的Item会自动流经此Pipeline:
    - Item类名去掉Item后缀作为表名（如NewsDetailItem -> news_detail）
    - 自动根据Item字段创建表
    - 批量插入数据
    """
    
    def __init__(self):
        db_path = os.path.join(os.path.dirname(__file__), 'feapder_crawled_data.db')
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._created_tables = set()
        print(f"[SQLitePipeline] 数据库已连接: {db_path}")
    
    def _ensure_table(self, table: str, item: Dict):
        """确保表存在，不存在则创建"""
        if table in self._created_tables:
            return
        
        # 根据item的字段动态创建表
        columns = ', '.join([f"{k} TEXT" for k in item.keys()])
        sql = f"CREATE TABLE IF NOT EXISTS {table} (id INTEGER PRIMARY KEY AUTOINCREMENT, {columns})"
        
        cursor = self.conn.cursor()
        cursor.execute(sql)
        self.conn.commit()
        self._created_tables.add(table)
        print(f"[SQLitePipeline] 表 {table} 已就绪")
    
    def save_items(self, table: str, items: List[Dict]) -> bool:
        """
        批量保存数据
        
        Args:
            table: 表名（由Item类名自动生成）
            items: 数据列表，[{字段:值}, ...]
        
        Returns:
            bool: 是否保存成功
        """
        if not items:
            return True
        
        # 确保表存在
        self._ensure_table(table, items[0])
        
        cursor = self.conn.cursor()
        for item in items:
            columns = ', '.join(item.keys())
            placeholders = ', '.join(['?' for _ in item])
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            try:
                cursor.execute(sql, list(item.values()))
            except Exception as e:
                print(f"[SQLitePipeline] 插入失败: {e}")
        
        self.conn.commit()
        print(f"[SQLitePipeline] ✓ 保存 {len(items)} 条到 {table} 表")
        return True
    
    def update_items(self, table: str, items: List[Dict], update_keys: Tuple = ()) -> bool:
        """更新数据（暂不实现）"""
        return True
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            print("[SQLitePipeline] 数据库连接已关闭")
