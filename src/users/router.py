from pathlib import Path
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.auth.dependencies import get_current_user, require_auth
from src.core.supabase import get_supabase_client

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent.parent / "templates")


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user: dict = Depends(require_auth)):
    """个人资料页面"""
    return templates.TemplateResponse(
        "users/profile.html",
        {"request": request, "title": "个人资料", "user": user},
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
                status_code=400,
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
