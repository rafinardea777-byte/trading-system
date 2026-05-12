"""רשימת מניות לסריקה - מאוחדת, ללא כפילויות ובלי הבאג של חוסר פסיק."""
from app.core.logging import get_logger

log = get_logger(__name__)

# =================================================================
# מניות אמריקאיות לפי קטגוריות
# =================================================================

AI_TECH = [
    # Mega-cap AI
    "NVDA", "AMD", "AVGO", "TSM", "ARM", "INTC", "QCOM", "MU", "MRVL",
    "AMAT", "LRCX", "KLAC", "ASML", "TXN", "ADI", "MCHP", "NXPI",
    # AI Software
    "MSFT", "GOOG", "GOOGL", "META", "AMZN", "AAPL", "ORCL", "CRM",
    "ADBE", "NOW", "INTU", "WDAY", "PLTR", "SNOW", "DDOG", "NET",
    # AI native / pure-play
    "AI", "SOUN", "BBAI", "RKLB", "CRWV", "NBIS", "PATH", "U", "CFLT",
    "ESTC", "MDB", "GTLB", "S", "ANET", "FROG", "DOCN", "TWLO",
]

SEMICONDUCTORS = [
    "ON", "MPWR", "WOLF", "SWKS", "QRVO", "TER", "ENTG", "AMBA", "POWI",
    "RMBS", "SIMO", "SLAB", "CRUS", "FORM", "ACLS", "AEHR", "CEVA",
    "ICHR", "UCTT", "VECO", "BRKS",
]

QUANTUM = [
    "IONQ", "QUBT", "RGTI", "QBTS", "ARQQ", "IBM",
]

CRYPTO_MINING = [
    "IREN", "MARA", "RIOT", "CLSK", "CORZ", "CIFR", "BTBT", "HUT",
    "MSTR", "COIN", "HOOD", "WULF", "BITF", "BTDR", "HIVE", "ARBK",
    "GBTC", "IBIT", "BITO", "DAPP", "WGMI",
]

EV_BATTERY = [
    "TSLA", "RIVN", "LCID", "NIO", "XPEV", "LI", "ZEEV", "GOEV",
    "MULN", "NKLA", "FFIE", "VLD", "FSR", "WKHS", "REE", "RIDE",
    "ENVX", "QS", "MBLY", "LAZR", "INVZ", "LIDR", "OUST", "AEVA",
    # Battery / energy storage
    "ENPH", "SEDG", "PLUG", "FCEL", "BE", "BLDP", "AMPX", "STEM",
]

EV_CHARGING = [
    "CHPT", "BLNK", "EVGO", "WBX", "WAVE", "PTRA", "ADV",
]

CLEAN_ENERGY = [
    "FSLR", "RUN", "SPWR", "NOVA", "ARRY", "SHLS", "SUNW",
    "TPIC", "NEE", "BEPC", "BEP", "AY", "CWEN", "VST", "TLN",
]

SPACE = [
    "RKLB", "ASTS", "PL", "RDW", "MNTS", "BKSY", "SPIR", "LMT",
    "BA", "NOC", "GD", "TDG", "HEI", "AJRD", "MOG.A",
]

DEFENSE = [
    "LMT", "RTX", "NOC", "GD", "BA", "TDG", "AXON", "KTOS", "LDOS",
    "CACI", "RCAT", "HII", "PSN", "TGE", "AVAV", "ONDS", "DRS",
    "MRCY", "BWXT", "VVX", "KVHI", "ATEN",
]

CYBERSECURITY = [
    "CRWD", "PANW", "FTNT", "ZS", "S", "OKTA", "NET", "QLYS", "TENB",
    "CYBR", "VRNS", "RPD", "OSPN", "FFIV", "CHKP", "MNDY", "FRSH",
]

ROBOTICS_AUTOMATION = [
    "SYM", "ROK", "ABB", "IRBT", "ISRG", "AUR", "TER", "EMR",
    "FANUY", "KUKA", "ZBRA",
]

BIOTECH_LARGE = [
    "GILD", "BIIB", "REGN", "VRTX", "ALNY", "INCY", "MRNA", "BNTX",
    "PFE", "JNJ", "LLY", "MRK", "ABBV", "AMGN", "BMY", "ZTS",
]

BIOTECH_SMALL = [
    "NVAX", "SAVA", "SRPT", "BEAM", "EDIT", "NTLA", "CRSP", "FATE",
    "BLUE", "OCGN", "ATOS", "VXRT", "INO", "DVAX", "RCKT", "DAWN",
    "ARWR", "IONS", "ALKS", "EXEL", "EXAS", "VEEV", "ILMN", "TWST",
    "PACB", "GH", "NTRA", "10X", "OMIC", "SDGR",
]

FINANCIALS_BANKS = [
    "JPM", "BAC", "GS", "MS", "C", "WFC", "BLK", "SCHW", "STT", "USB",
    "PNC", "TFC", "CFG", "FITB", "KEY", "RF", "MTB", "HBAN", "ZION",
    "WAL", "FCNCA", "BRK.B",
]

FINANCIALS_EXCHANGES_PAY = [
    "V", "MA", "AXP", "PYPL", "SQ", "FIS", "GPN", "FI", "WU", "RKT",
    "IBKR", "NDAQ", "ICE", "CME", "CBOE", "MKTX", "TROW", "BX",
    "KKR", "APO", "ARES", "OWL", "TPG", "BAM",
]

FINTECH_DISRUPT = [
    "SOFI", "UPST", "AFRM", "HOOD", "LU", "OPEN", "UWMC", "GNRC",
    "ALLY", "DFS",
]

MOMENTUM_MEME = [
    "GME", "AMC", "BB", "CLOV", "WISH", "TLRY", "SNDL", "RDDT",
    "PINS", "SNAP", "RBLX", "ROKU", "DKNG", "PENN", "FUBO",
]

CONSUMER_INTERNET = [
    "UBER", "LYFT", "ABNB", "DASH", "GRAB", "SE", "SHOP", "MELI",
    "ETSY", "EBAY", "PINS", "SPOT", "NFLX", "DIS", "WBD",
]

CONSUMER_RETAIL = [
    "WMT", "COST", "TGT", "HD", "LOW", "BBY", "DG", "DLTR", "AMZN",
    "TJX", "ROST", "ULTA", "LULU", "NKE", "DECK", "ANF", "AEO",
    "BURL", "FIVE", "CHWY",
]

FOOD_BEV = [
    "MCD", "SBUX", "CMG", "QSR", "DPZ", "WING", "TXRH", "DRI",
    "KO", "PEP", "MNST", "CELH", "STZ", "TAP", "BUD", "DEO", "BF.B",
]

ENERGY_OIL = [
    "XOM", "CVX", "COP", "OXY", "SLB", "HAL", "BKR", "DVN", "EOG",
    "PXD", "FANG", "MRO", "APA", "MPC", "PSX", "VLO", "TRGP", "ET",
    "WMB", "OKE", "KMI", "EQT", "AR",
]

MATERIALS_MINING = [
    "FCX", "NEM", "GOLD", "WPM", "AG", "PAAS", "MP", "URNM", "CCJ",
    "DNN", "UEC", "URA", "SAND", "AEM", "FNV", "BTG", "EXK", "HL",
    "MUX", "AUY", "VALE", "RIO", "BHP", "GLEN.L",
]

INDUSTRIAL_AERO = [
    "BA", "CAT", "DE", "MMM", "GE", "HON", "ITW", "ETN", "PH",
    "ROK", "EMR", "DOV", "IR", "PWR", "GWW", "MAS",
]

RECENT_IPO_HOT = [
    "RDDT", "ARM", "CART", "IBTA", "KVYO", "BIRK", "RXRX", "MBLY",
    "OWL", "ASTS", "RDDT", "ROVR", "GHC",
]

NUCLEAR_POWER = [
    "OKLO", "SMR", "BWXT", "CCJ", "NXE", "URNM", "URA", "DNN", "UEC",
    "LEU", "VST",
]

# =================================================================
# מניות ישראליות
# =================================================================

# חברות ישראליות שנסחרות בארה"ב (NASDAQ/NYSE) - הכי קל לסריקה
ISRAEL_US_LISTED = [
    "TEVA",      # טבע פרמצבטיקה
    "CHKP",      # צ'ק פוינט
    "NICE",      # NICE מערכות
    "CYBR",      # CyberArk
    "WIX",       # Wix.com
    "MNDY",      # Monday.com
    "FVRR",      # Fiverr
    "FROG",      # JFrog
    "NVMI",      # Nova Measuring
    "ESLT",      # אלביט מערכות
    "PLTK",      # Playtika
    "AUDC",      # AudioCodes
    "MGIC",      # מג'יק תוכנה
    "NNDM",      # Nano Dimension
    "GLBE",      # Global-e Online
    "ZIM",       # זים שירותי ספנות
    "INMD",      # InMode
    "ORMP",      # Oramed Pharma
    "CGNT",      # Cognyte Software
    "VRNT",      # Verint Systems
    "TARO",      # Taro Pharma
    "ICCM",      # IceCure Medical
    "ICL",       # כיל (גם בארה"ב)
    "PERI",      # Perion Network
    "FORTY",     # Formula Systems
    "CAMT",      # קמטק
    "ALLT",      # Allot Communications
    "ARBE",      # Arbe Robotics
    "GILT",      # Gilat Satellite
    "NVEI",      # Nuvei
    "PAYO",      # Payoneer
    "OPRA",      # אופרה
    "RDWR",      # Radware
    "TARO",      # Taro Pharma
]

# מניות TASE שאינן דואל-listed - דורש סיומת .TA
ISRAEL_TASE_ONLY = [
    # בנקים
    "POLI.TA",   # פועלים
    "LUMI.TA",   # לאומי
    "DSCT.TA",   # דיסקונט
    "MZTF.TA",   # מזרחי טפחות
    "FIBI.TA",   # הבינלאומי
    # נדל"ן
    "AZRG.TA",   # אזריאלי
    "MLSR.TA",   # מליסרון
    "BIG.TA",    # ביג מרכזי קניות
    "AMOT.TA",   # עמוס דלן
    "GZT.TA",    # גזית גלוב
    "ALDR.TA",   # אלרוב נדל"ן
    # תקשורת
    "BEZQ.TA",   # בזק
    "CEL.TA",    # סלקום
    "PTNR.TA",   # פרטנר
    "HOT.TA",    # הוט תקשורת
    # אנרגיה/תשתיות
    "PAZ.TA",    # פז נפט
    "DELT.TA",   # דלק קבוצה
    "ORMT.TA",   # אורמת
    "RTLS.TA",   # ריטיילורס (חברת ניווט)
    # תעשייה
    "ICL.TA",    # כיל (גם US)
    "STRS.TA",   # שטראוס
    "TEVA.TA",   # טבע (גם US)
    # קמעונאות / צריכה
    "SHUF.TA",   # שופרסל
    "RMLI.TA",   # רמי לוי
    "OSEM.TA",   # אסם
    "FOX.TA",    # פוקס ויזל
    "DLEA.TA",   # דלק רכב
    # ביטוח
    "PHOE.TA",   # הפניקס
    "MGDL.TA",   # מגדל
    "HARL.TA",   # הראל
    "KLIL.TA",   # כלל ביטוח
    # תעשיות אחרות
    "NICE.TA",   # NICE
    "ELCO.TA",   # אלקטרה
    "OPK.TA",    # OPKO Health
    "KAMN.TA",   # קמהדע
    "INRM.TA",   # אינרום (חברת בנייה)
    "DANEL.TA",  # דנאל
    # ביוטק
    "TEVA.TA",   # טבע
    "OPK.TA",    # אופקו
    "TGT1.TA",   # אלביט הדמיה
]

# =================================================================
# רשימות מאוחדות
# =================================================================

US_ALL = list(dict.fromkeys(
    AI_TECH + SEMICONDUCTORS + QUANTUM + CRYPTO_MINING
    + EV_BATTERY + EV_CHARGING + CLEAN_ENERGY + SPACE
    + DEFENSE + CYBERSECURITY + ROBOTICS_AUTOMATION
    + BIOTECH_LARGE + BIOTECH_SMALL
    + FINANCIALS_BANKS + FINANCIALS_EXCHANGES_PAY + FINTECH_DISRUPT
    + MOMENTUM_MEME + CONSUMER_INTERNET + CONSUMER_RETAIL + FOOD_BEV
    + ENERGY_OIL + MATERIALS_MINING + INDUSTRIAL_AERO + RECENT_IPO_HOT
    + NUCLEAR_POWER
))

ISRAEL_ALL = list(dict.fromkeys(ISRAEL_US_LISTED + ISRAEL_TASE_ONLY))

CURATED_SYMBOLS = list(dict.fromkeys(US_ALL + ISRAEL_ALL))


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


def get_universe(
    include_sp500: bool = True,
    include_israel: bool = True,
) -> list[str]:
    """מחזיר את רשימת המניות הסופית לסריקה."""
    symbols = list(US_ALL)
    if include_israel:
        symbols.extend(ISRAEL_ALL)
    if include_sp500:
        sp500 = fetch_sp500()
        symbols = list(dict.fromkeys(symbols + sp500))
    else:
        symbols = list(dict.fromkeys(symbols))

    log.info(
        "universe_built",
        total=len(symbols),
        us=len(US_ALL),
        israel=len(ISRAEL_ALL) if include_israel else 0,
    )
    return symbols
