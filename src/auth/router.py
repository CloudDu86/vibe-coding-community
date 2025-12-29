from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.auth.service import AuthService
from src.auth.dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent.parent / "templates")


def get_agreement_date() -> str:
    """获取协议生效日期（当前日期）"""
    return datetime.now().strftime("%Y年%m月%d日")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: dict = Depends(get_current_user)):
    """登录页面"""
    # 已登录用户重定向到首页
    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "title": "登录"},
    )


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    """处理登录"""
    success, error, session_data = AuthService.sign_in(email, password)

    if not success:
        # HTMX 请求返回部分 HTML
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "auth/partials/login_form.html",
                {"request": request, "error": error, "email": email},
                status_code=400,
            )
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "title": "登录", "error": error, "email": email},
            status_code=400,
        )

    # 设置 Cookie 并重定向
    # HTMX 请求使用 HX-Redirect 头
    if request.headers.get("HX-Request"):
        response = HTMLResponse(content="", status_code=200)
        response.headers["HX-Redirect"] = "/"
    else:
        response = RedirectResponse(url="/", status_code=303)

    response.set_cookie(
        key="access_token",
        value=session_data["access_token"],
        httponly=True,
        secure=False,  # 开发环境设为 False，生产环境设为 True
        samesite="lax",
        max_age=3600,  # 1 小时
    )
    response.set_cookie(
        key="refresh_token",
        value=session_data["refresh_token"],
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=604800,  # 7 天
    )
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user: dict = Depends(get_current_user)):
    """注册页面"""
    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        "auth/register.html",
        {"request": request, "title": "注册", "agreement_date": get_agreement_date()},
    )


@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    nickname: str = Form(...),
    user_role: str = Form(...),
    agree_terms: str = Form(None),
):
    """处理注册"""
    agreement_date = get_agreement_date()

    # 验证是否同意协议
    if not agree_terms:
        error = "请阅读并同意用户协议"
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "auth/partials/register_form.html",
                {"request": request, "error": error, "email": email, "nickname": nickname, "agreement_date": agreement_date},
            )
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "title": "注册", "error": error, "agreement_date": agreement_date},
        )

    # 验证角色（不允许双重身份）
    if user_role not in ["asker", "solver"]:
        error = "请选择有效的用户身份"
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "auth/partials/register_form.html",
                {"request": request, "error": error, "email": email, "nickname": nickname, "agreement_date": agreement_date},
            )
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "title": "注册", "error": error, "agreement_date": agreement_date},
        )

    # 记录同意协议的时间
    agreed_at = datetime.now().isoformat()
    success, error, user_data = AuthService.sign_up(email, password, nickname, user_role, agreed_at)

    if not success:
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "auth/partials/register_form.html",
                {"request": request, "error": error, "email": email, "nickname": nickname, "agreement_date": agreement_date},
            )
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "title": "注册", "error": error, "email": email, "nickname": nickname, "agreement_date": agreement_date},
        )

    # 注册成功，重定向到登录页
    # HTMX 请求使用 HX-Redirect 头
    if request.headers.get("HX-Request"):
        response = HTMLResponse(content="", status_code=200)
        response.headers["HX-Redirect"] = "/auth/login?registered=true"
        return response
    return RedirectResponse(url="/auth/login?registered=true", status_code=303)


@router.post("/logout")
async def logout(request: Request):
    """处理登出"""
    access_token = request.cookies.get("access_token")
    if access_token:
        AuthService.sign_out(access_token)

    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response
