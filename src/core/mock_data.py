"""
模拟数据 - 用于演示模式（无需 Supabase）
"""
import uuid
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 数据存储目录
DATA_DIR = Path(__file__).resolve().parent.parent.parent / ".data"
DATA_DIR.mkdir(exist_ok=True)
USERS_FILE = DATA_DIR / "users.json"

# 模拟用户数据
MOCK_USERS: Dict[str, dict] = {
    "demo-user-1": {
        "id": "demo-user-1",
        "email": "demo@example.com",
        "nickname": "演示用户",
        "user_role": "both",
        "avatar_url": None,
        "real_name": "张三",
        "id_card_verified": True,
        "phone": None,
        "wechat_id": None,
        "bio": "这是一个演示账号",
        "created_at": datetime.now().isoformat(),
    }
}

# 模拟解决者资料
MOCK_SOLVER_PROFILES: Dict[str, dict] = {
    "demo-user-1": {
        "id": str(uuid.uuid4()),
        "user_id": "demo-user-1",
        "experience_years": 5,
        "expertise_areas": ["Python", "FastAPI", "React"],
        "resume": "5年全栈开发经验",
        "hourly_rate": 200.0,
        "rating": 4.8,
        "total_solved": 42,
        "is_available": True,
    }
}

# 模拟用户协议同意记录
MOCK_AGREEMENTS: Dict[str, dict] = {}

# 模拟用户身份绑定表（支持多登录方式）
# key: identity_id, value: identity record
MOCK_USER_IDENTITIES: Dict[str, dict] = {}
# 索引: provider + provider_user_id -> identity_id
MOCK_IDENTITY_INDEX: Dict[str, str] = {}

# 模拟分类数据
MOCK_CATEGORIES: List[dict] = [
    {"id": "cat-1", "name": "网页开发", "slug": "web", "description": "网站、Web应用相关问题", "display_order": 1, "is_active": True},
    {"id": "cat-2", "name": "移动App", "slug": "app", "description": "iOS/Android应用开发问题", "display_order": 2, "is_active": True},
    {"id": "cat-3", "name": "微信小程序", "slug": "wechat-mini", "description": "微信小程序开发问题", "display_order": 3, "is_active": True},
    {"id": "cat-4", "name": "桌面应用", "slug": "desktop", "description": "桌面软件开发问题", "display_order": 4, "is_active": True},
    {"id": "cat-5", "name": "后端服务", "slug": "backend", "description": "API、数据库、服务器问题", "display_order": 5, "is_active": True},
    {"id": "cat-6", "name": "AI/机器学习", "slug": "ai-ml", "description": "AI模型、机器学习相关问题", "display_order": 6, "is_active": True},
    {"id": "cat-7", "name": "Web3开发", "slug": "web3", "description": "区块链、智能合约、DApp开发问题", "display_order": 7, "is_active": True},
    {"id": "cat-8", "name": "音视频开发", "slug": "av", "description": "音频、视频处理与流媒体开发问题", "display_order": 8, "is_active": True},
    {"id": "cat-9", "name": "其他", "slug": "other", "description": "其他类型问题", "display_order": 99, "is_active": True},
]

# 模拟帖子数据
MOCK_POSTS: Dict[str, dict] = {}

# 模拟回复数据
MOCK_RESPONSES: Dict[str, dict] = {}

# 模拟消息数据
MOCK_MESSAGES: Dict[str, dict] = {}

# 会话存储（模拟登录状态）
MOCK_SESSIONS: Dict[str, str] = {}  # token -> user_id


def init_mock_posts():
    """初始化模拟帖子数据"""
    posts = [
        {
            "id": "post-1",
            "author_id": "demo-user-1",
            "category_id": "cat-1",
            "title": "使用Cursor开发React项目时遇到TypeScript类型错误",
            "description": "我在使用Cursor的AI功能生成React组件时，遇到了一些TypeScript类型错误。AI生成的代码无法通过类型检查，我尝试了多次修改提示词但问题依然存在。\n\n具体错误是关于props类型推断的问题，希望有经验的开发者能帮忙看看。",
            "ai_tool_used": "Cursor",
            "error_message": "Type 'string' is not assignable to type 'number'",
            "code_snippet": "const MyComponent: React.FC<Props> = ({ count }) => {\n  return <div>{count}</div>\n}",
            "budget_type": "fixed",
            "budget_amount": 50.0,
            "urgency": "medium",
            "status": "open",
            "view_count": 156,
            "response_count": 2,
            "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "profiles": MOCK_USERS["demo-user-1"],
            "categories": MOCK_CATEGORIES[0],
        },
        {
            "id": "post-2",
            "author_id": "demo-user-1",
            "category_id": "cat-5",
            "title": "FastAPI + SQLAlchemy 异步查询性能问题",
            "description": "我按照ChatGPT的建议使用async SQLAlchemy，但查询性能反而变慢了。数据库连接池配置可能有问题，希望有人能帮忙排查。",
            "ai_tool_used": "ChatGPT-4",
            "error_message": None,
            "code_snippet": None,
            "budget_type": "hourly",
            "budget_amount": 100.0,
            "urgency": "high",
            "status": "open",
            "view_count": 89,
            "response_count": 1,
            "created_at": (datetime.now() - timedelta(hours=5)).isoformat(),
            "profiles": MOCK_USERS["demo-user-1"],
            "categories": MOCK_CATEGORIES[4],
        },
        {
            "id": "post-3",
            "author_id": "demo-user-1",
            "category_id": "cat-3",
            "title": "微信小程序云函数调用失败",
            "description": "使用Copilot生成的云函数代码，本地测试正常但部署后一直报错。错误信息是 'cloud function execution failed'，不知道是配置问题还是代码问题。",
            "ai_tool_used": "GitHub Copilot",
            "error_message": "cloud function execution failed: timeout",
            "code_snippet": None,
            "budget_type": "negotiable",
            "budget_amount": None,
            "urgency": "urgent",
            "status": "in_progress",
            "view_count": 234,
            "response_count": 3,
            "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
            "profiles": MOCK_USERS["demo-user-1"],
            "categories": MOCK_CATEGORIES[2],
        },
    ]

    for post in posts:
        MOCK_POSTS[post["id"]] = post


def init_mock_responses():
    """初始化模拟回复数据"""
    responses = [
        {
            "id": "resp-1",
            "post_id": "post-1",
            "solver_id": "demo-user-1",
            "content": "这个问题我遇到过，主要是因为TypeScript的类型推断在泛型组件中有些限制。",
            "proposed_solution": "可以通过显式声明Props接口并使用as const断言来解决。我可以帮你重构这部分代码。",
            "estimated_time": "30分钟",
            "proposed_price": 30.0,
            "status": "pending",
            "created_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "profiles": MOCK_USERS["demo-user-1"],
            "solver_profiles": MOCK_SOLVER_PROFILES["demo-user-1"],
        },
    ]

    for resp in responses:
        MOCK_RESPONSES[resp["id"]] = resp


def save_users():
    """保存用户数据到文件"""
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(MOCK_USERS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[MockData] Failed to save users: {e}")


def load_users():
    """从文件加载用户数据"""
    global MOCK_USERS
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                loaded_users = json.load(f)
                # 合并加载的用户和默认用户
                for user_id, user_data in loaded_users.items():
                    MOCK_USERS[user_id] = user_data
            print(f"[MockData] Loaded {len(loaded_users)} users from file")
        except Exception as e:
            print(f"[MockData] Failed to load users: {e}")


# 初始化数据
load_users()  # 加载持久化的用户数据
init_mock_posts()
init_mock_responses()
