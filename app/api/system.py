"""נקודות API מערכתיות - הפעלת סריקות, בריאות, מצב."""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.api.schemas import JobResult
from app.auth.deps import optional_user
from app.auth.plans import limits_for
from app.core.config import settings
from app.core.security import require_admin
from app.storage import User

router = APIRouter(prefix="/api/system", tags=["system"])


import secrets

from fastapi import Header


def require_pro_or_admin_key(
    user: Optional[User] = Depends(optional_user),
    x_admin_key: Optional[str] = Header(default=None),
):
    """מאפשר: (א) משתמש מחובר Pro+ או admin, (ב) X-Admin-Key תקין."""
    # משתמש Pro+ או admin
    if user and (user.is_admin or limits_for(user).can_manual_scan):
        return user
    # admin key מעוקף ב-public_mode=False (פיתוח)
    if not settings.public_mode:
        return None
    # public mode - בדוק admin key
    if (
        x_admin_key
        and settings.admin_api_key
        and secrets.compare_digest(x_admin_key, settings.admin_api_key)
    ):
        return None
    if user:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="סריקה ידנית זמינה למנויי Pro ומעלה",
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="חובה להתחבר או להזין מפתח admin",
    )


@router.get("/health")
def health():
    """מצב מערכת - חשיפת מפתחות מצומצמת ב-public_mode."""
    base = {"status": "ok", "trading_mode": settings.trading_mode}
    if settings.public_mode:
        return base
    return {
        **base,
        "env": settings.app_env,
        "use_x_api": settings.use_x_api,
        "use_openai": settings.use_openai,
        "telegram_alerts": settings.enable_telegram_alerts,
    }


@router.post("/scan/news", response_model=JobResult, dependencies=[Depends(require_pro_or_admin_key)])
def trigger_news_scan(background: BackgroundTasks):
    """מפעיל סריקת חדשות ברקע. Pro+ או admin key."""
    from app.scanners.news import run_news_scan

    background.add_task(run_news_scan)
    return JobResult(ok=True, detail={"queued": "news_scan"})


@router.post("/scan/market", response_model=JobResult, dependencies=[Depends(require_pro_or_admin_key)])
def trigger_market_scan(background: BackgroundTasks, max_symbols: int | None = None):
    """מפעיל סריקת שוק ברקע. Pro+ או admin key."""
    from app.scanners.market import run_market_scan

    background.add_task(run_market_scan, max_symbols=max_symbols)
    return JobResult(ok=True, detail={"queued": "market_scan", "max_symbols": max_symbols})
