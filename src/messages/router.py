from pathlib import Path
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.auth.dependencies import get_current_user, require_auth
from src.messages.service import MessageService

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent.parent / "templates")


@router.get("/unread-count")
async def get_unread_count(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """获取未读消息数量（HTMX片段）"""
    if not user:
        return HTMLResponse(content="<span class=\"icon\">🔔</span>")

    count = MessageService.get_unread_count(user["id"])

    if count > 0:
        badge_html = f'<span class="badge" id="unread-badge">{count}</span>'
    else:
        badge_html = '<span class="badge" id="unread-badge" style="display: none;">0</span>'

    return HTMLResponse(content=f'<span class="icon">🔔</span>{badge_html}')


@router.get("/recent")
async def get_recent_messages(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """获取最近消息（HTMX片段，用于下拉菜单）"""
    if not user:
        return HTMLResponse(content='<div class="message-empty">请先登录</div>')

    messages = MessageService.get_recent_messages(user["id"], limit=5)

    return templates.TemplateResponse(
        "messages/partials/message_dropdown.html",
        {"request": request, "messages": messages},
    )


@router.get("")
async def messages_list(
    request: Request,
    page: int = 1,
    user: dict = Depends(require_auth),
):
    """消息列表页面"""
    messages, total = MessageService.get_user_messages(user["id"], page=page, limit=20)
    total_pages = (total + 19) // 20

    return templates.TemplateResponse(
        "messages/list.html",
        {
            "request": request,
            "user": user,
            "messages": messages,
            "page": page,
            "total_pages": total_pages,
            "total": total,
        },
    )


@router.post("/{message_id}/read")
async def mark_message_read(
    request: Request,
    message_id: str,
    user: dict = Depends(require_auth),
):
    """标记消息为已读"""
    MessageService.mark_as_read(message_id, user["id"])

    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", status_code=200)

    return RedirectResponse(url="/messages", status_code=303)


@router.post("/read-all")
async def mark_all_read(
    request: Request,
    user: dict = Depends(require_auth),
):
    """标记所有消息为已读"""
    MessageService.mark_all_as_read(user["id"])

    if request.headers.get("HX-Request"):
        return HTMLResponse(content="", status_code=200)

    return RedirectResponse(url="/messages", status_code=303)
