"""
支付宝实名认证路由
"""
import uuid
import re
from pathlib import Path
from fastapi import APIRouter, Request, Form, Query, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.config import settings
from src.auth.dependencies import require_auth
from src.auth.alipay_verify import AlipayVerifyService, UserVerifyService

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent.parent / "templates")

# 存储认证会话（生产环境应使用Redis）
VERIFY_SESSIONS: dict = {}


def validate_id_card(id_card: str) -> bool:
    """验证身份证号格式"""
    pattern = r'^[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$'
    return bool(re.match(pattern, id_card))


def mask_name(name: str) -> str:
    """脱敏姓名"""
    if len(name) <= 1:
        return name
    return name[0] + "*" * (len(name) - 1)


@router.get("/verify", response_class=HTMLResponse)
async def verify_page(
    request: Request,
    user: dict = Depends(require_auth),
):
    """实名认证页面"""
    # 检查是否已认证
    if user.get("id_card_verified"):
        return templates.TemplateResponse(
            "auth/verify_success.html",
            {
                "request": request,
                "title": "实名认证",
                "user": user,
                "real_name": mask_name(user.get("real_name", "")),
                "message": "您已完成实名认证",
            }
        )

    # 检查支付宝是否配置
    alipay_configured = bool(settings.ALIPAY_APP_ID)

    return templates.TemplateResponse(
        "auth/verify_identity.html",
        {
            "request": request,
            "title": "实名认证",
            "user": user,
            "alipay_configured": alipay_configured,
        }
    )


@router.post("/verify/submit")
async def submit_verify(
    request: Request,
    real_name: str = Form(...),
    id_card: str = Form(...),
    user: dict = Depends(require_auth),
):
    """提交实名认证"""
    # 验证身份证格式
    if not validate_id_card(id_card):
        return templates.TemplateResponse(
            "auth/verify_identity.html",
            {
                "request": request,
                "title": "实名认证",
                "user": user,
                "error": "身份证号格式不正确",
                "alipay_configured": bool(settings.ALIPAY_APP_ID),
            },
            status_code=400,
        )

    # 验证姓名
    if not real_name or len(real_name) < 2:
        return templates.TemplateResponse(
            "auth/verify_identity.html",
            {
                "request": request,
                "title": "实名认证",
                "user": user,
                "error": "请输入有效的姓名",
                "alipay_configured": bool(settings.ALIPAY_APP_ID),
            },
            status_code=400,
        )

    # 检查是否配置了支付宝
    if not settings.ALIPAY_APP_ID:
        # 未配置支付宝时，测试环境下直接通过认证
        print(f"[Verify] Test mode: Auto-approve for {real_name}")
        success, error = UserVerifyService.update_verify_status(
            user_id=user["id"],
            real_name=real_name,
            verified=True,
        )
        if success:
            return RedirectResponse(url="/auth/verify/success", status_code=303)
        return templates.TemplateResponse(
            "auth/verify_identity.html",
            {
                "request": request,
                "title": "实名认证",
                "user": user,
                "error": error or "认证失败",
                "alipay_configured": False,
            },
            status_code=400,
        )

    # 生成订单号
    order_no = f"VERIFY_{user['id']}_{uuid.uuid4().hex[:8]}"

    # 初始化支付宝认证
    success, error, certify_id = await AlipayVerifyService.initialize_certify(
        outer_order_no=order_no,
        cert_name=real_name,
        cert_no=id_card,
    )

    if not success:
        return templates.TemplateResponse(
            "auth/verify_identity.html",
            {
                "request": request,
                "title": "实名认证",
                "user": user,
                "error": error,
                "alipay_configured": True,
            },
            status_code=400,
        )

    # 保存认证会话
    VERIFY_SESSIONS[certify_id] = {
        "user_id": user["id"],
        "real_name": real_name,
        "order_no": order_no,
    }

    # 获取认证URL并跳转
    certify_url = AlipayVerifyService.get_certify_url(certify_id)
    return RedirectResponse(url=certify_url, status_code=303)


@router.get("/verify/callback")
async def verify_callback(
    request: Request,
    certify_id: str = Query(None),
    user: dict = Depends(require_auth),
):
    """支付宝认证回调"""
    if not certify_id:
        return RedirectResponse(url="/auth/verify?error=认证参数无效", status_code=303)

    # 获取认证会话
    session = VERIFY_SESSIONS.pop(certify_id, None)
    if not session:
        return RedirectResponse(url="/auth/verify?error=认证会话已过期", status_code=303)

    # 验证用户
    if session["user_id"] != user["id"]:
        return RedirectResponse(url="/auth/verify?error=认证信息不匹配", status_code=303)

    # 查询认证结果
    success, error, result = await AlipayVerifyService.query_certify_result(certify_id)

    if not success:
        return templates.TemplateResponse(
            "auth/verify_failed.html",
            {
                "request": request,
                "title": "认证失败",
                "user": user,
                "error": error,
            }
        )

    if not result.get("passed"):
        return templates.TemplateResponse(
            "auth/verify_failed.html",
            {
                "request": request,
                "title": "认证失败",
                "user": user,
                "error": "身份验证未通过，请确认姓名和身份证号是否正确",
            }
        )

    # 更新用户认证状态
    success, error = UserVerifyService.update_verify_status(
        user_id=user["id"],
        real_name=session["real_name"],
        verified=True,
    )

    if not success:
        return templates.TemplateResponse(
            "auth/verify_failed.html",
            {
                "request": request,
                "title": "认证失败",
                "user": user,
                "error": error or "保存认证信息失败",
            }
        )

    return RedirectResponse(url="/auth/verify/success", status_code=303)


@router.get("/verify/success", response_class=HTMLResponse)
async def verify_success_page(
    request: Request,
    user: dict = Depends(require_auth),
):
    """认证成功页面"""
    # 重新获取用户信息以获取最新的认证状态
    success, error, verify_info = UserVerifyService.check_verify_status(user["id"])

    if not success or not verify_info.get("verified"):
        return RedirectResponse(url="/auth/verify", status_code=303)

    return templates.TemplateResponse(
        "auth/verify_success.html",
        {
            "request": request,
            "title": "认证成功",
            "user": user,
            "real_name": mask_name(verify_info.get("real_name", "")),
            "message": "恭喜！您已完成实名认证",
        }
    )
