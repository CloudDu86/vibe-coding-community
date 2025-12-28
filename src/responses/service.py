from typing import List, Optional, Tuple
import uuid
from datetime import datetime

from src.config import settings


class ResponseService:
    """回复服务"""

    @staticmethod
    def create_response(
        post_id: str,
        solver_id: str,
        content: str,
        proposed_solution: Optional[str] = None,
        estimated_time: Optional[str] = None,
        proposed_price: Optional[float] = None,
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """创建回复"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_RESPONSES, MOCK_POSTS, MOCK_USERS, MOCK_SOLVER_PROFILES

            # 检查是否已回复
            for resp in MOCK_RESPONSES.values():
                if resp["post_id"] == post_id and resp["solver_id"] == solver_id:
                    return False, "您已经回复过此帖子", None

            resp_id = str(uuid.uuid4())
            solver = MOCK_USERS.get(solver_id, {})
            solver_profile = MOCK_SOLVER_PROFILES.get(solver_id, {})

            new_response = {
                "id": resp_id,
                "post_id": post_id,
                "solver_id": solver_id,
                "content": content,
                "proposed_solution": proposed_solution,
                "estimated_time": estimated_time,
                "proposed_price": proposed_price,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "profiles": solver,
                "solver_profiles": solver_profile,
            }
            MOCK_RESPONSES[resp_id] = new_response

            # 更新帖子回复数
            post = MOCK_POSTS.get(post_id)
            if post:
                post["response_count"] = (post.get("response_count") or 0) + 1

            return True, None, new_response

        from src.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        try:
            existing = supabase.table("responses").select("id").eq("post_id", post_id).eq("solver_id", solver_id).execute()
            if existing.data:
                return False, "您已经回复过此帖子", None

            result = supabase.table("responses").insert({
                "post_id": post_id,
                "solver_id": solver_id,
                "content": content,
                "proposed_solution": proposed_solution,
                "estimated_time": estimated_time,
                "proposed_price": proposed_price,
            }).execute()

            post = supabase.table("posts").select("response_count").eq("id", post_id).single().execute()
            if post.data:
                new_count = (post.data.get("response_count") or 0) + 1
                supabase.table("posts").update({"response_count": new_count}).eq("id", post_id).execute()

            return True, None, result.data[0] if result.data else None

        except Exception as e:
            return False, str(e), None

    @staticmethod
    def get_responses(post_id: str) -> List[dict]:
        """获取帖子的所有回复"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_RESPONSES
            responses = [r for r in MOCK_RESPONSES.values() if r["post_id"] == post_id]
            responses.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return responses

        from src.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        try:
            result = supabase.table("responses").select(
                "*, profiles(id, nickname, avatar_url), solver_profiles(experience_years, rating, total_solved)"
            ).eq("post_id", post_id).order("created_at", desc=True).execute()

            return result.data or []

        except Exception:
            return []

    @staticmethod
    def get_response(response_id: str) -> Optional[dict]:
        """获取单个回复"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_RESPONSES
            return MOCK_RESPONSES.get(response_id)

        from src.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        try:
            result = supabase.table("responses").select(
                "*, profiles(id, nickname, avatar_url)"
            ).eq("id", response_id).single().execute()

            return result.data

        except Exception:
            return None

    @staticmethod
    def update_response_status(
        response_id: str,
        post_author_id: str,
        new_status: str,
    ) -> Tuple[bool, Optional[str]]:
        """更新回复状态"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_RESPONSES, MOCK_POSTS

            response = MOCK_RESPONSES.get(response_id)
            if not response:
                return False, "回复不存在"

            post = MOCK_POSTS.get(response["post_id"])
            if not post or post.get("author_id") != post_author_id:
                return False, "无权操作此回复"

            response["status"] = new_status

            if new_status == "accepted":
                post["status"] = "in_progress"

            return True, None

        from src.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        try:
            response = supabase.table("responses").select("*, posts(author_id, id)").eq("id", response_id).single().execute()

            if not response.data:
                return False, "回复不存在"

            if response.data.get("posts", {}).get("author_id") != post_author_id:
                return False, "无权操作此回复"

            supabase.table("responses").update({"status": new_status}).eq("id", response_id).execute()

            if new_status == "accepted":
                post_id = response.data.get("posts", {}).get("id")
                if post_id:
                    supabase.table("posts").update({"status": "in_progress"}).eq("id", post_id).execute()

            return True, None

        except Exception as e:
            return False, str(e)

    @staticmethod
    def mark_as_completed(response_id: str, post_author_id: str) -> Tuple[bool, Optional[str]]:
        """标记为已完成"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_RESPONSES, MOCK_POSTS, MOCK_SOLVER_PROFILES

            response = MOCK_RESPONSES.get(response_id)
            if not response:
                return False, "回复不存在"

            post = MOCK_POSTS.get(response["post_id"])
            if not post or post.get("author_id") != post_author_id:
                return False, "无权操作此回复"

            response["status"] = "completed"
            post["status"] = "resolved"

            solver_profile = MOCK_SOLVER_PROFILES.get(response["solver_id"])
            if solver_profile:
                solver_profile["total_solved"] = (solver_profile.get("total_solved") or 0) + 1

            return True, None

        from src.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        try:
            response = supabase.table("responses").select("*, posts(author_id, id)").eq("id", response_id).single().execute()

            if not response.data:
                return False, "回复不存在"

            if response.data.get("posts", {}).get("author_id") != post_author_id:
                return False, "无权操作此回复"

            supabase.table("responses").update({"status": "completed"}).eq("id", response_id).execute()

            post_id = response.data.get("posts", {}).get("id")
            if post_id:
                supabase.table("posts").update({"status": "resolved"}).eq("id", post_id).execute()

            solver_id = response.data.get("solver_id")
            if solver_id:
                solver = supabase.table("solver_profiles").select("total_solved").eq("user_id", solver_id).single().execute()
                if solver.data:
                    new_count = (solver.data.get("total_solved") or 0) + 1
                    supabase.table("solver_profiles").update({"total_solved": new_count}).eq("user_id", solver_id).execute()

            return True, None

        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_solver_responses(solver_id: str, page: int = 1, limit: int = 20) -> Tuple[List[dict], int]:
        """获取解决者的所有回复"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_RESPONSES
            responses = [r for r in MOCK_RESPONSES.values() if r["solver_id"] == solver_id]
            responses.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            total = len(responses)
            offset = (page - 1) * limit
            return responses[offset:offset + limit], total

        from src.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        try:
            offset = (page - 1) * limit
            result = supabase.table("responses").select(
                "*, posts(id, title, status)",
                count="exact",
            ).eq("solver_id", solver_id).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

            total = result.count if result.count else 0
            return result.data or [], total

        except Exception:
            return [], 0
