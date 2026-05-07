"""תזמור סריקת חדשות - Twitter+RSS, סינון, העשרה, שמירה ל-DB."""
from app.core.config import settings
from app.core.logging import get_logger
from app.scanners.news.filter import filter_us_market
from app.scanners.news.rss import fetch_rss
from app.scanners.news.twitter import fetch_tweets
from app.storage import NewsItem, get_session
from app.storage.repository import add_news_item, create_scan, finish_scan

log = get_logger(__name__)


def run_news_scan(
    hours_back: int | None = None,
    enrich: bool = True,
) -> dict:
    """
    סריקת חדשות - מחזיר {scan_id, fetched, saved, enriched}.
    enrich=True מפעיל תרגום עברית אם יש OpenAI key.
    """
    hours_back = hours_back or settings.news_scan_interval_hours
    log.info("news_scan_start", hours_back=hours_back)

    with get_session() as session:
        scan = create_scan(session, kind="news")
        scan_id = scan.id

        try:
            if settings.use_x_api:
                items = fetch_tweets(hours_back=hours_back)
                items = filter_us_market(items)  # X לא מסונן מהמקור
            else:
                items = fetch_rss(hours_back=hours_back)
                # RSS כבר מסונן בפנים

            if enrich and items:
                # translate_items נופל אלגנטית למילון מקומי אם אין OpenAI
                from app.enrichment.translator import translate_items
                items = translate_items(items[:60])

            saved = 0
            for raw in items:
                ni = NewsItem(
                    scan_id=scan_id,
                    source=raw["source"],
                    author=raw["author"],
                    text=raw["text"],
                    url=raw.get("url", ""),
                    published_at=raw.get("published_at"),
                    external_id=raw.get("external_id"),
                    hebrew_translation=raw.get("hebrew_translation"),
                    hebrew_explanation=raw.get("hebrew_explanation"),
                )
                if add_news_item(session, ni) is not None:
                    saved += 1

            finish_scan(session, scan, items_found=saved, status="success")
            log.info("news_scan_done", fetched=len(items), saved=saved)
            return {"scan_id": scan_id, "fetched": len(items), "saved": saved}

        except Exception as e:
            finish_scan(session, scan, items_found=0, status="failed", error=str(e))
            log.error("news_scan_failed", error=str(e))
            raise
