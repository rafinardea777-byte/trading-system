"""נקודות API לחדשות."""
from datetime import datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import select

from app.api.schemas import NewsOut
from app.auth.deps import optional_user
from app.storage import NewsItem, User, UserWatchlist, get_session
from app.storage.repository import get_news

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("", response_model=list[NewsOut])
def list_news(
    hours_back: int = Query(24, ge=1, le=24 * 7),
    limit: int = Query(100, ge=1, le=500),
    source: Optional[Literal["twitter", "rss", "stocktwits", "reddit"]] = Query(None),
    watchlist_only: bool = Query(False, description="רק חדשות שמזכירות מניות מה-watchlist"),
    symbol: Optional[str] = Query(None, max_length=10, description="סנן רק חדשות שמזכירות סמל זה"),
    since_id: Optional[int] = Query(None, description="רק חדשות שה-id שלהן גדול מהערך הזה"),
    user: Optional[User] = Depends(optional_user),
):
    with get_session() as session:
        # אם בקשה מסוננת ל-watchlist - דרוש משתמש מחובר עם פריטים ב-watchlist
        if watchlist_only:
            if not user:
                return []
            wl_syms = {
                r.symbol for r in session.exec(
                    select(UserWatchlist).where(UserWatchlist.user_id == user.id)
                )
            }
            if not wl_syms:
                return []

            cutoff = datetime.utcnow() - timedelta(hours=hours_back)
            stmt = select(NewsItem).where(
                NewsItem.fetched_at >= cutoff,
                NewsItem.mentioned_symbols.is_not(None),
            )
            if source:
                stmt = stmt.where(NewsItem.source == source)
            if since_id is not None:
                stmt = stmt.where(NewsItem.id > since_id)
            rows = list(session.exec(stmt.order_by(NewsItem.id.desc()).limit(limit)))
            # סנן ב-Python - הצלבה עם watchlist
            filtered = [
                r for r in rows
                if r.mentioned_symbols
                and any(s in wl_syms for s in r.mentioned_symbols.split(","))
            ]
            return [NewsOut.model_validate(r, from_attributes=True) for r in filtered]

        # זרם רגיל - או פילטר לפי symbol ספציפי
        if symbol:
            import re as _re
            sym = symbol.strip().upper()
            if not _re.match(r"^[A-Z]{1,6}(\.[A-Z]{1,3})?$", sym):
                return []
            cutoff = datetime.utcnow() - timedelta(hours=hours_back)
            stmt = select(NewsItem).where(
                NewsItem.fetched_at >= cutoff,
                NewsItem.mentioned_symbols.is_not(None),
                NewsItem.mentioned_symbols.contains(sym),
            )
            if source:
                stmt = stmt.where(NewsItem.source == source)
            if since_id is not None:
                stmt = stmt.where(NewsItem.id > since_id)
            rows = list(session.exec(stmt.order_by(NewsItem.id.desc()).limit(limit)))
            # ודא שהסמל באמת מופיע (contains יכול לתפוס substring - למשל "AAP" ב-"AAPL")
            filtered = [
                r for r in rows
                if r.mentioned_symbols and sym in r.mentioned_symbols.split(",")
            ]
            return [NewsOut.model_validate(r, from_attributes=True) for r in filtered]

        rows = get_news(session, hours_back=hours_back, limit=limit, source=source)
        if since_id is not None:
            rows = [r for r in rows if r.id > since_id]
        return [NewsOut.model_validate(r, from_attributes=True) for r in rows]
