"""נקודות API למשתמש המחובר - watchlist + העדפות."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import select

from app.auth.deps import current_user
from app.storage import User, UserWatchlist, get_session

router = APIRouter(prefix="/api/me", tags=["me"])


class WatchlistItemOut(BaseModel):
    symbol: str
    note: Optional[str] = None
    added_at: datetime


class WatchlistAddIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=8)
    note: Optional[str] = Field(default=None, max_length=140)


class WatchlistBulkIn(BaseModel):
    symbols: list[str]


def _norm(sym: str) -> str:
    return (sym or "").strip().upper()


@router.get("/watchlist", response_model=list[WatchlistItemOut])
def list_watchlist(user: User = Depends(current_user)):
    with get_session() as session:
        rows = list(session.exec(
            select(UserWatchlist)
            .where(UserWatchlist.user_id == user.id)
            .order_by(UserWatchlist.added_at.desc())
        ))
        return [WatchlistItemOut(symbol=r.symbol, note=r.note, added_at=r.added_at) for r in rows]


@router.post("/watchlist", response_model=WatchlistItemOut, status_code=status.HTTP_201_CREATED)
def add_watchlist(data: WatchlistAddIn, user: User = Depends(current_user)):
    sym = _norm(data.symbol)
    if not sym.isalpha():
        raise HTTPException(status_code=400, detail="סמל לא תקין")
    with get_session() as session:
        existing = session.exec(
            select(UserWatchlist).where(
                UserWatchlist.user_id == user.id,
                UserWatchlist.symbol == sym,
            )
        ).first()
        if existing:
            return WatchlistItemOut(symbol=existing.symbol, note=existing.note, added_at=existing.added_at)
        item = UserWatchlist(user_id=user.id, symbol=sym, note=data.note)
        session.add(item)
        session.flush()
        return WatchlistItemOut(symbol=item.symbol, note=item.note, added_at=item.added_at)


@router.delete("/watchlist/{symbol}")
def remove_watchlist(symbol: str, user: User = Depends(current_user)):
    sym = _norm(symbol)
    with get_session() as session:
        existing = session.exec(
            select(UserWatchlist).where(
                UserWatchlist.user_id == user.id,
                UserWatchlist.symbol == sym,
            )
        ).first()
        if not existing:
            raise HTTPException(status_code=404, detail="לא ב-watchlist")
        session.delete(existing)
    return {"ok": True}


@router.post("/watchlist/sync")
def sync_watchlist(data: WatchlistBulkIn, user: User = Depends(current_user)):
    """איחוד עם רשימה קיימת - מוסיף סמלים שעדיין לא בשרת. שימושי לסנכרון מ-localStorage."""
    added = 0
    with get_session() as session:
        existing_syms = {
            r.symbol for r in session.exec(
                select(UserWatchlist).where(UserWatchlist.user_id == user.id)
            )
        }
        for raw in data.symbols:
            sym = _norm(raw)
            if not sym.isalpha() or len(sym) > 8 or sym in existing_syms:
                continue
            session.add(UserWatchlist(user_id=user.id, symbol=sym))
            existing_syms.add(sym)
            added += 1
    return {"ok": True, "added": added}
