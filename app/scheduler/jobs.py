"""תזמון - APScheduler ברקע מתוך FastAPI."""
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def _news_job():
    from app.scanners.news import run_news_scan
    try:
        result = run_news_scan()
        log.info("scheduled_news_scan_done", **result)
    except Exception as e:
        log.error("scheduled_news_scan_failed", error=str(e))


def _market_job():
    from app.scanners.market import run_market_scan
    try:
        # סריקה ראשונית - ללא S&P 500 (לחיסכון בזמן)
        result = run_market_scan(include_sp500=False)
        log.info("scheduled_market_scan_done", **result)
    except Exception as e:
        log.error("scheduled_market_scan_failed", error=str(e))


def start_scheduler() -> None:
    global _scheduler
    if _scheduler:
        return

    _scheduler = BackgroundScheduler(timezone=settings.timezone)
    _scheduler.add_job(
        _news_job,
        IntervalTrigger(hours=settings.news_scan_interval_hours),
        id="news_scan",
        next_run_time=datetime.now(),
        max_instances=1,
        coalesce=True,
    )
    _scheduler.add_job(
        _market_job,
        IntervalTrigger(minutes=settings.market_scan_interval_minutes),
        id="market_scan",
        next_run_time=datetime.now(),
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    log.info(
        "scheduler_started",
        news_every_h=settings.news_scan_interval_hours,
        market_every_min=settings.market_scan_interval_minutes,
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("scheduler_stopped")
