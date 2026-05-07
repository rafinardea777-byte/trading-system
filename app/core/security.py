"""תלות אבטחה ל-FastAPI - admin API key + rate limiting."""
import secrets

from fastapi import Header, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def _client_id(request: Request) -> str:
    """מפתח rate limiting - X-Forwarded-For (אם מאחורי proxy) או IP ישיר."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_client_id, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    """תלות שמחייבת X-Admin-Key תקין.

    ב-public_mode=False (פיתוח מקומי) - אין בדיקה.
    ב-public_mode=True - חובה להגדיר ADMIN_API_KEY ולשלוח אותו ב-header.
    """
    if not settings.public_mode:
        return
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_API_KEY not configured on server",
        )
    if not x_admin_key or not secrets.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-Admin-Key header",
        )
