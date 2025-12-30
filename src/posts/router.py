from pathlib import Path
from fastapi import APIRouter, Request, Form, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.auth.dependencies import get_current_user, require_auth, require_verified
from src.posts.service import PostService
from src.categories.service import CategoryService

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent.parent / "templates")


@router.get("", response_class=HTMLResponse)
async def posts_list(
    request: Request,
    category: str = Query(None),
    status: str = Query(None),
    urgency: str = Query(None),
    q: str = Query(None),
    page: int = Query(1, ge=1),
    user: dict = Depends(get_current_user),
):
    """帖子列表页面"""
    posts, total = PostService.get_posts(
        category_slug=category,
        status=status,
        urgency=urgency,
        search_query=q,
        page=page,
    )

    categories = CategoryService.get_all_categories()
    total_pages = (total + 19) // 20

    # HTMX 请求只返回帖子列表部分
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "posts/partials/post_list.html",
            {
                "request": request,
                "posts": posts,
                "page": page,
                "total_pages": total_pages,
                "category": category,
                "status": status,
                "urgency": urgency,
                "search_query": q,
            },
        )

    return templates.TemplateResponse(
        "posts/list.html",
        {
            "request": request,
            "title": "浏览求助" if not q else f"搜索: {q}",
            "user": user,
            "posts": posts,
            "categories": categories,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "current_category": category,
            "current_status": status,
            "current_urgency": urgency,
            "search_query": q,
        },
    )


@router.get("/create", response_class=HTMLResponse)
async def create_post_page(
    request: Request,
    user: dict = Depends(require_verified),
):
    """创建帖子页面"""
    categories = CategoryService.get_all_categories()

    return templates.TemplateResponse(
        "posts/create.html",
        {
            "request": request,
            "title": "发布求助",
            "user": user,
            "categories": categories,
        },
    )


@router.post("/create")
async def create_post(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    category_id: str = Form(...),
    ai_tool_used: str = Form(None),
    error_message: str = Form(None),
    code_snippet: str = Form(None),
    budget_amount: float = Form(...),
    urgency: str = Form("medium"),
    user: dict = Depends(require_verified),
):
    """处理创建帖子"""
    # 验证预算金额必须大于0
    if not budget_amount or budget_amount <= 0:
        categories = CategoryService.get_all_categories()
        return templates.TemplateResponse(
            "posts/create.html",
            {
                "request": request,
                "title": "发布求助",
                "user": user,
                "categories": categories,
                "error": "预算金额必须大于0",
            },
            status_code=400,
        )

    success, error, post = PostService.create_post(
        author_id=user["id"],
        title=title,
        description=description,
        category_id=category_id,
        ai_tool_used=ai_tool_used,
        error_message=error_message,
        code_snippet=code_snippet,
        budget_type=None,
        budget_amount=budget_amount,
        urgency=urgency,
    )

    if not success:
        categories = CategoryService.get_all_categories()
        return templates.TemplateResponse(
            "posts/create.html",
            {
                "request": request,
                "title": "发布求助",
                "user": user,
                "categories": categories,
                "error": error,
            },
            status_code=400,
        )

    return RedirectResponse(url=f"/posts/{post['id']}", status_code=303)


@router.get("/my", response_class=HTMLResponse)
async def my_posts(
    request: Request,
    page: int = Query(1, ge=1),
    user: dict = Depends(require_auth),
):
    """我的帖子"""
    posts, total = PostService.get_posts(author_id=user["id"], page=page)
    total_pages = (total + 19) // 20

    return templates.TemplateResponse(
        "posts/my_posts.html",
        {
            "request": request,
            "title": "我的求助",
            "user": user,
            "posts": posts,
            "page": page,
            "total_pages": total_pages,
            "total": total,
        },
    )


@router.get("/{post_id}", response_class=HTMLResponse)
async def post_detail(
    request: Request,
    post_id: str,
    user: dict = Depends(get_current_user),
):
    """帖子详情页面"""
    post = PostService.get_post(post_id)

    if not post:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "title": "帖子不存在", "user": user},
            status_code=404,
        )

    # 增加浏览次数
    PostService.increment_view_count(post_id)

    # 获取回复列表
    from src.responses.service import ResponseService
    responses = ResponseService.get_responses(post_id)

    # 检查是否是作者
    is_author = user and user["id"] == post["author_id"]

    # 检查当前用户是否已回复，并获取用户的回复
    has_responded = False
    user_response = None
    has_pending_review = False
    if user:
        for r in responses:
            if r["solver_id"] == user["id"]:
                has_responded = True
                user_response = r
                break

    # 检查是否有待审核的解决方案
    for r in responses:
        if r.get("status") == "pending_review":
            has_pending_review = True
            break

    return templates.TemplateResponse(
        "posts/detail.html",
        {
            "request": request,
            "title": post["title"],
            "user": user,
            "post": post,
            "responses": responses,
            "is_author": is_author,
            "has_responded": has_responded,
            "user_response": user_response,
            "has_pending_review": has_pending_review,
        },
    )


@router.get("/{post_id}/edit", response_class=HTMLResponse)
async def edit_post_page(
    request: Request,
    post_id: str,
    user: dict = Depends(require_auth),
):
    """编辑帖子页面"""
    post = PostService.get_post(post_id)

    if not post:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "title": "帖子不存在", "user": user},
            status_code=404,
        )

    if post["author_id"] != user["id"]:
        return RedirectResponse(url=f"/posts/{post_id}", status_code=303)

    categories = CategoryService.get_all_categories()

    return templates.TemplateResponse(
        "posts/edit.html",
        {
            "request": request,
            "title": "编辑求助",
            "user": user,
            "post": post,
            "categories": categories,
        },
    )


@router.post("/{post_id}/edit")
async def edit_post(
    request: Request,
    post_id: str,
    title: str = Form(...),
    description: str = Form(...),
    category_id: str = Form(...),
    ai_tool_used: str = Form(None),
    error_message: str = Form(None),
    code_snippet: str = Form(None),
    budget_type: str = Form(None),
    budget_amount: float = Form(None),
    urgency: str = Form("medium"),
    user: dict = Depends(require_auth),
):
    """处理编辑帖子"""
    success, error = PostService.update_post(
        post_id=post_id,
        author_id=user["id"],
        title=title,
        description=description,
        category_id=category_id,
        ai_tool_used=ai_tool_used,
        error_message=error_message,
        code_snippet=code_snippet,
        budget_type=budget_type,
        budget_amount=budget_amount,
        urgency=urgency,
    )

    if not success:
        post = PostService.get_post(post_id)
        categories = CategoryService.get_all_categories()
        return templates.TemplateResponse(
            "posts/edit.html",
            {
                "request": request,
                "title": "编辑求助",
                "user": user,
                "post": post,
                "categories": categories,
                "error": error,
            },
            status_code=400,
        )

    return RedirectResponse(url=f"/posts/{post_id}", status_code=303)


@router.post("/{post_id}/delete")
async def delete_post(
    request: Request,
    post_id: str,
    user: dict = Depends(require_auth),
):
    """删除帖子"""
    success, error = PostService.delete_post(post_id, user["id"])

    if not success:
        # HTMX 请求返回错误
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "components/alert.html",
                {"request": request, "type": "error", "message": error},
                status_code=400,
            )
        return RedirectResponse(url=f"/posts/{post_id}?error={error}", status_code=303)

    return RedirectResponse(url="/posts/my", status_code=303)


@router.post("/{post_id}/status")
async def update_post_status(
    request: Request,
    post_id: str,
    status: str = Form(...),
    user: dict = Depends(require_auth),
):
    """更新帖子状态"""
    if status not in ["open", "in_progress", "resolved", "closed"]:
        return RedirectResponse(url=f"/posts/{post_id}", status_code=303)

    success, error = PostService.update_post(
        post_id=post_id,
        author_id=user["id"],
        status=status,
    )

    return RedirectResponse(url=f"/posts/{post_id}", status_code=303)
