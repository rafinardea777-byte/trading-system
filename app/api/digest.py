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


def _engagement_from(item: NewsItem) -> float:
    """ניקוד מעורבות - מתוך הטקסט עצמו (Reddit upvotes נמצאים בכותרת)."""
    text = item.text
    score = 1.0
    # Reddit: [👍 6763 | 💬 245]
    m = re.search(r"👍\s*(\d+)", text)
    if m:
        score += min(float(m.group(1)) / 500, 20)  # cap at 20
    m = re.search(r"💬\s*(\d+)", text)
    if m:
        score += min(float(m.group(1)) / 100, 10)  # cap at 10
    # StockTwits Bullish/Bearish - boost slightly
    if "📈" in text or "📉" in text:
        score += 2
    return score


def _primary_symbol(item: NewsItem) -> Optional[str]:
    """בוחר את הסמל הראשי של פריט (אם יש כמה, הכי קצר)."""
    if not item.mentioned_symbols:
        return None
    syms = [s for s in item.mentioned_symbols.split(",") if s and s not in _BLACKLIST]
    if not syms:
        return None
    # מעדיף סמלים של 3-4 אותיות (הכי תקניים)
    syms.sort(key=lambda s: (len(s) not in (3, 4), len(s)))
    return syms[0]


def _pick_best_item(items: list[NewsItem]) -> NewsItem:
    """הפריט הכי מייצג בקבוצה: עדיף תרגום מלא, אחרת ה-engagement הגבוה."""
    by_score = sorted(
        items,
        key=lambda i: (
            1 if i.hebrew_translation else 0,
            _engagement_from(i),
            i.fetched_at,
        ),
        reverse=True,
    )
    return by_score[0]


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

    with get_session() as session:
        rows = list(session.exec(
            select(NewsItem)
            .where(NewsItem.fetched_at >= cutoff)
            .order_by(NewsItem.fetched_at.desc())
        ))

        wl_set: set[str] = set()
        if user:
            wl_set = {
                r.symbol for r in session.exec(
                    select(UserWatchlist).where(UserWatchlist.user_id == user.id)
                )
            }

    # קיבוץ לפי symbol (None = "כללי")
    groups: dict[Optional[str], list[NewsItem]] = defaultdict(list)
    for r in rows:
        sym = _primary_symbol(r)
        groups[sym].append(r)

    # בנה DigestGroup לכל קבוצה
    digest_groups: list[DigestGroup] = []
    for sym, items in groups.items():
        if not items:
            continue

        sources = list({i.source for i in items})
        top = _pick_best_item(items)
        latest = max(items, key=lambda i: i.fetched_at).fetched_at

        # סנטימנט מאוחד
        sentiments = [_sentiment_for_text(i.text) for i in items]
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

        # ציון engagement
        eng = sum(_engagement_from(i) for i in items)

        is_wl = sym is not None and sym in wl_set

        # ציון חשיבות סופי
        importance = len(sources) * 3 + min(eng, 30) + (15 if is_wl else 0)

        digest_groups.append((importance, DigestGroup(
            symbol=sym,
            headline_count=len(items),
            sources=sorted(sources),
            top_item=DigestItem(
                id=top.id, source=top.source, author=top.author,
                text=top.text, hebrew_translation=top.hebrew_translation,
                hebrew_explanation=top.hebrew_explanation,
                url=top.url, fetched_at=top.fetched_at,
            ),
            sentiment=sentiment,
            engagement_score=round(eng, 1),
            is_watchlist=is_wl,
            latest_at=latest,
            items=[
                DigestItem(
                    id=i.id, source=i.source, author=i.author,
                    text=i.text, hebrew_translation=i.hebrew_translation,
                    hebrew_explanation=i.hebrew_explanation,
                    url=i.url, fetched_at=i.fetched_at,
                ) for i in sorted(items, key=lambda x: x.fetched_at, reverse=True)
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
