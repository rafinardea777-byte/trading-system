"""מילוי mentioned_symbols לפריטי חדשות קיימים.

שימוש:
    python scripts/backfill_symbols.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import select

from app.scanners.news.symbols import extract_symbols
from app.storage import NewsItem, get_session, init_db
from app.storage.repository import add_notification, find_users_watching


def backfill() -> int:
    init_db()
    updated = 0
    notif_count = 0
    with get_session() as session:
        rows = list(session.exec(select(NewsItem).where(NewsItem.mentioned_symbols.is_(None))))
        if not rows:
            print("[OK] no rows to backfill")
            return 0

        for r in rows:
            syms = extract_symbols(r.text)
            if syms:
                r.mentioned_symbols = ",".join(sorted(syms))
                session.add(r)
                updated += 1

                # יצירת התראות למשתמשים שמחזיקים ב-watchlist את המניות הללו
                matches = find_users_watching(session, syms)
                for user_id, matched in matches.items():
                    for sym in matched:
                        add_notification(
                            session,
                            kind="news",
                            title=f"📰 {sym}: חדשות חדשות",
                            message=r.text[:200],
                            symbol=sym,
                            icon="📰",
                            user_id=user_id,
                        )
                        notif_count += 1

    print(f"[OK] backfilled {updated} news items, created {notif_count} watchlist notifications")
    return 0


if __name__ == "__main__":
    sys.exit(backfill())
