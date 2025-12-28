from functools import lru_cache
from supabase import create_client, Client

from src.config import settings


@lru_cache()
def get_supabase_client() -> Client:
    """获取 Supabase 客户端（使用 anon key，受 RLS 限制）"""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


def get_supabase_admin_client() -> Client:
    """获取 Supabase 管理员客户端（使用 service role key，绕过 RLS）"""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
