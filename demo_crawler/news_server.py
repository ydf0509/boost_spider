"""
新闻服务端 - FastAPI实现
提供列表页、详情页和评论页API，用于爬虫测试
"""
import random
import string
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI(title="新闻服务API", description="模拟新闻网站，支持列表页、详情页和评论页")

# ================= 数据模型 =================
class NewsListItem(BaseModel):
    """列表页新闻项"""
    id: int
    title: str


class NewsDetail(BaseModel):
    """详情页新闻"""
    id: int
    title: str
    content: str
    author: str
    publish_time: str


# ================= 随机内容生成器 =================
def random_chinese_title() -> str:
    """生成随机新闻标题"""
    prefixes = ["突发", "重磅", "独家", "最新", "今日", "热点", "特别报道", "深度分析"]
    topics = ["科技发展", "经济形势", "社会新闻", "国际动态", "文化教育", "体育赛事", "娱乐八卦", "健康养生"]
    actions = ["引发关注", "成为焦点", "获得突破", "再创新高", "迎来变革", "取得进展", "备受瞩目", "值得期待"]
    return f"{random.choice(prefixes)}：{random.choice(topics)}{random.choice(actions)}"


def random_content(paragraphs: int = 5) -> str:
    """生成随机新闻正文"""
    sentences = [
        "这是一个令人振奋的消息。",
        "相关专家表示，这一发展具有重要意义。",
        "据了解，该事件引起了广泛关注。",
        "业内人士指出，未来发展前景十分乐观。",
        "根据最新数据显示，相关指标持续向好。",
        "有关部门正在积极推进相关工作。",
        "社会各界对此表示高度关注。",
        "这标志着我们在该领域取得了重要突破。",
        "预计未来还将有更多利好消息发布。",
        "相关政策的出台将进一步推动行业发展。",
    ]
    content_parts = []
    for _ in range(paragraphs):
        paragraph = "".join(random.sample(sentences, k=random.randint(2, 4)))
        content_parts.append(paragraph)
    return "\n\n".join(content_parts)


def random_author() -> str:
    """生成随机作者名"""
    surnames = ["张", "王", "李", "赵", "刘", "陈", "杨", "黄"]
    names = ["明", "华", "强", "伟", "芳", "敏", "静", "军"]
    return f"{random.choice(surnames)}{random.choice(names)}"


def random_time() -> str:
    """生成随机发布时间（最近7天内）"""
    delta = timedelta(days=random.randint(0, 7), hours=random.randint(0, 23), minutes=random.randint(0, 59))
    dt = datetime.now() - delta
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ================= API接口 =================
@app.get("/news/list", response_model=List[NewsListItem], summary="获取新闻列表")
def get_news_list(page: int = 1, size: int = 10):
    """
    获取新闻列表页
    - **page**: 页码，默认1
    - **size**: 每页数量，默认10
    """
    news_list = []
    start_id = (page - 1) * size + 1
    for i in range(size):
        news_list.append(NewsListItem(
            id=start_id + i,
            title=random_chinese_title()
        ))
    return news_list


@app.get("/news/{news_id}", response_model=NewsDetail, summary="获取新闻详情")
def get_news_detail(news_id: int):
    """
    获取新闻详情页
    - **news_id**: 新闻ID
    """
    return NewsDetail(
        id=news_id,
        title=random_chinese_title(),
        content=random_content(paragraphs=random.randint(3, 6)),
        author=random_author(),
        publish_time=random_time()
    )


# ================= 评论相关 =================
def random_comment_content() -> str:
    """生成随机评论内容"""
    comments = [
        "这篇文章写得真好，非常有深度！",
        "感谢分享，学到了很多新知识。",
        "作者的观点很有见地，支持！",
        "希望能看到更多这样的好文章。",
        "非常赞同作者的分析，逻辑清晰。",
        "这是我今天看到最好的一篇文章。",
        "太棒了！期待后续更新。",
        "收藏了，回头慢慢品读。",
        "虽然有些观点不太认同，但总体不错。",
        "专业的分析，受益匪浅。",
    ]
    return random.choice(comments)


@app.get("/news/{news_id}/comments", response_class=HTMLResponse, summary="获取新闻评论页(HTML)")
def get_news_comments_html(news_id: int, page: int = 1, size: int = 10):
    """
    获取新闻评论页 - 返回HTML格式，可使用xpath解析
    - **news_id**: 新闻ID
    - **page**: 页码，默认1
    - **size**: 每页数量，默认10
    """
    comments_html = ""
    start_id = (page - 1) * size + 1
    
    for i in range(size):
        comment_id = (news_id * 1000) + start_id + i
        author = random_author()
        content = random_comment_content()
        time_str = random_time()
        likes = random.randint(0, 100)
        
        comments_html += f"""
        <div class="comment-item" data-id="{comment_id}">
            <div class="comment-header">
                <span class="author">{author}</span>
                <span class="time">{time_str}</span>
            </div>
            <div class="comment-content">
                <p class="text">{content}</p>
            </div>
            <div class="comment-footer">
                <span class="likes">👍 {likes}</span>
                <a class="reply-link" href="/news/{news_id}/comments/{comment_id}/reply">回复</a>
            </div>
        </div>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>新闻{news_id}的评论 - 第{page}页</title>
        <style>
            body {{ font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            h1 {{ color: #333; }}
            .comment-list {{ background: white; padding: 20px; border-radius: 8px; }}
            .comment-item {{ border-bottom: 1px solid #eee; padding: 15px 0; }}
            .comment-header {{ margin-bottom: 8px; }}
            .author {{ font-weight: bold; color: #333; margin-right: 10px; }}
            .time {{ color: #999; font-size: 12px; }}
            .comment-content {{ color: #666; margin-bottom: 8px; }}
            .comment-footer {{ font-size: 12px; color: #999; }}
            .likes {{ margin-right: 15px; }}
            .reply-link {{ color: #1890ff; text-decoration: none; }}
            .pagination {{ margin-top: 20px; text-align: center; }}
            .pagination a {{ margin: 0 5px; padding: 5px 10px; background: #1890ff; color: white; 
                           text-decoration: none; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>新闻 #{news_id} 的评论</h1>
            <div class="comment-list" id="commentList">
                {comments_html}
            </div>
            <div class="pagination">
                <a href="/news/{news_id}/comments?page={max(1, page-1)}&size={size}">上一页</a>
                <span>第 {page} 页</span>
                <a href="/news/{news_id}/comments?page={page+1}&size={size}">下一页</a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/", summary="首页")
def root():
    """API根路径，返回欢迎信息"""
    return {
        "message": "欢迎访问新闻服务API",
        "endpoints": {
            "列表页": "/news/list?page=1&size=10",
            "详情页": "/news/{news_id}",
            "评论页(HTML)": "/news/{news_id}/comments?page=1&size=10",
            "API文档": "/docs"
        }
    }


if __name__ == "__main__":
    print("=" * 50)
    print("新闻服务端启动中...")
    print("API文档: http://127.0.0.1:7000/docs")
    print("=" * 50)
    uvicorn.run(app, host="127.0.0.1", port=7000)
