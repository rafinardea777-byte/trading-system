"""בדיקות לרשימת המניות - שאין כפילויות ושלא תוקן הבאג של חוסר פסיק."""
from app.scanners.market.universe import (
    AI_TECH,
    BIOTECH,
    CRYPTO,
    CURATED_SYMBOLS,
)


def test_no_duplicates_in_curated():
    assert len(CURATED_SYMBOLS) == len(set(CURATED_SYMBOLS))


def test_each_symbol_is_short_uppercase():
    for sym in CURATED_SYMBOLS:
        assert sym.isupper(), f"{sym} not uppercase"
        assert 1 <= len(sym) <= 5, f"{sym} length suspicious - implicit-string-concat bug?"
        assert sym.isalpha(), f"{sym} not alphabetic"


def test_categories_not_empty():
    assert len(AI_TECH) > 10
    assert len(CRYPTO) > 5
    assert len(BIOTECH) > 5


def test_known_symbols_present():
    assert "NVDA" in CURATED_SYMBOLS
    assert "TSLA" in CURATED_SYMBOLS
    assert "JPM" in CURATED_SYMBOLS
