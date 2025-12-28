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

    # 真实模式：JWT 验证
    try:
        from jose import jwt, JWTError
        from src.core.supabase import get_supabase_client

        payload = jwt.decode(
            access_token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        user_id = payload.get("sub")
        if user_id is None:
            return None

        supabase = get_supabase_client()
        result = supabase.table("profiles").select("*").eq("id", user_id).single().execute()

        if result.data:
            return {**result.data, "email": payload.get("email")}
        return None

    except Exception:
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
