"""אינדיקטורים טכניים - RSI, MA, ATR, Volume."""
from typing import Optional

import pandas as pd


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range. דורש high/low/close."""
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def volume_ratio(volume: pd.Series, avg_period: int = 20) -> pd.Series:
    avg = volume.rolling(avg_period).mean()
    return volume / avg.replace(0, pd.NA)


def add_all_indicators(
    df: pd.DataFrame,
    rsi_period: int = 14,
    ma_fast: int = 20,
    ma_slow: int = 50,
    atr_period: int = 14,
) -> pd.DataFrame:
    """מוסיף לכל הטור: RSI, MA_FAST, MA_SLOW, ATR, VOL_AVG, VOL_RATIO."""
    df = df.copy()
    df["RSI"] = rsi(df["Close"], rsi_period)
    df["MA_FAST"] = sma(df["Close"], ma_fast)
    df["MA_SLOW"] = sma(df["Close"], ma_slow)
    df["ATR"] = atr(df, atr_period)
    df["VOL_AVG"] = sma(df["Volume"], 20)
    df["VOL_RATIO"] = df["Volume"] / df["VOL_AVG"].replace(0, pd.NA)
    return df
