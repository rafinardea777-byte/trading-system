"""Trade Journal - תיעוד עסקאות ידני עם חישוב P&L מלא."""
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import select

from app.auth.deps import current_user
from app.storage import TradeJournal, User, get_session

router = APIRouter(prefix="/api/me/journal", tags=["journal"])

_SYMBOL_RE = re.compile(r"^[A-Z]{1,6}(\.[A-Z]{1,3})?$")


class JournalEntryIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=10)
    direction: str = "long"  # long | short
    shares: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    entry_at: Optional[datetime] = None
    target_price: Optional[float] = Field(default=None, gt=0)
    stop_loss: Optional[float] = Field(default=None, gt=0)
    exit_price: Optional[float] = Field(default=None, gt=0)
    exit_at: Optional[datetime] = None
    fees: float = Field(default=0, ge=0)
    notes: str = Field(default="", max_length=400)


class JournalEntryUpdate(BaseModel):
    target_price: Optional[float] = Field(default=None, gt=0)
    stop_loss: Optional[float] = Field(default=None, gt=0)
    exit_price: Optional[float] = Field(default=None, gt=0)
    exit_at: Optional[datetime] = None
    fees: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=400)


class JournalEntryOut(BaseModel):
    id: int
    symbol: str
    direction: str
    shares: float
    entry_price: float
    entry_at: datetime
    target_price: Optional[float]
    stop_loss: Optional[float]
    exit_price: Optional[float]
    exit_at: Optional[datetime]
    fees: float
    pnl_dollars: Optional[float]
    pnl_pct: Optional[float]
    status: str
    notes: str
    # מחושבים
    position_size: float  # shares * entry_price
    risk_reward: Optional[float] = None
    days_held: Optional[int] = None


def _validate_symbol(s: str) -> str:
    s = s.strip().upper()
    if not _SYMBOL_RE.match(s):
        raise HTTPException(400, "סמל לא תקין")
    return s


def _compute_pnl(entry: float, exit_p: float, shares: float, fees: float, direction: str) -> tuple[float, float]:
    """החזר (pnl_dollars, pnl_pct) - שורט מתהפך."""
    sign = 1 if direction == "long" else -1
    gross = (exit_p - entry) * shares * sign
    net = gross - fees
    pct = (exit_p - entry) / entry * 100 * sign
    return round(net, 2), round(pct, 2)


def _to_out(j: TradeJournal) -> JournalEntryOut:
    pos_size = round(j.shares * j.entry_price, 2)
    rr = None
    if j.target_price and j.stop_loss and j.entry_price:
        risk = abs(j.entry_price - j.stop_loss)
        reward = abs(j.target_price - j.entry_price)
        if risk > 0:
            rr = round(reward / risk, 2)
    days = None
    if j.exit_at and j.entry_at:
        days = max(0, (j.exit_at - j.entry_at).days)
    elif j.entry_at:
        days = max(0, (datetime.utcnow() - j.entry_at).days)
    return JournalEntryOut(
        id=j.id, symbol=j.symbol, direction=j.direction or "long",
        shares=j.shares, entry_price=j.entry_price, entry_at=j.entry_at,
        target_price=j.target_price, stop_loss=j.stop_loss,
        exit_price=j.exit_price, exit_at=j.exit_at,
        fees=j.fees or 0, pnl_dollars=j.pnl_dollars, pnl_pct=j.pnl_pct,
        status=j.status, notes=j.notes or "",
        position_size=pos_size, risk_reward=rr, days_held=days,
    )


@router.get("", response_model=list[JournalEntryOut])
def list_entries(status: Optional[str] = None, user: User = Depends(current_user)):
    """כל העסקאות הידניות של המשתמש - ברירת מחדל: כולן (פתוחות+סגורות)."""
    with get_session() as session:
        stmt = select(TradeJournal).where(TradeJournal.user_id == user.id)
        if status in ("open", "closed"):
            stmt = stmt.where(TradeJournal.status == status)
        rows = list(session.exec(stmt.order_by(TradeJournal.entry_at.desc())))
        return [_to_out(r) for r in rows]


@router.post("", response_model=JournalEntryOut)
def create_entry(data: JournalEntryIn, user: User = Depends(current_user)):
    if data.direction not in ("long", "short"):
        raise HTTPException(400, "direction חייב להיות long או short")
    sym = _validate_symbol(data.symbol)

    pnl_d = pnl_p = None
    status = "open"
    if data.exit_price:
        pnl_d, pnl_p = _compute_pnl(
            data.entry_price, data.exit_price, data.shares, data.fees, data.direction
        )
        status = "closed"

    with get_session() as session:
        # מגבלה: מקסימום 500 עסקאות
        total = session.exec(
            select(TradeJournal).where(TradeJournal.user_id == user.id)
        ).all()
        if len(total) >= 500:
            raise HTTPException(429, "הגעת ל-500 עסקאות. מחק ישנות.")

        j = TradeJournal(
            user_id=user.id,
            symbol=sym,
            direction=data.direction,
            shares=data.shares,
            entry_price=data.entry_price,
            entry_at=data.entry_at or datetime.utcnow(),
            target_price=data.target_price,
            stop_loss=data.stop_loss,
            exit_price=data.exit_price,
            exit_at=data.exit_at if data.exit_price else None,
            fees=data.fees or 0,
            pnl_dollars=pnl_d,
            pnl_pct=pnl_p,
            status=status,
            notes=data.notes or "",
            # legacy NOT NULL fields - default values
            position_size_usd=data.shares * data.entry_price,
            target_1=data.target_price or 0,
            target_2=0,
        )
        session.add(j)
        session.flush()
        return _to_out(j)


@router.patch("/{entry_id}", response_model=JournalEntryOut)
def update_entry(entry_id: int, data: JournalEntryUpdate, user: User = Depends(current_user)):
    with get_session() as session:
        j = session.get(TradeJournal, entry_id)
        if not j or j.user_id != user.id:
            raise HTTPException(404, "עסקה לא נמצאה")
        if data.target_price is not None:
            j.target_price = data.target_price
        if data.stop_loss is not None:
            j.stop_loss = data.stop_loss
        if data.fees is not None:
            j.fees = data.fees
        if data.notes is not None:
            j.notes = data.notes
        if data.exit_price is not None:
            j.exit_price = data.exit_price
            j.exit_at = data.exit_at or datetime.utcnow()
            pnl_d, pnl_p = _compute_pnl(
                j.entry_price, j.exit_price, j.shares, j.fees or 0, j.direction or "long"
            )
            j.pnl_dollars = pnl_d
            j.pnl_pct = pnl_p
            j.status = "closed"
        session.add(j)
        session.flush()
        return _to_out(j)


@router.delete("/{entry_id}")
def delete_entry(entry_id: int, user: User = Depends(current_user)):
    with get_session() as session:
        j = session.get(TradeJournal, entry_id)
        if not j or j.user_id != user.id:
            raise HTTPException(404, "לא נמצא")
        session.delete(j)
    return {"ok": True}


@router.get("/stats")
def journal_stats(user: User = Depends(current_user)):
    """סטטיסטיקות יומן - מנצחים/מפסידים, win-rate, total P&L."""
    # שלב 1: snapshot ל-dicts בתוך session (להימנע מ-DetachedInstanceError)
    with get_session() as session:
        rows = list(session.exec(
            select(TradeJournal).where(TradeJournal.user_id == user.id)
        ))
        snaps = [{"status": r.status, "pnl_d": r.pnl_dollars, "pnl_p": r.pnl_pct} for r in rows]

    total = len(snaps)
    open_n = sum(1 for s in snaps if s["status"] == "open")
    closed = [s for s in snaps if s["status"] == "closed" and s["pnl_d"] is not None]
    wins = [s for s in closed if s["pnl_d"] > 0]
    losses = [s for s in closed if s["pnl_d"] <= 0]
    total_pnl = round(sum(s["pnl_d"] for s in closed), 2) if closed else 0.0
    avg_win = round(sum(s["pnl_p"] for s in wins) / len(wins), 2) if wins else 0.0
    avg_loss = round(sum(s["pnl_p"] for s in losses) / len(losses), 2) if losses else 0.0
    win_rate = round(len(wins) / len(closed) * 100, 1) if closed else 0.0
    return {
        "total": total,
        "open": open_n,
        "closed": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "total_pnl_dollars": total_pnl,
        "avg_win_pct": avg_win,
        "avg_loss_pct": avg_loss,
    }
