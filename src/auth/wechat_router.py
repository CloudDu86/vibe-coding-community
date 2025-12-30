"""
微信OAuth路由 - 处理微信登录/注册回调
"""
import secrets
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Request, Form, Query, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.config import settings
from src.auth.wechat_oauth import WeChatOAuthService, WeChatAuthService, UserIdentityService
from src.auth.dependencies import get_current_user, require_auth

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent.parent / "templates")

# 存储OAuth state（生产环境应使用Redis等）
OAUTH_STATES: dict = {}


@router.get("/wechat/authorize")
async def wechat_authorize(
    request: Request,
    action: str = Query("login", description="login、register或bind"),
    user_role: str = Query(None, description="注册时的用户角色"),
    user: dict = Depends(get_current_user),
):
    """
    发起微信授权 - 重定向到微信授权页面

    Args:
        action: login(登录)、register(注册) 或 bind(绑定)
        user_role: 注册时的用户角色 (asker/solver)
    """
    # 绑定操作需要已登录
    if action == "bind" and not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    if not settings.WECHAT_APP_ID:
        # 未配置微信，返回错误页面
        return templates.TemplateResponse(
            "auth/wechat_error.html",
            {
                "request": request,
                "title": "微信登录",
                "error": "微信登录功能尚未配置，请联系管理员",
            }
        )

    # 生成随机state防止CSRF
    state = secrets.token_urlsafe(32)
    OAUTH_STATES[state] = {
        "action": action,
        "user_role": user_role,
        "user_id": user["id"] if user else None,  # 绑定时保存用户ID
        "created_at": datetime.now().isoformat(),
    }

    # 获取微信授权URL
    authorize_url = WeChatOAuthService.get_authorize_url(state=state)

    return RedirectResponse(url=authorize_url, status_code=302)


@router.get("/wechat/callback")
async def wechat_callback(
    request: Request,
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
):
    """
    微信授权回调

    微信会重定向到这里，携带code和state参数
    """
    # 检查错误
    if error:
        return templates.TemplateResponse(
            "auth/wechat_error.html",
            {"request": request, "title": "微信登录", "error": f"授权失败: {error}"}
        )

    if not code or not state:
        return templates.TemplateResponse(
            "auth/wechat_error.html",
            {"request": request, "title": "微信登录", "error": "授权参数无效"}
        )

    # 验证state
    state_data = OAUTH_STATES.pop(state, None)
    if not state_data:
        return templates.TemplateResponse(
            "auth/wechat_error.html",
            {"request": request, "title": "微信登录", "error": "授权已过期，请重试"}
        )

    action = state_data.get("action", "login")
    user_role = state_data.get("user_role", "asker")
    bind_user_id = state_data.get("user_id")  # 绑定时的用户ID

    # 用code换取access_token
    success, error_msg, token_data = await WeChatOAuthService.get_access_token(code)
    if not success:
        return templates.TemplateResponse(
            "auth/wechat_error.html",
            {"request": request, "title": "微信登录", "error": error_msg}
        )

    openid = token_data["openid"]
    unionid = token_data.get("unionid")

    # 获取用户信息
    success, error_msg, wechat_user_info = await WeChatOAuthService.get_user_info(
        token_data["access_token"], openid
    )
    if not success:
        wechat_user_info = {"nickname": "微信用户", "openid": openid}

    if action == "bind":
        # 绑定流程 - 将微信绑定到现有用户
        if not bind_user_id:
            return templates.TemplateResponse(
                "auth/wechat_error.html",
                {"request": request, "title": "绑定失败", "error": "绑定操作无效，请重新登录后再试"}
            )

        success, error_msg = WeChatAuthService.bind_wechat_to_user(
            user_id=bind_user_id,
            openid=openid,
            unionid=unionid,
            wechat_user_info=wechat_user_info,
        )

        if not success:
            return templates.TemplateResponse(
                "auth/wechat_error.html",
                {"request": request, "title": "绑定失败", "error": error_msg}
            )

        # 绑定成功，跳转回个人资料页
        return RedirectResponse(url="/users/profile?bind_success=true", status_code=302)

    elif action == "register":
        # 注册流程 - 跳转到角色选择页面（如果未选择角色）
        if not user_role:
            return templates.TemplateResponse(
                "auth/wechat_role_select.html",
                {
                    "request": request,
                    "title": "选择身份",
                    "openid": openid,
                    "unionid": unionid or "",
                    "nickname": wechat_user_info.get("nickname", "微信用户"),
                    "avatar_url": wechat_user_info.get("headimgurl", ""),
                }
            )

        # 执行注册
        terms_agreed_at = datetime.now().isoformat()
        success, error_msg, session_data = WeChatAuthService.sign_up_with_wechat(
            openid=openid,
            unionid=unionid,
            wechat_user_info=wechat_user_info,
            user_role=user_role,
            terms_agreed_at=terms_agreed_at,
        )

        if not success:
            # 如果是"已注册"错误，尝试登录
            if "已注册" in (error_msg or ""):
                success, error_msg, session_data = WeChatAuthService.sign_in_with_wechat(openid)

        if not success:
            return templates.TemplateResponse(
                "auth/wechat_error.html",
                {"request": request, "title": "微信注册", "error": error_msg}
            )

    else:
        # 登录流程
        success, error_msg, session_data = WeChatAuthService.sign_in_with_wechat(openid)

        if not success:
            # 如果用户不存在，引导去注册
            if "尚未注册" in (error_msg or ""):
                return templates.TemplateResponse(
                    "auth/wechat_role_select.html",
                    {
                        "request": request,
                        "title": "选择身份完成注册",
                        "openid": openid,
                        "unionid": unionid or "",
                        "nickname": wechat_user_info.get("nickname", "微信用户"),
                        "avatar_url": wechat_user_info.get("headimgurl", ""),
                        "message": "该微信账号尚未注册，请选择身份完成注册",
                    }
                )
            return templates.TemplateResponse(
                "auth/wechat_error.html",
                {"request": request, "title": "微信登录", "error": error_msg}
            )

    # 登录/注册成功，设置Cookie并跳转首页
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=session_data["access_token"],
        httponly=True,
        secure=False,  # 生产环境设为True
        samesite="lax",
        max_age=3600,
    )
    response.set_cookie(
        key="refresh_token",
        value=session_data["refresh_token"],
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=604800,
    )
    return response


@router.post("/wechat/complete-register")
async def complete_wechat_register(
    request: Request,
    openid: str = Form(...),
    unionid: str = Form(""),
    nickname: str = Form(...),
    avatar_url: str = Form(""),
    user_role: str = Form(...),
    agree_terms: str = Form(None),
):
    """
    完成微信注册 - 用户选择角色后提交
    """
    if not agree_terms:
        return templates.TemplateResponse(
            "auth/wechat_role_select.html",
            {
                "request": request,
                "title": "选择身份",
                "openid": openid,
                "unionid": unionid,
                "nickname": nickname,
                "avatar_url": avatar_url,
                "error": "请阅读并同意用户协议",
            }
        )

    if user_role not in ["asker", "solver"]:
        return templates.TemplateResponse(
            "auth/wechat_role_select.html",
            {
                "request": request,
                "title": "选择身份",
                "openid": openid,
                "unionid": unionid,
                "nickname": nickname,
                "avatar_url": avatar_url,
                "error": "请选择有效的用户身份",
            }
        )

    wechat_user_info = {
        "nickname": nickname,
        "headimgurl": avatar_url,
    }

    terms_agreed_at = datetime.now().isoformat()
    success, error_msg, session_data = WeChatAuthService.sign_up_with_wechat(
        openid=openid,
        unionid=unionid if unionid else None,
        wechat_user_info=wechat_user_info,
        user_role=user_role,
        terms_agreed_at=terms_agreed_at,
    )

    if not success:
        # 如果已注册，尝试直接登录
        if "已注册" in (error_msg or ""):
            success, error_msg, session_data = WeChatAuthService.sign_in_with_wechat(openid)

    if not success:
        return templates.TemplateResponse(
            "auth/wechat_role_select.html",
            {
                "request": request,
                "title": "选择身份",
                "openid": openid,
                "unionid": unionid,
                "nickname": nickname,
                "avatar_url": avatar_url,
                "error": error_msg,
            }
        )

    # 成功，设置Cookie
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=session_data["access_token"],
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=3600,
    )
    response.set_cookie(
        key="refresh_token",
        value=session_data["refresh_token"],
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=604800,
    )
    return response
