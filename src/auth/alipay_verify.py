"""
支付宝实名认证服务

使用支付宝身份认证接口进行实名认证：
1. alipay.user.certify.open.initialize - 初始化认证
2. alipay.user.certify.open.certify - 生成认证链接
3. alipay.user.certify.open.query - 查询认证结果
"""
import json
import base64
import hashlib
import urllib.parse
from datetime import datetime
from typing import Optional, Tuple
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
import httpx

from src.config import settings


class AlipaySignature:
    """支付宝签名工具"""

    @staticmethod
    def sign(data: str, private_key: str) -> str:
        """使用RSA2签名"""
        try:
            key = RSA.import_key(private_key)
            h = SHA256.new(data.encode('utf-8'))
            signer = PKCS1_v1_5.new(key)
            signature = signer.sign(h)
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            print(f"[Alipay] Sign error: {e}")
            return ""

    @staticmethod
    def verify(data: str, signature: str, public_key: str) -> bool:
        """验证支付宝返回的签名"""
        try:
            key = RSA.import_key(public_key)
            h = SHA256.new(data.encode('utf-8'))
            verifier = PKCS1_v1_5.new(key)
            return verifier.verify(h, base64.b64decode(signature))
        except Exception as e:
            print(f"[Alipay] Verify error: {e}")
            return False


class AlipayVerifyService:
    """支付宝实名认证服务"""

    @staticmethod
    def _build_common_params(method: str, biz_content: dict) -> dict:
        """构建公共请求参数"""
        params = {
            "app_id": settings.ALIPAY_APP_ID,
            "method": method,
            "format": "JSON",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "biz_content": json.dumps(biz_content, ensure_ascii=False),
        }
        return params

    @staticmethod
    def _sign_params(params: dict) -> str:
        """对参数进行签名"""
        # 按字母顺序排序参数
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        # 拼接成字符串
        sign_str = "&".join([f"{k}={v}" for k, v in sorted_params if v])
        # 签名
        return AlipaySignature.sign(sign_str, settings.ALIPAY_PRIVATE_KEY)

    @staticmethod
    async def initialize_certify(
        outer_order_no: str,
        cert_name: str,
        cert_no: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        初始化身份认证

        Args:
            outer_order_no: 商户唯一订单号
            cert_name: 真实姓名
            cert_no: 身份证号

        Returns:
            (success, error_msg, certify_id)
        """
        if not settings.ALIPAY_APP_ID:
            return False, "支付宝认证功能尚未配置", None

        biz_content = {
            "outer_order_no": outer_order_no,
            "biz_code": "FACE",  # 人脸认证
            "identity_param": {
                "identity_type": "CERT_INFO",
                "cert_type": "IDENTITY_CARD",
                "cert_name": cert_name,
                "cert_no": cert_no,
            },
            "merchant_config": {
                "return_url": settings.ALIPAY_RETURN_URL or f"{settings.ALIPAY_GATEWAY}/auth/verify/callback",
            },
        }

        params = AlipayVerifyService._build_common_params(
            "alipay.user.certify.open.initialize",
            biz_content
        )
        params["sign"] = AlipayVerifyService._sign_params(params)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.ALIPAY_GATEWAY,
                    data=params,
                    timeout=30.0
                )
                result = response.json()

            # 解析响应
            resp_data = result.get("alipay_user_certify_open_initialize_response", {})
            if resp_data.get("code") == "10000":
                certify_id = resp_data.get("certify_id")
                return True, None, certify_id
            else:
                error_msg = resp_data.get("sub_msg") or resp_data.get("msg", "初始化认证失败")
                return False, error_msg, None

        except Exception as e:
            print(f"[Alipay] Initialize error: {e}")
            return False, f"认证服务异常: {str(e)}", None

    @staticmethod
    def get_certify_url(certify_id: str) -> str:
        """
        获取认证页面URL

        Args:
            certify_id: 认证ID

        Returns:
            认证页面URL
        """
        biz_content = {"certify_id": certify_id}
        params = AlipayVerifyService._build_common_params(
            "alipay.user.certify.open.certify",
            biz_content
        )
        params["sign"] = AlipayVerifyService._sign_params(params)

        # 构建完整URL
        query_string = urllib.parse.urlencode(params)
        return f"{settings.ALIPAY_GATEWAY}?{query_string}"

    @staticmethod
    async def query_certify_result(certify_id: str) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        查询认证结果

        Args:
            certify_id: 认证ID

        Returns:
            (success, error_msg, result_data)
        """
        biz_content = {"certify_id": certify_id}
        params = AlipayVerifyService._build_common_params(
            "alipay.user.certify.open.query",
            biz_content
        )
        params["sign"] = AlipayVerifyService._sign_params(params)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.ALIPAY_GATEWAY,
                    data=params,
                    timeout=30.0
                )
                result = response.json()

            resp_data = result.get("alipay_user_certify_open_query_response", {})
            if resp_data.get("code") == "10000":
                passed = resp_data.get("passed") == "T"
                return True, None, {
                    "passed": passed,
                    "identity_info": resp_data.get("identity_info"),
                    "material_info": resp_data.get("material_info"),
                }
            else:
                error_msg = resp_data.get("sub_msg") or resp_data.get("msg", "查询认证结果失败")
                return False, error_msg, None

        except Exception as e:
            print(f"[Alipay] Query error: {e}")
            return False, f"查询服务异常: {str(e)}", None


class UserVerifyService:
    """用户实名认证服务"""

    @staticmethod
    def update_verify_status(
        user_id: str,
        real_name: str,
        verified: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        更新用户实名认证状态

        Args:
            user_id: 用户ID
            real_name: 真实姓名
            verified: 是否验证通过

        Returns:
            (success, error_msg)
        """
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_USERS, save_users

            if user_id not in MOCK_USERS:
                return False, "用户不存在"

            MOCK_USERS[user_id]["real_name"] = real_name
            MOCK_USERS[user_id]["id_card_verified"] = verified

            # 保存用户数据
            save_users()
            print(f"[UserVerify] User verification updated: {user_id}")

            return True, None

        # 真实模式：更新 Supabase
        try:
            from src.core.supabase import get_supabase_admin_client
            supabase = get_supabase_admin_client()

            print(f"[UserVerify] Updating user {user_id}: {real_name}, verified={verified}")
            result = supabase.table("profiles").update({
                "real_name": real_name,
                "id_card_verified": verified,
            }).eq("id", user_id).execute()

            print(f"[UserVerify] Update result: {result}")
            if result.data:
                print(f"[UserVerify] Successfully updated user {user_id}")
                return True, None
            print(f"[UserVerify] No data returned from update")
            return False, "更新认证状态失败"

        except Exception as e:
            print(f"[UserVerify] Update error: {e}")
            import traceback
            traceback.print_exc()
            return False, f"更新失败: {str(e)}"

    @staticmethod
    def check_verify_status(user_id: str) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        检查用户实名认证状态

        Returns:
            (success, error_msg, verify_info)
        """
        if settings.is_demo_mode:
            from src.core.mock_data import MOCK_USERS

            if user_id not in MOCK_USERS:
                return False, "用户不存在", None

            user = MOCK_USERS[user_id]
            return True, None, {
                "verified": user.get("id_card_verified", False),
                "real_name": user.get("real_name"),
            }

        # 真实模式
        try:
            from src.core.supabase import get_supabase_client
            supabase = get_supabase_client()

            result = supabase.table("profiles").select(
                "real_name", "id_card_verified"
            ).eq("id", user_id).single().execute()

            if result.data:
                return True, None, {
                    "verified": result.data.get("id_card_verified", False),
                    "real_name": result.data.get("real_name"),
                }
            return False, "用户不存在", None

        except Exception as e:
            print(f"[UserVerify] Check error: {e}")
            return False, f"查询失败: {str(e)}", None
