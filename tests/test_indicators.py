"""בדיקות אינדיקטורים טכניים."""
import pandas as pd
import pytest

from app.scanners.market.indicators import add_all_indicators, atr, rsi, sma


@pytest.fixture
def price_series():
    # 60 ימי נתונים סינתטיים - מגמת עליה
    closes = [100 + i * 0.5 + (i % 5) for i in range(60)]
    return pd.Series(closes)


@pytest.fixture
def ohlcv_df():
    closes = [100 + i * 0.5 for i in range(60)]
    return pd.DataFrame({
        "Open": closes,
        "High": [c + 1 for c in closes],
        "Low": [c - 1 for c in closes],
        "Close": closes,
        "Volume": [1_000_000 + i * 1000 for i in range(60)],
    })


def test_rsi_returns_series(price_series):
    result = rsi(price_series, period=14)
    assert isinstance(result, pd.Series)
    assert len(result) == len(price_series)


def test_rsi_in_uptrend_above_50(price_series):
    result = rsi(price_series, period=14)
    # מגמת עליה רציפה צריכה להחזיר RSI גבוה
    assert result.iloc[-1] > 50


def test_sma_smoothes(price_series):
    result = sma(price_series, period=10)
    assert pd.isna(result.iloc[0])
    assert not pd.isna(result.iloc[-1])
    # SMA צריך להיות נמוך מהמחיר האחרון בעליה
    assert result.iloc[-1] < price_series.iloc[-1]


def test_atr_returns_positive(ohlcv_df):
    result = atr(ohlcv_df, period=14)
    assert (result.dropna() > 0).all()


def test_add_all_indicators(ohlcv_df):
    df = add_all_indicators(ohlcv_df)
    for col in ["RSI", "MA_FAST", "MA_SLOW", "ATR", "VOL_AVG", "VOL_RATIO"]:
        assert col in df.columns
