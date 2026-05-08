"""תזמור סריקת שוק - יורד מ-yfinance, מסנן, שומר ל-DB, שולח התראות."""
from app.core.config import settings
from app.core.logging import get_logger
from app.scanners.market.signal import evaluate_symbol
from app.scanners.market.universe import get_universe
from app.storage import Signal, get_session
from app.storage.repository import (
    add_notification,
    create_scan,
    finish_scan,
    signal_exists_today,
    upsert_signal,
)

log = get_logger(__name__)


def _fetch_history(symbol: str, period: str = "60d"):
    try:
        import yfinance as yf

        df = yf.Ticker(symbol).history(period=period)
        if df is None or df.empty:
            return None
        return df
    except Exception as e:
        log.debug("yf_fetch_failed", symbol=symbol, error=str(e))
        return None


def run_market_scan(
    include_sp500: bool = True,
    send_alerts: bool = True,
    max_symbols: int | None = None,
) -> dict:
    """סריקת שוק - מחזיר {scan_id, scanned, signals, new_signals}."""
    log.info("market_scan_start")

    symbols = get_universe(include_sp500=include_sp500)
    if max_symbols:
        symbols = symbols[:max_symbols]

    with get_session() as session:
        scan = create_scan(session, kind="market")
        scan_id = scan.id

        try:
            new_signals: list[Signal] = []
            for i, symbol in enumerate(symbols):
                df = _fetch_history(symbol)
                tech = evaluate_symbol(symbol, df) if df is not None else None
                if not tech:
                    continue
                if signal_exists_today(session, symbol):
                    continue

                sig = Signal(
                    scan_id=scan_id,
                    symbol=tech.symbol,
                    price=tech.price,
                    rsi=tech.rsi,
                    volume_ratio=tech.volume_ratio,
                    ma_fast=tech.ma_fast,
                    ma_slow=tech.ma_slow,
                    strength=tech.strength,
                    target_1=tech.target_1,
                    target_2=tech.target_2,
                    stop_loss=tech.stop_loss,
                )
                upsert_signal(session, sig)
                session.flush()  # כדי שיהיה sig.id ל-notification
                new_signals.append(sig)
                log.info("signal_found", symbol=symbol, strength=tech.strength)

                # יצירת התראה ל-bell icon בדשבורד
                emoji = "🔥" if tech.strength >= 8 else ("⭐" if tech.strength >= 6 else "📊")
                add_notification(
                    session,
                    kind="signal",
                    title=f"{emoji} סיגנל חדש: {symbol}",
                    message=f"מחיר ${tech.price:.2f} | RSI {tech.rsi:.1f} | וולום x{tech.volume_ratio:.1f} | חוזק {tech.strength:.1f}/10",
                    symbol=symbol,
                    signal_id=sig.id,
                    icon=emoji,
                )

                if (i + 1) % 50 == 0:
                    log.info("market_scan_progress", scanned=i + 1, total=len(symbols))

            finish_scan(session, scan, items_found=len(new_signals), status="success")

        except Exception as e:
            finish_scan(session, scan, items_found=0, status="failed", error=str(e))
            log.error("market_scan_failed", error=str(e))
            raise

    # התראות מחוץ ל-session (לאחר commit)
    if send_alerts and new_signals:
        try:
            from app.alerts.telegram import send_signal_alert

            for sig in new_signals:
                send_signal_alert(sig)
        except Exception as e:
            log.warning("alert_send_failed", error=str(e))

    log.info("market_scan_done", scanned=len(symbols), found=len(new_signals))
    return {
        "scan_id": scan_id,
        "scanned": len(symbols),
        "new_signals": len(new_signals),
    }
