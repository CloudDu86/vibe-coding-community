from pydantic import BaseModel, EmailStr
from typing import Optional


class UserLogin(BaseModel):
    """登录请求"""
    email: EmailStr
    password: str


class UserRegister(BaseModel):
    """注册请求"""
    email: EmailStr
    password: str
    nickname: str
    user_role: str  # 'asker', 'solver', 'both'


class UserProfile(BaseModel):
    """用户资料"""
    id: str
    email: str
    nickname: str
    user_role: str
    avatar_url: Optional[str] = None
    real_name: Optional[str] = None
    id_card_verified: bool = False
    phone: Optional[str] = None
    wechat_id: Optional[str] = None
    bio: Optional[str] = None


class TokenData(BaseModel):
    """JWT 令牌数据"""
    sub: str  # user_id
    email: Optional[str] = None
    exp: Optional[int] = None
