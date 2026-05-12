"""דפים משפטיים - terms of service + privacy policy."""
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.core.config import settings

router = APIRouter(prefix="/legal", tags=["legal"])


def _wrap(title: str, body_html: str) -> str:
    last_updated = datetime.now().strftime("%d/%m/%Y")
    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | {settings.app_name}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Heebo',-apple-system,Segoe UI,sans-serif;background:#f7fafc;color:#1a202c;line-height:1.7}}
.page{{max-width:780px;margin:0 auto;padding:30px 20px 60px}}
.hdr{{background:linear-gradient(135deg,#1a365d,#2c5282);color:#fff;padding:2rem;border-radius:12px;margin-bottom:2rem}}
.hdr h1{{font-size:1.75rem;margin-bottom:.5rem}}
.hdr .meta{{font-size:.9rem;opacity:.9}}
.content{{background:#fff;border-radius:12px;padding:2rem;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
h2{{font-size:1.2rem;color:#2b6cb0;margin:1.5rem 0 .8rem;border-bottom:2px solid #e2e8f0;padding-bottom:.4rem}}
h3{{font-size:1rem;color:#2c5282;margin:1.2rem 0 .5rem}}
p{{margin-bottom:.8rem}}
ul{{margin:.5rem 1.5rem}}
li{{margin-bottom:.4rem}}
.warn{{background:#fff5e6;border-right:4px solid #d69e2e;padding:.8rem 1rem;border-radius:0 6px 6px 0;margin:1rem 0}}
.back{{display:inline-block;margin-top:1.5rem;padding:.6rem 1.2rem;background:#2b6cb0;color:#fff;text-decoration:none;border-radius:6px}}
.back:hover{{background:#1a365d}}
a{{color:#2b6cb0}}
</style>
</head>
<body>
<div class="page">
<header class="hdr">
<h1>{title}</h1>
<div class="meta">{settings.app_name} · עודכן: {last_updated}</div>
</header>
<div class="content">
{body_html}
<a href="/" class="back">← חזרה לאתר</a>
</div>
</div>
</body>
</html>"""


@router.get("/terms", response_class=HTMLResponse)
def terms_of_service():
    body = f"""
<div class="warn">
<strong>⚠️ הודעה חשובה:</strong> תקנון זה הוא <strong>תבנית בסיס</strong>. לפני שימוש מסחרי
חובה להתייעץ עם עו"ד המתמחה בדיני אינטרנט וניירות ערך בישראל.
</div>

<h2>1. הגדרות</h2>
<p>
<strong>"השירות"</strong> - אתר ואפליקציית {settings.app_name} ושירותיהם הנלווים.<br>
<strong>"המפעיל"</strong> - {settings.company_name}.<br>
<strong>"המשתמש"</strong> - כל מי שגולש או נרשם לשירות.
</p>

<h2>2. הסכמה לתנאים</h2>
<p>השימוש בשירות מהווה הסכמה מלאה לתנאים אלה. אם אינך מסכים - הימנע מהשימוש.</p>

<h2>3. תכלית השירות</h2>
<p>השירות מספק כלים טכנולוגיים לסריקת מניות, איסוף חדשות וניתוח טכני.
<strong>השירות אינו מספק ייעוץ השקעות, ייעוץ פיננסי או המלצות לרכישת/מכירת ניירות ערך.</strong></p>

<h2>4. אזהרה ואחריות</h2>
<div class="warn">
<strong>השקעה בשוק ההון כרוכה בסיכון.</strong>
המידע באתר מבוסס על נתונים פומביים, יתכנו טעויות או עיכובים. החלטות מסחר הן באחריות המשתמש בלבד.
המפעיל לא יישא באחריות לכל הפסד כספי או נזק שייגרם משימוש במידע.
</div>
<ul>
<li>נתוני המחירים מסופקים ב-best-effort, ייתכן עיכוב של 15-20 דקות (yfinance).</li>
<li>הסיגנלים הם תוצר אלגוריתמי - לא יועצי השקעות מורשים.</li>
<li>אין במידע משום הצעה, המלצה, ייעוץ או שידול לרכישה/מכירת ני"ע.</li>
</ul>

<h2>5. הרשמה ושימוש</h2>
<ul>
<li>הרשמה דורשת מייל וסיסמה. אסור לפתוח חשבון בשם אדם אחר.</li>
<li>המשתמש אחראי לשמירה על סודיות פרטי ההתחברות.</li>
<li>המפעיל רשאי לסגור חשבון בכל עת בשל הפרת התנאים.</li>
</ul>

<h2>6. תוכניות מנוי ותשלום</h2>
<ul>
<li><strong>FREE</strong> - חינם, מוגבל ל-5 מניות ב-Watchlist.</li>
<li><strong>PRO</strong> - ₪99/חודש, עד 50 מניות + סריקה ידנית.</li>
<li><strong>VIP</strong> - ₪349/חודש, ללא הגבלה + אסטרטגיות מותאמות.</li>
</ul>
<p>חיוב מתבצע מראש על בסיס חודשי. ביטול - בכל עת, נכנס לתוקף בסוף תקופת החיוב.
לאחר ביטול - החשבון יחזור לרמת FREE.</p>

<h2>7. שימוש מותר וקניין רוחני</h2>
<ul>
<li>כל הזכויות לקוד, עיצוב ותוכן שמורות למפעיל.</li>
<li>אסור: scraping אוטומטי, reverse engineering, מכירה מחדש.</li>
<li>מותר: שימוש אישי, שיתוף לינק לאתר, ציטוט מקור (יחד עם קרדיט).</li>
</ul>

<h2>8. שינוי תנאים</h2>
<p>המפעיל רשאי לשנות תקנון זה בכל עת. שינויים מהותיים יודעו במייל ובאתר 14 יום מראש.</p>

<h2>9. ברירת דין וסמכות שיפוט</h2>
<p>על תנאים אלה יחול הדין הישראלי. סמכות השיפוט הבלעדית - בתי המשפט במחוז תל-אביב.</p>

<h2>10. יצירת קשר</h2>
<p>שאלות לגבי תקנון זה - <a href="mailto:{settings.contact_email}">{settings.contact_email}</a></p>
"""
    return HTMLResponse(_wrap("תקנון שימוש", body))


@router.get("/privacy", response_class=HTMLResponse)
def privacy_policy():
    body = f"""
<div class="warn">
<strong>⚠️ הודעה חשובה:</strong> מדיניות זו היא <strong>תבנית בסיס</strong>.
לפני שימוש בייצור חובה להתאים עם עו"ד וכפיף ל-GDPR/חוק הפרטיות הישראלי.
</div>

<h2>1. כללי</h2>
<p>{settings.company_name} ("המפעיל") מכבד את פרטיותך. מסמך זה מתאר אילו נתונים אנו אוספים, איך משתמשים בהם, ואיך מגנים עליהם.</p>

<h2>2. נתונים שאנו אוספים</h2>
<h3>2.1 נתונים שאתה מספק</h3>
<ul>
<li>כתובת מייל (חובה להרשמה)</li>
<li>שם מלא (אופציונלי)</li>
<li>סיסמה (נשמרת מוצפנת ב-bcrypt - לעולם לא ב-plaintext)</li>
<li>רשימת מניות ב-Watchlist</li>
<li>הערות שתוסיף למניות</li>
</ul>
<h3>2.2 נתונים טכניים</h3>
<ul>
<li>כתובת IP (לצרכי אבטחה ו-rate limiting)</li>
<li>זמני התחברות אחרונים</li>
<li>סוג דפדפן (User-Agent header)</li>
</ul>

<h2>3. שימוש בנתונים</h2>
<ul>
<li>אספקת השירות (הצגת Watchlist, התראות אישיות)</li>
<li>שליחת מיילים תפעוליים (אימות, איפוס סיסמה, חשבונית)</li>
<li>אבטחה ומניעת שימוש לרעה</li>
<li>שיפור המוצר (סטטיסטיקות מצטברות בלבד)</li>
</ul>
<p>אנחנו <strong>לא</strong> מוכרים את הנתונים שלך לצדדים שלישיים. אנחנו <strong>לא</strong> משתמשים בנתונים שלך לפרסום מטורגט.</p>

<h2>4. שירותים חיצוניים</h2>
<ul>
<li><strong>yfinance / Yahoo Finance</strong> - נתוני מחירים (פומבי).</li>
<li><strong>Resend</strong> - שליחת מיילים.</li>
<li><strong>OpenAI</strong> - תרגום חדשות (אופציונלי).</li>
<li><strong>Stripe</strong> - עיבוד תשלומים (אם רכשת מנוי).</li>
<li><strong>GitHub Pages / Cloudflare</strong> - אירוח האתר.</li>
</ul>

<h2>5. אחסון הנתונים</h2>
<ul>
<li>בסיס הנתונים: SQLite/PostgreSQL מאובטח.</li>
<li>גיבויים: יומיים, מוצפנים.</li>
<li>תקופת שמירה: כל עוד החשבון פעיל + 30 יום לאחר מחיקה.</li>
</ul>

<h2>6. הזכויות שלך</h2>
<p>בהתאם לחוק הגנת הפרטיות הישראלי ו-GDPR:</p>
<ul>
<li><strong>גישה</strong> - לראות אילו נתונים יש לנו עליך</li>
<li><strong>תיקון</strong> - לעדכן פרטים</li>
<li><strong>מחיקה</strong> - למחוק את כל הנתונים שלך</li>
<li><strong>יצוא</strong> - לבקש העתק של הנתונים שלך</li>
</ul>
<p>לבקשה: <a href="mailto:{settings.contact_email}">{settings.contact_email}</a></p>

<h2>7. עוגיות (Cookies)</h2>
<p>אנו משתמשים ב-localStorage עבור:</p>
<ul>
<li>token התחברות (JWT) - 30 יום</li>
<li>העדפות תצוגה</li>
<li>Watchlist (כשלא מחובר)</li>
</ul>
<p>אנו <strong>לא</strong> משתמשים בעוגיות מעקב או פרסום צד-שלישי.</p>

<h2>8. אבטחה</h2>
<ul>
<li>HTTPS על כל התעבורה</li>
<li>סיסמאות מוצפנות ב-bcrypt</li>
<li>Rate limiting (60 בקשות/דקה)</li>
<li>JWT חתום עם secret של 48 תווים</li>
</ul>

<h2>9. קטינים</h2>
<p>השירות מיועד לבני 18+. אם אתה מתחת לגיל 18 - אל תירשם.</p>

<h2>10. עדכוני מדיניות</h2>
<p>נעדכן מדיניות זו כשנדרש. שינויים מהותיים יישלחו במייל.</p>

<h2>11. יצירת קשר</h2>
<p><a href="mailto:{settings.contact_email}">{settings.contact_email}</a></p>
"""
    return HTMLResponse(_wrap("מדיניות פרטיות", body))
