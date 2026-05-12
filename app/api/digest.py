"""חדשות מרוכזות - קיבוץ לפי מנייה + ניקוד חשיבות."""
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import select

from app.auth.deps import optional_user
from app.scanners.news.symbols import _BLACKLIST
from app.storage import NewsItem, User, UserWatchlist, get_session

router = APIRouter(prefix="/api/news", tags=["news"])


class DigestItem(BaseModel):
    id: int
    source: str
    author: str
    text: str
    hebrew_translation: Optional[str] = None
    hebrew_explanation: Optional[str] = None
    url: str
    fetched_at: datetime


class DigestGroup(BaseModel):
    symbol: Optional[str]
    headline_count: int
    sources: list[str]
    top_item: DigestItem
    sentiment: str  # bullish | bearish | mixed | neutral
    engagement_score: float
    is_watchlist: bool
    latest_at: datetime
    items: list[DigestItem]


_BULL_RE = re.compile(r"📈|bullish|surge|soar|rally|jump|rocket|beat|crush|smash|record|high|strong",
                      re.IGNORECASE)
_BEAR_RE = re.compile(r"📉|bearish|plunge|tumble|crash|drop|miss|disappoint|weak|fall|sink|tank|recession",
                      re.IGNORECASE)


def _sentiment_for_text(text: str) -> str:
    bull = len(_BULL_RE.findall(text))
    bear = len(_BEAR_RE.findall(text))
    if bull > bear:
        return "bullish"
    if bear > bull:
        return "bearish"
    return "neutral"


def _engagement_from(item: dict) -> float:
    """ניקוד מעורבות - מתוך הטקסט עצמו (Reddit upvotes נמצאים בכותרת)."""
    text = item.get("text", "")
    score = 1.0
    m = re.search(r"👍\s*(\d+)", text)
    if m:
        score += min(float(m.group(1)) / 500, 20)
    m = re.search(r"💬\s*(\d+)", text)
    if m:
        score += min(float(m.group(1)) / 100, 10)
    if "📈" in text or "📉" in text:
        score += 2
    return score


def _primary_symbol_dict(item: dict) -> Optional[str]:
    """בוחר את הסמל הראשי של פריט (אם יש כמה, הכי קצר)."""
    syms_str = item.get("mentioned_symbols")
    if not syms_str:
        return None
    syms = [s for s in syms_str.split(",") if s and s not in _BLACKLIST]
    if not syms:
        return None
    syms.sort(key=lambda s: (len(s) not in (3, 4), len(s)))
    return syms[0]


def _pick_best_item(items: list[dict]) -> dict:
    return sorted(
        items,
        key=lambda i: (
            1 if i.get("hebrew_translation") else 0,
            _engagement_from(i),
            i.get("fetched_at") or datetime.min,
        ),
        reverse=True,
    )[0]


@router.get("/digest", response_model=list[DigestGroup])
def news_digest(
    hours_back: int = Query(24, ge=1, le=24 * 7),
    limit: int = Query(25, ge=1, le=100),
    watchlist_first: bool = Query(True),
    user: Optional[User] = Depends(optional_user),
):
    """מחזיר קבוצות חדשות לפי מנייה - הכי חשובות בראש.

    אלגוריתם:
    1. קבץ news מ-N שעות אחרונות לפי primary symbol
    2. חשב לכל קבוצה: # מקורות, סנטימנט, engagement
    3. ניקוד חשיבות = sources_count*3 + engagement + watchlist_bonus
    4. החזר top N בסדר יורד
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours_back)

    # נטען את כל המידע הנדרש בתוך ה-session ונחלץ ל-dicts לפני שהוא נסגר
    plain_rows: list[dict] = []
    wl_set: set[str] = set()
    with get_session() as session:
        for r in session.exec(
            select(NewsItem)
            .where(NewsItem.fetched_at >= cutoff)
            .order_by(NewsItem.fetched_at.desc())
        ):
            plain_rows.append({
                "id": r.id, "source": r.source, "author": r.author,
                "text": r.text, "url": r.url or "",
                "hebrew_translation": r.hebrew_translation,
                "hebrew_explanation": r.hebrew_explanation,
                "fetched_at": r.fetched_at,
                "mentioned_symbols": r.mentioned_symbols,
            })
        if user:
            wl_set = {
                r.symbol for r in session.exec(
                    select(UserWatchlist).where(UserWatchlist.user_id == user.id)
                )
            }

    # קיבוץ לפי symbol (None = "כללי")
    groups: dict[Optional[str], list[dict]] = defaultdict(list)
    for r in plain_rows:
        sym = _primary_symbol_dict(r)
        groups[sym].append(r)

    # בנה DigestGroup לכל קבוצה
    digest_groups: list = []
    for sym, items in groups.items():
        if not items:
            continue

        sources = list({i["source"] for i in items})
        top = _pick_best_item(items)
        latest = max(items, key=lambda i: i["fetched_at"])["fetched_at"]

        # סנטימנט מאוחד
        sentiments = [_sentiment_for_text(i["text"]) for i in items]
        bull = sentiments.count("bullish")
        bear = sentiments.count("bearish")
        if bull > bear and bull >= 2:
            sentiment = "bullish"
        elif bear > bull and bear >= 2:
            sentiment = "bearish"
        elif bull and bear:
            sentiment = "mixed"
        else:
            sentiment = "neutral"

        eng = sum(_engagement_from(i) for i in items)
        is_wl = sym is not None and sym in wl_set
        importance = len(sources) * 3 + min(eng, 30) + (15 if is_wl else 0)

        digest_groups.append((importance, DigestGroup(
            symbol=sym,
            headline_count=len(items),
            sources=sorted(sources),
            top_item=DigestItem(**{k: top[k] for k in ("id","source","author","text","hebrew_translation","hebrew_explanation","url","fetched_at")}),
            sentiment=sentiment,
            engagement_score=round(eng, 1),
            is_watchlist=is_wl,
            latest_at=latest,
            items=[
                DigestItem(**{k: i[k] for k in ("id","source","author","text","hebrew_translation","hebrew_explanation","url","fetched_at")})
                for i in sorted(items, key=lambda x: x["fetched_at"], reverse=True)
            ][:8],
        )))

    # מיון: watchlist קודם (אם ביקשו), אחרת importance
    if watchlist_first:
        digest_groups.sort(
            key=lambda x: (-1 if x[1].is_watchlist else 0, -x[0])
        )
    else:
        digest_groups.sort(key=lambda x: -x[0])

    return [g for _, g in digest_groups[:limit]]
