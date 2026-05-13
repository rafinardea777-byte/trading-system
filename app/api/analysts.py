"""המלצות אנליסטים - אגרגציה ממניות פופולריות + watchlist המשתמש."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import select

from app.auth.deps import optional_user
from app.core.logging import get_logger
from app.storage import User, UserWatchlist, get_session

log = get_logger(__name__)

# קאש פשוט - 30 דקות (אנליסטים לא משנים המלצות תוך יום בד"כ)
_CACHE: dict[str, tuple[datetime, list]] = {}
_CACHE_TTL = timedelta(minutes=30)

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
    """ממיר recommendations של yfinance ל-list. עם cache של 30 דקות."""
    # בדיקת cache
    cache_key = f"{symbol}:{max_age_days}"
    cached = _CACHE.get(cache_key)
    if cached and (datetime.utcnow() - cached[0]) < _CACHE_TTL:
        return cached[1]

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
        result = out[:5]
        _CACHE[cache_key] = (datetime.utcnow(), result)
        return result
    except Exception:
        _CACHE[cache_key] = (datetime.utcnow(), [])
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

    # מקבילי - עד 10 סמלים בו זמנית. רץ ~5-10x מהר מסדרתי
    all_recs: list[RecOut] = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch_recommendations, sym, days): sym for sym in symbols}
        for future in as_completed(futures):
            try:
                all_recs.extend(future.result(timeout=15))
            except Exception as e:
                log.debug("analyst_fetch_failed", symbol=futures[future], error=str(e))

    # מיון - חדש קודם
    all_recs.sort(key=lambda r: r.date, reverse=True)
    return all_recs[:limit]
