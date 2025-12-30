from typing import Optional, Tuple
import uuid
import hashlib
from datetime import datetime

from src.config import settings


class AuthService:
    """认证服务"""

    @staticmethod
    def sign_up(
        email: str,
        password: str,
        nickname: str,
        user_role: str,
        terms_agreed_at: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """用户注册"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_USERS, MOCK_SOLVER_PROFILES, MOCK_AGREEMENTS, save_users

            # 检查邮箱是否已存在
            for user in MOCK_USERS.values():
                if user.get("email") == email:
                    return False, "该邮箱已被注册", None

            user_id = str(uuid.uuid4())
            new_user = {
                "id": user_id,
                "email": email,
                "nickname": nickname,
                "user_role": user_role,
                "avatar_url": None,
                "real_name": None,
                "id_card_verified": False,
                "phone": None,
                "wechat_id": None,
                "bio": None,
                "created_at": datetime.now().isoformat(),
                "password_hash": hashlib.sha256(password.encode()).hexdigest(),
                "terms_agreed_at": terms_agreed_at,
            }
            MOCK_USERS[user_id] = new_user

            # 记录协议同意存档
            if terms_agreed_at:
                MOCK_AGREEMENTS[user_id] = {
                    "user_id": user_id,
                    "email": email,
                    "agreed_at": terms_agreed_at,
                    "agreement_version": "1.0",
                }

            if user_role in ["solver", "both"]:
                MOCK_SOLVER_PROFILES[user_id] = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "experience_years": None,
                    "expertise_areas": [],
                    "resume": None,
                    "hourly_rate": None,
                    "rating": 0.0,
                    "total_solved": 0,
                    "is_available": True,
                }

            # 保存用户数据到文件
            save_users()
            print(f"[Auth] User registered and saved: {email}")

            return True, None, {
                "id": user_id,
                "email": email,
                "nickname": nickname,
                "user_role": user_role,
            }

        # 真实 Supabase 模式
        from src.core.supabase import get_supabase_client, get_supabase_admin_client

        supabase = get_supabase_client()
        try:
            auth_response = supabase.auth.sign_up({
                "email": email,
                "password": password,
            })

            if not auth_response.user:
                return False, "注册失败，请稍后重试", None

            user_id = auth_response.user.id
            admin_client = get_supabase_admin_client()

            # 创建用户资料，包含协议同意时间
            profile_data = {
                "id": user_id,
                "nickname": nickname,
                "user_role": user_role,
            }
            if terms_agreed_at:
                profile_data["terms_agreed_at"] = terms_agreed_at

            admin_client.table("profiles").insert(profile_data).execute()

            # 记录协议同意存档
            if terms_agreed_at:
                try:
                    admin_client.table("user_agreements").insert({
                        "user_id": user_id,
                        "agreed_at": terms_agreed_at,
                        "agreement_version": "1.0",
                    }).execute()
                except Exception:
                    pass  # 如果表不存在则忽略

            if user_role in ["solver", "both"]:
                admin_client.table("solver_profiles").insert({
                    "user_id": user_id,
                }).execute()

            return True, None, {
                "id": user_id,
                "email": email,
                "nickname": nickname,
                "user_role": user_role,
            }

        except Exception as e:
            error_msg = str(e)
            if "already registered" in error_msg.lower():
                return False, "该邮箱已被注册", None
            return False, f"注册失败: {error_msg}", None

    @staticmethod
    def sign_in(email: str, password: str) -> Tuple[bool, Optional[str], Optional[dict]]:
        """用户登录"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_USERS, MOCK_SESSIONS

            # 查找用户
            user = None
            for u in MOCK_USERS.values():
                if u.get("email") == email:
                    user = u
                    break

            if not user:
                return False, "邮箱或密码错误", None

            # 验证密码（演示模式简化处理）
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            print(f"[Debug] Login attempt - Email: {email}")
            print(f"[Debug] User password_hash: {user.get('password_hash')}")
            print(f"[Debug] Input password_hash: {password_hash}")
            if user.get("password_hash") and user["password_hash"] != password_hash:
                print(f"[Debug] Password mismatch!")
                return False, "邮箱或密码错误", None

            # 创建演示 token
            token = f"demo-token-{user['id']}"
            MOCK_SESSIONS[token] = user["id"]

            return True, None, {
                "access_token": token,
                "refresh_token": f"refresh-{token}",
                "user": {
                    "id": user["id"],
                    "email": user["email"],
                },
            }

        # 真实 Supabase 模式
        from src.core.supabase import get_supabase_client

        supabase = get_supabase_client()
        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })

            if not auth_response.session:
                return False, "登录失败", None

            return True, None, {
                "access_token": auth_response.session.access_token,
                "refresh_token": auth_response.session.refresh_token,
                "user": {
                    "id": auth_response.user.id,
                    "email": auth_response.user.email,
                },
            }

        except Exception as e:
            error_msg = str(e)
            if "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
                return False, "邮箱或密码错误", None
            return False, f"登录失败: {error_msg}", None

    @staticmethod
    def sign_out(access_token: str) -> bool:
        """用户登出"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_SESSIONS
            MOCK_SESSIONS.pop(access_token, None)
            return True

        try:
            from src.core.supabase import get_supabase_client
            supabase = get_supabase_client()
            supabase.auth.sign_out()
            return True
        except Exception:
            return False

    @staticmethod
    def get_user_profile(user_id: str) -> Optional[dict]:
        """获取用户资料"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_USERS
            return MOCK_USERS.get(user_id)

        try:
            from src.core.supabase import get_supabase_client
            supabase = get_supabase_client()
            result = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
            return result.data
        except Exception:
            return None
