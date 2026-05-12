"""מתרגם מחדש את כל פריטי החדשות עם הלוגיקה החדשה."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import select

from app.enrichment.glossary import translate_headline
from app.storage import NewsItem, get_session, init_db


def retranslate() -> int:
    init_db()
    full = 0
    hint = 0
    none = 0
    with get_session() as session:
        rows = list(session.exec(select(NewsItem)))
        for r in rows:
            translated, is_full = translate_headline(r.text)
            if not translated:
                none += 1
                continue
            if is_full:
                r.hebrew_translation = translated
                r.hebrew_explanation = "תרגום אוטומטי לפי תבנית"
                full += 1
            else:
                r.hebrew_translation = None  # נקה תרגומים ישנים שלא תקפים
                r.hebrew_explanation = translated
                hint += 1
            session.add(r)
    print(f"[OK] retranslated {len(rows)} items: full={full}, hint={hint}, none={none}")
    return 0


if __name__ == "__main__":
    sys.exit(retranslate())
