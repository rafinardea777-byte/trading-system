"""חילוץ סמלי מניות מטקסט חדשות - $TICKER + שמות חברות נפוצות."""
import re

# Regex ל-$TICKER (פורמט סטנדרטי בפיננסים)
_DOLLAR_TICKER = re.compile(r"\$([A-Z]{1,5})\b")

# Regex ל-ALL CAPS symbols חופשיים בטקסט (זהירות עם false positives)
_BARE_TICKER = re.compile(r"\b([A-Z]{2,5})\b")

# מילים שאסור להחשיב כסמלים גם אם בכל הCaps
_BLACKLIST = {
    "CEO", "CFO", "CTO", "COO", "USA", "FED", "EU", "UK", "EPS", "GDP", "CPI",
    "PCE", "FOMC", "SEC", "IPO", "ETF", "LLC", "INC", "AI", "ML", "API",
    "URL", "HTML", "CSS", "JS", "TV", "PR", "HQ", "ID", "OK", "NEW", "USD",
    "UAE", "ECB", "BOJ", "PCE", "AP", "WSJ", "CNN", "BBC", "FBI", "CIA",
    "FDA", "EPA", "DOJ", "IRS", "DOE", "NSA", "NATO", "UN", "WHO",
    "BREAKING", "MARKETS", "STOCKS", "BONDS", "TODAY", "WALL", "STREET",
    "DOW", "JONES", "NEWS", "RATE", "CUT", "CUTS", "EARNINGS", "JOBS",
    "INFLATION", "RECESSION", "RALLY", "CRASH", "RECORD", "HIGH", "LOW",
    "OPEN", "CLOSE", "BUY", "SELL", "HOLD", "BULL", "BEAR",
    # מקורות תקשורת - שלא ייתפסו כסמלים
    "CNBC", "BBCNEWS", "ABCNEWS", "NBCNEWS", "CBSNEWS", "FOX", "AXIOS",
    "BLOOMBERG", "REUTERS", "FORBES", "CNN", "BBC", "ABC", "NBC", "CBS",
    "TWITTER", "X", "META", "PRESS", "RELEASE",
    # מילים תכופות בכותרות
    "QUARTER", "YEAR", "MONTH", "WEEK", "DAY", "TIME", "PRICE", "DEAL",
    "PLAN", "PLANS", "REPORT", "STUDY", "SAID", "SAYS", "TELLS", "ASKS",
    "AHEAD", "AFTER", "BEFORE", "DURING", "WHILE", "WHEN", "WHERE",
    "WHAT", "WHY", "HOW", "WHO", "THE", "AND", "BUT", "FOR", "WITH",
    "POSTS", "POST", "VIEWS", "VIEW", "TAKES", "TAKE", "TAKING",
    "NEAR", "OVER", "UNDER", "ABOVE", "BELOW", "INTO", "FROM", "TO",
    "TIPS", "TIP", "DEAL", "DEALS", "TALK", "TALKS", "FACE", "FACES",
}

# מיפוי שם חברה → סמל. רק חברות נפוצות מאוד שיופיעו בחדשות.
COMPANY_NAMES = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "amazon": "AMZN",
    "google": "GOOG",
    "alphabet": "GOOG",
    "tesla": "TSLA",
    "nvidia": "NVDA",
    "meta": "META",
    "facebook": "META",
    "netflix": "NFLX",
    "intel": "INTC",
    "amd": "AMD",
    "advanced micro devices": "AMD",
    "broadcom": "AVGO",
    "qualcomm": "QCOM",
    "oracle": "ORCL",
    "salesforce": "CRM",
    "adobe": "ADBE",
    "palantir": "PLTR",
    "snowflake": "SNOW",
    "datadog": "DDOG",
    "cloudflare": "NET",
    "crowdstrike": "CRWD",
    "zscaler": "ZS",
    "palo alto": "PANW",
    "okta": "OKTA",
    "shopify": "SHOP",
    "paypal": "PYPL",
    "visa": "V",
    "mastercard": "MA",
    "jpmorgan": "JPM",
    "jp morgan": "JPM",
    "goldman sachs": "GS",
    "morgan stanley": "MS",
    "bank of america": "BAC",
    "wells fargo": "WFC",
    "blackrock": "BLK",
    "citigroup": "C",
    "schwab": "SCHW",
    "berkshire": "BRK.B",
    "exxon": "XOM",
    "chevron": "CVX",
    "boeing": "BA",
    "lockheed": "LMT",
    "raytheon": "RTX",
    "general motors": "GM",
    "ford": "F",
    "rivian": "RIVN",
    "lucid": "LCID",
    "nio": "NIO",
    "uber": "UBER",
    "lyft": "LYFT",
    "airbnb": "ABNB",
    "doordash": "DASH",
    "robinhood": "HOOD",
    "coinbase": "COIN",
    "microstrategy": "MSTR",
    "marathon digital": "MARA",
    "riot platforms": "RIOT",
    "moderna": "MRNA",
    "pfizer": "PFE",
    "johnson & johnson": "JNJ",
    "eli lilly": "LLY",
    "merck": "MRK",
    "walmart": "WMT",
    "costco": "COST",
    "target": "TGT",
    "home depot": "HD",
    "mcdonald": "MCD",
    "starbucks": "SBUX",
    "disney": "DIS",
    "spotify": "SPOT",
    "reddit": "RDDT",
    "snap": "SNAP",
    "pinterest": "PINS",
    "square": "SQ",
    "block": "SQ",
    "sofi": "SOFI",
    "upstart": "UPST",
    "affirm": "AFRM",
    "draftkings": "DKNG",
    "roblox": "RBLX",
    "samsung": "005930.KS",  # קוריאני - לא נסחר ב-NYSE
    "tsmc": "TSM",
    "taiwan semiconductor": "TSM",
    "alibaba": "BABA",
    "baidu": "BIDU",
    "jd.com": "JD",
}


def extract_symbols(text: str) -> set[str]:
    """מחזיר set של סמלי מניות שצוינו בטקסט."""
    if not text:
        return set()

    out: set[str] = set()

    # 1. $TICKER פורמט - הכי אמין
    for sym in _DOLLAR_TICKER.findall(text):
        out.add(sym.upper())

    # 2. שמות חברות נפוצות (case-insensitive)
    text_lower = text.lower()
    for company, sym in COMPANY_NAMES.items():
        # word boundary - "apple" לא ייתפס בתוך "applesauce"
        if re.search(r"\b" + re.escape(company) + r"\b", text_lower):
            out.add(sym)

    # 3. סמלים חשופים בקפיטל (מסוכן יותר - filter blacklist)
    for sym in _BARE_TICKER.findall(text):
        if sym in _BLACKLIST or len(sym) < 2:
            continue
        # חייב להיות לפחות 3 אותיות כדי להיות בטוחים יותר
        if len(sym) >= 3:
            out.add(sym)

    return out


def extract_symbols_csv(text: str) -> str:
    """מחזיר מחרוזת CSV של הסמלים, להאחסון ב-DB."""
    syms = extract_symbols(text)
    return ",".join(sorted(syms)) if syms else ""
