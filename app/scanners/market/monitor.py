"""Monitor סיגנלים פתוחים - intraday data + trailing stop + סגירה מדויקת.

האלגוריתם:
1. לכל סיגנל פתוח - מביא היסטוריה intraday מאז ה-created_at
2. עובר נר-נר ומעדכן מחיר שיא (highest)
3. מחשב trailing stop לפי מחיר השיא:
   - +10% → סטופ נע ל-+6%
   - +6%  → סטופ נע ל-+3%
   - +3%  → סטופ נע ל-breakeven
   - אחרת → stop_loss המקורי
4. בודק לכל נר: low <= trail_stop? high >= target?
5. סוגר במחיר המדויק (לא ב-current price חודש אחרי)
"""
from datetime import datetime
from typing import Optional

import pandas as pd

from app.core.config import settings
from app.core.logging import get_logger
from app.storage import Signal, get_session
from app.storage.repository import add_notification

log = get_logger(__name__)


def _intraday_history(symbol: str, days: int) -> Optional[pd.DataFrame]:
    """מביא נרות שעתיים מאז created_at. מחזיר DataFrame או None."""
    try:
        import yfinance as yf
        # yfinance מגביל interval=60m לטווח של 730 ימים. אבל מעל ~60 ימים האיכות יורדת
        if days <= 7:
            period, interval = "1mo", "60m"
        elif days <= 30:
            period, interval = "3mo", "60m"
        else:
            period, interval = "6mo", "1d"  # נר יומי מספיק לטווח ארוך
        df = yf.Ticker(symbol).history(period=period, interval=interval)
        if df is None or df.empty:
            return None
        return df
    except Exception as e:
        log.debug("intraday_fetch_failed", symbol=symbol, error=str(e))
        return None


def _compute_trail_stop(entry: float, peak: float, original_stop: float) -> float:
    """מחזיר את ה-stop הנוכחי לפי הרווח המקסימלי שהושג."""
    gain_pct = (peak - entry) / entry if entry > 0 else 0

    if gain_pct >= settings.trail_gain_3:
        return entry * (1 + settings.trail_stop_3)
    if gain_pct >= settings.trail_gain_2:
        return entry * (1 + settings.trail_stop_2)
    if gain_pct >= settings.trail_gain_1:
        return entry * (1 + settings.trail_stop_1)
    return original_stop


def _simulate_exit(sig: Signal, df: pd.DataFrame) -> Optional[tuple[float, str, str]]:
    """מחזיר (exit_price, reason, emoji) או None אם עדיין פתוח."""
    # סינון נרות מאז ה-created_at
    entry_time = sig.created_at
    df = df[df.index.tz_localize(None) >= entry_time] if df.index.tz is not None else df[df.index >= entry_time]
    if df is None or df.empty:
        return None

    peak = sig.price
    for ts, row in df.iterrows():
        high = float(row["High"])
        low = float(row["Low"])
        peak = max(peak, high)

        trail_stop = _compute_trail_stop(sig.price, peak, sig.stop_loss)

        # סדר עדיפויות לבדיקה תוך-יומית: low קודם (worst case) אם הנר נפל
        # ואז high (אם פגע ביעד)
        # אם נר ירד מתחת לסטופ הנע
        if low <= trail_stop:
            # סוגרים ב-trail_stop בדיוק (מדמה stop order)
            if trail_stop >= sig.price:
                return (trail_stop, "trail_stop_lock", "🔒")
            return (trail_stop, "stop_loss", "🛑")

        # אם נר עלה ליעד 2 - סגירה מלאה
        if high >= sig.target_2:
            return (sig.target_2, "target_2_hit", "🎯")

    # לא נסגר - אבל אולי טיים-סטופ
    age_days = (datetime.utcnow() - sig.created_at).days
    if age_days >= 14:
        current_price = float(df["Close"].iloc[-1])
        if current_price > sig.price:
            return (current_price, "time_stop_win", "⏰")
        return (current_price, "time_stop_loss", "⏰❌")

    return None


def check_open_signals() -> dict:
    """סוגר את כל הסיגנלים הפתוחים שלפי intraday data נסגרו.

    שיפורים:
    - שימוש בנרות שעתיים (לא רק last close) → דיוק בסגירה
    - Trailing stop: נועלים רווחים ככל שהמחיר עולה
    - שומר peak per signal לבדיקה נכונה
    """
    closed_wins = 0
    closed_losses = 0
    still_open = 0
    skipped = 0
    skipped_closed_market = 0
    trail_locks = 0

    with get_session() as session:
        from sqlmodel import select

        open_sigs = list(session.exec(select(Signal).where(Signal.status == "open")))
        log.info("monitor_start", count=len(open_sigs))

        for sig in open_sigs:
            # המוניטור עובד על היסטוריה - לא צריך שהשוק יהיה פתוח כרגע
            age_days = max((datetime.utcnow() - sig.created_at).days, 1)
            df = _intraday_history(sig.symbol, age_days + 1)
            if df is None or df.empty:
                skipped += 1
                continue

            result = _simulate_exit(sig, df)
            if result is None:
                still_open += 1
                continue

            exit_price, reason, emoji = result
            _close_signal(session, sig, exit_price, reason, emoji)
            pnl = (exit_price - sig.price) / sig.price * 100
            if reason == "trail_stop_lock":
                trail_locks += 1
                closed_wins += 1  # סגירה מעל הכניסה = ניצחון
            elif pnl > 0:
                closed_wins += 1
            else:
                closed_losses += 1

    log.info(
        "monitor_done",
        closed_wins=closed_wins,
        closed_losses=closed_losses,
        trail_locks=trail_locks,
        still_open=still_open,
        skipped=skipped,
        skipped_closed_market=skipped_closed_market,
    )
    return {
        "closed_wins": closed_wins,
        "closed_losses": closed_losses,
        "trail_locks": trail_locks,
        "still_open": still_open,
        "skipped": skipped,
        "skipped_closed_market": skipped_closed_market,
    }


def _close_signal(session, sig: Signal, exit_price: float, reason: str, emoji: str) -> None:
    """סוגר סיגנל ומחשב pnl_pct + יוצר התראה."""
    pnl_pct = ((exit_price - sig.price) / sig.price) * 100

    sig.status = "closed"
    sig.closed_at = datetime.utcnow()
    sig.exit_price = round(exit_price, 2)
    sig.pnl_pct = round(pnl_pct, 2)
    session.add(sig)

    reason_he = {
        "target_2_hit": "יעד 2 הושג",
        "target_1_hit": "יעד 1 הושג",
        "trail_stop_lock": "סטופ נע - רווח ננעל",
        "stop_loss": "סטופ הופעל",
        "time_stop_win": "טיים-סטופ ברווח",
        "time_stop_loss": "טיים-סטופ בהפסד",
    }.get(reason, reason)

    add_notification(
        session,
        kind="signal",
        title=f"{emoji} {sig.symbol} - {reason_he}",
        message=f"כניסה ${sig.price:.2f} → יציאה ${exit_price:.2f} ({pnl_pct:+.2f}%)",
        symbol=sig.symbol,
        signal_id=sig.id,
        icon=emoji,
    )
    log.info(
        "signal_closed",
        symbol=sig.symbol,
        reason=reason,
        entry=sig.price,
        exit=round(exit_price, 2),
        pnl_pct=round(pnl_pct, 2),
    )
