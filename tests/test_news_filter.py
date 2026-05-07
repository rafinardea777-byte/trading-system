"""בדיקות לסינון חדשות שוק אמריקאי."""
from app.scanners.news.filter import filter_us_market, is_us_market_related


def test_detects_fed():
    assert is_us_market_related("Fed cuts rates by 25bps")


def test_detects_inflation():
    assert is_us_market_related("CPI came in at 3.2%")


def test_detects_stock_symbol():
    assert is_us_market_related("$AAPL beats earnings")


def test_ignores_unrelated():
    assert not is_us_market_related("My cat is cute")
    assert not is_us_market_related("Football game tonight")


def test_filter_list():
    items = [
        {"text": "Fed meeting Wednesday"},
        {"text": "weather is nice"},
        {"text": "S&P 500 hits ATH"},
    ]
    out = filter_us_market(items)
    assert len(out) == 2
