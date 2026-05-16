"""Stock detail endpoint - יסודות + נתוני מסחר + סריקה טכנית."""
import re
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.logging import get_logger

router = APIRouter(prefix="/api/stocks", tags=["stocks"])
log = get_logger(__name__)

# קאש פשוט בזיכרון - 5 דקות (yfinance איטי, אין סיבה לקרוא לכל בקשה)
_CACHE: dict[str, tuple[datetime, dict]] = {}
_CACHE_TTL = timedelta(minutes=5)


class StockSnapshot(BaseModel):
    symbol: str
    name: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    summary: Optional[str] = None

    # מחיר
    price: Optional[float] = None
    previous_close: Optional[float] = None
    day_change_pct: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    volume: Optional[int] = None
    avg_volume: Optional[int] = None
    market_cap: Optional[int] = None

    # יסודות
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    eps: Optional[float] = None
    beta: Optional[float] = None
    dividend_yield: Optional[float] = None
    profit_margin: Optional[float] = None
    revenue: Optional[int] = None
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    debt_to_equity: Optional[float] = None
    return_on_equity: Optional[float] = None

    # אנליסטים
    target_mean_price: Optional[float] = None
    target_high_price: Optional[float] = None
    target_low_price: Optional[float] = None
    recommendation: Optional[str] = None
    analyst_count: Optional[int] = None

    # תמונת Finviz (ציבורי, hotlinkable)
    finviz_chart_url: str = ""
    finviz_page_url: str = ""

    # מטא
    fetched_at: datetime


def _safe_float(v) -> Optional[float]:
    try:
        if v is None:
            return None
        f = float(v)
        return f if f == f else None  # NaN check
    except (TypeError, ValueError):
        return None


def _safe_int(v) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _fetch_snapshot(symbol: str) -> dict:
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    info = ticker.info or {}
    if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
        # ננסה fast_info כפולבק
        try:
            fast = ticker.fast_info
            if fast and getattr(fast, "last_price", None):
                info = {
                    "currentPrice": fast.last_price,
                    "previousClose": getattr(fast, "previous_close", None),
                    "dayHigh": getattr(fast, "day_high", None),
                    "dayLow": getattr(fast, "day_low", None),
                    "marketCap": getattr(fast, "market_cap", None),
                }
            else:
                raise ValueError("no data")
        except Exception:
            raise HTTPException(status_code=404, detail=f"לא נמצא מידע למניה {symbol}")

    price = _safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
    prev = _safe_float(info.get("previousClose") or info.get("regularMarketPreviousClose"))
    day_change = ((price - prev) / prev * 100) if (price and prev) else None

    return {
        "symbol": symbol.upper(),
        "name": info.get("longName") or info.get("shortName"),
        "exchange": info.get("exchange") or info.get("fullExchangeName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "country": info.get("country"),
        "website": info.get("website"),
        "summary": (info.get("longBusinessSummary") or "")[:1000],

        "price": price,
        "previous_close": prev,
        "day_change_pct": round(day_change, 2) if day_change is not None else None,
        "day_high": _safe_float(info.get("dayHigh")),
        "day_low": _safe_float(info.get("dayLow")),
        "fifty_two_week_high": _safe_float(info.get("fiftyTwoWeekHigh")),
        "fifty_two_week_low": _safe_float(info.get("fiftyTwoWeekLow")),
        "volume": _safe_int(info.get("volume")),
        "avg_volume": _safe_int(info.get("averageVolume")),
        "market_cap": _safe_int(info.get("marketCap")),

        "pe_ratio": _safe_float(info.get("trailingPE")),
        "forward_pe": _safe_float(info.get("forwardPE")),
        "eps": _safe_float(info.get("trailingEps")),
        "beta": _safe_float(info.get("beta")),
        "dividend_yield": _safe_float(info.get("dividendYield")),
        "profit_margin": _safe_float(info.get("profitMargins")),
        "revenue": _safe_int(info.get("totalRevenue")),
        "revenue_growth": _safe_float(info.get("revenueGrowth")),
        "earnings_growth": _safe_float(info.get("earningsGrowth")),
        "debt_to_equity": _safe_float(info.get("debtToEquity")),
        "return_on_equity": _safe_float(info.get("returnOnEquity")),

        "target_mean_price": _safe_float(info.get("targetMeanPrice")),
        "target_high_price": _safe_float(info.get("targetHighPrice")),
        "target_low_price": _safe_float(info.get("targetLowPrice")),
        "recommendation": info.get("recommendationKey"),
        "analyst_count": _safe_int(info.get("numberOfAnalystOpinions")),

        "finviz_chart_url": f"https://finviz.com/chart.ashx?t={symbol.upper()}&ty=c&ta=1&p=d&s=l",
        "finviz_page_url": f"https://finviz.com/quote.ashx?t={symbol.upper()}",

        "fetched_at": datetime.utcnow(),
    }


@router.get("/{symbol}", response_model=StockSnapshot)
def get_stock(symbol: str):
    """מידע מקיף על מניה - יסודות, מסחר, אנליסטים, קישורי Finviz."""
    symbol = symbol.upper().strip()
    if not symbol or not symbol.isalnum() or len(symbol) > 6:
        raise HTTPException(status_code=400, detail="symbol לא תקין")

    cached = _CACHE.get(symbol)
    if cached and (datetime.utcnow() - cached[0]) < _CACHE_TTL:
        return cached[1]

    try:
        snap = _fetch_snapshot(symbol)
    except HTTPException:
        raise
    except Exception as e:
        log.warning("yfinance_fetch_failed", symbol=symbol, error=str(e))
        raise HTTPException(status_code=502, detail=f"yfinance error: {e}")

    _CACHE[symbol] = (datetime.utcnow(), snap)
    return snap


# קאש לוח שנה - דוחות לא משתנים בזמן אמת, שעה זה בסדר
_CALENDAR_CACHE: dict[str, tuple[datetime, dict]] = {}
_CALENDAR_TTL = timedelta(hours=1)


@router.get("/{symbol}/earnings")
def get_stock_earnings(symbol: str):
    """לוח דוחות + דיבידנד - תאריכים צפויים, אומדן EPS/הכנסות."""
    symbol = symbol.upper().strip()
    if not re.match(r"^[A-Z]{1,6}(\.[A-Z]{1,3})?$", symbol):
        raise HTTPException(status_code=400, detail="invalid symbol")

    cached = _CALENDAR_CACHE.get(symbol)
    if cached and (datetime.utcnow() - cached[0]) < _CALENDAR_TTL:
        return cached[1]

    def _iso(v):
        if v is None:
            return None
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return str(v)

    try:
        import yfinance as yf
        cal = yf.Ticker(symbol).calendar or {}
    except Exception as e:
        log.warning("earnings_fetch_failed", symbol=symbol, error=str(e))
        raise HTTPException(status_code=502, detail=str(e))

    out: dict = {"symbol": symbol, "fetched_at": datetime.utcnow().isoformat()}
    dates = cal.get("Earnings Date") or []
    if isinstance(dates, list):
        out["earnings_dates"] = [_iso(d) for d in dates if d is not None]
    elif dates:
        out["earnings_dates"] = [_iso(dates)]
    else:
        out["earnings_dates"] = []

    out["eps_estimate"] = _safe_float(cal.get("EPS Estimate"))
    out["eps_high"] = _safe_float(cal.get("EPS High"))
    out["eps_low"] = _safe_float(cal.get("EPS Low"))
    out["revenue_estimate"] = _safe_int(cal.get("Revenue Estimate"))
    out["revenue_high"] = _safe_int(cal.get("Revenue High"))
    out["revenue_low"] = _safe_int(cal.get("Revenue Low"))
    out["ex_dividend_date"] = _iso(cal.get("Ex-Dividend Date"))
    out["dividend_date"] = _iso(cal.get("Dividend Date"))

    _CALENDAR_CACHE[symbol] = (datetime.utcnow(), out)
    return out


_VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
_VALID_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"}


@router.get("/{symbol}/history")
def get_stock_history(
    symbol: str,
    period: str = Query("3mo"),
    interval: str = Query("1d"),
):
    """OHLC חתוך לפרק זמן + interval (לציור גרף נרות)."""
    symbol = symbol.upper().strip()
    if not re.match(r"^[A-Z]{1,6}(\.[A-Z]{1,3})?$", symbol):
        raise HTTPException(status_code=400, detail="invalid symbol")
    if period not in _VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"invalid period (allowed: {sorted(_VALID_PERIODS)})")
    if interval not in _VALID_INTERVALS:
        raise HTTPException(status_code=400, detail=f"invalid interval (allowed: {sorted(_VALID_INTERVALS)})")
    try:
        import yfinance as yf

        df = yf.Ticker(symbol).history(period=period, interval=interval)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    if df is None or df.empty:
        return {"symbol": symbol, "candles": []}

    candles = []
    for ts, row in df.iterrows():
        candles.append({
            "time": int(ts.timestamp()),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row["Volume"]) if row["Volume"] == row["Volume"] else 0,
        })
    return {"symbol": symbol, "interval": interval, "period": period, "candles": candles}
