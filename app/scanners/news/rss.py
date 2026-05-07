"""גיבוי RSS - כשאין מפתח X API."""
from datetime import datetime, timedelta, timezone

from app.core.logging import get_logger
from app.scanners.news.filter import is_us_market_related

log = get_logger(__name__)

RSS_FEEDS = [
    ("https://www.cnbc.com/id/100003114/device/rss/rss.html", "CNBC"),
    ("https://feeds.content.dowjones.io/public/rss/mw_topstories", "MarketWatch"),
    ("https://www.wsj.com/xml/rss/3_7014.xml", "WSJ"),
    ("https://feeds.bloomberg.com/markets/news.rss", "Bloomberg"),
]


def fetch_rss(hours_back: int = 24, max_items: int = 80) -> list[dict]:
    try:
        import feedparser
    except ImportError:
        log.error("feedparser_not_installed")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    out: list[dict] = []

    for url, source in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:25]:
                title = getattr(entry, "title", "") or ""
                if not title or not is_us_market_related(title):
                    continue
                link = getattr(entry, "link", "") or url
                pub = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
                if pub:
                    from time import mktime
                    dt = datetime.fromtimestamp(mktime(pub), tz=timezone.utc)
                    if dt < cutoff:
                        continue
                else:
                    dt = datetime.now(timezone.utc)

                # external_id יציב - URL כבסיס
                eid = f"rss:{link}"
                out.append({
                    "external_id": eid,
                    "source": "rss",
                    "author": source,
                    "text": title,
                    "url": link,
                    "published_at": dt,
                })
        except Exception as e:
            log.warning("rss_fetch_failed", source=source, error=str(e))

    log.info("rss_fetch_done", count=len(out))
    return out[:max_items]
