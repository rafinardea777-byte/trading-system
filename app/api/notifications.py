"""נקודות API להתראות - bell icon + drawer."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.storage import get_session
from app.storage.repository import (
    count_unread,
    get_notifications,
    mark_all_read,
    mark_notification_read,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: int
    kind: str
    title: str
    message: str
    symbol: Optional[str] = None
    signal_id: Optional[int] = None
    icon: str
    created_at: datetime
    read_at: Optional[datetime] = None


@router.get("", response_model=list[NotificationOut])
def list_notifications(limit: int = 50, unread_only: bool = False):
    with get_session() as session:
        rows = get_notifications(session, limit=limit, unread_only=unread_only)
        return [NotificationOut.model_validate(r, from_attributes=True) for r in rows]


@router.get("/count")
def get_unread_count():
    with get_session() as session:
        return {"unread": count_unread(session)}


@router.post("/{nid}/read")
def mark_read(nid: int):
    with get_session() as session:
        mark_notification_read(session, nid)
    return {"ok": True}


@router.post("/read-all")
def mark_all():
    with get_session() as session:
        n = mark_all_read(session)
    return {"ok": True, "marked": n}
