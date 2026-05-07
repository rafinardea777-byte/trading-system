"""מילון בסיסי - תרגום מונחים פיננסיים ללא API."""
import re

PHRASES = [
    (r"inflation\s*breakdown", "פירוט נתוני האינפלציה"),
    (r"\bCPI\b", "מדד המחירים (אינפלציה)"),
    (r"Fed\s*Wagers?", "הימורים על החלטות הפד"),
    (r"rate\s*cuts?", "הורדות ריבית"),
    (r"Inflation\s*[Cc]ools?", "האינפלציה מתמתנת"),
    (r"earnings\s*beat", "דוחות רווח מעל הצפי"),
    (r"record\s*quarter", "רבעון שיא"),
    (r"premium\s*subscriptions?", "מנויים פרימיום"),
    (r"bull\s*market", "שוק עליה (בול)"),
    (r"bear\s*market", "שוק יורד (דוב)"),
    (r"running\s*on\s*fumes", "סוף המחזור"),
    (r"stock\s*surges?", "מניה מזנקת"),
    (r"Treasury\s*[Yy]ields?", "תשואות אג\"ח ארה\"ב"),
    (r"losing\s*streak", "רצף הפסדים"),
    (r"credit\s*markets?", "שוקי האשראי"),
    (r"crypto\s*market\s*bottom", "תחתית שוק הקריפטו"),
    (r"dip\s*buyers?", "רוכשים בירידות"),
    (r"AI\s*fears?", "חששות מפני בינה מלאכותית"),
    (r"FDA\s*approval", "אישור מינהל המזון והתרופות"),
]

WORDS = {
    "inflation": "אינפלציה",
    "earnings": "דוחות רווח",
    "stock": "מניה",
    "stocks": "מניות",
    "market": "שוק",
    "markets": "שווקים",
    "rate": "ריבית",
    "recession": "מיתון",
    "rally": "עליה",
    "surge": "זינוק",
    "crash": "צניחה",
    "record": "שיא",
    "Fed": "הפדרל ריזרב",
}


def quick_translate(text: str) -> str:
    if not text:
        return ""
    text_lower = text.lower()
    parts: list[str] = []

    for pattern, heb in PHRASES:
        if re.search(pattern, text, re.I):
            parts.append(heb)

    for en, heb in WORDS.items():
        if en.lower() in text_lower and heb not in " ".join(parts):
            if len(parts) < 3:
                parts.append(heb)

    return " | ".join(parts[:3])


def add_glossary_to_items(items: list[dict]) -> list[dict]:
    """מוסיף הסבר בסיסי לכל פריט שאין לו תרגום."""
    for it in items:
        if not it.get("hebrew_explanation") and not it.get("hebrew_translation"):
            hint = quick_translate(it.get("text", ""))
            if hint:
                it["hebrew_explanation"] = f"קשור ל: {hint}"
    return items
