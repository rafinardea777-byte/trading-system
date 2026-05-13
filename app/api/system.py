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


def require_authed_or_admin_key(
    user: Optional[User] = Depends(optional_user),
    x_admin_key: Optional[str] = Header(default=None),
):
    """סריקה ידנית: כל משתמש מחובר (כולל FREE), או Admin Key לחיצוני אנונימי.

    אנונימי לחלוטין נחסם כדי למנוע DDoS חיצוני.
    """
    if user:
        if user.is_admin or limits_for(user).can_manual_scan:
            return user
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="התוכנית שלך לא תומכת בסריקה ידנית",
        )
    # אנונימי - חובה Admin Key ב-public_mode
    if not settings.public_mode:
        return None
    if (
        x_admin_key
        and settings.admin_api_key
        and secrets.compare_digest(x_admin_key, settings.admin_api_key)
    ):
        return None
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="חובה להתחבר כדי להפעיל סריקה",
    )


@router.get("/health")
def health(user: Optional[User] = Depends(optional_user)):
    """מצב מערכת - כולל מצב שווקים. אדמין מקבל מידע מלא."""
    from app.scheduler.jobs import is_il_market_open, is_us_market_open
    base = {
        "status": "ok",
        "trading_mode": settings.trading_mode,
        "us_market_open": is_us_market_open(),
        "il_market_open": is_il_market_open(),
    }
    if (user and user.is_admin) or not settings.public_mode:
        return {
            **base,
            "env": settings.app_env,
            "use_x_api": settings.use_x_api,
            "use_openai": settings.use_openai,
            "telegram_alerts": settings.enable_telegram_alerts,
            "public_mode": settings.public_mode,
        }
    return base


@router.post("/scan/news", response_model=JobResult, dependencies=[Depends(require_authed_or_admin_key)])
def trigger_news_scan(background: BackgroundTasks):
    """מפעיל סריקת חדשות ברקע. Pro+ או admin key."""
    from app.scanners.news import run_news_scan

    background.add_task(run_news_scan)
    return JobResult(ok=True, detail={"queued": "news_scan"})


@router.post("/scan/market", response_model=JobResult, dependencies=[Depends(require_authed_or_admin_key)])
def trigger_market_scan(background: BackgroundTasks, max_symbols: int | None = None):
    """מפעיל סריקת שוק ברקע. Pro+ או admin key."""
    from app.scanners.market import run_market_scan

    background.add_task(run_market_scan, max_symbols=max_symbols)
    return JobResult(ok=True, detail={"queued": "market_scan", "max_symbols": max_symbols})


@router.post("/monitor/run", response_model=JobResult, dependencies=[Depends(require_authed_or_admin_key)])
def trigger_monitor(background: BackgroundTasks):
    """בודק את כל הסיגנלים הפתוחים וסוגר כשרלוונטי."""
    from app.scanners.market.monitor import check_open_signals

    background.add_task(check_open_signals)
    return JobResult(ok=True, detail={"queued": "monitor"})


@router.post("/scan/symbol/{symbol}", response_model=JobResult)
def trigger_single_symbol_scan(symbol: str, background: BackgroundTasks):
    """סריקה מהירה של סמל יחיד - שימושי אחרי הוספה ל-Watchlist."""
    import re as _re
    sym = symbol.strip().upper()
    if not _re.match(r"^[A-Z]{1,6}(\.[A-Z]{1,3})?$", sym):
        raise HTTPException(status_code=400, detail="invalid symbol")

    def _scan():
        from app.storage import get_session, Signal
        from app.storage.repository import upsert_signal, signal_exists_today
        from app.scanners.market.signal import evaluate_symbol
        from app.scheduler.jobs import is_symbol_market_open
        try:
            import yfinance as yf
            if not is_symbol_market_open(sym):
                return
            df = yf.Ticker(sym).history(period="60d")
            if df is None or df.empty:
                return
            tech = evaluate_symbol(sym, df)
            if not tech or tech.strength < settings.min_signal_strength:
                return
            with get_session() as session:
                if signal_exists_today(session, sym):
                    return
                sig = Signal(
                    symbol=tech.symbol, price=tech.price, rsi=tech.rsi,
                    volume_ratio=tech.volume_ratio, ma_fast=tech.ma_fast,
                    ma_slow=tech.ma_slow, strength=tech.strength,
                    target_1=tech.target_1, target_2=tech.target_2,
                    stop_loss=tech.stop_loss,
                )
                upsert_signal(session, sig)
        except Exception:
            pass

    background.add_task(_scan)
    return JobResult(ok=True, detail={"queued": "single_scan", "symbol": sym})
