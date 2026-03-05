from sqlmodel import SQLModel, Field
from typing import Optional
from sqlalchemy import Text
from boost_scrapy import Item

# ================= 定义 Item (继承 SQLModel) =================

class NewsItem(Item, table=True):
    """新闻详情数据项 (映射数据库表 news_detail)"""
    __tablename__ = "news_detail"

    id: Optional[int] = Field(default=None, primary_key=True)
    news_id: int
    title: str = Field(max_length=200) # 指定 VARCHAR(200)
    author: Optional[str] = Field(default=None, max_length=50)
    publish_time: Optional[str] = Field(default=None, max_length=50)
    content: Optional[str] = Field(default=None, sa_type=Text) # 指定使用 TEXT 类型（不限长度）


class CommentItem(Item, table=True):
    """评论数据项 (映射数据库表 comments)"""
    __tablename__ = "comments"

    id: Optional[int] = Field(default=None, primary_key=True)
    news_id: int
    comment_id: str = Field(max_length=50)
    author: Optional[str] = Field(default=None, max_length=50)
    content: Optional[str] = Field(default=None, sa_type=Text)
    likes: Optional[str] = Field(default=None, max_length=20)