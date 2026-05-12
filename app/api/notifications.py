"""נקודות API להתראות - bell icon + drawer."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends

from app.auth.deps import optional_user
from app.storage import User, get_session
from app.storage.repository import (
    count_unread,
    get_notifications,
    mark_all_read,
    mark_notification_read,
)
from pydantic import BaseModel

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


def _user_id(user: Optional[User]) -> Optional[int]:
    return user.id if user else None


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    limit: int = 50,
    unread_only: bool = False,
    user: Optional[User] = Depends(optional_user),
):
    with get_session() as session:
        rows = get_notifications(session, limit=limit, unread_only=unread_only, user_id=_user_id(user))
        return [NotificationOut.model_validate(r, from_attributes=True) for r in rows]


@router.get("/count")
def get_unread_count(user: Optional[User] = Depends(optional_user)):
    with get_session() as session:
        return {"unread": count_unread(session, user_id=_user_id(user))}


@router.post("/{nid}/read")
def mark_read(nid: int):
    with get_session() as session:
        mark_notification_read(session, nid)
    return {"ok": True}


@router.post("/read-all")
def mark_all(user: Optional[User] = Depends(optional_user)):
    with get_session() as session:
        n = mark_all_read(session)
    return {"ok": True, "marked": n}
