"""
微信OAuth服务 - 处理微信登录/注册
"""
import uuid
import hashlib
import httpx
from typing import Optional, Tuple
from datetime import datetime
from urllib.parse import urlencode

from src.config import settings


class WeChatOAuthService:
    """微信OAuth服务"""

    # 微信OAuth接口地址
    AUTHORIZE_URL = "https://open.weixin.qq.com/connect/oauth2/authorize"
    ACCESS_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
    USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"

    @classmethod
    def get_authorize_url(cls, state: str, scope: str = "snsapi_userinfo") -> str:
        """
        获取微信授权URL

        Args:
            state: 防CSRF的随机字符串，回调时原样返回
            scope: 授权范围，snsapi_base(静默授权) 或 snsapi_userinfo(获取用户信息)

        Returns:
            微信授权页面URL
        """
        params = {
            "appid": settings.WECHAT_APP_ID,
            "redirect_uri": settings.WECHAT_REDIRECT_URI,
            "response_type": "code",
            "scope": scope,
            "state": state,
        }
        return f"{cls.AUTHORIZE_URL}?{urlencode(params)}#wechat_redirect"

    @classmethod
    async def get_access_token(cls, code: str) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        用code换取access_token

        Args:
            code: 微信返回的授权码

        Returns:
            (success, error_msg, token_data)
        """
        params = {
            "appid": settings.WECHAT_APP_ID,
            "secret": settings.WECHAT_APP_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(cls.ACCESS_TOKEN_URL, params=params)
                data = response.json()

            if "errcode" in data:
                return False, f"微信授权失败: {data.get('errmsg', '未知错误')}", None

            return True, None, {
                "access_token": data["access_token"],
                "openid": data["openid"],
                "unionid": data.get("unionid"),  # 只有在绑定了开放平台账号时才有
                "expires_in": data["expires_in"],
                "refresh_token": data["refresh_token"],
                "scope": data["scope"],
            }

        except Exception as e:
            return False, f"获取微信access_token失败: {str(e)}", None

    @classmethod
    async def get_user_info(cls, access_token: str, openid: str) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        获取微信用户信息

        Args:
            access_token: 访问令牌
            openid: 用户openid

        Returns:
            (success, error_msg, user_info)
        """
        params = {
            "access_token": access_token,
            "openid": openid,
            "lang": "zh_CN",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(cls.USERINFO_URL, params=params)
                data = response.json()

            if "errcode" in data:
                return False, f"获取用户信息失败: {data.get('errmsg', '未知错误')}", None

            return True, None, {
                "openid": data["openid"],
                "unionid": data.get("unionid"),
                "nickname": data.get("nickname", "微信用户"),
                "sex": data.get("sex", 0),  # 0未知 1男 2女
                "province": data.get("province", ""),
                "city": data.get("city", ""),
                "country": data.get("country", ""),
                "headimgurl": data.get("headimgurl", ""),
            }

        except Exception as e:
            return False, f"获取微信用户信息失败: {str(e)}", None


class UserIdentityService:
    """用户身份绑定服务"""

    PROVIDER_WECHAT = "wechat"
    PROVIDER_EMAIL = "email"

    @classmethod
    def create_identity(
        cls,
        user_id: str,
        provider: str,
        provider_user_id: str,
        provider_data: Optional[dict] = None,
    ) -> dict:
        """
        创建用户身份绑定记录

        Args:
            user_id: 本系统用户ID
            provider: 登录提供商 (wechat, email)
            provider_user_id: 提供商的用户标识 (微信openid, 邮箱地址)
            provider_data: 提供商返回的额外数据
        """
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_USER_IDENTITIES, MOCK_IDENTITY_INDEX

            identity_id = str(uuid.uuid4())
            identity = {
                "id": identity_id,
                "user_id": user_id,
                "provider": provider,
                "provider_user_id": provider_user_id,
                "provider_data": provider_data or {},
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            MOCK_USER_IDENTITIES[identity_id] = identity
            # 创建索引方便快速查找
            index_key = f"{provider}:{provider_user_id}"
            MOCK_IDENTITY_INDEX[index_key] = identity_id
            return identity

        # Supabase模式
        from src.core.supabase import get_supabase_admin_client
        admin_client = get_supabase_admin_client()
        result = admin_client.table("user_identities").insert({
            "user_id": user_id,
            "provider": provider,
            "provider_user_id": provider_user_id,
            "provider_data": provider_data or {},
        }).execute()
        return result.data[0] if result.data else None

    @classmethod
    def find_by_provider(cls, provider: str, provider_user_id: str) -> Optional[dict]:
        """
        根据提供商和用户ID查找身份绑定

        Returns:
            身份绑定记录，如果不存在返回None
        """
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_USER_IDENTITIES, MOCK_IDENTITY_INDEX

            index_key = f"{provider}:{provider_user_id}"
            identity_id = MOCK_IDENTITY_INDEX.get(index_key)
            if identity_id:
                return MOCK_USER_IDENTITIES.get(identity_id)
            return None

        # Supabase模式
        from src.core.supabase import get_supabase_admin_client
        admin_client = get_supabase_admin_client()
        result = admin_client.table("user_identities").select("*").eq(
            "provider", provider
        ).eq("provider_user_id", provider_user_id).execute()
        return result.data[0] if result.data else None

    @classmethod
    def get_user_identities(cls, user_id: str) -> list:
        """获取用户的所有身份绑定"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_USER_IDENTITIES
            return [
                identity for identity in MOCK_USER_IDENTITIES.values()
                if identity["user_id"] == user_id
            ]

        # Supabase模式
        from src.core.supabase import get_supabase_admin_client
        admin_client = get_supabase_admin_client()
        result = admin_client.table("user_identities").select("*").eq("user_id", user_id).execute()
        return result.data or []

    @classmethod
    def delete_identity(cls, identity_id: str) -> bool:
        """删除身份绑定"""
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_USER_IDENTITIES, MOCK_IDENTITY_INDEX

            identity = MOCK_USER_IDENTITIES.pop(identity_id, None)
            if identity:
                index_key = f"{identity['provider']}:{identity['provider_user_id']}"
                MOCK_IDENTITY_INDEX.pop(index_key, None)
                return True
            return False

        # Supabase模式
        from src.core.supabase import get_supabase_admin_client
        admin_client = get_supabase_admin_client()
        admin_client.table("user_identities").delete().eq("id", identity_id).execute()
        return True


class WeChatAuthService:
    """微信登录/注册服务"""

    @classmethod
    def sign_up_with_wechat(
        cls,
        openid: str,
        unionid: Optional[str],
        wechat_user_info: dict,
        user_role: str,
        terms_agreed_at: str,
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        使用微信注册新用户

        Args:
            openid: 微信openid
            unionid: 微信unionid（如果有）
            wechat_user_info: 微信用户信息
            user_role: 用户角色 (asker/solver)
            terms_agreed_at: 同意协议时间

        Returns:
            (success, error_msg, session_data)
        """
        # 检查是否已存在该微信账号
        existing = UserIdentityService.find_by_provider(
            UserIdentityService.PROVIDER_WECHAT,
            openid
        )
        if existing:
            return False, "该微信账号已注册，请直接登录", None

        if settings.is_demo_mode:
            from src.core.mock_data import (
                MOCK_USERS, MOCK_SOLVER_PROFILES,
                MOCK_AGREEMENTS, MOCK_SESSIONS
            )

            user_id = str(uuid.uuid4())
            nickname = wechat_user_info.get("nickname", "微信用户")
            avatar_url = wechat_user_info.get("headimgurl")

            # 创建用户
            new_user = {
                "id": user_id,
                "email": None,  # 微信注册暂无邮箱
                "nickname": nickname,
                "user_role": user_role,
                "avatar_url": avatar_url,
                "real_name": None,
                "id_card_verified": False,
                "phone": None,
                "wechat_id": None,
                "bio": None,
                "created_at": datetime.now().isoformat(),
                "password_hash": None,  # 微信注册无密码
                "terms_agreed_at": terms_agreed_at,
            }
            MOCK_USERS[user_id] = new_user

            # 创建身份绑定
            UserIdentityService.create_identity(
                user_id=user_id,
                provider=UserIdentityService.PROVIDER_WECHAT,
                provider_user_id=openid,
                provider_data={
                    "unionid": unionid,
                    "nickname": nickname,
                    "avatar_url": avatar_url,
                    "sex": wechat_user_info.get("sex"),
                }
            )

            # 记录协议同意
            MOCK_AGREEMENTS[user_id] = {
                "user_id": user_id,
                "email": None,
                "agreed_at": terms_agreed_at,
                "agreement_version": "1.0",
            }

            # 如果是解决者，创建解决者资料
            if user_role == "solver":
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

            # 创建登录会话
            token = f"wechat-token-{user_id}"
            MOCK_SESSIONS[token] = user_id

            return True, None, {
                "access_token": token,
                "refresh_token": f"refresh-{token}",
                "user": {
                    "id": user_id,
                    "nickname": nickname,
                    "is_new_user": True,
                },
            }

        # Supabase模式 - 待实现
        return False, "Supabase模式下的微信注册暂未实现", None

    @classmethod
    def sign_in_with_wechat(cls, openid: str) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        使用微信登录

        Args:
            openid: 微信openid

        Returns:
            (success, error_msg, session_data)
        """
        # 查找已绑定的身份
        identity = UserIdentityService.find_by_provider(
            UserIdentityService.PROVIDER_WECHAT,
            openid
        )

        if not identity:
            return False, "该微信账号尚未注册", None

        user_id = identity["user_id"]

        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_USERS, MOCK_SESSIONS

            user = MOCK_USERS.get(user_id)
            if not user:
                return False, "用户不存在", None

            # 创建登录会话
            token = f"wechat-token-{user_id}"
            MOCK_SESSIONS[token] = user_id

            return True, None, {
                "access_token": token,
                "refresh_token": f"refresh-{token}",
                "user": {
                    "id": user_id,
                    "nickname": user.get("nickname"),
                    "is_new_user": False,
                },
            }

        # Supabase模式 - 待实现
        return False, "Supabase模式下的微信登录暂未实现", None

    @classmethod
    def bind_wechat_to_user(
        cls,
        user_id: str,
        openid: str,
        unionid: Optional[str],
        wechat_user_info: dict,
    ) -> Tuple[bool, Optional[str]]:
        """
        将微信账号绑定到现有用户

        Args:
            user_id: 用户ID
            openid: 微信openid
            unionid: 微信unionid
            wechat_user_info: 微信用户信息

        Returns:
            (success, error_msg)
        """
        # 检查该微信是否已被其他账号绑定
        existing = UserIdentityService.find_by_provider(
            UserIdentityService.PROVIDER_WECHAT,
            openid
        )
        if existing:
            if existing["user_id"] == user_id:
                return False, "该微信账号已绑定到当前账户"
            return False, "该微信账号已被其他账户绑定"

        # 创建绑定
        UserIdentityService.create_identity(
            user_id=user_id,
            provider=UserIdentityService.PROVIDER_WECHAT,
            provider_user_id=openid,
            provider_data={
                "unionid": unionid,
                "nickname": wechat_user_info.get("nickname"),
                "avatar_url": wechat_user_info.get("headimgurl"),
                "sex": wechat_user_info.get("sex"),
            }
        )

        return True, None
