"""סיכום פריטי חדשות - GPT או fallback מקומי."""
from collections import Counter

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


def summarize_with_openai(items: list[dict]) -> str | None:
    if not settings.use_openai:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None

    client = OpenAI(api_key=settings.openai_api_key)
    bullets = []
    for it in items[:80]:
        author = it.get("author", "?")
        text = (it.get("text", "") or "")[:500]
        if text:
            bullets.append(f"[@{author}] {text}")
    content = "\n\n---\n\n".join(bullets)
    if len(content) > 12000:
        content = content[:12000] + "\n\n[... חתוך ...]"

    prompt = """סכם את החדשות העיקריות לגבי השוק האמריקאי מהציוצים הבאים.
דוח בעברית בלבד, מובנה, עם כותרות:
1. סיכום מנהלים (2-3 משפטים)
2. נושאים מרכזיים
3. תובנות ואזהרות למשקיעים
4. אירועים בולטים

כתוב תמציתי ומקצועי.

ציוצים:
"""
    try:
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "אתה אנליסט שוק פיננסי. סכם תמציתי ומקצועי."},
                {"role": "user", "content": prompt + content},
            ],
            max_tokens=1500,
        )
        return resp.choices[0].message.content
    except Exception as e:
        log.warning("openai_summary_failed", error=str(e))
        return None


def summarize_extractive(items: list[dict]) -> str:
    if not items:
        return "לא נמצאו ציוצים רלוונטיים."

    by_author = Counter(t.get("author", "?") for t in items)
    top = by_author.most_common(10)

    strong_words = {"rally", "crash", "earnings", "fed", "inflation", "recession", "record"}
    highlights = []
    for t in items[:50]:
        text = (t.get("text", "") or "").lower()
        if any(w in text for w in strong_words):
            author = t.get("author", "?")
            snippet = (t.get("text", "") or "")[:200]
            highlights.append(f"• @{author}: {snippet}")

    lines = [
        "**מקורות עיקריים היום:**", "",
        *[f"- {a}: {c} פריטים" for a, c in top], "",
        "**כותרות בולטות:**", "",
        *highlights[:12], "",
        f"סה\"כ {len(items)} פריטים רלוונטיים לשוק האמריקאי.", "",
        "_💡 לתרגום מלא בעברית - הוסף OPENAI_API_KEY ל-.env_",
    ]
    return "\n".join(lines)


def create_summary(items: list[dict]) -> str:
    summary = summarize_with_openai(items)
    if summary:
        return summary
    return summarize_extractive(items)
