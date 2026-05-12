"""Reddit scanner - r/wallstreetbets + r/stocks + r/investing. JSON ציבורי, ללא Auth."""
from datetime import datetime, timezone
from typing import Optional

import requests

from app.core.logging import get_logger
from app.scanners.news.filter import is_us_market_related

log = get_logger(__name__)

_TIMEOUT = 10
_HEADERS = {"User-Agent": "TradingProBot/1.0 (by /u/tradingpro)"}

# סאברדיטים פיננסיים
SUBREDDITS = [
    ("wallstreetbets", "WSB", 25, 200),     # subreddit, label, limit, min_upvotes
    ("stocks", "r/stocks", 15, 50),
    ("investing", "r/investing", 10, 30),
    ("StockMarket", "r/StockMarket", 10, 30),
]


def fetch_subreddit(subreddit: str, limit: int = 25, sort: str = "hot") -> list[dict]:
    """מביא פוסטים מסאברדיט. JSON ציבורי."""
    out = []
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
    try:
        r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        if r.status_code != 200:
            log.warning("reddit_fetch_failed", subreddit=subreddit, status=r.status_code)
            return out
        data = r.json()
        posts = data.get("data", {}).get("children", []) or []
        for p in posts:
            d = p.get("data") or {}
            if d.get("stickied"):
                continue  # דלג על pinned/announcements
            out.append(d)
    except Exception as e:
        log.warning("reddit_fetch_exception", subreddit=subreddit, error=str(e))
    return out


def _normalize_post(p: dict, sub_label: str) -> dict:
    title = (p.get("title") or "").strip()
    selftext = (p.get("selftext") or "").strip()
    score = p.get("score") or 0
    num_comments = p.get("num_comments") or 0
    author = p.get("author") or "reddit"
    permalink = p.get("permalink") or ""
    url = f"https://www.reddit.com{permalink}" if permalink else (p.get("url") or "")
    pid = p.get("id") or ""

    created = p.get("created_utc")
    if created:
        published = datetime.fromtimestamp(float(created), tz=timezone.utc)
    else:
        published = datetime.now(timezone.utc)

    # תקציר: title + 100 תווי selftext + score
    body_preview = ""
    if selftext:
        body_preview = " — " + selftext[:120].replace("\n", " ")
    text = f"[👍 {score} | 💬 {num_comments}] {title}{body_preview}"

    return {
        "external_id": f"reddit:{pid}",
        "source": "reddit",
        "author": f"{sub_label}:{author}",
        "text": text[:500],
        "url": url,
        "published_at": published,
        "score": score,
    }


def fetch_reddit(hours_back: int = 24) -> list[dict]:
    """מאגד פוסטים מכל הסאברדיטים הפיננסיים."""
    all_items: list[dict] = []
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    for sub, label, limit, min_score in SUBREDDITS:
        posts = fetch_subreddit(sub, limit=limit, sort="hot")
        for p in posts:
            score = p.get("score") or 0
            if score < min_score:
                continue
            item = _normalize_post(p, label)
            if item["published_at"] < cutoff:
                continue
            # סנן רק פוסטים שמזכירים שוק/סמל
            if not is_us_market_related(item["text"]) and "$" not in item["text"]:
                continue
            all_items.append(item)

    # סדר לפי score יורד (popular first)
    all_items.sort(key=lambda x: x.get("score", 0), reverse=True)
    log.info("reddit_fetch_done", count=len(all_items))
    return all_items[:60]
