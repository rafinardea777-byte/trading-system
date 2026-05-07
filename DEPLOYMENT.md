# מדריך פריסה ל-Render.com

מדריך צעד אחר צעד לפריסת המערכת לאינטרנט עם URL ציבורי קבוע.

**עלות צפויה**: ₪25-50 לחודש (Render Starter $7 + Postgres $7 אחרי 90 יום חינם)

---

## שלב 1: העלאת הקוד ל-GitHub (חובה)

Render מתחבר לקוד דרך GitHub. אם אין לך עדיין account:

```bash
cd "C:\Users\Refael Vardi\Desktop\trading-system"
git init
git add .
git commit -m "initial commit"
```

1. היכנס ל-https://github.com/new
2. צור repo בשם `trading-system` (private מומלץ)
3. **לפני push - וודא ש-`.env` לא נכלל!** (יש .gitignore שחוסם, אבל בדוק):
   ```bash
   git status
   ```
   אסור שיופיע `.env`. אם כן - תפסיק ותתקן את `.gitignore`.
4. Push:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/trading-system.git
   git branch -M main
   git push -u origin main
   ```

---

## שלב 2: יצירת חשבון Render

1. https://render.com → "Get Started" → התחבר עם GitHub
2. אישור גישה ל-repo `trading-system`

---

## שלב 3: פריסה אוטומטית (1 קליק)

הקובץ `render.yaml` כבר מוכן בפרויקט. ב-Render:

1. Dashboard → **"New +"** → **"Blueprint"**
2. בחר את ה-repo `trading-system`
3. Render יקרא את `render.yaml` ויראה לך:
   - שירות web בשם `trading-system`
   - DB בשם `trading-db` (Postgres)
4. לחץ **"Apply"**

⏱️ זמן פריסה ראשונית: 5-10 דקות.

---

## שלב 4: הזנת מפתחות סודיים

ב-Render Dashboard → `trading-system` → **"Environment"**:

| משתנה | ערך | מתי נדרש |
|--------|-----|----------|
| `OPENAI_API_KEY` | `sk-...` | אם רוצים תרגום אוטומטי לעברית |
| `TELEGRAM_BOT_TOKEN` | מ-@BotFather | להתראות |
| `TELEGRAM_CHAT_ID` | ה-chat ID שלך | להתראות |
| `ENABLE_TELEGRAM_ALERTS` | `true` | להפעיל התראות |
| `X_BEARER_TOKEN` | מ-developer.x.com | אופציונלי, להחליף RSS |
| `CORS_ORIGINS` | `https://yourdomain.com` | אם תקנה דומיין |

לחץ **"Save Changes"** - השרת ירוצץ אוטומטית.

> 🔑 **חשוב!**: ה-`ADMIN_API_KEY` נוצר אוטומטית ע"י Render. כדי לראות אותו: Environment → גלגל ל-`ADMIN_API_KEY` → לחץ "Reveal". **שמור אותו** - תצטרך אותו כדי להפעיל סריקות ידניות מהדשבורד.

---

## שלב 5: ה-URL הציבורי

אחרי שהפריסה הסתיימה, Render יציג URL כמו:
```
https://trading-system-xxxx.onrender.com
```

**זאת הכתובת שאתה מפרסם.** היא:
- ✅ פעילה 24/7
- ✅ HTTPS אוטומטי
- ✅ נגישה מכל מקום בעולם
- ✅ מתעדכנת בכל push ל-main

---

## שלב 6: דומיין משלך (אופציונלי)

אם קנית דומיין כמו `trading-pro.co.il`:

1. Render Dashboard → `trading-system` → **"Settings"** → **"Custom Domain"**
2. הזן את הדומיין → Render ייתן רשומות DNS
3. אצל ה-registrar שלך: הוסף את רשומות ה-CNAME / A
4. חכה 5-30 דקות לעדכון
5. ב-Render → "Verify"
6. **חזור ל-Environment** ועדכן `CORS_ORIGINS=https://trading-pro.co.il`

---

## שלב 7: שימוש ראשון

1. היכנס לכתובת הציבורית
2. תראה את הדשבורד עם **באנר ה-disclaimer בולט בראש**
3. כפתורי "🔄 סרוק חדשות" / "🔄 סרוק שוק" יעבדו רק עם הheader `X-Admin-Key`. כדי להפעיל אותם:
   ```javascript
   // פתח DevTools (F12) ב-Console:
   localStorage.setItem('adminKey', 'PASTE_YOUR_ADMIN_KEY_HERE');
   ```
   וצריך לעדכן את הפרונטאנד שישלח את ה-key... (ראה הערה בהמשך)

---

## ✅ Checklist לפני שמפרסמים את ה-URL

- [ ] `.env` המקומי **לא** הועלה ל-git (`git ls-files | grep .env` ריק)
- [ ] `OPENAI_API_KEY` הוזן ב-Render Environment
- [ ] טוקן הטלגרם הישן בוטל ב-@BotFather (אם עדיין לא)
- [ ] `PUBLIC_MODE=true` ב-Render
- [ ] בדקת שה-URL נטען ושיש disclaimer
- [ ] הסיגנלים מציגים נתונים תקינים (לחץ על מנייה ותראה את ה-modal)
- [ ] `/docs` ו-`/redoc` מוסתרים (חזרת 404) - אבטחה ב-public_mode
- [ ] התראות טלגרם מגיעות (אם הופעלו)

---

## ⚠️ מגבלות ידועות

| בעיה | פתרון |
|--------|--------|
| Render Starter עולה ל-sleep אחרי 15 דקות חוסר פעילות | שדרג ל-Standard ($25/mo) או השתמש ב-cron-job חיצוני שמעיר |
| נתוני yfinance בעיכוב 15-20 דקות | שדרג ל-Polygon.io / Alpaca ($30+/mo לבזמן אמת) |
| Postgres free pierce after 90d | Render ידרוש שדרוג ל-$7/mo, או יגרום DB drop |
| הסקדיולר רץ באותו process של ה-API | בקנה מידה - להפריד ל-worker process נפרד |

---

## פקודות שימושיות

```bash
# צפייה ב-logs בזמן אמת
# Render Dashboard → trading-system → "Logs"

# הפעלת סריקה ידנית מהשרת:
# Render Dashboard → trading-system → "Shell" →
python -m app.cli scan-market --max 100

# הגירת signals.json ישן ל-DB החדש (אם רלוונטי):
python scripts/migrate_old_signals.py /app/data/old_signals.json

# Backfill עברית לחדשות קיימות אחרי הוספת OPENAI_API_KEY:
python scripts/backfill_hebrew.py
```

---

## עזרה

- Render docs: https://render.com/docs
- בעיה? תפתח issue ב-repo או תחזור אליי
