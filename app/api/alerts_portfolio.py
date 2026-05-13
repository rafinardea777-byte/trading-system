"""Price Alerts + Portfolio - הכל ב-namespace /api/me."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import select

from app.auth.deps import current_user
from app.storage import PortfolioPosition, PriceAlert, User, get_session

router = APIRouter(prefix="/api/me", tags=["me"])


# ========== PRICE ALERTS ==========

class AlertIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=10)
    target_price: float = Field(gt=0)
    direction: str = "above"  # above | below
    note: Optional[str] = Field(default=None, max_length=140)


class AlertOut(BaseModel):
    id: int
    symbol: str
    target_price: float
    direction: str
    note: Optional[str]
    triggered: bool
    triggered_at: Optional[datetime]
    triggered_price: Optional[float]
    created_at: datetime


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(active_only: bool = True, user: User = Depends(current_user)):
    with get_session() as session:
        stmt = select(PriceAlert).where(PriceAlert.user_id == user.id)
        if active_only:
            stmt = stmt.where(PriceAlert.triggered == False)  # noqa: E712
        stmt = stmt.order_by(PriceAlert.created_at.desc())
        rows = list(session.exec(stmt))
        return [AlertOut(
            id=r.id, symbol=r.symbol, target_price=r.target_price,
            direction=r.direction, note=r.note, triggered=r.triggered,
            triggered_at=r.triggered_at, triggered_price=r.triggered_price,
            created_at=r.created_at,
        ) for r in rows]


@router.post("/alerts", response_model=AlertOut)
def create_alert(data: AlertIn, user: User = Depends(current_user)):
    sym = data.symbol.strip().upper()
    if data.direction not in ("above", "below"):
        raise HTTPException(400, "direction חייב להיות above או below")
    import re
    if not re.match(r"^[A-Z]{1,6}(\.[A-Z]{1,3})?$", sym):
        raise HTTPException(400, "סמל לא תקין")

    with get_session() as session:
        # אזהרה: לא יותר מ-50 התראות פעילות
        active_count = len(list(session.exec(
            select(PriceAlert).where(
                PriceAlert.user_id == user.id,
                PriceAlert.triggered == False,  # noqa: E712
            )
        )))
        if active_count >= 50:
            raise HTTPException(429, "הגעת ל-50 התראות פעילות. מחק ישנות.")

        alert = PriceAlert(
            user_id=user.id, symbol=sym,
            target_price=data.target_price, direction=data.direction,
            note=data.note,
        )
        session.add(alert)
        session.flush()
        return AlertOut(
            id=alert.id, symbol=alert.symbol, target_price=alert.target_price,
            direction=alert.direction, note=alert.note, triggered=False,
            triggered_at=None, triggered_price=None, created_at=alert.created_at,
        )


@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: int, user: User = Depends(current_user)):
    with get_session() as session:
        alert = session.get(PriceAlert, alert_id)
        if not alert or alert.user_id != user.id:
            raise HTTPException(404, "התראה לא נמצאה")
        session.delete(alert)
    return {"ok": True}


# ========== PORTFOLIO ==========

class PositionIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=10)
    shares: float = Field(gt=0)
    avg_price: float = Field(gt=0)
    notes: Optional[str] = Field(default=None, max_length=200)


class CloseIn(BaseModel):
    exit_price: float = Field(gt=0)


class PositionOut(BaseModel):
    id: int
    symbol: str
    shares: float
    avg_price: float
    opened_at: datetime
    closed_at: Optional[datetime]
    exit_price: Optional[float]
    status: str
    notes: Optional[str]
    # מחושב
    current_price: Optional[float] = None
    pnl_dollars: Optional[float] = None
    pnl_pct: Optional[float] = None


def _current_price(symbol: str) -> Optional[float]:
    try:
        import yfinance as yf
        t = yf.Ticker(symbol)
        info = t.fast_info
        price = info.get("last_price") or info.get("lastPrice")
        if price:
            return float(price)
        df = t.history(period="2d")
        if df is not None and not df.empty:
            return float(df["Close"].iloc[-1])
    except Exception:
        return None
    return None


@router.get("/portfolio", response_model=list[PositionOut])
def list_portfolio(status: Optional[str] = None, user: User = Depends(current_user)):
    """תיק - פוזיציות פתוחות (default) או סגורות. כולל P&L נוכחי לפתוחות."""
    with get_session() as session:
        stmt = select(PortfolioPosition).where(PortfolioPosition.user_id == user.id)
        if status in ("open", "closed"):
            stmt = stmt.where(PortfolioPosition.status == status)
        rows = list(session.exec(stmt.order_by(PortfolioPosition.opened_at.desc())))

    # P&L לפתוחות - מחיר נוכחי
    out = []
    for p in rows:
        item = PositionOut(
            id=p.id, symbol=p.symbol, shares=p.shares, avg_price=p.avg_price,
            opened_at=p.opened_at, closed_at=p.closed_at, exit_price=p.exit_price,
            status=p.status, notes=p.notes,
        )
        if p.status == "open":
            cp = _current_price(p.symbol)
            if cp:
                item.current_price = round(cp, 2)
                item.pnl_dollars = round((cp - p.avg_price) * p.shares, 2)
                item.pnl_pct = round((cp - p.avg_price) / p.avg_price * 100, 2)
        else:
            if p.exit_price:
                item.pnl_dollars = round((p.exit_price - p.avg_price) * p.shares, 2)
                item.pnl_pct = round((p.exit_price - p.avg_price) / p.avg_price * 100, 2)
        out.append(item)
    return out


@router.post("/portfolio", response_model=PositionOut)
def add_position(data: PositionIn, user: User = Depends(current_user)):
    sym = data.symbol.strip().upper()
    import re
    if not re.match(r"^[A-Z]{1,6}(\.[A-Z]{1,3})?$", sym):
        raise HTTPException(400, "סמל לא תקין")
    with get_session() as session:
        p = PortfolioPosition(
            user_id=user.id, symbol=sym, shares=data.shares,
            avg_price=data.avg_price, notes=data.notes, status="open",
        )
        session.add(p)
        session.flush()
        return PositionOut(
            id=p.id, symbol=p.symbol, shares=p.shares, avg_price=p.avg_price,
            opened_at=p.opened_at, closed_at=None, exit_price=None,
            status="open", notes=p.notes,
        )


@router.post("/portfolio/{pos_id}/close", response_model=PositionOut)
def close_position(pos_id: int, data: CloseIn, user: User = Depends(current_user)):
    with get_session() as session:
        p = session.get(PortfolioPosition, pos_id)
        if not p or p.user_id != user.id:
            raise HTTPException(404, "פוזיציה לא נמצאה")
        if p.status == "closed":
            raise HTTPException(400, "פוזיציה כבר סגורה")
        p.status = "closed"
        p.closed_at = datetime.utcnow()
        p.exit_price = data.exit_price
        session.add(p)
        session.flush()
        return PositionOut(
            id=p.id, symbol=p.symbol, shares=p.shares, avg_price=p.avg_price,
            opened_at=p.opened_at, closed_at=p.closed_at, exit_price=p.exit_price,
            status=p.status, notes=p.notes,
            pnl_dollars=round((p.exit_price - p.avg_price) * p.shares, 2),
            pnl_pct=round((p.exit_price - p.avg_price) / p.avg_price * 100, 2),
        )


@router.delete("/portfolio/{pos_id}")
def delete_position(pos_id: int, user: User = Depends(current_user)):
    with get_session() as session:
        p = session.get(PortfolioPosition, pos_id)
        if not p or p.user_id != user.id:
            raise HTTPException(404, "לא נמצא")
        session.delete(p)
    return {"ok": True}


# ========== DAILY DIGEST PREFERENCE ==========

class DigestPref(BaseModel):
    enabled: bool


@router.post("/digest-pref")
def set_digest(data: DigestPref, user: User = Depends(current_user)):
    with get_session() as session:
        u = session.get(User, user.id)
        u.daily_digest_enabled = data.enabled
        session.add(u)
    return {"ok": True, "enabled": data.enabled}
