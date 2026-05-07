"""נקודות API לחדשות."""
from typing import Optional

from fastapi import APIRouter, Query

from app.api.schemas import NewsOut
from app.storage import get_session
from app.storage.repository import get_news

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("", response_model=list[NewsOut])
def list_news(
    hours_back: int = Query(24, ge=1, le=24 * 7),
    limit: int = Query(100, ge=1, le=500),
    source: Optional[str] = Query(None, description="twitter | rss"),
):
    with get_session() as session:
        rows = get_news(session, hours_back=hours_back, limit=limit, source=source)
        return [NewsOut.model_validate(r, from_attributes=True) for r in rows]
