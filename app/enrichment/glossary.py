"""תרגום עברי ללא תלות ב-OpenAI - תבניות + מילון מורחב."""
import re

# =================================================================
# תבניות תלויות-רישיות (case-sensitive) - לסמלי מניות
# =================================================================
PATTERNS_CASE_SENSITIVE = [
    # Ticker movements
    (r"\b([A-Z]{2,5})\b\s*(?:stock\s*)?(?:soars?|surges?|jumps?|rockets?|skyrockets?)",
     r"\1 מזנקת"),
    (r"\b([A-Z]{2,5})\b\s*(?:stock\s*)?(?:plunges?|tumbles?|drops?|sinks?|tanks?|crashes?)",
     r"\1 צונחת"),
    (r"\b([A-Z]{2,5})\b\s*(?:stock\s*)?(?:rises?|gains?|climbs?)",
     r"\1 עולה"),
    (r"\b([A-Z]{2,5})\b\s*(?:stock\s*)?(?:falls?|slips?|declines?)",
     r"\1 יורדת"),
    (r"\b([A-Z]{2,5})\b\s*(?:hits?|reaches?)\s*(?:new\s*)?(?:all[- ]time\s*)?high",
     r"\1 שיא חדש"),
    (r"\b([A-Z]{2,5})\b\s*(?:hits?|reaches?)\s*(?:new\s*)?(?:all[- ]time\s*)?low",
     r"\1 שפל חדש"),
    (r"\b([A-Z]{2,5})\b\s*(?:earnings|results)\s*(?:beat|crush(?:es)?|smash(?:es)?|top)",
     r"\1 דיווחה רווחים מעל הצפי"),
    (r"\b([A-Z]{2,5})\b\s*(?:earnings|results)\s*(?:miss|disappoint)",
     r"\1 דיווחה רווחים מתחת לצפי"),
    (r"\b([A-Z]{2,5})\b\s*reports\s*(?:Q[1-4]|record|strong)\s*(?:earnings|results|revenue)",
     r"\1 דיווחה תוצאות חזקות"),
    (r"\b([A-Z]{2,5})\b\s*(?:to\s*acquire|buys?|acquires?)\s*",
     r"\1 רוכשת את "),
    (r"merger\s*(?:between|of)\s*([A-Z]{2,5})\s*and\s*([A-Z]{2,5})",
     r"מיזוג בין \1 ל-\2"),
]

# =================================================================
# תבניות שלא-תלויות-רישיות (case-insensitive) - לביטויים כלליים
# =================================================================
PATTERNS_CASE_INSENSITIVE = [
    # Earnings generic
    (r"earnings\s*(?:beat|smash|crush|top)", "רווחים מעל הצפי"),
    (r"earnings\s*(?:miss|fall\s*short|disappoint)", "רווחים מתחת לצפי"),
    (r"record\s*(?:quarter|earnings|revenue)", "רבעון שיא"),

    # Fed / rates
    (r"\bFed\s*(?:hikes?|raises?|lifts?)\s*(?:interest\s*)?rates?", "הפד מעלה ריבית"),
    (r"\bFed\s*(?:cuts?|lowers?|slashes?)\s*(?:interest\s*)?rates?", "הפד מוריד ריבית"),
    (r"\bFed\s*(?:holds?|keeps?|maintains?)\s*rates?", "הפד משאיר ריבית"),
    (r"rate\s*cut", "הורדת ריבית"),
    (r"rate\s*hike", "העלאת ריבית"),
    (r"Powell\s*(?:says?|signals?|hints?)", "פאוול הודיע"),

    # Inflation
    (r"(?:CPI|inflation)\s*(?:cools?|eases?|falls?|drops?|declines?)", "האינפלציה מתמתנת"),
    (r"(?:CPI|inflation)\s*(?:rises?|jumps?|surges?|accelerates?)", "האינפלציה מאיצה"),
    (r"hot\s*(?:CPI|inflation)", "אינפלציה גבוהה מהצפי"),

    # Market broad
    (r"(?:S&P|S&P\s*500|Dow|Dow\s*Jones|Nasdaq)\s*(?:hits?|reach(?:es)?)\s*(?:new\s*)?(?:record|all[- ]time\s*high)",
     "השווקים בשיא"),
    (r"(?:stocks?|markets?)\s*(?:hit|reach(?:es)?)\s*(?:new\s*)?(?:record|all[- ]time\s*high)",
     "השווקים בשיא"),
    (r"(?:S&P|S&P\s*500|Dow|Nasdaq)\s*(?:rally|surge|jump|soar)", "השווקים מזנקים"),
    (r"(?:S&P|S&P\s*500|Dow|Nasdaq)\s*(?:sell[- ]off|crash|plunge|tumble)", "השווקים צוללים"),
    (r"bull\s*market", "שוק שורי"),
    (r"bear\s*market", "שוק דובי"),
    (r"market\s*correction", "תיקון בשוק"),

    # IPO
    (r"\bIPO\b", "הנפקה"),

    # Crypto
    (r"bitcoin\s*(?:hits?|reaches?)\s*(?:new\s*)?(?:high|record|all[- ]time)", "ביטקוין בשיא חדש"),
    (r"bitcoin\s*(?:crash|plunge|tumble)", "ביטקוין צונח"),
    (r"crypto\s*(?:crash|sell[- ]off)", "צניחה בקריפטו"),
    (r"\bbitcoin\b", "ביטקוין"),
    (r"\bcrypto\b", "קריפטו"),

    # Geopolitical
    (r"\btariffs?\b", "מכסים"),
    (r"trade\s*war", "מלחמת סחר"),
    (r"recession\s*(?:fears?|concerns?|risks?)", "חששות מיתון"),
    (r"GDP\s*(?:grows?|expands?)", "הצמיחה התרחבה"),
    (r"jobs?\s*report\s*(?:beats?|strong)", "דוח תעסוקה חזק"),
    (r"jobs?\s*report\s*(?:miss|weak)", "דוח תעסוקה חלש"),
    (r"unemployment\s*(?:rises?|jumps?)", "האבטלה עולה"),

    # Politics
    (r"\bTrump\s*(?:announces?|signs?|says?)", "טראמפ הכריז"),
    (r"White\s*House", "הבית הלבן"),
    (r"Treasury\s*Secretary", "שר האוצר"),

    # AI
    (r"\bAI\s*(?:boom|rally|surge)", "ראלי AI"),
    (r"\bAI\s*(?:bubble|fears)", "חששות בועת AI"),

    # FDA
    (r"\bFDA\s*(?:approves?|approval)", "FDA אישרה"),
    (r"\bFDA\s*(?:rejects?|denial)", "FDA דחתה"),
    (r"trial\s*(?:success|positive)", "ניסוי קליני מוצלח"),

    # Generic stock movements (lowercase forms)
    (r"\bsurges?\b", "מזנקת"),
    (r"\bplunges?\b", "צונחת"),
    (r"\bsoars?\b", "מזנקת"),
    (r"\btumbles?\b", "צוללת"),
    (r"\brallies?\b", "מתחזקת"),
    (r"\brebounds?\b", "מתאוששת"),
    (r"\bbeats?\s*expectations\b", "מעל הציפיות"),
    (r"\bmisses?\s*expectations\b", "מתחת לציפיות"),
]

# תאימות לאחור
PATTERNS = PATTERNS_CASE_SENSITIVE + PATTERNS_CASE_INSENSITIVE

# =================================================================
# מילון מילים בודדות - להסבר בסיסי כשאין pattern
# =================================================================
WORDS = {
    "inflation": "אינפלציה", "CPI": "מדד מחירים", "PCE": "מדד הוצאות",
    "earnings": "רווחים", "revenue": "הכנסות", "EPS": "רווח למניה",
    "guidance": "תחזית", "outlook": "תחזית עתידית",
    "stock": "מניה", "stocks": "מניות", "shares": "מניות",
    "market": "שוק", "markets": "שווקים", "trading": "מסחר",
    "rate": "ריבית", "rates": "ריביות", "yield": "תשואה",
    "Treasury": "אג\"ח", "bond": "אגרת חוב",
    "recession": "מיתון", "expansion": "התרחבות", "GDP": "תמ\"ג",
    "rally": "עליה חזקה", "surge": "זינוק", "crash": "צניחה",
    "record": "שיא", "high": "גבוה", "low": "נמוך",
    "Fed": "הפד (בנק מרכזי)", "FOMC": "ועדת הריבית", "Powell": "פאוול (יו\"ר הפד)",
    "Treasury": "אוצר", "SEC": "רשות ני\"ע", "IPO": "הנפקה",
    "merger": "מיזוג", "acquisition": "רכישה", "buyback": "רכישת מניות חוזרת",
    "dividend": "דיבידנד", "split": "פיצול מניה",
    "bull": "שורי (עולה)", "bear": "דובי (יורד)",
    "China": "סין", "tariff": "מכס", "tariffs": "מכסים",
    "AI": "בינה מלאכותית", "earnings season": "עונת דוחות",
    "volatility": "תנודתיות", "VIX": "מדד פחד",
}


def translate_headline(text: str) -> tuple[str, bool]:
    """תרגום כותרת - מחזיר (translation, was_full_translation).

    אסטרטגיה: מחיל את כל ה-patterns ברצף (לא רק הראשון).
    שומר סמלי מניות, מספרים, אחוזים. מילים אנגליות שלא הוכרו - נשארות.
    """
    if not text:
        return "", False

    translated = text
    any_match = False

    # סבב 1: case-sensitive (סמלי מניות)
    for pattern, replacement in PATTERNS_CASE_SENSITIVE:
        try:
            if re.search(pattern, translated):
                translated = re.sub(pattern, replacement, translated, count=1)
                any_match = True
        except Exception:
            continue

    # סבב 2: case-insensitive (ביטויים כלליים)
    for pattern, replacement in PATTERNS_CASE_INSENSITIVE:
        try:
            if re.search(pattern, translated, re.IGNORECASE):
                translated = re.sub(pattern, replacement, translated, count=1, flags=re.IGNORECASE)
                any_match = True
        except Exception:
            continue

    if any_match:
        # החלף מילים בודדות שעדיין באנגלית - רק אם נמצאות במילון
        translated = _translate_word_by_word(translated)
        translated = re.sub(r"\s{2,}", " ", translated).strip(" ,.:;-")
        # בדיקה מינימלית
        hebrew_chars = len(re.findall(r"[֐-׿]", translated))
        if hebrew_chars >= 4:
            return translated, True

    # fallback - רמזים ממילון
    parts: list[str] = []
    seen: set[str] = set()
    text_lower = text.lower()
    for en, heb in WORDS.items():
        if heb in seen:
            continue
        if re.search(r"\b" + re.escape(en.lower()) + r"\b", text_lower):
            parts.append(heb)
            seen.add(heb)
        if len(parts) >= 4:
            break

    if parts:
        return "מילות מפתח: " + " · ".join(parts), False
    return "", False


def _translate_word_by_word(text: str) -> str:
    """מחליף מילים שיש להן תרגום במילון. שומר את היתר."""
    def replace_word(match: re.Match) -> str:
        word = match.group(0)
        lower = word.lower()
        for en, heb in WORDS.items():
            if lower == en.lower():
                return heb
        return word  # שמור את המקור

    # מתאים רק מילים בעלות 2+ אותיות, לא ALL CAPS (אלו tickers שצריך לשמור)
    return re.sub(r"\b[a-zA-Z]{3,}(?:'s)?\b", replace_word, text)


def quick_translate(text: str) -> str:
    """תאימות לאחור - מחזיר רק חלק הרמזים (בלי תרגום מלא)."""
    out, _ = translate_headline(text)
    if out.startswith("מילות מפתח: "):
        return out.replace("מילות מפתח: ", "")
    return out


def add_glossary_to_items(items: list[dict]) -> list[dict]:
    """מוסיף הסבר/תרגום בעברית לכל פריט שאין לו תרגום."""
    for it in items:
        if it.get("hebrew_translation"):
            continue  # יש כבר OpenAI translation
        text = it.get("text", "")
        translated, is_full = translate_headline(text)
        if not translated:
            continue
        if is_full:
            it["hebrew_translation"] = translated
            if not it.get("hebrew_explanation"):
                it["hebrew_explanation"] = "תרגום אוטומטי לפי תבנית"
        else:
            # רק רמזים
            it["hebrew_explanation"] = translated
    return items
