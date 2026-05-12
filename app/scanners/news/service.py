"""תזמור סריקת חדשות - Twitter+RSS, סינון, העשרה, שמירה ל-DB."""
from app.core.config import settings
from app.core.logging import get_logger
from app.scanners.news.filter import filter_us_market
from app.scanners.news.reddit import fetch_reddit
from app.scanners.news.rss import fetch_rss
from app.scanners.news.stocktwits import fetch_stocktwits
from app.scanners.news.symbols import extract_symbols
from app.scanners.news.twitter import fetch_tweets
from app.storage import NewsItem, get_session
from app.storage.repository import (
    add_news_item,
    add_notification,
    create_scan,
    find_users_watching,
    finish_scan,
)

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
            items: list[dict] = []

            # RSS - תמיד פעיל
            try:
                items.extend(fetch_rss(hours_back=hours_back))
            except Exception as e:
                log.warning("rss_failed", error=str(e))

            # X / Twitter - רק אם יש מפתח
            if settings.use_x_api:
                try:
                    tweets = fetch_tweets(hours_back=hours_back)
                    items.extend(filter_us_market(tweets))
                except Exception as e:
                    log.warning("twitter_failed", error=str(e))

            # StockTwits - חינמי
            try:
                items.extend(fetch_stocktwits(hours_back=hours_back))
            except Exception as e:
                log.warning("stocktwits_failed", error=str(e))

            # Reddit (WSB + stocks) - חינמי
            try:
                items.extend(fetch_reddit(hours_back=hours_back))
            except Exception as e:
                log.warning("reddit_failed", error=str(e))

            log.info("news_sources_aggregated", total=len(items))

            if enrich and items:
                # translate_items נופל אלגנטית למילון מקומי אם אין OpenAI
                from app.enrichment.translator import translate_items
                items = translate_items(items[:80])

            saved = 0
            watchlist_alerts = 0
            for raw in items:
                # חילוץ סמלי מניות מהכותרת
                syms = extract_symbols(raw.get("text", ""))
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
                    mentioned_symbols=",".join(sorted(syms)) if syms else None,
                )
                added = add_news_item(session, ni)
                if added is None:
                    continue  # כבר קיים
                saved += 1

                # התראה למשתמשים עם המניות האלה ב-Watchlist
                if syms:
                    matches = find_users_watching(session, syms)
                    for user_id, matched_syms in matches.items():
                        for sym in matched_syms:
                            add_notification(
                                session,
                                kind="news",
                                title=f"📰 {sym}: חדשות חדשות",
                                message=raw["text"][:200],
                                symbol=sym,
                                icon="📰",
                                user_id=user_id,
                            )
                            watchlist_alerts += 1

            finish_scan(session, scan, items_found=saved, status="success")
            log.info("news_scan_done", fetched=len(items), saved=saved, watchlist_alerts=watchlist_alerts)
            return {"scan_id": scan_id, "fetched": len(items), "saved": saved, "watchlist_alerts": watchlist_alerts}

        except Exception as e:
            finish_scan(session, scan, items_found=0, status="failed", error=str(e))
            log.error("news_scan_failed", error=str(e))
            raise
