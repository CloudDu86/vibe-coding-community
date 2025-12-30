from pathlib import Path
import os
import uuid
from fastapi import APIRouter, Request, Form, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.auth.dependencies import get_current_user, require_auth, require_solver, require_verified_solver
from src.responses.service import ResponseService
from src.posts.service import PostService

# 上传目录
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent.parent / "templates")


@router.post("/posts/{post_id}/respond")
async def create_response(
    request: Request,
    post_id: str,
    content: str = Form(...),
    proposed_solution: str = Form(None),
    estimated_time: str = Form(None),
    proposed_price: float = Form(None),
    user: dict = Depends(require_verified_solver),
):
    """创建回复"""
    # 检查帖子是否存在
    post = PostService.get_post(post_id)
    if not post:
        return RedirectResponse(url="/posts", status_code=303)

    # 不能回复自己的帖子
    if post["author_id"] == user["id"]:
        return RedirectResponse(url=f"/posts/{post_id}?error=不能回复自己的帖子", status_code=303)

    success, error, response = ResponseService.create_response(
        post_id=post_id,
        solver_id=user["id"],
        content=content,
        proposed_solution=proposed_solution,
        estimated_time=estimated_time,
        proposed_price=proposed_price,
    )

    if not success:
        # HTMX 请求返回错误提示
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "components/alert.html",
                {"request": request, "type": "error", "message": error},
                status_code=400,
            )
        return RedirectResponse(url=f"/posts/{post_id}?error={error}", status_code=303)

    # 接单成功后刷新整个页面（因为帖子状态改变了）
    if request.headers.get("HX-Request"):
        from fastapi.responses import HTMLResponse
        response = HTMLResponse(content="", status_code=200)
        response.headers["HX-Redirect"] = f"/posts/{post_id}"
        return response

    return RedirectResponse(url=f"/posts/{post_id}", status_code=303)


@router.post("/{response_id}/accept")
async def accept_response(
    request: Request,
    response_id: str,
    user: dict = Depends(require_auth),
):
    """接受回复"""
    success, error = ResponseService.update_response_status(
        response_id=response_id,
        post_author_id=user["id"],
        new_status="accepted",
    )

    if not success:
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "components/alert.html",
                {"request": request, "type": "error", "message": error},
                status_code=400,
            )

    # 获取回复信息以重定向
    response = ResponseService.get_response(response_id)
    post_id = response["post_id"] if response else ""

    if request.headers.get("HX-Request"):
        # 返回更新后的回复卡片
        post = PostService.get_post(post_id)
        responses = ResponseService.get_responses(post_id)
        return templates.TemplateResponse(
            "posts/partials/response_list.html",
            {
                "request": request,
                "responses": responses,
                "post": post,
                "user": user,
                "is_author": True,
            },
        )

    return RedirectResponse(url=f"/posts/{post_id}", status_code=303)


@router.post("/{response_id}/reject")
async def reject_response(
    request: Request,
    response_id: str,
    user: dict = Depends(require_auth),
):
    """拒绝回复"""
    success, error = ResponseService.update_response_status(
        response_id=response_id,
        post_author_id=user["id"],
        new_status="rejected",
    )

    response = ResponseService.get_response(response_id)
    post_id = response["post_id"] if response else ""

    if request.headers.get("HX-Request"):
        post = PostService.get_post(post_id)
        responses = ResponseService.get_responses(post_id)
        return templates.TemplateResponse(
            "posts/partials/response_list.html",
            {
                "request": request,
                "responses": responses,
                "post": post,
                "user": user,
                "is_author": True,
            },
        )

    return RedirectResponse(url=f"/posts/{post_id}", status_code=303)


@router.post("/{response_id}/complete")
async def complete_response(
    request: Request,
    response_id: str,
    user: dict = Depends(require_auth),
):
    """标记为已完成"""
    success, error = ResponseService.mark_as_completed(
        response_id=response_id,
        post_author_id=user["id"],
    )

    response = ResponseService.get_response(response_id)
    post_id = response["post_id"] if response else ""

    if not success:
        return RedirectResponse(url=f"/posts/{post_id}?error={error}", status_code=303)

    return RedirectResponse(url=f"/posts/{post_id}?success=问题已标记为解决", status_code=303)


@router.post("/{response_id}/solution")
async def upload_solution(
    request: Request,
    response_id: str,
    solution: str = Form(...),
    attachment: UploadFile = File(None),
    user: dict = Depends(require_auth),
):
    """上传解决方案"""
    # 处理附件上传
    attachment_url = None
    if attachment and attachment.filename:
        # 生成唯一文件名
        file_ext = os.path.splitext(attachment.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename

        # 保存文件
        content = await attachment.read()
        with open(file_path, "wb") as f:
            f.write(content)

        attachment_url = f"/static/uploads/{unique_filename}"

    success, error = ResponseService.update_solution(
        response_id=response_id,
        solver_id=user["id"],
        solution=solution,
        attachment_url=attachment_url,
    )

    if not success:
        return RedirectResponse(url=f"/users/my-orders?error={error}", status_code=303)

    # 获取帖子ID以便跳转到帖子详情
    response = ResponseService.get_response(response_id)
    post_id = response["post_id"] if response else ""

    return RedirectResponse(url=f"/posts/{post_id}?success=解决方案已上传，等待求助者确认", status_code=303)
