"""שכבת גישה ל-DB - פונקציות שימושיות."""
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from app.storage.models import NewsItem, Notification, Scan, Signal, TradeJournal


# --- Scans ---
def create_scan(session: Session, kind: str) -> Scan:
    scan = Scan(kind=kind, started_at=datetime.utcnow())
    session.add(scan)
    session.flush()
    return scan


def finish_scan(
    session: Session,
    scan: Scan,
    items_found: int,
    status: str = "success",
    error: Optional[str] = None,
) -> None:
    scan.finished_at = datetime.utcnow()
    scan.items_found = items_found
    scan.status = status
    scan.error = error
    session.add(scan)


def list_recent_scans(session: Session, limit: int = 20) -> list[Scan]:
    stmt = select(Scan).order_by(Scan.started_at.desc()).limit(limit)
    return list(session.exec(stmt))


# --- Signals ---
def upsert_signal(session: Session, signal: Signal) -> Signal:
    session.add(signal)
    return signal


def get_open_signals(session: Session) -> list[Signal]:
    stmt = select(Signal).where(Signal.status == "open").order_by(Signal.created_at.desc())
    return list(session.exec(stmt))


def get_signals(session: Session, limit: int = 100, status: Optional[str] = None) -> list[Signal]:
    stmt = select(Signal).order_by(Signal.created_at.desc())
    if status:
        stmt = stmt.where(Signal.status == status)
    stmt = stmt.limit(limit)
    return list(session.exec(stmt))


def signal_exists_today(session: Session, symbol: str) -> bool:
    """לא להוסיף סיגנל כפול לאותה מניה באותו יום."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = select(Signal).where(
        Signal.symbol == symbol,
        Signal.created_at >= today_start,
        Signal.status != "skipped",
    )
    return session.exec(stmt).first() is not None


# --- News ---
def add_news_item(session: Session, item: NewsItem) -> Optional[NewsItem]:
    """מוסיף פריט; מחזיר None אם כבר קיים (לפי external_id)."""
    if item.external_id:
        existing = session.exec(
            select(NewsItem).where(NewsItem.external_id == item.external_id)
        ).first()
        if existing:
            return None
    session.add(item)
    return item


def get_news(
    session: Session,
    hours_back: int = 24,
    limit: int = 100,
    source: Optional[str] = None,
) -> list[NewsItem]:
    cutoff = datetime.utcnow() - timedelta(hours=hours_back)
    stmt = select(NewsItem).where(NewsItem.fetched_at >= cutoff)
    if source:
        stmt = stmt.where(NewsItem.source == source)
    stmt = stmt.order_by(NewsItem.published_at.desc().nullslast()).limit(limit)
    return list(session.exec(stmt))


# --- Journal / Stats ---
def get_journal(session: Session, limit: int = 50) -> list[TradeJournal]:
    stmt = select(TradeJournal).order_by(TradeJournal.entry_at.desc()).limit(limit)
    return list(session.exec(stmt))


# --- Notifications ---
def add_notification(
    session: Session,
    kind: str,
    title: str,
    message: str,
    symbol: Optional[str] = None,
    signal_id: Optional[int] = None,
    icon: str = "🔔",
) -> Notification:
    n = Notification(
        kind=kind, title=title, message=message,
        symbol=symbol, signal_id=signal_id, icon=icon,
    )
    session.add(n)
    return n


def get_notifications(
    session: Session,
    limit: int = 50,
    unread_only: bool = False,
    user_id: Optional[int] = None,
) -> list[Notification]:
    """אם user_id ניתן - מחזיר התראות של המשתמש + התראות גלובליות. אחרת רק גלובליות."""
    stmt = select(Notification).order_by(Notification.created_at.desc())
    if user_id is not None:
        stmt = stmt.where(
            (Notification.user_id == user_id) | (Notification.user_id.is_(None))
        )
    else:
        stmt = stmt.where(Notification.user_id.is_(None))
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    return list(session.exec(stmt.limit(limit)))


def count_unread(session: Session, user_id: Optional[int] = None) -> int:
    stmt = select(Notification).where(Notification.read_at.is_(None))
    if user_id is not None:
        stmt = stmt.where(
            (Notification.user_id == user_id) | (Notification.user_id.is_(None))
        )
    else:
        stmt = stmt.where(Notification.user_id.is_(None))
    return len(list(session.exec(stmt)))


def mark_notification_read(session: Session, nid: int) -> None:
    n = session.get(Notification, nid)
    if n and not n.read_at:
        n.read_at = datetime.utcnow()
        session.add(n)


def mark_all_read(session: Session) -> int:
    items = list(session.exec(select(Notification).where(Notification.read_at.is_(None))))
    now = datetime.utcnow()
    for n in items:
        n.read_at = now
        session.add(n)
    return len(items)


def compute_stats(session: Session) -> dict:
    """חישוב סטטיסטיקות מהירות לדשבורד."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today.replace(day=1)

    today_signals = session.exec(
        select(Signal).where(Signal.created_at >= today)
    ).all()
    open_signals = session.exec(
        select(Signal).where(Signal.status == "open")
    ).all()
    closed_month = session.exec(
        select(Signal).where(Signal.status == "closed", Signal.closed_at >= month_start)
    ).all()

    wins = [s for s in closed_month if (s.pnl_pct or 0) > 0]
    win_rate = (len(wins) / len(closed_month) * 100) if closed_month else 0
    monthly_pnl = sum((s.pnl_pct or 0) for s in closed_month)

    return {
        "signals_today": len(today_signals),
        "open_positions": len(open_signals),
        "win_rate_pct": round(win_rate, 1),
        "monthly_pnl_pct": round(monthly_pnl, 2),
        "closed_this_month": len(closed_month),
    }
