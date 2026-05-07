"""יצוא דוח חדשות פורמט HTML מעוצב."""
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Optional

from app.core.config import settings


def _format_time(created: str | datetime | None) -> str:
    if not created:
        return ""
    try:
        if isinstance(created, str):
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        else:
            dt = created
        return dt.strftime("%d.%m.%Y | %H:%M")
    except Exception:
        return str(created)[:16]


def _src_color(src: str) -> str:
    return {
        "Bloomberg": "#2c5282", "CNBC": "#c53030", "MarketWatch": "#2f855a",
        "WSJ": "#744210", "AP": "#da1a32", "Reuters": "#00a396",
        "WhiteHouse": "#0a2540", "realDonaldTrump": "#1d9bf0",
        "CNN": "#cc0000", "BBCNews": "#bb1919",
    }.get(src, "#4a5568")


def generate_html_report(
    items: list[dict],
    summary: str,
    run_date: Optional[datetime] = None,
) -> Path:
    run_date = run_date or datetime.now()
    date_str = run_date.strftime("%Y-%m-%d")
    time_str = run_date.strftime("%H:%M")

    sorted_items = sorted(items, key=lambda t: t.get("created_at") or "", reverse=True)
    cards = []
    for n, t in enumerate(sorted_items[:100], 1):
        author = t.get("author", "?")
        text = (t.get("text", "") or "").replace("\n", " ")[:400]
        url = t.get("url", "")
        formatted_time = _format_time(t.get("created_at"))
        trans = t.get("hebrew_translation", "")
        expl = t.get("hebrew_explanation", "")

        article = f"""
<article class="news-card">
  <header class="ah">
    <span class="num">{n}</span>
    <span class="src" style="--c:{_src_color(author)}">{escape(author)}</span>
    <time class="t">{escape(formatted_time)}</time>
  </header>
  <h2>{escape(text)}</h2>"""
        if expl:
            article += f'<p class="ctx">{escape(expl)}</p>'
        if trans and trans != expl:
            article += f'<p class="trans">{escape(trans)}</p>'
        article += f'<a href="{escape(url)}" target="_blank" rel="noopener">קריאת הכתבה →</a></article>'
        cards.append(article)

    summary_html = _md_to_html(summary)

    html = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<title>דוח שוק אמריקאי | {date_str}</title>
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Heebo',sans-serif;background:#f7fafc;color:#1a202c;line-height:1.6}}
.page{{max-width:800px;margin:0 auto;padding:2rem 1.5rem}}
.hdr{{background:linear-gradient(135deg,#1a365d,#2c5282);color:#fff;padding:2rem;border-radius:12px;margin-bottom:2rem}}
.hdr h1{{font-size:1.75rem;margin-bottom:.5rem}}
.meta{{display:flex;gap:1.5rem;font-size:.9rem;opacity:.95}}
section.summary,article.news-card{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:1.5rem;margin-bottom:1.25rem}}
section.summary h2{{font-size:1.1rem;color:#2b6cb0;margin-bottom:1rem}}
.ah{{display:flex;align-items:center;gap:.75rem;margin-bottom:.75rem}}
.num{{width:28px;height:28px;background:#2b6cb0;color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.8rem;font-weight:600}}
.src{{font-weight:600;font-size:.85rem;color:var(--c)}}
.t{{margin-right:auto;font-size:.8rem;color:#718096}}
.news-card h2{{font-size:1.05rem;font-weight:600;margin-bottom:.5rem}}
.ctx{{background:#f8fafc;padding:.75rem 1rem;border-right:4px solid #2b6cb0;border-radius:0 6px 6px 0;margin:.75rem 0;font-size:.9rem}}
.trans{{font-size:.9rem;color:#2d3748}}
.news-card a{{display:inline-block;margin-top:.75rem;color:#2b6cb0;text-decoration:none;font-weight:500}}
</style></head><body>
<div class="page">
<header class="hdr"><h1>דוח חדשות שוק אמריקאי</h1>
<div class="meta"><span>📅 {date_str}</span><span>🕐 {time_str}</span><span>📰 {len(items)} פריטים</span></div></header>
<section class="summary"><h2>סיכום היום</h2>{summary_html}</section>
{"".join(cards)}
</div></body></html>"""

    filepath = settings.reports_dir / f"news_report_{date_str}.html"
    filepath.write_text(html, encoding="utf-8")
    return filepath


def _md_to_html(s: str) -> str:
    import re

    out = []
    for line in s.split("\n"):
        if not line.strip():
            out.append("<br>")
            continue
        line_e = escape(line)
        if line.startswith("**") and line.endswith("**") and "**" not in line[2:-2]:
            out.append(f"<p><strong>{escape(line[2:-2])}</strong></p>")
        elif line.startswith(("• ", "- ")):
            out.append(f"<p>• {line_e[2:]}</p>")
        else:
            line_e = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", line_e)
            out.append(f"<p>{line_e}</p>")
    return "".join(out)
