from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # 应用设置
    APP_NAME: str = "Vibe Coding互助社区"
    DEBUG: bool = True

    # 演示模式（无需 Supabase）
    DEMO_MODE: bool = True

    # Supabase 配置（演示模式下可为空）
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = "demo-secret-key"

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
