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
_IL = ZoneInfo("Asia/Jerusalem")


def is_us_market_open(now: datetime | None = None) -> bool:
    """NYSE: שני-שישי 09:30-16:00 ET. בלי טיפול בחגים פדרליים."""
    et = (now or datetime.now(_NY)).astimezone(_NY)
    if et.weekday() >= 5:
        return False
    minutes = et.hour * 60 + et.minute
    return 570 <= minutes <= 960  # 09:30=570, 16:00=960


def is_il_market_open(now: datetime | None = None) -> bool:
    """TASE עדכון 2026: שני-שישי 09:30-17:14 שעון ישראל. סגור שבת-ראשון.

    Python weekday: Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
    """
    il = (now or datetime.now(_IL)).astimezone(_IL)
    if il.weekday() not in (0, 1, 2, 3, 4):  # Mon-Fri
        return False
    minutes = il.hour * 60 + il.minute
    # יום שישי - סיום מוקדם יותר ב-14:30 (סיום מסחר רציף)
    if il.weekday() == 4:
        return 570 <= minutes <= 870  # 09:30 to 14:30
    return 570 <= minutes <= 1034  # 09:30 to 17:14


def is_any_market_open(now: datetime | None = None) -> bool:
    return is_us_market_open(now) or is_il_market_open(now)


def is_symbol_market_open(symbol: str, now: datetime | None = None) -> bool:
    """האם הבורסה של הסמל הספציפי פתוחה כרגע."""
    if symbol.endswith(".TA"):
        return is_il_market_open(now)
    return is_us_market_open(now)


def _news_job():
    from app.scanners.news import run_news_scan
    try:
        result = run_news_scan()
        log.info("scheduled_news_scan_done", **result)
    except Exception as e:
        log.error("scheduled_news_scan_failed", error=str(e))


def _market_job():
    # סריקה רק כשלפחות אחד השווקים פתוח - US או TASE
    if not is_any_market_open():
        log.info("market_scan_skipped", reason="all_markets_closed")
        return

    from app.scanners.market import run_market_scan
    try:
        result = run_market_scan(include_sp500=False)
        log.info(
            "scheduled_market_scan_done",
            us_open=is_us_market_open(),
            il_open=is_il_market_open(),
            **result,
        )
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


def _cleanup_job():
    """מחיקת נתונים ישנים - news/notifs > 60-90 יום, closed signals > 180 יום."""
    from app.storage import get_session
    from app.storage.repository import cleanup_old_data
    try:
        with get_session() as session:
            result = cleanup_old_data(session)
        log.info("scheduled_cleanup_done", **result)
    except Exception as e:
        log.error("scheduled_cleanup_failed", error=str(e))


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
    # ניקוי DB - פעם ביום ב-03:00 שעון ישראל
    from apscheduler.triggers.cron import CronTrigger
    _scheduler.add_job(
        _cleanup_job,
        CronTrigger(hour=3, minute=0, timezone=_IL),
        id="db_cleanup",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    log.info(
        "scheduler_started",
        news_every_h=settings.news_scan_interval_hours,
        market_every_min=settings.market_scan_interval_minutes,
        monitor_every_h=2,
        cleanup_daily_at="03:00 IL",
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("scheduler_stopped")
