from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PostCreate(BaseModel):
    """创建帖子请求"""
    title: str
    description: str
    category_id: str
    ai_tool_used: Optional[str] = None
    error_message: Optional[str] = None
    code_snippet: Optional[str] = None
    budget_type: Optional[str] = None  # 'fixed', 'hourly', 'negotiable'
    budget_amount: Optional[float] = None
    urgency: Optional[str] = "medium"  # 'low', 'medium', 'high', 'urgent'


class PostUpdate(BaseModel):
    """更新帖子请求"""
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    ai_tool_used: Optional[str] = None
    error_message: Optional[str] = None
    code_snippet: Optional[str] = None
    budget_type: Optional[str] = None
    budget_amount: Optional[float] = None
    urgency: Optional[str] = None
    status: Optional[str] = None


class PostResponse(BaseModel):
    """帖子响应"""
    id: str
    author_id: str
    category_id: str
    title: str
    description: str
    ai_tool_used: Optional[str] = None
    error_message: Optional[str] = None
    code_snippet: Optional[str] = None
    budget_type: Optional[str] = None
    budget_amount: Optional[float] = None
    urgency: str
    status: str
    view_count: int
    response_count: int
    created_at: datetime
    updated_at: datetime


class PostListFilter(BaseModel):
    """帖子列表筛选"""
    category: Optional[str] = None
    status: Optional[str] = None
    urgency: Optional[str] = None
    page: int = 1
    limit: int = 20
