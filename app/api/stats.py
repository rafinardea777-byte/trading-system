"""נקודות API לסטטיסטיקות."""
from fastapi import APIRouter

from app.api.schemas import ScanOut, StatsOut
from app.storage import get_session
from app.storage.repository import compute_stats, list_recent_scans

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def get_stats():
    with get_session() as session:
        return StatsOut(**compute_stats(session))


@router.get("/scans", response_model=list[ScanOut])
def get_scans(limit: int = 20):
    with get_session() as session:
        rows = list_recent_scans(session, limit=limit)
        return [ScanOut.model_validate(r, from_attributes=True) for r in rows]
