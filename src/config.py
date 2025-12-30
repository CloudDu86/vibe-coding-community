from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # 应用设置
    APP_NAME: str = "AI生成社区"
    DEBUG: bool = True

    # 演示模式（无需 Supabase）
    DEMO_MODE: bool = True

    # Supabase 配置（演示模式下可为空）
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = "demo-secret-key"

    # 微信OAuth配置
    WECHAT_APP_ID: Optional[str] = None
    WECHAT_APP_SECRET: Optional[str] = None
    WECHAT_REDIRECT_URI: Optional[str] = None  # 回调地址

    # 支付宝实名认证配置
    ALIPAY_APP_ID: Optional[str] = None
    ALIPAY_PRIVATE_KEY: Optional[str] = None  # 应用私钥
    ALIPAY_PUBLIC_KEY: Optional[str] = None   # 支付宝公钥
    ALIPAY_GATEWAY: str = "https://openapi.alipay.com/gateway.do"
    ALIPAY_RETURN_URL: Optional[str] = None   # 认证完成后的回调地址

    # 安全配置
    SECRET_KEY: str = "demo-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }

    @property
    def is_demo_mode(self) -> bool:
        """检查是否为演示模式"""
        return self.DEMO_MODE or not self.SUPABASE_URL


@lru_cache()
def get_settings() -> Settings:
    """获取缓存的配置实例"""
    return Settings()


settings = get_settings()
