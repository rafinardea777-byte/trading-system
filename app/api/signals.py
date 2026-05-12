"""נקודות API לסיגנלים."""
from typing import Literal, Optional

from fastapi import APIRouter, Query

from app.api.schemas import SignalOut
from app.storage import get_session
from app.storage.repository import get_signals

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("", response_model=list[SignalOut])
def list_signals(
    limit: int = Query(100, ge=1, le=500),
    status: Optional[Literal["open", "closed", "skipped"]] = Query(None),
):
    with get_session() as session:
        rows = get_signals(session, limit=limit, status=status)
        return [SignalOut.model_validate(r, from_attributes=True) for r in rows]
