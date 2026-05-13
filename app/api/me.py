"""נקודות API למשתמש המחובר - watchlist + העדפות."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import select

from app.auth.deps import current_user
from app.auth.plans import limits_for, PLANS
from app.storage import User, UserWatchlist, get_session

router = APIRouter(prefix="/api/me", tags=["me"])


class WatchlistItemOut(BaseModel):
    symbol: str
    note: Optional[str] = None
    added_at: datetime


class WatchlistAddIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=8)
    note: Optional[str] = Field(default=None, max_length=140)


class WatchlistBulkIn(BaseModel):
    symbols: list[str]


def _norm(sym: str) -> str:
    return (sym or "").strip().upper()


def _valid_symbol(sym: str) -> bool:
    """אפשר אותיות, ספרות ונקודה (לדוגמה POLI.TA, BRK.B)."""
    if not sym or len(sym) > 10:
        return False
    import re
    return bool(re.match(r"^[A-Z]{1,6}(\.[A-Z]{1,3})?$", sym))


@router.get("/watchlist", response_model=list[WatchlistItemOut])
def list_watchlist(user: User = Depends(current_user)):
    with get_session() as session:
        rows = list(session.exec(
            select(UserWatchlist)
            .where(UserWatchlist.user_id == user.id)
            .order_by(UserWatchlist.added_at.desc())
        ))
        return [WatchlistItemOut(symbol=r.symbol, note=r.note, added_at=r.added_at) for r in rows]


@router.post("/watchlist", response_model=WatchlistItemOut, status_code=status.HTTP_201_CREATED)
def add_watchlist(data: WatchlistAddIn, user: User = Depends(current_user)):
    sym = _norm(data.symbol)
    if not _valid_symbol(sym):
        raise HTTPException(status_code=400, detail="סמל לא תקין")
    plan = limits_for(user)

    with get_session() as session:
        existing = session.exec(
            select(UserWatchlist).where(
                UserWatchlist.user_id == user.id,
                UserWatchlist.symbol == sym,
            )
        ).first()
        if existing:
            return WatchlistItemOut(symbol=existing.symbol, note=existing.note, added_at=existing.added_at)

        # אכיפת מגבלת תוכנית
        if plan.watchlist_max > 0 and not user.is_admin:
            current_count = len(list(session.exec(
                select(UserWatchlist).where(UserWatchlist.user_id == user.id)
            )))
            if current_count >= plan.watchlist_max:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"הגעת למגבלת {plan.watchlist_max} מניות בתוכנית {plan.display_name}. שדרג ל-Pro להוספה נוספת.",
                )

        item = UserWatchlist(user_id=user.id, symbol=sym, note=data.note)
        session.add(item)
        session.flush()

        # יצירת התראות על חדשות עבר (24h) שמזכירות את המנייה
        from datetime import timedelta
        from app.storage import NewsItem
        from app.storage.repository import add_notification
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_news = list(session.exec(
            select(NewsItem).where(
                NewsItem.fetched_at >= cutoff,
                NewsItem.mentioned_symbols.is_not(None),
            ).limit(50)
        ))
        for ni in recent_news:
            if sym in (ni.mentioned_symbols or "").split(","):
                add_notification(
                    session,
                    kind="news",
                    title=f"📰 {sym}: חדשות מעקב חדשות",
                    message=ni.text[:200],
                    symbol=sym,
                    icon="📰",
                    user_id=user.id,
                )

        return WatchlistItemOut(symbol=item.symbol, note=item.note, added_at=item.added_at)


@router.delete("/watchlist/{symbol}")
def remove_watchlist(symbol: str, user: User = Depends(current_user)):
    sym = _norm(symbol)
    with get_session() as session:
        existing = session.exec(
            select(UserWatchlist).where(
                UserWatchlist.user_id == user.id,
                UserWatchlist.symbol == sym,
            )
        ).first()
        if not existing:
            raise HTTPException(status_code=404, detail="לא ב-watchlist")
        session.delete(existing)
    return {"ok": True}


class PlanInfoOut(BaseModel):
    name: str
    display_name: str
    watchlist_max: int
    watchlist_used: int
    can_manual_scan: bool
    can_custom_strategy: bool
    can_export: bool
    notifications_history_days: int
    monthly_price_ils: int


@router.get("/plan", response_model=PlanInfoOut)
def my_plan(user: User = Depends(current_user)):
    plan = limits_for(user)
    with get_session() as session:
        used = len(list(session.exec(
            select(UserWatchlist).where(UserWatchlist.user_id == user.id)
        )))
    return PlanInfoOut(
        name=plan.name,
        display_name=plan.display_name,
        watchlist_max=plan.watchlist_max,
        watchlist_used=used,
        can_manual_scan=plan.can_manual_scan,
        can_custom_strategy=plan.can_custom_strategy,
        can_export=plan.can_export,
        notifications_history_days=plan.notifications_history_days,
        monthly_price_ils=plan.monthly_price_ils,
    )


@router.get("/plans/all")
def all_plans():
    """רשימת התוכניות הזמינות - לדף שדרוג."""
    return [
        {
            "name": p.name,
            "display_name": p.display_name,
            "watchlist_max": p.watchlist_max,
            "can_manual_scan": p.can_manual_scan,
            "can_custom_strategy": p.can_custom_strategy,
            "can_export": p.can_export,
            "notifications_history_days": p.notifications_history_days,
            "monthly_price_ils": p.monthly_price_ils,
        }
        for p in PLANS.values()
    ]


class WatchlistPerfItem(BaseModel):
    symbol: str
    name: Optional[str] = None
    price: Optional[float] = None
    day_change_pct: Optional[float] = None
    week_change_pct: Optional[float] = None
    month_change_pct: Optional[float] = None
    rsi: Optional[float] = None
    above_ma20: Optional[bool] = None
    error: Optional[str] = None


class AnalyticsOut(BaseModel):
    total_symbols: int
    avg_day_change_pct: Optional[float] = None
    avg_week_change_pct: Optional[float] = None
    avg_month_change_pct: Optional[float] = None
    best_day: Optional[WatchlistPerfItem] = None
    worst_day: Optional[WatchlistPerfItem] = None
    items: list[WatchlistPerfItem]


def _compute_perf(symbol: str) -> WatchlistPerfItem:
    """מחשב ביצועים לסמל בודד ע"י yfinance."""
    try:
        import yfinance as yf
        import pandas as pd

        t = yf.Ticker(symbol)
        hist = t.history(period="3mo")
        if hist is None or hist.empty:
            return WatchlistPerfItem(symbol=symbol, error="no data")

        close = hist["Close"]
        last = float(close.iloc[-1])
        # day change
        day_chg = None
        if len(close) >= 2:
            prev = float(close.iloc[-2])
            if prev > 0:
                day_chg = ((last - prev) / prev) * 100
        # week change (5 trading days back)
        week_chg = None
        if len(close) >= 6:
            ago = float(close.iloc[-6])
            if ago > 0:
                week_chg = ((last - ago) / ago) * 100
        # month change (~21 trading days)
        month_chg = None
        if len(close) >= 22:
            ago = float(close.iloc[-22])
            if ago > 0:
                month_chg = ((last - ago) / ago) * 100
        # RSI 14
        rsi_val = None
        try:
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss.replace(0, pd.NA)
            rsi_series = 100 - (100 / (1 + rs))
            rsi_val = float(rsi_series.iloc[-1]) if pd.notna(rsi_series.iloc[-1]) else None
        except Exception:
            pass
        # MA20
        above_ma = None
        if len(close) >= 20:
            ma20 = close.rolling(20).mean().iloc[-1]
            if pd.notna(ma20):
                above_ma = bool(last > float(ma20))
        # name
        name = None
        try:
            info = t.fast_info
            name = info.get("longName") or info.get("shortName")
        except Exception:
            pass

        return WatchlistPerfItem(
            symbol=symbol,
            name=name,
            price=round(last, 2),
            day_change_pct=round(day_chg, 2) if day_chg is not None else None,
            week_change_pct=round(week_chg, 2) if week_chg is not None else None,
            month_change_pct=round(month_chg, 2) if month_chg is not None else None,
            rsi=round(rsi_val, 1) if rsi_val is not None else None,
            above_ma20=above_ma,
        )
    except Exception as e:
        return WatchlistPerfItem(symbol=symbol, error=str(e)[:100])


@router.get("/analytics", response_model=AnalyticsOut)
def watchlist_analytics(user: User = Depends(current_user)):
    """ביצועים אגרגטיביים של ה-Watchlist."""
    with get_session() as session:
        symbols = [
            r.symbol for r in session.exec(
                select(UserWatchlist).where(UserWatchlist.user_id == user.id)
            )
        ]

    items = [_compute_perf(s) for s in symbols]
    valid = [i for i in items if i.error is None and i.day_change_pct is not None]

    def avg(field: str) -> Optional[float]:
        vals = [getattr(i, field) for i in valid if getattr(i, field) is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    best = max(valid, key=lambda i: i.day_change_pct, default=None) if valid else None
    worst = min(valid, key=lambda i: i.day_change_pct, default=None) if valid else None

    return AnalyticsOut(
        total_symbols=len(items),
        avg_day_change_pct=avg("day_change_pct"),
        avg_week_change_pct=avg("week_change_pct"),
        avg_month_change_pct=avg("month_change_pct"),
        best_day=best,
        worst_day=worst,
        items=items,
    )


@router.post("/watchlist/sync")
def sync_watchlist(data: WatchlistBulkIn, user: User = Depends(current_user)):
    """איחוד עם רשימה קיימת + אכיפת מגבלת תוכנית.

    אם המשתמש הוא FREE ויש לו 3 ב-DB, וברשימה שולחים 10 חדשים -
    נוסיף רק 2 (להגיע ל-5). מחזיר added + truncated.
    """
    added = 0
    truncated = 0
    plan = limits_for(user)
    max_allowed = plan.watchlist_max  # 0 = unlimited
    with get_session() as session:
        existing_syms = {
            r.symbol for r in session.exec(
                select(UserWatchlist).where(UserWatchlist.user_id == user.id)
            )
        }
        current_count = len(existing_syms)
        for raw in data.symbols:
            sym = _norm(raw)
            if not _valid_symbol(sym) or sym in existing_syms:
                continue
            # אכיפת מגבלה
            if max_allowed > 0 and not user.is_admin and current_count >= max_allowed:
                truncated += 1
                continue
            session.add(UserWatchlist(user_id=user.id, symbol=sym))
            existing_syms.add(sym)
            current_count += 1
            added += 1
    return {
        "ok": True,
        "added": added,
        "truncated": truncated,
        "plan_limit": max_allowed,
    }
