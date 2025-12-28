from typing import List, Optional, Tuple
import uuid
from datetime import datetime

from src.config import settings


class MessageService:
    """消息服务"""

    @staticmethod
    def create_message(
        recipient_id: str,
        message_type: str,
        title: str,
        content: str,
        sender_id: Optional[str] = None,
        related_post_id: Optional[str] = None,
        related_response_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """创建消息"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_MESSAGES

            msg_id = str(uuid.uuid4())
            new_message = {
                "id": msg_id,
                "recipient_id": recipient_id,
                "sender_id": sender_id,
                "message_type": message_type,
                "title": title,
                "content": content,
                "related_post_id": related_post_id,
                "related_response_id": related_response_id,
                "is_read": False,
                "created_at": datetime.now().isoformat(),
            }
            MOCK_MESSAGES[msg_id] = new_message
            return True, None, new_message

        from src.core.supabase import get_supabase_admin_client
        supabase = get_supabase_admin_client()

        try:
            data = {
                "recipient_id": recipient_id,
                "message_type": message_type,
                "title": title,
                "content": content,
            }
            if sender_id:
                data["sender_id"] = sender_id
            if related_post_id:
                data["related_post_id"] = related_post_id
            if related_response_id:
                data["related_response_id"] = related_response_id

            result = supabase.table("messages").insert(data).execute()
            return True, None, result.data[0] if result.data else None

        except Exception as e:
            print(f"[Messages] Error creating message: {e}")
            return False, str(e), None

    @staticmethod
    def get_user_messages(
        user_id: str,
        page: int = 1,
        limit: int = 20,
        unread_only: bool = False,
    ) -> Tuple[List[dict], int]:
        """获取用户消息列表"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_MESSAGES

            messages = [m for m in MOCK_MESSAGES.values() if m["recipient_id"] == user_id]
            if unread_only:
                messages = [m for m in messages if not m.get("is_read")]
            messages.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            total = len(messages)
            offset = (page - 1) * limit
            return messages[offset:offset + limit], total

        from src.core.supabase import get_supabase_admin_client
        supabase = get_supabase_admin_client()

        try:
            offset = (page - 1) * limit
            query = supabase.table("messages").select(
                "*, sender:profiles!sender_id(id, nickname, avatar_url)",
                count="exact",
            ).eq("recipient_id", user_id)

            if unread_only:
                query = query.eq("is_read", False)

            result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            total = result.count if result.count else 0
            return result.data or [], total

        except Exception as e:
            print(f"[Messages] Error fetching messages: {e}")
            return [], 0

    @staticmethod
    def get_recent_messages(user_id: str, limit: int = 5) -> List[dict]:
        """获取最近的消息（用于下拉菜单）"""
        messages, _ = MessageService.get_user_messages(user_id, page=1, limit=limit)
        return messages

    @staticmethod
    def get_unread_count(user_id: str) -> int:
        """获取未读消息数量"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_MESSAGES

            return sum(1 for m in MOCK_MESSAGES.values()
                       if m["recipient_id"] == user_id and not m.get("is_read"))

        from src.core.supabase import get_supabase_admin_client
        supabase = get_supabase_admin_client()

        try:
            result = supabase.table("messages").select(
                "id", count="exact"
            ).eq("recipient_id", user_id).eq("is_read", False).execute()

            return result.count if result.count else 0

        except Exception as e:
            print(f"[Messages] Error counting unread: {e}")
            return 0

    @staticmethod
    def mark_as_read(message_id: str, user_id: str) -> Tuple[bool, Optional[str]]:
        """标记消息为已读"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_MESSAGES

            message = MOCK_MESSAGES.get(message_id)
            if not message:
                return False, "消息不存在"
            if message["recipient_id"] != user_id:
                return False, "无权操作此消息"
            message["is_read"] = True
            return True, None

        from src.core.supabase import get_supabase_admin_client
        supabase = get_supabase_admin_client()

        try:
            supabase.table("messages").update({"is_read": True}).eq(
                "id", message_id
            ).eq("recipient_id", user_id).execute()
            return True, None

        except Exception as e:
            return False, str(e)

    @staticmethod
    def mark_all_as_read(user_id: str) -> Tuple[bool, Optional[str]]:
        """标记所有消息为已读"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_MESSAGES

            for msg in MOCK_MESSAGES.values():
                if msg["recipient_id"] == user_id:
                    msg["is_read"] = True
            return True, None

        from src.core.supabase import get_supabase_admin_client
        supabase = get_supabase_admin_client()

        try:
            supabase.table("messages").update({"is_read": True}).eq(
                "recipient_id", user_id
            ).eq("is_read", False).execute()
            return True, None

        except Exception as e:
            return False, str(e)

    @staticmethod
    def send_order_notification(
        requester_id: str,
        solver_id: str,
        solver_nickname: str,
        solver_bio: Optional[str],
        solver_wechat: Optional[str],
        post_id: str,
        post_title: str,
        response_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """发送接单通知给求助者"""
        content = f"解决者 {solver_nickname} 已接下您的求助「{post_title}」。\n\n"

        if solver_bio:
            content += f"解决者简介：{solver_bio}\n\n"

        if solver_wechat:
            content += f"微信号：{solver_wechat}"
        else:
            content += "请在帖子详情页查看解决者联系方式。"

        success, error, _ = MessageService.create_message(
            recipient_id=requester_id,
            sender_id=solver_id,
            message_type="order",
            title=f"您的求助已被接单",
            content=content,
            related_post_id=post_id,
            related_response_id=response_id,
        )
        return success, error
