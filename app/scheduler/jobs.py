"""תזמון - APScheduler ברקע מתוך FastAPI."""
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

_scheduler: Optional[BackgroundScheduler] = None

_NY = ZoneInfo("America/New_York")


def is_us_market_open(now: datetime | None = None) -> bool:
    """NYSE: שני-שישי 09:30-16:00 ET. בלי טיפול בחגים פדרליים."""
    et = (now or datetime.now(_NY)).astimezone(_NY)
    if et.weekday() >= 5:
        return False
    minutes = et.hour * 60 + et.minute
    return 570 <= minutes <= 960  # 09:30=570, 16:00=960


def _news_job():
    from app.scanners.news import run_news_scan
    try:
        result = run_news_scan()
        log.info("scheduled_news_scan_done", **result)
    except Exception as e:
        log.error("scheduled_news_scan_failed", error=str(e))


def _market_job():
    # סריקה רק כשהשוק פתוח - חיסכון משאבים, נתונים אקטואליים
    if not is_us_market_open():
        log.info("market_scan_skipped", reason="market_closed")
        return

    from app.scanners.market import run_market_scan
    try:
        result = run_market_scan(include_sp500=False)
        log.info("scheduled_market_scan_done", **result)
    except Exception as e:
        log.error("scheduled_market_scan_failed", error=str(e))


def _monitor_job():
    """בדיקת סיגנלים פתוחים - סוגר כשמגיעים ליעד/סטופ. רץ גם כשהשוק סגור (yfinance זמין 24/7)."""
    from app.scanners.market.monitor import check_open_signals
    try:
        result = check_open_signals()
        log.info("scheduled_monitor_done", **result)
    except Exception as e:
        log.error("scheduled_monitor_failed", error=str(e))


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
    # Signal monitor - בודק סגירות אוטומטיות כל שעתיים
    _scheduler.add_job(
        _monitor_job,
        IntervalTrigger(hours=2),
        id="signal_monitor",
        next_run_time=datetime.now(),
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    log.info(
        "scheduler_started",
        news_every_h=settings.news_scan_interval_hours,
        market_every_min=settings.market_scan_interval_minutes,
        monitor_every_h=2,
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("scheduler_stopped")
