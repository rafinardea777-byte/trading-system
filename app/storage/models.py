"""מודלי DB - SQLModel."""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Scan(SQLModel, table=True):
    """ריצה של סורק (news או market)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    kind: str = Field(index=True)  # "news" | "market"
    started_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    finished_at: Optional[datetime] = None
    status: str = "running"  # running | success | failed
    items_found: int = 0
    error: Optional[str] = None


class Signal(SQLModel, table=True):
    """סיגנל מסחר מהסורק הטכני."""

    id: Optional[int] = Field(default=None, primary_key=True)
    scan_id: Optional[int] = Field(default=None, foreign_key="scan.id", index=True)
    symbol: str = Field(index=True)
    price: float
    rsi: float
    volume_ratio: float
    ma_fast: float
    ma_slow: float
    strength: float = 0.0  # 0-10
    target_1: float
    target_2: float
    stop_loss: float
    status: str = Field(default="open", index=True)  # open | closed | skipped
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    closed_at: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl_pct: Optional[float] = None


class NewsItem(SQLModel, table=True):
    """פריט חדשות (ציוץ או RSS)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    scan_id: Optional[int] = Field(default=None, foreign_key="scan.id", index=True)
    source: str = Field(index=True)  # twitter | rss
    author: str = Field(index=True)
    text: str
    url: str = ""
    published_at: Optional[datetime] = Field(default=None, index=True)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    hebrew_translation: Optional[str] = None
    hebrew_explanation: Optional[str] = None

    # למניעת כפילויות
    external_id: Optional[str] = Field(default=None, unique=True, index=True)


class TradeJournal(SQLModel, table=True):
    """יומן עסקאות (לאחר כניסה)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    signal_id: Optional[int] = Field(default=None, foreign_key="signal.id")
    symbol: str = Field(index=True)
    entry_price: float
    entry_at: datetime = Field(default_factory=datetime.utcnow)
    position_size_usd: float
    target_1: float
    target_2: float
    stop_loss: float
    exit_price: Optional[float] = None
    exit_at: Optional[datetime] = None
    pnl_pct: Optional[float] = None
    status: str = Field(default="open", index=True)  # open | closed
    notes: str = ""
