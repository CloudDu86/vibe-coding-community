from typing import List, Optional, Tuple
import uuid
from datetime import datetime

from src.config import settings
from src.messages.service import MessageService


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

            # 检查帖子是否已被接单
            post = MOCK_POSTS.get(post_id)
            if post and post.get("status") != "open":
                return False, "此单子已被其他人接了", None

            # 检查是否已回复
            for resp in MOCK_RESPONSES.values():
                if resp["post_id"] == post_id and resp["solver_id"] == solver_id:
                    return False, "您已经接过此单子", None

            resp_id = str(uuid.uuid4())
            solver = MOCK_USERS.get(solver_id, {})
            solver_profile = MOCK_SOLVER_PROFILES.get(solver_id, {})

            new_response = {
                "id": resp_id,
                "post_id": post_id,
                "solver_id": solver_id,
                "content": content,
                "status": "accepted",  # 直接设为已接受
                "created_at": datetime.now().isoformat(),
                "profiles": solver,
                "solver_profiles": solver_profile,
            }
            MOCK_RESPONSES[resp_id] = new_response

            # 更新帖子状态和回复数
            if post:
                post["status"] = "in_progress"
                post["response_count"] = 1

                # 发送通知给求助者
                MessageService.send_order_notification(
                    requester_id=post["author_id"],
                    solver_id=solver_id,
                    solver_nickname=solver.get("nickname", "解决者"),
                    solver_wechat=solver.get("wechat_id"),
                    post_id=post_id,
                    post_title=post.get("title", ""),
                    response_id=resp_id,
                )

            return True, None, new_response

        from src.core.supabase import get_supabase_admin_client
        supabase = get_supabase_admin_client()

        try:
            existing = supabase.table("responses").select("id").eq("post_id", post_id).eq("solver_id", solver_id).execute()
            if existing.data:
                return False, "您已经接过此单子", None

            # 检查帖子是否已被接单，并获取帖子信息
            post_check = supabase.table("posts").select("status, author_id, title").eq("id", post_id).single().execute()
            if post_check.data and post_check.data.get("status") != "open":
                return False, "此单子已被其他人接了", None

            result = supabase.table("responses").insert({
                "post_id": post_id,
                "solver_id": solver_id,
                "content": content,
                "status": "accepted",  # 直接设为已接受
            }).execute()

            print(f"[Responses] Created response: {result.data}")

            # 更新帖子状态为进行中，并增加回复数
            supabase.table("posts").update({
                "status": "in_progress",
                "response_count": 1,
            }).eq("id", post_id).execute()

            # 发送通知给求助者
            if result.data and post_check.data:
                # 获取解决者信息
                solver_info = supabase.table("profiles").select("nickname, wechat_id").eq("id", solver_id).single().execute()
                solver_data = solver_info.data if solver_info.data else {}

                MessageService.send_order_notification(
                    requester_id=post_check.data.get("author_id"),
                    solver_id=solver_id,
                    solver_nickname=solver_data.get("nickname", "解决者"),
                    solver_wechat=solver_data.get("wechat_id"),
                    post_id=post_id,
                    post_title=post_check.data.get("title", ""),
                    response_id=result.data[0].get("id"),
                )

            return True, None, result.data[0] if result.data else None

        except Exception as e:
            print(f"[Responses] Error creating response: {e}")
            return False, str(e), None

    @staticmethod
    def get_responses(post_id: str) -> List[dict]:
        """获取帖子的所有回复"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_RESPONSES
            responses = [r for r in MOCK_RESPONSES.values() if r["post_id"] == post_id]
            responses.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return responses

        from src.core.supabase import get_supabase_admin_client
        supabase = get_supabase_admin_client()

        try:
            # 只关联 profiles，包含联系方式
            result = supabase.table("responses").select(
                "*, profiles(id, nickname, avatar_url, wechat_id, phone)"
            ).eq("post_id", post_id).order("created_at", desc=True).execute()

            print(f"[Responses] Found {len(result.data or [])} responses for post {post_id}")
            return result.data or []

        except Exception as e:
            print(f"[Responses] Error fetching responses: {e}")
            return []

    @staticmethod
    def get_response(response_id: str) -> Optional[dict]:
        """获取单个回复"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_RESPONSES
            return MOCK_RESPONSES.get(response_id)

        from src.core.supabase import get_supabase_admin_client
        supabase = get_supabase_admin_client()

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

        from src.core.supabase import get_supabase_admin_client
        supabase = get_supabase_admin_client()

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

        from src.core.supabase import get_supabase_admin_client
        supabase = get_supabase_admin_client()

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

        from src.core.supabase import get_supabase_admin_client
        supabase = get_supabase_admin_client()

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
