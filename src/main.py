from pathlib import Path
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from src.config import settings
from src.auth.router import router as auth_router
from src.auth.dependencies import get_current_user
from src.users.router import router as users_router
from src.posts.router import router as posts_router
from src.categories.router import router as categories_router
from src.responses.router import router as responses_router
from src.categories.service import CategoryService
from src.posts.service import PostService

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    description="连接AI编程求助者与解决者的互助社区平台",
    version="0.1.0",
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# 配置模板引擎
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# 注册路由
app.include_router(auth_router, prefix="/auth", tags=["认证"])
app.include_router(users_router, prefix="/users", tags=["用户"])
app.include_router(posts_router, prefix="/posts", tags=["帖子"])
app.include_router(categories_router, prefix="/categories", tags=["分类"])
app.include_router(responses_router, prefix="/responses", tags=["回复"])


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user: dict = Depends(get_current_user)):
    """首页"""
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "title": "首页", "user": user},
    )


@app.get("/partials/categories", response_class=HTMLResponse)
async def partials_categories(request: Request):
    """分类网格片段"""
    categories = CategoryService.get_all_categories()

    html_parts = []
    icons = {
        'web': '🌐',
        'app': '📱',
        'wechat-mini': '💬',
        'desktop': '🖥️',
        'backend': '⚙️',
        'ai-ml': '🤖',
    }

    for cat in categories:
        icon = icons.get(cat['slug'], '📁')
        html_parts.append(f'''
        <a href="/categories/{cat['slug']}" class="category-card">
            <div class="category-icon">{icon}</div>
            <span class="category-name">{cat['name']}</span>
        </a>
        ''')

    return HTMLResponse("".join(html_parts))


@app.get("/partials/posts/recent", response_class=HTMLResponse)
async def partials_recent_posts(request: Request, user: dict = Depends(get_current_user)):
    """最新帖子片段"""
    posts, _ = PostService.get_posts(limit=6)

    if not posts:
        return HTMLResponse('''
        <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <p>暂无求助帖子</p>
            <a href="/posts/create" class="btn-primary">发布第一条求助</a>
        </div>
        ''')

    return templates.TemplateResponse(
        "posts/partials/post_list.html",
        {
            "request": request,
            "posts": posts,
            "page": 1,
            "total_pages": 1,
            "user": user,
        },
    )


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "app": settings.APP_NAME}
