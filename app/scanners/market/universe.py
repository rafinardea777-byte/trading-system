"""רשימת מניות לסריקה - מאוחדת, ללא כפילויות ובלי הבאג של חוסר פסיק."""
from app.core.logging import get_logger

log = get_logger(__name__)

# קבוצות נושאיות - ניתן לערוך בנפרד
AI_TECH = [
    "NVDA", "AMD", "SMCI", "AVGO", "ARM", "ORCL", "CRWV", "NBIS",
    "SOUN", "BBAI", "IONQ", "QUBT", "RGTI", "QBTS", "ARQQ", "MSFT",
    "GOOG", "META", "AMZN", "AAPL", "TSM", "INTC", "QCOM", "MU",
    "AMAT", "LRCX", "KLAC", "MRVL", "SNOW", "PLTR", "DDOG", "NET",
    "CRWD", "ZS", "PANW", "OKTA", "GTLB", "PATH", "AI", "CFLT",
]

CRYPTO = [
    "IREN", "MARA", "RIOT", "CLSK", "CORZ", "CIFR", "BTBT", "HUT",
    "MSTR", "COIN", "HOOD", "WULF", "BITI", "GBTC", "IBIT",
    "ARBK", "HIVE", "BITF", "DMGI", "BTDR",
]

EV_ENERGY = [
    "TSLA", "RIVN", "LCID", "NIO", "XPEV", "LI", "FFIE",
    "PLUG", "FCEL", "BE", "CHPT", "BLNK", "EVGO", "PTRA",
    "FSR", "GOEV", "WKHS", "REX", "SPWR", "ENPH", "SEDG",
]

BIOTECH = [
    "NVAX", "MRNA", "BNTX", "SAVA", "ACHR", "JOBY", "LILM",
    "SRPT", "BEAM", "EDIT", "NTLA", "CRSP", "FATE", "BLUE",
    "OCGN", "ATOS", "VXRT", "INO", "DVAX", "RCKT", "DAWN",
    "GILD", "BIIB", "REGN", "VRTX", "ALNY", "INCY",
]

MOMENTUM = [
    "GME", "AMC", "BBBY", "SOFI", "UPST", "AFRM",
    "DKNG", "RBLX", "SNAP", "PINS", "RDDT", "UBER", "LYFT",
    "ABNB", "DASH", "GRAB", "SE", "SHOP", "SQ", "PYPL",
    "OPEN", "UWMC", "RKT", "CLOV", "WISH",
]

DEFENSE = [
    "AXON", "KTOS", "LDOS", "CACI", "RCAT",
    "HII", "LMT", "RTX", "NOC", "GD", "BA", "TDG",
]

FINANCE = [
    "JPM", "BAC", "GS", "MS", "C", "WFC", "BLK",
    "SCHW", "IBKR", "NDAQ", "ICE", "CME", "V", "MA",
]

ROBOTICS_LIDAR = [
    "IRBT", "HYLN", "LAZR", "LIDR", "OUST",
    "AEYE", "MVIS", "INVZ", "AEVA", "VLDR",
]

COMMODITIES_ENERGY = [
    "XOM", "CVX", "COP", "OXY", "SLB", "HAL",
    "FCX", "NEM", "GOLD", "WPM", "AG", "PAAS",
]

# רשימה ידנית - ללא כפילויות, מובטח שכל איבר הוא מחרוזת תקנית
CURATED_SYMBOLS = list(dict.fromkeys(
    AI_TECH + CRYPTO + EV_ENERGY + BIOTECH + MOMENTUM
    + DEFENSE + FINANCE + ROBOTICS_LIDAR + COMMODITIES_ENERGY
))


def fetch_sp500() -> list[str]:
    """מנסה להוריד S&P 500 מ-GitHub (לא חובה)."""
    try:
        import pandas as pd
        df = pd.read_csv(
            "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
        )
        return df["Symbol"].tolist()
    except Exception as e:
        log.warning("sp500_fetch_failed", error=str(e))
        return []


def get_universe(include_sp500: bool = True) -> list[str]:
    """מחזיר את רשימת המניות הסופית לסריקה."""
    symbols = list(CURATED_SYMBOLS)
    if include_sp500:
        sp500 = fetch_sp500()
        symbols = list(dict.fromkeys(symbols + sp500))
    log.info("universe_built", total=len(symbols), curated=len(CURATED_SYMBOLS))
    return symbols
