"""שירות מייל - Resend + log fallback (כשאין key)."""
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class EmailResult:
    sent: bool
    provider: str
    error: Optional[str] = None


def send_email(to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> EmailResult:
    """שולח מייל. אם אין Resend key - רק רושם ב-log (פיתוח / fallback)."""
    if not settings.resend_api_key:
        log.info(
            "email_logged_only",
            to=to,
            subject=subject,
            body_preview=(text_body or html_body)[:200],
        )
        return EmailResult(sent=False, provider="log-only", error="no API key configured")

    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": f"{settings.email_from_name} <{settings.email_from}>",
                    "to": [to],
                    "subject": subject,
                    "html": html_body,
                    "text": text_body or _strip_html(html_body),
                },
            )
            if r.status_code in (200, 202):
                log.info("email_sent", to=to, subject=subject, provider="resend")
                return EmailResult(sent=True, provider="resend")
            log.warning("email_failed", status=r.status_code, body=r.text[:200])
            return EmailResult(sent=False, provider="resend", error=f"HTTP {r.status_code}")
    except Exception as e:
        log.error("email_exception", error=str(e))
        return EmailResult(sent=False, provider="resend", error=str(e)[:200])


def _strip_html(html: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", html).strip()


# ---------- Templates (Hebrew RTL) ----------

def _wrap(content_html: str, preview: str = "") -> str:
    return f"""<!DOCTYPE html><html lang="he" dir="rtl">
<head><meta charset="UTF-8"><title>{settings.app_name}</title></head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f4f6f8;color:#1a202c">
<div style="display:none;max-height:0;overflow:hidden">{preview}</div>
<div style="max-width:560px;margin:0 auto;padding:30px 20px">
  <div style="background:#fff;border-radius:12px;padding:32px;box-shadow:0 2px 8px rgba(0,0,0,.06)">
    <div style="font-size:24px;font-weight:bold;color:#00d4ff;margin-bottom:20px">📈 {settings.app_name}</div>
    {content_html}
    <hr style="margin-top:30px;border:none;border-top:1px solid #e2e8f0">
    <div style="font-size:11px;color:#718096;margin-top:14px">
      {settings.company_name} · <a href="{settings.public_base_url}" style="color:#00d4ff;text-decoration:none">{settings.public_base_url}</a>
    </div>
  </div>
</div></body></html>"""


def welcome_email(name: str) -> dict:
    return {
        "subject": f"ברוך הבא ל-{settings.app_name}! 🎉",
        "html_body": _wrap(f"""
            <h2 style="font-size:18px;margin-bottom:14px">שלום {name or 'חבר'},</h2>
            <p>נרשמת בהצלחה ל-{settings.app_name}.</p>
            <p>החשבון שלך פעיל במצב <strong>FREE</strong> - מאפשר עד 5 מניות ב-Watchlist וצפייה בסיגנלים.</p>
            <p style="margin-top:20px"><a href="{settings.public_base_url}" style="background:#00d4ff;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block">היכנס לחשבון</a></p>
            <p style="font-size:12px;color:#718096;margin-top:24px">⚠️ אין במידע באתר משום ייעוץ השקעות. כל החלטה מסחרית באחריותך.</p>
        """, preview=f"ברוך הבא ל-{settings.app_name}")
    }


def reset_password_email(reset_link: str) -> dict:
    return {
        "subject": "איפוס סיסמה",
        "html_body": _wrap(f"""
            <h2 style="font-size:18px;margin-bottom:14px">איפוס סיסמה</h2>
            <p>קיבלנו בקשה לאיפוס סיסמת החשבון שלך.</p>
            <p style="margin-top:20px"><a href="{reset_link}" style="background:#00d4ff;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block">אפס סיסמה</a></p>
            <p style="font-size:12px;color:#718096;margin-top:14px">הקישור תקף ל-30 דקות. אם לא ביקשת איפוס - תוכל להתעלם מהמייל הזה.</p>
        """, preview="קישור לאיפוס סיסמה")
    }


def verify_email_email(verify_link: str) -> dict:
    return {
        "subject": "אימות כתובת המייל שלך",
        "html_body": _wrap(f"""
            <h2 style="font-size:18px;margin-bottom:14px">אמת את כתובת המייל</h2>
            <p>לחץ על הכפתור כדי לאמת את כתובת המייל ולפתוח את כל פיצ'רי המערכת:</p>
            <p style="margin-top:20px"><a href="{verify_link}" style="background:#00ff88;color:#000;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block">אמת כעת</a></p>
            <p style="font-size:12px;color:#718096;margin-top:14px">הקישור תקף ל-48 שעות.</p>
        """, preview="אמת את כתובת המייל שלך")
    }
