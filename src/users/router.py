from pathlib import Path
import hashlib
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.auth.dependencies import get_current_user, require_auth
from src.auth.wechat_oauth import UserIdentityService
from src.core.supabase import get_supabase_client
from src.config import settings

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent.parent / "templates")


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user: dict = Depends(require_auth)):
    """个人资料页面"""
    # 获取用户的身份绑定信息
    identities = UserIdentityService.get_user_identities(user["id"])

    # 查找微信绑定
    wechat_identity = None
    for identity in identities:
        if identity.get("provider") == "wechat":
            wechat_identity = identity
            break

    # 判断是否可以解绑微信（必须有邮箱或其他登录方式）
    can_unbind_wechat = bool(user.get("email"))

    return templates.TemplateResponse(
        "users/profile.html",
        {
            "request": request,
            "title": "个人资料",
            "user": user,
            "wechat_identity": wechat_identity,
            "can_unbind_wechat": can_unbind_wechat,
        },
    )


@router.get("/my-posts", response_class=HTMLResponse)
async def my_posts_page(request: Request, user: dict = Depends(require_auth)):
    """我的求助单页面"""
    from src.posts.service import PostService
    from src.responses.service import ResponseService

    # 获取用户所有求助单
    all_posts, total = PostService.get_posts(author_id=user["id"], limit=100)

    # 检查每个帖子是否有待审核的解决方案
    for post in all_posts:
        responses = ResponseService.get_responses(post["id"])
        post["has_pending_review"] = any(r.get("status") == "pending_review" for r in responses)

    # 分类：未解决和已解决
    pending_posts = [p for p in all_posts if p.get("status") in ["open", "in_progress"]]
    resolved_posts = [p for p in all_posts if p.get("status") in ["resolved", "closed"]]

    return templates.TemplateResponse(
        "users/my_posts.html",
        {
            "request": request,
            "title": "我的求助单",
            "user": user,
            "pending_posts": pending_posts,
            "resolved_posts": resolved_posts,
        },
    )


@router.get("/my-orders", response_class=HTMLResponse)
async def my_orders_page(request: Request, user: dict = Depends(require_auth)):
    """我接的单子页面"""
    if user.get("user_role") not in ["solver", "both"]:
        return RedirectResponse(url="/users/profile", status_code=303)

    from src.responses.service import ResponseService

    # 获取解决者接的所有单子
    responses, total = ResponseService.get_solver_responses(user["id"], limit=100)
    # 分类：进行中（包括已接单和审核中）和已完成
    in_progress = [r for r in responses if r.get("status") in ["accepted", "pending_review"]]
    completed = [r for r in responses if r.get("status") == "completed"]

    return templates.TemplateResponse(
        "users/my_orders.html",
        {
            "request": request,
            "title": "我接的单子",
            "user": user,
            "in_progress": in_progress,
            "completed": completed,
        },
    )


@router.post("/profile")
async def update_profile(
    request: Request,
    nickname: str = Form(...),
    bio: str = Form(None),
    phone: str = Form(None),
    wechat_id: str = Form(None),
    user: dict = Depends(require_auth),
):
    """更新个人资料"""
    # 调试：打印接收到的数据
    print(f"[ProfileUpdate] User: {user.get('email')}, Role: {user.get('user_role')}")
    print(f"[ProfileUpdate] Nickname: '{nickname}', WeChat ID: '{wechat_id}', Bio: '{bio}', Phone: '{phone}'")

    # 验证微信号（solver和both角色必填）
    if user.get("user_role") in ["solver", "both"]:
        if not wechat_id or not wechat_id.strip():
            error = "解决者必须填写微信号，用于与求助者沟通"
            print(f"[ProfileUpdate] Validation failed: WeChat ID is empty")
            if request.headers.get("HX-Request"):
                return templates.TemplateResponse(
                    "users/partials/profile_form.html",
                    {"request": request, "user": user, "error": error},
                    status_code=200,
                )
            return templates.TemplateResponse(
                "users/profile.html",
                {"request": request, "title": "个人资料", "user": user, "error": error},
                status_code=400,
            )

    # 演示模式
    if settings.is_demo_mode:
        from src.core.mock_data import MOCK_USERS, save_users

        if user["id"] in MOCK_USERS:
            MOCK_USERS[user["id"]]["nickname"] = nickname
            MOCK_USERS[user["id"]]["bio"] = bio
            MOCK_USERS[user["id"]]["phone"] = phone
            MOCK_USERS[user["id"]]["wechat_id"] = wechat_id
            save_users()

        # 更新 user 对象
        user["nickname"] = nickname
        user["bio"] = bio
        user["phone"] = phone
        user["wechat_id"] = wechat_id

        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "users/partials/profile_form.html",
                {"request": request, "user": user, "success": "资料更新成功"},
            )

        return RedirectResponse(url="/users/profile?updated=true", status_code=303)

    # Supabase 模式
    supabase = get_supabase_client()

    try:
        supabase.table("profiles").update({
            "nickname": nickname,
            "bio": bio,
            "phone": phone,
            "wechat_id": wechat_id,
        }).eq("id", user["id"]).execute()

        # 更新 user 对象
        user["nickname"] = nickname
        user["bio"] = bio
        user["phone"] = phone
        user["wechat_id"] = wechat_id

        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "users/partials/profile_form.html",
                {"request": request, "user": user, "success": "资料更新成功"},
            )

        return RedirectResponse(url="/users/profile?updated=true", status_code=303)

    except Exception as e:
        error = f"更新失败: {str(e)}"
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "users/partials/profile_form.html",
                {"request": request, "user": user, "error": error},
                status_code=200,
            )
        return templates.TemplateResponse(
            "users/profile.html",
            {"request": request, "title": "个人资料", "user": user, "error": error},
            status_code=400,
        )


@router.get("/solver/profile", response_class=HTMLResponse)
async def solver_profile_page(request: Request, user: dict = Depends(require_auth)):
    """解决者资料页面"""
    if user.get("user_role") not in ["solver", "both"]:
        return RedirectResponse(url="/users/profile", status_code=303)

    # 获取解决者资料
    supabase = get_supabase_client()
    result = supabase.table("solver_profiles").select("*").eq("user_id", user["id"]).single().execute()
    solver_profile = result.data if result.data else {}

    return templates.TemplateResponse(
        "users/solver_profile.html",
        {"request": request, "title": "解决者资料", "user": user, "solver_profile": solver_profile},
    )


@router.post("/solver/profile")
async def update_solver_profile(
    request: Request,
    experience_years: int = Form(None),
    expertise_areas: str = Form(None),
    resume: str = Form(None),
    hourly_rate: float = Form(None),
    is_available: bool = Form(True),
    user: dict = Depends(require_auth),
):
    """更新解决者资料"""
    if user.get("user_role") not in ["solver", "both"]:
        return RedirectResponse(url="/users/profile", status_code=303)

    supabase = get_supabase_client()

    # 处理擅长领域（逗号分隔转数组）
    areas_list = [a.strip() for a in expertise_areas.split(",")] if expertise_areas else []

    try:
        supabase.table("solver_profiles").update({
            "experience_years": experience_years,
            "expertise_areas": areas_list,
            "resume": resume,
            "hourly_rate": hourly_rate,
            "is_available": is_available,
        }).eq("user_id", user["id"]).execute()

        return RedirectResponse(url="/users/solver/profile?updated=true", status_code=303)

    except Exception as e:
        return templates.TemplateResponse(
            "users/solver_profile.html",
            {"request": request, "title": "解决者资料", "user": user, "error": str(e)},
            status_code=400,
        )


@router.post("/bind/email")
async def bind_email(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    user: dict = Depends(require_auth),
):
    """绑定邮箱"""
    # 验证密码
    if password != password_confirm:
        return RedirectResponse(url="/users/profile?error=passwords_not_match", status_code=303)

    if len(password) < 6:
        return RedirectResponse(url="/users/profile?error=password_too_short", status_code=303)

    if settings.is_demo_mode:
        from src.core.mock_data import MOCK_USERS

        # 检查邮箱是否已被使用
        for u in MOCK_USERS.values():
            if u.get("email") == email and u["id"] != user["id"]:
                return RedirectResponse(url="/users/profile?error=email_exists", status_code=303)

        # 更新用户邮箱和密码
        if user["id"] in MOCK_USERS:
            MOCK_USERS[user["id"]]["email"] = email
            MOCK_USERS[user["id"]]["password_hash"] = hashlib.sha256(password.encode()).hexdigest()

        # 创建邮箱身份绑定
        UserIdentityService.create_identity(
            user_id=user["id"],
            provider=UserIdentityService.PROVIDER_EMAIL,
            provider_user_id=email,
        )

        return RedirectResponse(url="/users/profile?bind_success=true", status_code=303)

    # Supabase模式 - 待实现
    return RedirectResponse(url="/users/profile?error=not_implemented", status_code=303)


@router.post("/unbind/wechat")
async def unbind_wechat(
    request: Request,
    user: dict = Depends(require_auth),
):
    """解绑微信"""
    # 必须有邮箱才能解绑微信
    if not user.get("email"):
        return RedirectResponse(url="/users/profile?error=need_email_first", status_code=303)

    # 查找微信绑定
    identities = UserIdentityService.get_user_identities(user["id"])
    wechat_identity = None
    for identity in identities:
        if identity.get("provider") == "wechat":
            wechat_identity = identity
            break

    if not wechat_identity:
        return RedirectResponse(url="/users/profile?error=no_wechat_binding", status_code=303)

    # 删除绑定
    UserIdentityService.delete_identity(wechat_identity["id"])

    return RedirectResponse(url="/users/profile?unbind_success=true", status_code=303)


@router.get("/{user_id}", response_class=HTMLResponse)
async def view_user_profile(
    request: Request,
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    """查看他人资料"""
    supabase = get_supabase_client()

    # 获取用户资料
    result = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
    if not result.data:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "title": "用户不存在"},
            status_code=404,
        )

    profile = result.data

    # 如果是解决者，获取解决者资料
    solver_profile = None
    if profile.get("user_role") in ["solver", "both"]:
        solver_result = supabase.table("solver_profiles").select("*").eq("user_id", user_id).single().execute()
        solver_profile = solver_result.data if solver_result.data else None

    return templates.TemplateResponse(
        "users/view_profile.html",
        {
            "request": request,
            "title": f"{profile['nickname']}的资料",
            "user": current_user,
            "profile": profile,
            "solver_profile": solver_profile,
        },
    )
