---
title: Market Watcher
emoji: 🔭
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
short_description: Hebrew dashboard for market news aggregation and analysis
---

# Trading System

מערכת מאוחדת לסריקת חדשות שוק אמריקאי + סיגנלי מסחר טכניים, עם דשבורד RTL בעברית.

איחדה שלושה פרויקטים נפרדים:
- `My ai agent test` (FinTwit Scanner)
- `trading_bot` (סריקה טכנית)
- `traind_dashbord` (UI)

---

## ⚠️ אזהרת אבטחה - לפני שמתחילים

בפרויקטים הישנים נמצאו סודות שדלפו וצריך להחליף אותם **מיד**:

| מה | איפה היה | פעולה |
|----|----------|--------|
| 🚨 טוקן בוט טלגרם | `trading_bot/config.py:44` | בטל ב-[@BotFather](https://t.me/BotFather) → `/revoke` → צור טוקן חדש |
| 🚨 GitHub Personal Access Token | `trading_bot/scanner.py:159` | בטל ב-[github.com/settings/tokens](https://github.com/settings/tokens) |
| 🚨 OpenAI Key (גם אם דמה) | `My ai agent test/config.env` | בטל ב-[platform.openai.com](https://platform.openai.com/api-keys) |

המערכת החדשה לא נוגעת בקבצים הישנים — הסודות עדיין שם. **תרוקן אותם או תמחק את הקבצים.**

---

## ארכיטקטורה

```
trading-system/
├── app/
│   ├── core/           # config (pydantic-settings) + logging
│   ├── storage/        # SQLite + SQLModel - signals, news, scans, journal
│   ├── scanners/
│   │   ├── news/       # X (Twitter) + RSS fallback + סינון רלוונטיות
│   │   └── market/     # yfinance + RSI/MA/Volume + signal scoring
│   ├── enrichment/     # OpenAI translator + summarizer + glossary
│   ├── alerts/         # Telegram (env-only)
│   ├── reports/        # יצוא Markdown + HTML
│   ├── api/            # FastAPI routers - signals, news, stats, system
│   ├── scheduler/      # APScheduler ברקע
│   ├── web/static/     # דשבורד RTL בעברית - HTML+JS וניל
│   ├── main.py         # FastAPI entrypoint
│   └── cli.py          # שורת פקודה
├── data/               # DB + reports (לא נכנס ל-git)
├── tests/
├── scripts/            # סקריפט הגירה
├── .env.example
├── requirements.txt
└── *.bat               # סקריפטים להפעלה ב-Windows
```

---

## התקנה

### 1. התקנת תלויות
```bash
cd "C:\Users\Refael Vardi\Desktop\trading-system"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. הגדרת משתני סביבה
```bash
copy .env.example .env
notepad .env
```

מלא לפחות:
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` + `ENABLE_TELEGRAM_ALERTS=true` (אם רוצים התראות)
- `OPENAI_API_KEY` (אם רוצים תרגום ועברית)
- `X_BEARER_TOKEN` (אופציונלי - בלי זה יעבוד רק RSS)

המערכת **תעבוד גם בלי שום מפתחות** - תיקח חדשות מ-RSS ותסרוק את השוק עם yfinance.

### 3. אתחול DB
```bash
python -m app.cli init-db
```

---

## הרצה

### דרך 1 - שרת + דשבורד (מומלץ)
```bash
start_api.bat
```
פותח דשבורד ב-http://127.0.0.1:8000 — כולל סקדיולר ברקע (סורק שוק כל שעה, חדשות כל 24 שעות).

### דרך 2 - סריקה ידנית
```bash
scan_news_once.bat        # רק חדשות
scan_market_once.bat      # רק שוק
```

### דרך 3 - CLI
```bash
python -m app.cli scan-news --hours 24 --report
python -m app.cli scan-market --max 100 --no-alerts
python -m app.cli serve --reload
```

---

## API Endpoints

| Endpoint | תיאור |
|----------|-------|
| `GET /` | דשבורד |
| `GET /docs` | Swagger UI אוטומטי |
| `GET /api/stats` | סטטיסטיקות (win rate, סיגנלים היום, וכו') |
| `GET /api/stats/scans` | היסטוריית ריצות סורק |
| `GET /api/signals?status=open` | רשימת סיגנלים |
| `GET /api/news?hours_back=24` | חדשות אחרונות |
| `GET /api/system/health` | מצב מערכת |
| `POST /api/system/scan/news` | הפעלת סריקת חדשות (ברקע) |
| `POST /api/system/scan/market` | הפעלת סריקת שוק (ברקע) |

---

## מה שודרג מהפרויקטים הישנים

| היה | עכשיו |
|------|--------|
| סודות hardcoded ב-3 קבצים | `.env` יחיד + `.gitignore` שחוסם דליפה |
| `signals.json` עובר בין פרויקטים בקובץ | SQLite מרכזי + API |
| באג: רשימת מניות עם `'EDIT' 'NVDA'` (חיבור מחרוזות) | רשימה מקובצת לפי נושאים, מבוטל-כפילויות |
| `print()` בכל מקום | `structlog` עם רמות וצבעים |
| `main.py` של trading_bot מדפיס "הבוט עולה..." | CLI עם פקודות אמיתיות |
| דשבורד עם נתונים דמה | דשבורד מחובר ל-API אמיתי |
| 3 entry points נפרדים | אחד: `python -m app.cli serve` |
| אין tests | pytest setup + בדיקות אינדיקטורים וסינון |
| כל סורק שולח ידנית ל-Telegram | מודול `alerts` יחיד שמחליט |
| אין תזמון משולב | APScheduler ב-FastAPI lifespan |

---

## פיצ'רים חדשים שנוספו

1. **ציון חוזק (strength) 0-10** לכל סיגנל — שילוב RSI, וולום, פריצה
2. **דה-דופ אוטומטי** — לא יוצרים סיגנל כפול לאותה מניה באותו יום
3. **דף "ריצות סורק"** — היסטוריה מלאה + משך + שגיאות
4. **כפתורי "סרוק עכשיו"** בדשבורד
5. **ייצוא CSV** מהדשבורד
6. **מצב Paper trading כברירת מחדל** — בטוח להריץ
7. **fallback לעברית בלי OpenAI** — מילון מקומי מתרגם מונחים בסיסיים
8. **/health endpoint** מראה איזה מקורות מחוברים
9. **שמירה ל-DB עם external_id** — לא יישמר אותו ציוץ פעמיים

---

## הגירת נתונים מהפרויקט הישן

יש סקריפט שלוקח את `signals.json` הישן ושומר ל-DB החדש:
```bash
python scripts\migrate_old_signals.py "C:\Users\Refael Vardi\PycharmProjects\trading_bot\signals.json"
```

---

## בדיקות

```bash
pytest
```

---

## מה עוד אפשר להוסיף (לא נכלל)

- חיבור IBKR אמיתי (היום: yfinance בלבד = לא בזמן אמת)
- ניהול פוזיציות (פתיחה/סגירה אוטומטית)
- backtest engine
- שליחת דוחות יומיים במייל
- 2FA/auth לדשבורד אם הוא נחשף לאינטרנט
- Docker compose
