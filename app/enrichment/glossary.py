"""תרגום עברי חכם ללא תלות ב-OpenAI - בונה כותרת מובנית מקצועית.

אסטרטגיה: במקום לתרגם מילה-במילה (שיוצר עירוב מבולגן של עברית ואנגלית),
מזהים את החלקים החשובים (סמל, כיוון, אחוז, אירוע) ובונים שורה תמציתית בעברית
שתופסת את הרעיון. אם אין מספיק מידע - מציגים תגית "מילות מפתח" עם רמזים.
"""
import re

# =================================================================
# מילון תווי-מפתח לאירועים שכיחים בכותרות פיננסיות
# כל מפתח: regex (case-insensitive) → תיוג עברי תמציתי
# =================================================================
EVENT_PATTERNS: list[tuple[str, str]] = [
    # Earnings & financials
    (r"\b(?:earnings?\s*(?:beat|crush|top|smash)|beats?\s*(?:est|expectation|consensus))", "📊 דוחות חזקים"),
    (r"\b(?:earnings?\s*(?:miss|disappoint|fall\s*short)|misses?\s*(?:est|expectation))", "📊 דוחות חלשים"),
    (r"\b(?:earnings?\s*(?:report|release|preview)|reports?\s*Q[1-4])", "📊 דוחות רבעוניים"),
    (r"\b(?:record\s*(?:revenue|earnings|quarter))", "📊 רבעון שיא"),
    (r"\b(?:guidance|outlook)\s*(?:raised|boost|hike)", "🎯 הגדלת תחזית"),
    (r"\b(?:guidance|outlook)\s*(?:cut|lowered|reduced)", "🎯 הקטנת תחזית"),

    # Fed / rates / macro
    (r"\bFed\s*(?:hike|raise|lift|increase)|rate\s*hike", "🏦 העלאת ריבית"),
    (r"\bFed\s*(?:cut|lower|slash|reduce)|rate\s*cut", "🏦 הורדת ריבית"),
    (r"\bFed\s*(?:hold|keep|maintain|pause)", "🏦 הפד משאיר ריבית"),
    (r"\bPowell\b", "🏦 פאוול / הפד"),
    (r"\bFOMC\b", "🏦 ועדת הפד"),
    (r"\b(?:CPI|inflation)\s*(?:cool|ease|fall|drop|decline)", "📉 אינפלציה יורדת"),
    (r"\b(?:CPI|inflation)\s*(?:rise|jump|surge|accelerate|hot)", "📈 אינפלציה עולה"),
    (r"\b(?:jobs?\s*report|payrolls?|unemployment)", "💼 דוח תעסוקה"),
    (r"\bGDP\b", "📈 תמ\"ג"),
    (r"\brecession\b", "⚠️ מיתון"),

    # Corporate actions (acquisition - דורש הקשר מובהק, לא "upgraded to buy")
    (r"\b(?:merger|acquisition|takeover\s+bid|to\s+acquire\s+[A-Z\$]|acquires?\s+[A-Z\$])", "🤝 מיזוג / רכישה"),
    (r"\b(?:IPO|initial\s*public\s*offering|going\s*public)", "🚀 הנפקה (IPO)"),
    (r"\b(?:stock\s*split|share\s*split|\d+[- ]for[- ]\d+\s*split)", "✂️ פיצול מניה"),
    (r"\b(?:dividend\s*(?:hike|raise|boost|increase))", "💰 העלאת דיבידנד"),
    (r"\b(?:dividend\s*(?:cut|reduce|suspend))", "💸 הקטנת דיבידנד"),
    (r"\bbuyback|share\s*repurchase", "🔄 רכישה חוזרת"),
    (r"\b(?:bankruptcy|chapter\s*11|chapter\s*7)\b", "💥 פשיטת רגל"),
    (r"\b(?:CEO|CFO)\s*(?:steps?\s*down|resigns?|fired|out)", "👤 שינוי הנהלה"),

    # Analyst actions
    (r"\b(?:upgrade[ds]?|raised\s*to\s*buy|price\s*target\s*raise)", "🎯 שדרוג אנליסט"),
    (r"\b(?:downgrade[ds]?|cut\s*to\s*sell|price\s*target\s*cut)", "⚠️ הורדת דירוג"),
    (r"\b(?:initiated\s*coverage|new\s*coverage)", "🆕 כיסוי אנליסט חדש"),

    # FDA / biotech / clinical
    (r"\bFDA\s*(?:approve|approval|grant)", "💊 FDA אישרה"),
    (r"\bFDA\s*(?:reject|denial|deny|warn)", "❌ FDA דחתה"),
    (r"\b(?:phase\s*[123]|clinical\s*trial)\s*(?:success|positive|meets?)", "🧪 ניסוי חיובי"),
    (r"\b(?:phase\s*[123]|clinical\s*trial)\s*(?:fail|miss|negative)", "🧪 ניסוי שלילי"),

    # Tariffs / trade / political
    (r"\btariff[s]?\b", "🌐 מכסים"),
    (r"\btrade\s*war", "⚔️ מלחמת סחר"),
    (r"\bsanctions?\b", "🚫 סנקציות"),
    (r"\b(?:Trump|White\s*House)\s*(?:announce|sign|say|propose)", "🏛 הבית הלבן"),

    # AI / tech
    (r"\bAI\s*(?:boom|rally|surge|hype)", "🤖 ראלי AI"),
    (r"\bAI\s*(?:bubble|fears?|crash|correction)", "🫧 חששות בועת AI"),
    (r"\bchip(?:s|maker)?\b", "💾 שבבים"),

    # Crypto - הקלות לפסיכון בין המילים
    (r"\b(?:bitcoin|BTC)\b[^.]{0,40}?(?:record|all[- ]?time|new\s*high)", "₿ ביטקוין בשיא"),
    (r"\b(?:bitcoin|BTC)\b[^.]{0,30}?(?:crash|plunge|tumble|dump)", "₿ ביטקוין צונח"),
    (r"\bbitcoin\b|\bcrypto\b", "₿ קריפטו"),

    # Broad market
    (r"\b(?:S&P|Nasdaq|Dow)\s*(?:record|high|all[- ]?time)", "🏆 שווקים בשיא"),
    (r"\bsell[- ]?off\b|\bcorrection\b", "📉 גל מכירות"),
    (r"\bvolatility\s*spike|VIX\s*surge", "⚡ זינוק תנודתיות"),
    (r"\bbull\s*market", "🐂 שוק שורי"),
    (r"\bbear\s*market", "🐻 שוק דובי"),
]

# מילים בודדות לרמזים (כשאין pattern מלא)
KEYWORDS: dict[str, str] = {
    "earnings": "רווחים", "revenue": "הכנסות", "EPS": "רווח למניה",
    "guidance": "תחזית", "outlook": "תחזית",
    "Fed": "הפד", "FOMC": "ועדת הפד", "Powell": "פאוול",
    "rate": "ריבית", "rates": "ריבית", "yield": "תשואה",
    "inflation": "אינפלציה", "CPI": "אינפלציה",
    "recession": "מיתון", "GDP": "תמ\"ג",
    "merger": "מיזוג", "acquisition": "רכישה",
    "IPO": "הנפקה", "dividend": "דיבידנד", "buyback": "רכישה חוזרת",
    "tariff": "מכסים", "tariffs": "מכסים", "China": "סין",
    "AI": "AI", "chip": "שבבים", "chips": "שבבים",
    "bitcoin": "ביטקוין", "crypto": "קריפטו",
    "Trump": "טראמפ", "Biden": "ביידן",
    "FDA": "FDA",
    "split": "פיצול",
    "volatility": "תנודתיות", "VIX": "פחד",
}

# =================================================================
# זיהוי מבני: כיוון, אחוז, סמל
# =================================================================
BULLISH_RE = re.compile(
    r"\b(?:soar|surge|jump|rally|gain|rise|climb|spike|pop|rocket|moon|bull|"
    r"breakout|outperform|beat|strong|record)\w*", re.IGNORECASE,
)
BEARISH_RE = re.compile(
    r"\b(?:plunge|tumble|drop|fall|sink|crash|tank|slide|dump|bear|sell-?off|"
    r"miss|weak|underperform|disappoint)\w*", re.IGNORECASE,
)
TICKER_RE = re.compile(r"\$([A-Z]{2,5})\b")
TICKER_BARE_RE = re.compile(r"\b([A-Z]{2,5})\b")
PCT_RE = re.compile(r"([+-]?\d{1,3}(?:\.\d+)?)\s*%")
PRICE_RE = re.compile(r"\$\s*(\d{1,4}(?:\.\d+)?)")


def translate_headline(text: str) -> tuple[str, bool]:
    """מחזיר (translation, is_full_translation).

    הגישה החדשה:
    1. מזהה את האירוע העיקרי (event) ע"י pattern matching.
    2. מזהה כיוון (📈/📉), אחוז, סמל.
    3. בונה כותרת תמציתית מובנית בעברית: 'TICKER · 📈 +5% · 📊 דוחות חזקים'
    4. אם לא נמצא כלום משמעותי - מחזיר ריק.
    """
    if not text:
        return "", False

    # נקה רעש שכיח של StockTwits
    cleaned = re.sub(r"\[👍\s*\d+\s*\|\s*💬\s*\d+\]\s*", "", text)
    cleaned = re.sub(r"\[(?:Bullish|Bearish)[^\]]*\]", "", cleaned)
    cleaned = re.sub(r"https?://\S+", "", cleaned).strip()

    # 1. מצא אירוע עיקרי (1 בלבד - הראשון שתפס)
    events: list[str] = []
    for pattern, label in EVENT_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            events.append(label)
            break

    # 2. כיוון
    direction = ""
    if BULLISH_RE.search(cleaned):
        direction = "📈 עליה"
    elif BEARISH_RE.search(cleaned):
        direction = "📉 ירידה"

    # 3. סמל מנייה (קודם עם $, אחר כך bare ALL-CAPS)
    tickers = TICKER_RE.findall(cleaned)
    if not tickers:
        # סינון מילים אנגליות נפוצות שנראות כמו tickers
        skip = {"USA", "USD", "CEO", "CFO", "IPO", "AI", "GDP", "CPI", "FED",
                "FOMC", "FDA", "SEC", "NYC", "ETF", "VIX", "ATH", "EPS",
                "RSI", "API", "URL", "PR", "Q1", "Q2", "Q3", "Q4", "YTD",
                "OMG", "WTF", "LOL", "BTW", "FYI", "TBD", "ASAP", "ETA",
                "RSV", "COVID", "BTC", "ETH", "USA", "UK", "EU", "UN",
                "NATO", "OPEC", "TV", "VR", "AR", "VPN", "GPS", "USB",
                "ML", "GPT", "LLM", "EV", "SUV", "DUI", "HR", "IT", "MBA"}
        bare = [t for t in TICKER_BARE_RE.findall(cleaned) if t not in skip]
        tickers = bare[:2]
    tickers = list(dict.fromkeys(tickers))[:3]  # unique, max 3

    # 4. אחוז
    pct_match = PCT_RE.search(cleaned)
    pct = pct_match.group(0).replace(" ", "") if pct_match else ""

    # 5. בנה
    parts: list[str] = []
    if tickers:
        parts.append("/".join(tickers))
    if direction:
        if pct:
            parts.append(f"{direction} {pct}")
        else:
            parts.append(direction)
    elif pct:
        parts.append(pct)
    for ev in events:
        parts.append(ev)

    # 'אירוע משמעותי' (event מזוהה) → תרגום מלא גם בלי ticker/אחוז
    if events or len(parts) >= 2:
        if not parts:
            parts = events
        return " · ".join(parts), True

    # 6. fallback - מילות מפתח מהמילון
    text_lower = cleaned.lower()
    hints: list[str] = []
    seen: set[str] = set()
    for en, heb in KEYWORDS.items():
        if heb in seen:
            continue
        if re.search(r"\b" + re.escape(en.lower()) + r"\b", text_lower):
            hints.append(heb)
            seen.add(heb)
        if len(hints) >= 4:
            break
    if hints:
        return " · ".join(hints), False
    return "", False


def quick_translate(text: str) -> str:
    """תאימות לאחור."""
    out, _ = translate_headline(text)
    return out


def add_glossary_to_items(items: list[dict]) -> list[dict]:
    """מוסיף תרגום/הסבר עברי לפריטים שאין להם תרגום OpenAI.

    is_full=True → hebrew_translation (כותרת תמציתית מובנית)
    is_full=False → hebrew_explanation (מילות מפתח בלבד)
    """
    for it in items:
        if it.get("hebrew_translation"):
            continue  # יש OpenAI translation
        text = it.get("text", "")
        translated, is_full = translate_headline(text)
        if not translated:
            continue
        if is_full:
            it["hebrew_translation"] = translated
            # אל תוסיף 'explanation' כשיש translation - זה מבלגן
        else:
            it["hebrew_explanation"] = translated
    return items


# =================================================================
# תאימות לאחור (קוד ישן עוד מייבא את אלה)
# =================================================================
PATTERNS_CASE_SENSITIVE: list = []
PATTERNS_CASE_INSENSITIVE: list = [(p, l) for p, l in EVENT_PATTERNS]
PATTERNS = PATTERNS_CASE_INSENSITIVE
WORDS = KEYWORDS
