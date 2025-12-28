from typing import Optional, List, Tuple
import uuid
from datetime import datetime

from src.config import settings


class PostService:
    """帖子服务"""

    @staticmethod
    def create_post(
        author_id: str,
        title: str,
        description: str,
        category_id: str,
        ai_tool_used: Optional[str] = None,
        error_message: Optional[str] = None,
        code_snippet: Optional[str] = None,
        budget_type: Optional[str] = None,
        budget_amount: Optional[float] = None,
        urgency: str = "medium",
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """创建帖子"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_POSTS, MOCK_USERS, MOCK_CATEGORIES

            post_id = str(uuid.uuid4())
            author = MOCK_USERS.get(author_id, {})
            category = None
            for cat in MOCK_CATEGORIES:
                if cat["id"] == category_id:
                    category = cat
                    break

            new_post = {
                "id": post_id,
                "author_id": author_id,
                "category_id": category_id,
                "title": title,
                "description": description,
                "ai_tool_used": ai_tool_used,
                "error_message": error_message,
                "code_snippet": code_snippet,
                "budget_type": budget_type,
                "budget_amount": budget_amount,
                "urgency": urgency,
                "status": "open",
                "view_count": 0,
                "response_count": 0,
                "created_at": datetime.now().isoformat(),
                "profiles": author,
                "categories": category,
            }
            MOCK_POSTS[post_id] = new_post
            return True, None, new_post

        from src.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        try:
            result = supabase.table("posts").insert({
                "author_id": author_id,
                "title": title,
                "description": description,
                "category_id": category_id,
                "ai_tool_used": ai_tool_used,
                "error_message": error_message,
                "code_snippet": code_snippet,
                "budget_type": budget_type,
                "budget_amount": budget_amount,
                "urgency": urgency,
            }).execute()

            return True, None, result.data[0] if result.data else None

        except Exception as e:
            return False, str(e), None

    @staticmethod
    def get_post(post_id: str) -> Optional[dict]:
        """获取单个帖子"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_POSTS
            return MOCK_POSTS.get(post_id)

        from src.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        try:
            result = supabase.table("posts").select(
                "*, profiles(id, nickname, avatar_url), categories(id, name, slug)"
            ).eq("id", post_id).single().execute()

            return result.data

        except Exception:
            return None

    @staticmethod
    def get_posts(
        category_slug: Optional[str] = None,
        status: Optional[str] = None,
        urgency: Optional[str] = None,
        author_id: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[dict], int]:
        """获取帖子列表"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_POSTS, MOCK_CATEGORIES

            posts = list(MOCK_POSTS.values())

            # 筛选
            if category_slug:
                cat_id = None
                for cat in MOCK_CATEGORIES:
                    if cat["slug"] == category_slug:
                        cat_id = cat["id"]
                        break
                if cat_id:
                    posts = [p for p in posts if p.get("category_id") == cat_id]

            if status:
                posts = [p for p in posts if p.get("status") == status]

            if urgency:
                posts = [p for p in posts if p.get("urgency") == urgency]

            if author_id:
                posts = [p for p in posts if p.get("author_id") == author_id]

            # 排序（按创建时间倒序）
            posts.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            total = len(posts)
            offset = (page - 1) * limit
            posts = posts[offset:offset + limit]

            return posts, total

        from src.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        try:
            query = supabase.table("posts").select(
                "*, profiles(id, nickname, avatar_url), categories(id, name, slug)",
                count="exact",
            )

            if category_slug:
                cat_result = supabase.table("categories").select("id").eq("slug", category_slug).single().execute()
                if cat_result.data:
                    query = query.eq("category_id", cat_result.data["id"])

            if status:
                query = query.eq("status", status)

            if urgency:
                query = query.eq("urgency", urgency)

            if author_id:
                query = query.eq("author_id", author_id)

            offset = (page - 1) * limit
            result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

            total = result.count if result.count else 0
            return result.data or [], total

        except Exception:
            return [], 0

    @staticmethod
    def update_post(post_id: str, author_id: str, **kwargs) -> Tuple[bool, Optional[str]]:
        """更新帖子"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_POSTS

            post = MOCK_POSTS.get(post_id)
            if not post:
                return False, "帖子不存在"
            if post.get("author_id") != author_id:
                return False, "无权修改此帖子"

            for key, value in kwargs.items():
                if value is not None:
                    post[key] = value

            return True, None

        from src.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        try:
            post = supabase.table("posts").select("author_id").eq("id", post_id).single().execute()
            if not post.data or post.data["author_id"] != author_id:
                return False, "无权修改此帖子"

            update_data = {k: v for k, v in kwargs.items() if v is not None}
            if not update_data:
                return True, None

            supabase.table("posts").update(update_data).eq("id", post_id).execute()
            return True, None

        except Exception as e:
            return False, str(e)

    @staticmethod
    def delete_post(post_id: str, author_id: str) -> Tuple[bool, Optional[str]]:
        """删除帖子"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_POSTS

            post = MOCK_POSTS.get(post_id)
            if not post:
                return False, "帖子不存在"
            if post.get("author_id") != author_id:
                return False, "无权删除此帖子"

            del MOCK_POSTS[post_id]
            return True, None

        from src.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        try:
            post = supabase.table("posts").select("author_id").eq("id", post_id).single().execute()
            if not post.data or post.data["author_id"] != author_id:
                return False, "无权删除此帖子"

            supabase.table("posts").delete().eq("id", post_id).execute()
            return True, None

        except Exception as e:
            return False, str(e)

    @staticmethod
    def increment_view_count(post_id: str):
        """增加浏览次数"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_POSTS
            post = MOCK_POSTS.get(post_id)
            if post:
                post["view_count"] = (post.get("view_count") or 0) + 1
            return

        from src.core.supabase import get_supabase_client
        supabase = get_supabase_client()
        try:
            post = supabase.table("posts").select("view_count").eq("id", post_id).single().execute()
            if post.data:
                new_count = (post.data.get("view_count") or 0) + 1
                supabase.table("posts").update({"view_count": new_count}).eq("id", post_id).execute()
        except Exception:
            pass
