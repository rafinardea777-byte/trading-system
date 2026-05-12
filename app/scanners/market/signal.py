"""לוגיקת סיגנל מסחר - פריצת MA20 + RSI + נפח חריג."""
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app.core.config import settings
from app.scanners.market.indicators import add_all_indicators


@dataclass
class TechnicalSignal:
    symbol: str
    price: float
    rsi: float
    volume_ratio: float
    ma_fast: float
    ma_slow: float
    strength: float  # 0-10
    target_1: float
    target_2: float
    stop_loss: float

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "price": round(self.price, 2),
            "rsi": round(self.rsi, 1),
            "volume_ratio": round(self.volume_ratio, 1),
            "ma_fast": round(self.ma_fast, 2),
            "ma_slow": round(self.ma_slow, 2),
            "strength": round(self.strength, 1),
            "target_1": round(self.target_1, 2),
            "target_2": round(self.target_2, 2),
            "stop_loss": round(self.stop_loss, 2),
        }


def _strength_score(rsi: float, vol_ratio: float, breakout_pct: float) -> float:
    """ציון 0-10. שילוב RSI במרכז הטווח, וולום חריג, ופריצה ברורה מעל MA."""
    rsi_score = 1.0 - abs(rsi - 60) / 30  # שיא ב-60
    rsi_score = max(0, min(1, rsi_score))
    vol_score = min(1.0, (vol_ratio - 1) / 3)  # x4 = ציון מלא
    breakout_score = min(1.0, breakout_pct / 0.05)  # 5% מעל MA = ציון מלא
    raw = rsi_score * 4 + vol_score * 3 + breakout_score * 3
    return round(raw, 1)


def _symbol_market_open(symbol: str) -> bool:
    """האם הבורסה הרלוונטית לסמל פתוחה כרגע."""
    from app.scheduler.jobs import is_il_market_open, is_us_market_open

    if symbol.endswith(".TA"):
        return is_il_market_open()
    return is_us_market_open()


def evaluate_symbol(symbol: str, df: pd.DataFrame) -> Optional[TechnicalSignal]:
    """בדיקה אם המניה עומדת בקריטריונים. מחזיר Signal או None.

    חוסם אוטומטית אם הבורסה של הסמל סגורה - לא יוצרים סיגנל על נתונים סטטיים.
    """
    if not _symbol_market_open(symbol):
        return None

    if df is None or len(df) < max(settings.ma_slow, 30):
        return None

    df = add_all_indicators(
        df,
        rsi_period=settings.rsi_period,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
    )
    last = df.iloc[-1]

    price = float(last["Close"])

    # TASE מחירים באגורות (1 ש"ח = 100 אגורות). מרחיב את הטווח בהתאם
    is_tase = symbol.endswith(".TA")
    min_price = settings.scan_min_price
    max_price = settings.scan_max_price * (100 if is_tase else 1)

    if not (min_price <= price <= max_price):
        return None

    vol_ratio = float(last["VOL_RATIO"]) if pd.notna(last["VOL_RATIO"]) else 0
    if vol_ratio < settings.volume_spike_ratio:
        return None

    ma_fast = float(last["MA_FAST"]) if pd.notna(last["MA_FAST"]) else 0
    ma_slow = float(last["MA_SLOW"]) if pd.notna(last["MA_SLOW"]) else 0
    if price <= ma_fast or ma_fast <= ma_slow:
        return None

    rsi_val = float(last["RSI"]) if pd.notna(last["RSI"]) else 0
    if not (settings.rsi_min <= rsi_val <= settings.rsi_max):
        return None

    breakout_pct = (price - ma_fast) / ma_fast if ma_fast else 0
    strength = _strength_score(rsi_val, vol_ratio, breakout_pct)

    return TechnicalSignal(
        symbol=symbol,
        price=price,
        rsi=rsi_val,
        volume_ratio=vol_ratio,
        ma_fast=ma_fast,
        ma_slow=ma_slow,
        strength=strength,
        target_1=price * (1 + settings.target_1_pct),
        target_2=price * (1 + settings.target_2_pct),
        stop_loss=price * (1 - settings.stop_loss_pct),
    )
