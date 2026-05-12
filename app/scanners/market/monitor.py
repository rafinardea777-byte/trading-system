"""Monitor של סיגנלים פתוחים - סוגר אוטומטית כשפוגעים ביעד או בסטופ."""
from datetime import datetime
from typing import Optional

from app.core.logging import get_logger
from app.storage import Signal, get_session
from app.storage.repository import add_notification

log = get_logger(__name__)


def _current_price(symbol: str) -> Optional[float]:
    """מחיר נוכחי דרך yfinance. None אם נכשל."""
    try:
        import yfinance as yf

        info = yf.Ticker(symbol).fast_info
        price = info.get("last_price") or info.get("lastPrice")
        if price is None:
            # fallback to history
            hist = yf.Ticker(symbol).history(period="2d")
            if hist is not None and not hist.empty:
                price = float(hist["Close"].iloc[-1])
        return float(price) if price else None
    except Exception as e:
        log.debug("price_fetch_failed", symbol=symbol, error=str(e))
        return None


def check_open_signals() -> dict:
    """בודק את כל הסיגנלים הפתוחים, סוגר אם פגעו ביעד או סטופ.

    סוגר רק כשהבורסה של הסמל פתוחה - לא על נתונים סטטיים.

    כללי סגירה:
    - מחיר >= target_2: סגירה מלאה
    - מחיר >= target_1 + 3+ ימים: סגירה ברווח חלקי
    - מחיר <= stop_loss: סגירה בהפסד
    - גיל >= 14 ימים: time stop
    """
    closed_wins = 0
    closed_losses = 0
    still_open = 0
    skipped = 0
    skipped_closed_market = 0

    with get_session() as session:
        from sqlmodel import select

        open_sigs = list(session.exec(select(Signal).where(Signal.status == "open")))
        log.info("monitor_start", count=len(open_sigs))

        from app.scheduler.jobs import is_symbol_market_open

        for sig in open_sigs:
            # אל תבדוק אם הבורסה של הסמל סגורה
            if not is_symbol_market_open(sig.symbol):
                skipped_closed_market += 1
                still_open += 1
                continue

            price = _current_price(sig.symbol)
            if price is None:
                skipped += 1
                continue

            entry = sig.price
            age_days = (datetime.utcnow() - sig.created_at).days

            # Hit target_2 - יציאה מלאה
            if price >= sig.target_2:
                _close_signal(session, sig, price, "target_2_hit", "🎯")
                closed_wins += 1
                continue

            # Hit stop_loss
            if price <= sig.stop_loss:
                _close_signal(session, sig, price, "stop_loss_hit", "🛑")
                closed_losses += 1
                continue

            # Hit target_1 וגיל מעל 3 ימים → סוגר עם רווח חלקי
            if price >= sig.target_1 and age_days >= 3:
                _close_signal(session, sig, price, "target_1_hit", "✅")
                closed_wins += 1
                continue

            # יותר מ-14 יום ועדיין פתוח - time stop
            if age_days >= 14:
                reason = "time_stop_win" if price > entry else "time_stop_loss"
                emoji = "⏰" if price > entry else "⏰❌"
                _close_signal(session, sig, price, reason, emoji)
                if price > entry:
                    closed_wins += 1
                else:
                    closed_losses += 1
                continue

            still_open += 1

    log.info(
        "monitor_done",
        closed_wins=closed_wins,
        closed_losses=closed_losses,
        still_open=still_open,
        skipped=skipped,
        skipped_closed_market=skipped_closed_market,
    )
    return {
        "closed_wins": closed_wins,
        "closed_losses": closed_losses,
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

    add_notification(
        session,
        kind="signal",
        title=f"{emoji} {sig.symbol} נסגרה ({reason})",
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
