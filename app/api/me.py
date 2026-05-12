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
    if not sym.isalpha():
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


@router.post("/watchlist/sync")
def sync_watchlist(data: WatchlistBulkIn, user: User = Depends(current_user)):
    """איחוד עם רשימה קיימת - מוסיף סמלים שעדיין לא בשרת. שימושי לסנכרון מ-localStorage."""
    added = 0
    with get_session() as session:
        existing_syms = {
            r.symbol for r in session.exec(
                select(UserWatchlist).where(UserWatchlist.user_id == user.id)
            )
        }
        for raw in data.symbols:
            sym = _norm(raw)
            if not sym.isalpha() or len(sym) > 8 or sym in existing_syms:
                continue
            session.add(UserWatchlist(user_id=user.id, symbol=sym))
            existing_syms.add(sym)
            added += 1
    return {"ok": True, "added": added}
