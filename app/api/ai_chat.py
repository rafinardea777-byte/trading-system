"""AI Chat לניתוח עסקאות - תומך OpenAI, fallback להסבר חוקי-מבוסס."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from app.auth.deps import current_user
from app.core.config import settings
from app.core.logging import get_logger
from app.storage import Signal, User, get_session

router = APIRouter(prefix="/api/ai", tags=["ai"])
log = get_logger(__name__)


class AskIn(BaseModel):
    question: str
    signal_id: Optional[int] = None
    symbol: Optional[str] = None


class AskOut(BaseModel):
    answer: str
    source: str  # "openai" | "rule_based"
    context: dict


def _signal_context(session, signal_id: int) -> Optional[dict]:
    sig = session.get(Signal, signal_id)
    if not sig:
        return None
    return {
        "symbol": sig.symbol,
        "entry_price": sig.price,
        "rsi": sig.rsi,
        "volume_ratio": sig.volume_ratio,
        "strength": sig.strength,
        "ma_fast": sig.ma_fast,
        "ma_slow": sig.ma_slow,
        "target_1": sig.target_1,
        "target_2": sig.target_2,
        "stop_loss": sig.stop_loss,
        "status": sig.status,
        "pnl_pct": sig.pnl_pct,
        "exit_price": sig.exit_price,
        "age_days": (datetime.utcnow() - sig.created_at).days,
    }


def _symbol_context(symbol: str) -> dict:
    """מידע יסודי על סמל - מחיר, וולום, אינדיקטורים."""
    try:
        import yfinance as yf
        import pandas as pd
        t = yf.Ticker(symbol)
        df = t.history(period="3mo")
        if df is None or df.empty:
            return {"symbol": symbol, "error": "no data"}

        last = df.iloc[-1]
        close = df["Close"]

        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rsi = 100 - (100 / (1 + gain / loss.replace(0, pd.NA)))

        ma20 = close.rolling(20).mean().iloc[-1]
        ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
        ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None

        return {
            "symbol": symbol,
            "price": float(last["Close"]),
            "volume": int(last["Volume"]),
            "rsi": float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None,
            "ma_20": float(ma20) if pd.notna(ma20) else None,
            "ma_50": float(ma50) if ma50 and pd.notna(ma50) else None,
            "ma_200": float(ma200) if ma200 and pd.notna(ma200) else None,
            "30d_change_pct": round(((float(last["Close"]) - float(close.iloc[-30])) / float(close.iloc[-30]) * 100), 2) if len(close) >= 30 else None,
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)[:100]}


def _rule_based_answer(question: str, ctx: dict) -> str:
    """תשובה מבוססת חוקים כשאין OpenAI."""
    out = ["📊 ניתוח טכני בסיסי (ללא AI):"]
    price = ctx.get("price") or ctx.get("entry_price")
    rsi = ctx.get("rsi")

    if price:
        out.append(f"• מחיר נוכחי: ${price:.2f}")

    if rsi is not None:
        if rsi > 70:
            out.append(f"• RSI {rsi:.1f} - **קנייתי-יתר** ⚠️ סיכון לתיקון")
        elif rsi < 30:
            out.append(f"• RSI {rsi:.1f} - **מכירת-יתר** 🟢 הזדמנות פוטנציאלית")
        elif 40 <= rsi <= 60:
            out.append(f"• RSI {rsi:.1f} - **ניטרלי** - בלי כיוון ברור")
        else:
            out.append(f"• RSI {rsi:.1f} - {'מומנטום חיובי' if rsi > 50 else 'מומנטום שלילי'}")

    ma_fast = ctx.get("ma_20") or ctx.get("ma_fast")
    ma_slow = ctx.get("ma_50") or ctx.get("ma_slow")
    if ma_fast and ma_slow and price:
        if price > ma_fast > ma_slow:
            out.append("• מבנה עלייה חזק 🟢 (מחיר מעל MA20 מעל MA50)")
        elif price < ma_fast < ma_slow:
            out.append("• מבנה ירידה 🔴 (מחיר מתחת MA20 מתחת MA50)")
        else:
            out.append("• מבנה ממוצעים מעורב - חוסר כיוון ברור")

    if "pnl_pct" in ctx and ctx["pnl_pct"] is not None:
        pnl = ctx["pnl_pct"]
        out.append(f"• {'רווח' if pnl > 0 else 'הפסד'} נוכחי: {pnl:+.2f}% {'✅' if pnl > 0 else '🔴'}")

    out.append("\n💡 **לתשובה מפורטת יותר** - הוסף OpenAI API key ב-`.env`.")
    out.append("\n⚠️ המידע אינו ייעוץ השקעות. החלטות מסחר באחריותך בלבד.")
    return "\n".join(out)


def _openai_answer(question: str, ctx: dict) -> Optional[str]:
    if not settings.use_openai:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)

        system = (
            "אתה אנליסט פיננסי שמדבר עברית. ענה תמציתית (4-6 שורות), "
            "מבוסס נתונים בלבד, בלי המלצות קנייה/מכירה ספציפיות. "
            "תמיד הוסף בסוף: '⚠️ אינו ייעוץ השקעות'."
        )
        user_msg = (
            f"נתוני מנייה: {ctx}\n\n"
            f"שאלת המשתמש: {question}\n\n"
            "ענה בעברית בצורה תמציתית ומקצועית. הסבר את הנתונים, אל תמליץ ספציפית מה לעשות."
        )

        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=400,
            temperature=0.5,
        )
        return resp.choices[0].message.content
    except Exception as e:
        log.warning("ai_chat_openai_failed", error=str(e))
        return None


@router.post("/ask", response_model=AskOut)
def ask(data: AskIn, user: User = Depends(current_user)):
    """שאלה ל-AI על עסקה / מנייה. דורש משתמש מחובר."""
    if not data.question or len(data.question.strip()) < 3:
        raise HTTPException(status_code=400, detail="שאלה ריקה")

    ctx: dict = {}
    if data.signal_id:
        with get_session() as session:
            sig_ctx = _signal_context(session, data.signal_id)
            if not sig_ctx:
                raise HTTPException(status_code=404, detail="סיגנל לא נמצא")
            ctx = sig_ctx
            if not data.symbol:
                data.symbol = sig_ctx["symbol"]

    if data.symbol:
        sym_ctx = _symbol_context(data.symbol.upper())
        ctx = {**sym_ctx, **ctx}

    answer = _openai_answer(data.question, ctx)
    if answer:
        return AskOut(answer=answer, source="openai", context=ctx)

    return AskOut(answer=_rule_based_answer(data.question, ctx), source="rule_based", context=ctx)
