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


def _price_alerts_job():
    """בדיקת התראות מחיר פעילות. מפעיל התראה כשמחיר חוצה את היעד."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from datetime import datetime as _dt
    from app.storage import PriceAlert, get_session
    from app.storage.repository import add_notification
    from sqlmodel import select

    try:
        import yfinance as yf
    except ImportError:
        return

    def get_price(sym: str) -> Optional[float]:
        try:
            info = yf.Ticker(sym).fast_info
            return float(info.get("last_price") or info.get("lastPrice") or 0) or None
        except Exception:
            return None

    with get_session() as session:
        active = list(session.exec(
            select(PriceAlert).where(PriceAlert.triggered == False)  # noqa: E712
        ))
        if not active:
            return

        # קבץ סמלים ייחודיים - הימנע מקריאה כפולה
        symbols = list({a.symbol for a in active})
        prices: dict[str, Optional[float]] = {}
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = {ex.submit(get_price, s): s for s in symbols}
            for f in as_completed(futures):
                prices[futures[f]] = f.result(timeout=10) if not f.exception() else None

        triggered = 0
        for alert in active:
            price = prices.get(alert.symbol)
            if price is None:
                continue
            hit = (alert.direction == "above" and price >= alert.target_price) or \
                  (alert.direction == "below" and price <= alert.target_price)
            if not hit:
                continue

            alert.triggered = True
            alert.triggered_at = _dt.utcnow()
            alert.triggered_price = price
            session.add(alert)
            triggered += 1

            # הוסף התראה למשתמש
            arrow = "📈" if alert.direction == "above" else "📉"
            sign = ">=" if alert.direction == "above" else "<="
            add_notification(
                session,
                kind="alert",
                title=f"🔔 {alert.symbol} - יעד מחיר הופעל",
                message=f"{alert.symbol} {arrow} ${price:.2f} {sign} ${alert.target_price:.2f}",
                symbol=alert.symbol,
                icon="🔔",
                user_id=alert.user_id,
            )

        log.info("price_alerts_check", active=len(active), triggered=triggered)


def _daily_digest_job():
    """דוח יומי במייל למשתמשים שביקשו - ב-08:00 שעון ישראל."""
    from datetime import datetime as _dt, timedelta as _td
    from app.core.email import send_email
    from app.storage import NewsItem, Notification, Signal, User, UserWatchlist, get_session
    from sqlmodel import select

    with get_session() as session:
        users = list(session.exec(
            select(User).where(User.daily_digest_enabled == True)  # noqa: E712
        ))
        if not users:
            return

        cutoff = _dt.utcnow() - _td(hours=24)
        sent = 0
        for u in users:
            try:
                wl_syms = [r.symbol for r in session.exec(
                    select(UserWatchlist).where(UserWatchlist.user_id == u.id)
                )]
                if not wl_syms:
                    continue

                news_count = len(list(session.exec(
                    select(NewsItem).where(
                        NewsItem.fetched_at >= cutoff,
                        NewsItem.mentioned_symbols.is_not(None),
                    )
                )))
                signals_count = len(list(session.exec(
                    select(Signal).where(Signal.created_at >= cutoff)
                )))
                alerts = list(session.exec(
                    select(Notification).where(
                        Notification.user_id == u.id,
                        Notification.created_at >= cutoff,
                        Notification.kind == "alert",
                    )
                ))

                from app.core.config import settings as _s
                subject = f"☕ דוח בוקר - {_dt.now().strftime('%d/%m/%Y')}"
                body = f"""<!DOCTYPE html><html dir="rtl"><body style="font-family:Arial,sans-serif;background:#f4f6f8;padding:20px">
<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;padding:30px">
  <h2 style="color:#00d4ff;margin-bottom:20px">☕ בוקר טוב {u.full_name or ''}</h2>
  <p>הנה מה שקרה ב-24 השעות האחרונות:</p>
  <ul style="font-size:14px;line-height:2">
    <li>📰 <b>{news_count}</b> כתבות חדשות על מניות במעקב</li>
    <li>🔥 <b>{signals_count}</b> סיגנלים חדשים</li>
    <li>🔔 <b>{len(alerts)}</b> התראות מחיר הופעלו</li>
    <li>⭐ <b>{len(wl_syms)}</b> מניות ב-Watchlist שלך</li>
  </ul>
  <p style="margin-top:20px">
    <a href="{_s.public_base_url}" style="background:#00d4ff;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold">פתח את האפליקציה →</a>
  </p>
  <hr style="margin-top:24px;border:none;border-top:1px solid #e2e8f0">
  <div style="font-size:11px;color:#718096">
    לביטול הדוח היומי: היכנס ל-"החשבון שלי" → כבה את התיבה.<br>
    ⚠️ אין במידע משום ייעוץ השקעות.
  </div>
</div></body></html>"""
                result = send_email(u.email, subject, body)
                if result.sent:
                    sent += 1
            except Exception as e:
                log.warning("digest_send_failed", user_id=u.id, error=str(e))

        log.info("daily_digest_done", users=len(users), sent=sent)


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
    # בדיקת התראות מחיר - כל 15 דקות
    _scheduler.add_job(
        _price_alerts_job,
        IntervalTrigger(minutes=15),
        id="price_alerts",
        next_run_time=datetime.now(),
        max_instances=1,
        coalesce=True,
    )
    # דוח יומי - 08:00 שעון ישראל
    _scheduler.add_job(
        _daily_digest_job,
        CronTrigger(hour=8, minute=0, timezone=_IL),
        id="daily_digest",
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
