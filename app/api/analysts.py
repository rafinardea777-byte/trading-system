"""המלצות אנליסטים - אגרגציה ממניות פופולריות + watchlist המשתמש."""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import select

from app.auth.deps import optional_user
from app.storage import User, UserWatchlist, get_session

router = APIRouter(prefix="/api/analysts", tags=["analysts"])


# מניות פופולריות לבדיקה בכל פעם - מצומצם כדי לא לחנוק את yfinance
_TOP_WATCH = [
    "NVDA", "AAPL", "MSFT", "GOOG", "META", "AMZN", "TSLA", "AMD",
    "NFLX", "ARM", "AVGO", "TSM", "PLTR", "COIN", "MSTR",
    "SOFI", "HOOD", "JPM", "BAC", "GS", "XOM", "WMT", "DIS",
    "TEVA", "CHKP", "NICE", "WIX", "MNDY", "MRNA", "PFE",
]


class RecOut(BaseModel):
    symbol: str
    firm: Optional[str] = None
    to_grade: Optional[str] = None
    from_grade: Optional[str] = None
    action: Optional[str] = None
    date: datetime


def _fetch_recommendations(symbol: str, max_age_days: int = 7) -> list[RecOut]:
    """ממיר recommendations של yfinance ל-list."""
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        return []

    try:
        t = yf.Ticker(symbol)
        df = t.upgrades_downgrades
        if df is None or df.empty:
            return []

        # הnodef DataFrame עם MultiIndex לפעמים. ננרמל.
        df = df.reset_index() if df.index.name else df.copy()

        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        out = []
        for _, row in df.iterrows():
            try:
                d = row.get("GradeDate") or row.get("Date") or row.name
                if hasattr(d, "to_pydatetime"):
                    d = d.to_pydatetime()
                if not isinstance(d, datetime):
                    continue
                if d.tzinfo is not None:
                    d = d.replace(tzinfo=None)
                if d < cutoff:
                    continue
                out.append(RecOut(
                    symbol=symbol,
                    firm=str(row.get("Firm", "")) or None,
                    to_grade=str(row.get("ToGrade", "")) or None,
                    from_grade=str(row.get("FromGrade", "")) or None,
                    action=str(row.get("Action", "")) or None,
                    date=d,
                ))
            except Exception:
                continue
        return out[:5]
    except Exception:
        return []


@router.get("/recent", response_model=list[RecOut])
def recent_recommendations(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(40, ge=1, le=100),
    watchlist_first: bool = Query(True),
    user: Optional[User] = Depends(optional_user),
):
    """אוסף המלצות אנליסטים אחרונות מרשימה משולבת של top stocks + Watchlist המשתמש."""
    symbols: list[str] = []
    if user and watchlist_first:
        with get_session() as session:
            wl = [r.symbol for r in session.exec(
                select(UserWatchlist).where(UserWatchlist.user_id == user.id)
            )]
            symbols.extend(wl[:30])

    # מוסיף top watch ללא כפילויות
    for s in _TOP_WATCH:
        if s not in symbols:
            symbols.append(s)

    # מבטח שלא נסרוק יותר מ-30
    symbols = symbols[:30]

    all_recs: list[RecOut] = []
    for sym in symbols:
        all_recs.extend(_fetch_recommendations(sym, max_age_days=days))

    # מיון - חדש קודם
    all_recs.sort(key=lambda r: r.date, reverse=True)
    return all_recs[:limit]
