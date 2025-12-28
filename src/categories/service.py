from typing import List, Optional
from src.config import settings


class CategoryService:
    """分类服务"""

    @staticmethod
    def get_all_categories() -> List[dict]:
        """获取所有分类"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_CATEGORIES
            return [c for c in MOCK_CATEGORIES if c.get("is_active", True)]

        from src.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        try:
            result = supabase.table("categories").select("*").eq("is_active", True).order("display_order").execute()
            return result.data or []
        except Exception:
            return []

    @staticmethod
    def get_category_by_slug(slug: str) -> Optional[dict]:
        """根据 slug 获取分类"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_CATEGORIES
            for cat in MOCK_CATEGORIES:
                if cat["slug"] == slug:
                    return cat
            return None

        from src.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        try:
            result = supabase.table("categories").select("*").eq("slug", slug).single().execute()
            return result.data
        except Exception:
            return None

    @staticmethod
    def get_category_by_id(category_id: str) -> Optional[dict]:
        """根据 ID 获取分类"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_CATEGORIES
            for cat in MOCK_CATEGORIES:
                if cat["id"] == category_id:
                    return cat
            return None

        from src.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        try:
            result = supabase.table("categories").select("*").eq("id", category_id).single().execute()
            return result.data
        except Exception:
            return None
