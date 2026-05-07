"""יצוא דוח חדשות פורמט Markdown."""
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.config import settings


def generate_markdown_report(
    items: list[dict],
    summary: str,
    run_date: Optional[datetime] = None,
) -> Path:
    run_date = run_date or datetime.now()
    date_str = run_date.strftime("%Y-%m-%d")
    time_str = run_date.strftime("%H:%M")

    header = f"""# דוח חדשות שוק אמריקאי

| | |
|---|---|
| **תאריך** | {date_str} |
| **שעה** | {time_str} |
| **מקורות** | {len(items)} פריטים |

---

## סיכום מנהלים

{summary}

---

## פירוט לפי מקור

"""

    sorted_items = sorted(items, key=lambda t: t.get("created_at") or "", reverse=True)
    blocks = []
    for n, t in enumerate(sorted_items[:100], 1):
        author = t.get("author", "?")
        author_disp = author if author in ("CNBC", "WSJ", "Bloomberg", "MarketWatch") else f"@{author}"
        text = (t.get("text", "") or "").replace("\n", " ")[:350]
        url = t.get("url", "")
        created = (t.get("created_at") or "")[:19]
        trans = t.get("hebrew_translation", "")
        expl = t.get("hebrew_explanation", "")

        b = [f"### {n}. {author_disp} · {created}", "", f"**מקור:** {text}", ""]
        if trans:
            b.extend([f"**תרגום:** {trans}", ""])
        if expl:
            b.extend([f"**משמעות:** {expl}", ""])
        b.extend([f"🔗 [קישור]({url})", "", "---", ""])
        blocks.append("\n".join(b))

    content = header + "\n".join(blocks)
    filepath = settings.reports_dir / f"news_report_{date_str}.md"
    filepath.write_text(content, encoding="utf-8")
    return filepath
