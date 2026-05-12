"""Pydantic schemas - תגובות API."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SignalOut(BaseModel):
    id: int
    symbol: str
    price: float
    rsi: float
    volume_ratio: float
    strength: float
    target_1: float
    target_2: float
    stop_loss: float
    status: str
    created_at: datetime
    pnl_pct: Optional[float] = None


class NewsOut(BaseModel):
    id: int
    source: str
    author: str
    text: str
    url: str
    published_at: Optional[datetime]
    fetched_at: datetime
    hebrew_translation: Optional[str] = None
    hebrew_explanation: Optional[str] = None
    mentioned_symbols: Optional[str] = None  # CSV של סמלים


class ScanOut(BaseModel):
    id: int
    kind: str
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    items_found: int


class StatsOut(BaseModel):
    signals_today: int
    open_positions: int
    win_rate_pct: float
    monthly_pnl_pct: float
    closed_this_month: int


class JobResult(BaseModel):
    ok: bool
    detail: dict
