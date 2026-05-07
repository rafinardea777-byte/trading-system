"""התראות טלגרם - טוקן וChat ID נטענים מ-.env בלבד."""
import requests

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

_API = "https://api.telegram.org/bot{token}/sendMessage"


def _enabled() -> bool:
    return (
        settings.enable_telegram_alerts
        and bool(settings.telegram_bot_token)
        and bool(settings.telegram_chat_id)
    )


def send_message(text: str, parse_mode: str = "HTML") -> bool:
    if not _enabled():
        log.debug("telegram_disabled")
        return False
    url = _API.format(token=settings.telegram_bot_token)
    try:
        r = requests.post(
            url,
            data={"chat_id": settings.telegram_chat_id, "text": text, "parse_mode": parse_mode},
            timeout=10,
        )
        if r.status_code == 200:
            return True
        log.warning("telegram_send_failed", status=r.status_code, body=r.text[:200])
    except Exception as e:
        log.warning("telegram_send_exception", error=str(e))
    return False


def send_signal_alert(signal) -> bool:
    """signal יכול להיות Signal model או dict."""
    if hasattr(signal, "symbol"):
        s = signal
        symbol = s.symbol
        price = s.price
        rsi = s.rsi
        vol = s.volume_ratio
        strength = getattr(s, "strength", "")
        t1 = s.target_1
        t2 = s.target_2
        sl = s.stop_loss
    else:
        symbol = signal["symbol"]
        price = signal["price"]
        rsi = signal["rsi"]
        vol = signal["volume_ratio"]
        strength = signal.get("strength", "")
        t1 = signal.get("target_1", "")
        t2 = signal.get("target_2", "")
        sl = signal.get("stop_loss", "")

    msg = (
        f"🚨 <b>סיגנל חדש: {symbol}</b>\n\n"
        f"💰 מחיר: <b>${price}</b>\n"
        f"📊 RSI: <b>{rsi}</b>\n"
        f"🔥 וולום: <b>x{vol}</b>\n"
        f"⭐ חוזק: <b>{strength}/10</b>\n\n"
        f"🎯 יעד 1: ${t1}\n"
        f"🎯 יעד 2: ${t2}\n"
        f"🛑 סטופ: ${sl}\n"
    )
    return send_message(msg)
