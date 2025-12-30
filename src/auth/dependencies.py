from typing import Optional
from fastapi import Depends, HTTPException, Request, status

from src.config import settings


async def get_current_user(request: Request) -> Optional[dict]:
    """
    从 Cookie 或 Authorization 头获取当前用户。
    返回 None 表示未登录（不抛异常）。
    """
    access_token = request.cookies.get("access_token")

    if not access_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ")[1]

    if not access_token:
        return None

    if settings.is_demo_mode:
        from src.core.mock_data import MOCK_SESSIONS, MOCK_USERS

        # 演示模式：从 session 获取用户
        if access_token.startswith("demo-token-"):
            user_id = MOCK_SESSIONS.get(access_token)
            if user_id and user_id in MOCK_USERS:
                user = MOCK_USERS[user_id].copy()
                return user
        return None

    # 真实模式：使用 Supabase 验证 token
    try:
        from supabase import create_client

        # 创建带有 access_token 的 Supabase 客户端
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )

        # 使用 access_token 获取用户
        user_response = supabase.auth.get_user(access_token)

        if not user_response or not user_response.user:
            print(f"[Auth] Invalid token - no user returned")
            return None

        user_id = user_response.user.id
        user_email = user_response.user.email

        # 获取用户资料
        result = supabase.table("profiles").select("*").eq("id", user_id).single().execute()

        if result.data:
            return {**result.data, "email": user_email}

        print(f"[Auth] User profile not found for id: {user_id}")
        return None

    except Exception as e:
        print(f"[Auth] Token verification error: {type(e).__name__}: {e}")
        return None


async def require_auth(user: Optional[dict] = Depends(get_current_user)) -> dict:
    """要求用户已登录"""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或登录已过期",
            headers={"HX-Redirect": "/auth/login"},
        )
    return user


async def require_solver(user: dict = Depends(require_auth)) -> dict:
    """要求用户是解决者"""
    if user.get("user_role") not in ["solver", "both"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要解决者权限",
        )
    return user


async def require_asker(user: dict = Depends(require_auth)) -> dict:
    """要求用户是求助者"""
    if user.get("user_role") not in ["asker", "both"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要求助者权限",
        )
    return user


async def require_verified(user: dict = Depends(require_auth)) -> dict:
    """要求用户已完成实名认证"""
    if not user.get("id_card_verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要完成实名认证才能执行此操作",
            headers={"HX-Redirect": "/auth/verify"},
        )
    return user


async def require_verified_solver(user: dict = Depends(require_verified)) -> dict:
    """要求用户是已实名认证的解决者"""
    if user.get("user_role") not in ["solver", "both"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要解决者权限",
        )

    # 检查是否填写了微信号
    if not user.get("wechat_id") or not user.get("wechat_id").strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="接单前需要先在个人资料中填写微信号，用于与求助者沟通",
            headers={"HX-Redirect": "/users/profile"},
        )

    return user
