"""StockTwits scanner - API חינמי, ממוקד פיננסים, $TICKER בכל מקום."""
from datetime import datetime, timezone
from typing import Optional

import requests

from app.core.logging import get_logger
from app.scanners.news.filter import is_us_market_related

log = get_logger(__name__)

_BASE = "https://api.stocktwits.com/api/2"
_TIMEOUT = 8
_HEADERS = {"User-Agent": "Mozilla/5.0 TradingProBot/1.0"}


def fetch_trending(max_messages: int = 60) -> list[dict]:
    """ציוצים מ-trending stream של StockTwits - השיחות החמות עכשיו."""
    out: list[dict] = []
    try:
        url = f"{_BASE}/streams/trending.json"
        r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        if r.status_code != 200:
            log.warning("stocktwits_trending_failed", status=r.status_code)
            return out
        data = r.json()
        msgs = data.get("messages", []) or []
        for m in msgs[:max_messages]:
            try:
                out.append(_normalize_message(m, source="stocktwits"))
            except Exception as e:
                log.debug("stocktwits_normalize_failed", error=str(e))
    except Exception as e:
        log.warning("stocktwits_fetch_failed", error=str(e))
    return out


def fetch_for_symbol(symbol: str, max_messages: int = 20) -> list[dict]:
    """ציוצים על סמל מסוים."""
    out: list[dict] = []
    try:
        url = f"{_BASE}/streams/symbol/{symbol}.json"
        r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        if r.status_code != 200:
            return out
        data = r.json()
        msgs = data.get("messages", []) or []
        for m in msgs[:max_messages]:
            try:
                item = _normalize_message(m, source="stocktwits")
                # סמן את הסמל המבוקש כקיים גם אם לא נמצא במלל
                item.setdefault("forced_symbol", symbol)
                out.append(item)
            except Exception:
                continue
    except Exception as e:
        log.debug("stocktwits_symbol_failed", symbol=symbol, error=str(e))
    return out


def fetch_watchlist_streams(symbols: list[str], per_symbol: int = 5) -> list[dict]:
    """ציוצים על מניות ספציפיות. limit נמוך כדי לא לחרוג מ-rate."""
    out: list[dict] = []
    for sym in symbols[:20]:  # מקסימום 20 כדי לא להתבזבז
        items = fetch_for_symbol(sym, max_messages=per_symbol)
        out.extend(items)
    return out


def _normalize_message(m: dict, source: str) -> dict:
    """ממיר message של StockTwits לפורמט אחיד."""
    mid = m.get("id")
    body = (m.get("body") or "").strip()
    user = m.get("user") or {}
    username = user.get("username") or "stocktwits"
    created = m.get("created_at")
    if created:
        try:
            published = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except Exception:
            published = datetime.now(timezone.utc)
    else:
        published = datetime.now(timezone.utc)

    # סנטימנט אם יש
    sentiment_obj = m.get("entities", {}).get("sentiment") or {}
    sent = (sentiment_obj or {}).get("basic", "") if isinstance(sentiment_obj, dict) else ""

    # סמלים שצוינו
    symbols = m.get("symbols") or []
    sym_list = [(s.get("symbol") or "").upper() for s in symbols if s.get("symbol")]

    url = f"https://stocktwits.com/{username}/message/{mid}" if mid else "https://stocktwits.com"

    suffix = ""
    if sent == "Bullish":
        suffix = " [📈 Bullish]"
    elif sent == "Bearish":
        suffix = " [📉 Bearish]"

    return {
        "external_id": f"stocktwits:{mid}",
        "source": source,
        "author": f"st:{username}",
        "text": (body + suffix)[:500],
        "url": url,
        "published_at": published,
        "extra_symbols": sym_list,  # נשתמש בזה ב-service כתוספת לחילוץ
    }


def fetch_stocktwits(
    hours_back: int = 24,
    user_watchlist_symbols: Optional[list[str]] = None,
) -> list[dict]:
    """נקודת כניסה - מחזיר רשימת פריטים מאוחדת."""
    items = fetch_trending(max_messages=50)
    if user_watchlist_symbols:
        items += fetch_watchlist_streams(user_watchlist_symbols, per_symbol=4)

    # סינון: רק פוסטים עם תוכן שוק אמריקאי או שמזכירים סמל
    filtered = [
        i for i in items
        if i.get("extra_symbols") or i.get("forced_symbol") or is_us_market_related(i["text"])
    ]
    log.info("stocktwits_fetch_done", total=len(items), filtered=len(filtered))
    return filtered
