"""תלויות FastAPI לבקשת משתמש מחובר."""
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlmodel import Session, select

from app.auth.security import decode_token
from app.storage import User, get_session


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip()


def _user_from_token(token: str) -> Optional[User]:
    payload = decode_token(token)
    if not payload:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        return None
    with get_session() as session:
        user = session.get(User, user_id)
        if user and user.is_active:
            # detach from session
            session.expunge(user)
            return user
    return None


def current_user(authorization: Optional[str] = Header(default=None)) -> User:
    """דורש משתמש מחובר. 401 אם אין/לא תקף."""
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    user = _user_from_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return user


def optional_user(authorization: Optional[str] = Header(default=None)) -> Optional[User]:
    """מחזיר user אם יש token תקף, אחרת None - בלי 401."""
    token = _extract_token(authorization)
    if not token:
        return None
    return _user_from_token(token)


def require_admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user
