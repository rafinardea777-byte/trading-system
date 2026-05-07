"""סינון פריטי חדשות לפי רלוונטיות לשוק האמריקאי."""
import re

_KEYWORDS = [
    r"S&P\s*500", r"NASDAQ", r"Dow\s*Jones", r"SPX", r"SPY", r"QQQ",
    r"Federal\s*Reserve", r"\bFed\b", r"FOMC", r"Jerome\s*Powell",
    r"inflation", r"CPI", r"PCE", r"interest\s*rate", r"rate\s*cut",
    r"earnings", r"EPS", r"revenue", r"guidance",
    r"stock\s*market", r"Wall\s*Street", r"trading", r"markets",
    r"recession", r"bull\s*market", r"bear\s*market", r"rally",
    r"GDP", r"employment", r"jobs\s*report", r"unemployment",
    r"\$[A-Z]{1,5}\b",
    r"SEC", r"IPO", r"M&A", r"merger", r"acquisition",
    r"tariff", r"tariffs", r"executive\s*order", r"policy",
    r"Treasury", r"trade", r"tax", r"China", r"economy",
]

US_MARKET_PATTERN = re.compile("|".join(f"({k})" for k in _KEYWORDS), re.IGNORECASE)


def is_us_market_related(text: str) -> bool:
    if not text:
        return False
    return bool(US_MARKET_PATTERN.search(text))


def filter_us_market(items: list[dict]) -> list[dict]:
    return [i for i in items if is_us_market_related(i.get("text", ""))]
