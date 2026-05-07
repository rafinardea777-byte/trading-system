"""מילוי תרגום עברי לפריטי חדשות קיימים שאין להם תרגום.

שימוש:
    python scripts/backfill_hebrew.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import select

from app.enrichment.glossary import quick_translate
from app.enrichment.translator import translate_items
from app.core.config import settings
from app.storage import NewsItem, get_session, init_db


def backfill() -> int:
    init_db()
    updated = 0
    with get_session() as session:
        rows = list(session.exec(select(NewsItem).where(
            NewsItem.hebrew_translation.is_(None),
            NewsItem.hebrew_explanation.is_(None),
        )))
        if not rows:
            print("[OK] no rows to backfill")
            return 0

        if settings.use_openai:
            # שימוש ב-OpenAI (אצווה של 60 בכל פעם)
            for i in range(0, len(rows), 60):
                batch = rows[i:i+60]
                items = [{"text": r.text} for r in batch]
                enriched = translate_items(items)
                for r, e in zip(batch, enriched):
                    r.hebrew_translation = e.get("hebrew_translation")
                    r.hebrew_explanation = e.get("hebrew_explanation")
                    session.add(r)
                    updated += 1
                print(f"[OK] enriched {min(i+60, len(rows))}/{len(rows)} via OpenAI")
        else:
            # רק מילון מקומי
            for r in rows:
                hint = quick_translate(r.text)
                if hint:
                    r.hebrew_explanation = f"קשור ל: {hint}"
                    session.add(r)
                    updated += 1
            print(f"[OK] enriched {updated}/{len(rows)} via local glossary")

    print(f"[OK] backfill complete: {updated} rows updated")
    return 0


if __name__ == "__main__":
    sys.exit(backfill())
