from pathlib import Path
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.auth.dependencies import get_current_user
from src.categories.service import CategoryService
from src.posts.service import PostService

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent.parent / "templates")


@router.get("", response_class=HTMLResponse)
async def categories_list(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """分类列表页面"""
    categories = CategoryService.get_all_categories()

    # 获取每个分类的帖子数量（只计算未完成的）
    for category in categories:
        posts, total = PostService.get_posts(category_slug=category["slug"], exclude_resolved=True, limit=1)
        category["post_count"] = total

    return templates.TemplateResponse(
        "categories/list.html",
        {
            "request": request,
            "title": "项目分类",
            "user": user,
            "categories": categories,
        },
    )


@router.get("/{slug}", response_class=HTMLResponse)
async def category_posts(
    request: Request,
    slug: str,
    page: int = Query(1, ge=1),
    status: str = Query(None),
    urgency: str = Query(None),
    user: dict = Depends(get_current_user),
):
    """分类下的帖子列表"""
    category = CategoryService.get_category_by_slug(slug)

    if not category:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "title": "分类不存在", "user": user},
            status_code=404,
        )

    posts, total = PostService.get_posts(
        category_slug=slug,
        status=status,
        urgency=urgency,
        page=page,
    )

    total_pages = (total + 19) // 20

    return templates.TemplateResponse(
        "categories/posts.html",
        {
            "request": request,
            "title": f"{category['name']} - 求助列表",
            "user": user,
            "category": category,
            "posts": posts,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "current_status": status,
            "current_urgency": urgency,
        },
    )
