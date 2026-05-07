"""נקודות API מערכתיות - הפעלת סריקות, בריאות, מצב."""
from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.schemas import JobResult
from app.core.config import settings
from app.core.security import require_admin

router = APIRouter(prefix="/api/system", tags=["system"])


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


@router.post("/scan/news", response_model=JobResult, dependencies=[Depends(require_admin)])
def trigger_news_scan(background: BackgroundTasks):
    """מפעיל סריקת חדשות ברקע (admin only ב-public_mode)."""
    from app.scanners.news import run_news_scan

    background.add_task(run_news_scan)
    return JobResult(ok=True, detail={"queued": "news_scan"})


@router.post("/scan/market", response_model=JobResult, dependencies=[Depends(require_admin)])
def trigger_market_scan(background: BackgroundTasks, max_symbols: int | None = None):
    """מפעיל סריקת שוק ברקע (admin only ב-public_mode)."""
    from app.scanners.market import run_market_scan

    background.add_task(run_market_scan, max_symbols=max_symbols)
    return JobResult(ok=True, detail={"queued": "market_scan", "max_symbols": max_symbols})
