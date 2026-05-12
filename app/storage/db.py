"""חיבור DB + יצירת טבלאות. תומך SQLite (לוקאלי) ו-Postgres (cloud)."""
import re
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings


def _normalize_db_url(url: str) -> str:
    """Render/Heroku נותנים postgres:// - SQLAlchemy 2 דורש postgresql://."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


_db_url = _normalize_db_url(settings.database_url)
_is_sqlite = _db_url.startswith("sqlite")

if _is_sqlite:
    _connect_args = {"check_same_thread": False, "timeout": 30}
    _engine_kwargs = {}
else:
    # Postgres - pre_ping למנוע idle connection drops; pool קטן ל-Render Starter
    _connect_args = {}
    _engine_kwargs = {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10}

_engine = create_engine(
    _db_url,
    connect_args=_connect_args,
    echo=False,
    **_engine_kwargs,
)


if _is_sqlite:
    @event.listens_for(_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _):
        """WAL מאפשר reads מקבילים תוך כדי writes - חיוני לסקדיולר + API."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


def init_db() -> None:
    """יצירת כל הטבלאות (idempotent) + מיגרציות בסיסיות."""
    # ייבוא ביטול-עצלן כדי שכל המודלים יירשמו ב-metadata
    from app.storage import models  # noqa: F401

    SQLModel.metadata.create_all(_engine)

    # SQLite migrations - הוספת עמודות חסרות בטבלאות קיימות
    if _is_sqlite:
        with _engine.begin() as conn:
            _add_column_if_missing(conn, "notification", "user_id", "INTEGER")
            _add_column_if_missing(conn, "newsitem", "mentioned_symbols", "TEXT")
            # User additions
            _add_column_if_missing(conn, "user", "email_verified", "BOOLEAN DEFAULT 0")
            _add_column_if_missing(conn, "user", "email_verify_token", "TEXT")
            _add_column_if_missing(conn, "user", "email_verify_expires", "TEXT")
            _add_column_if_missing(conn, "user", "reset_token", "TEXT")
            _add_column_if_missing(conn, "user", "reset_token_expires", "TEXT")
            _add_column_if_missing(conn, "user", "stripe_customer_id", "TEXT")
            _add_column_if_missing(conn, "user", "stripe_subscription_id", "TEXT")
            _add_column_if_missing(conn, "user", "subscription_status", "TEXT")
            _add_column_if_missing(conn, "user", "accepted_terms_at", "TEXT")


_VALID_TABLE = re.compile(r"^[a-z_][a-z0-9_]*$")
_VALID_COLUMN = re.compile(r"^[a-z_][a-z0-9_]*$")
_VALID_COL_DEF = re.compile(r"^[A-Z][A-Z0-9_ \(\)']*$", re.IGNORECASE)


def _add_column_if_missing(conn, table: str, column: str, col_def: str) -> None:
    """SQLite ALTER TABLE ADD COLUMN - idempotent. Validates identifiers to prevent injection."""
    from sqlalchemy import text

    # אימות שמות (idempotent migrations - שמות מקור פנימי, אבל חגורה+שלייקס)
    if not _VALID_TABLE.match(table):
        from app.core.logging import get_logger
        get_logger(__name__).error("migration_invalid_table", table=table)
        return
    if not _VALID_COLUMN.match(column):
        from app.core.logging import get_logger
        get_logger(__name__).error("migration_invalid_column", column=column)
        return
    if not _VALID_COL_DEF.match(col_def):
        from app.core.logging import get_logger
        get_logger(__name__).error("migration_invalid_coldef", col_def=col_def)
        return

    try:
        rows = conn.execute(text(f'PRAGMA table_info("{table}")')).fetchall()
        existing = {r[1] for r in rows}
        if column not in existing:
            conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {col_def}'))
    except Exception as e:
        from app.core.logging import get_logger
        get_logger(__name__).warning("migration_failed", table=table, column=column, error=str(e))


@contextmanager
def get_session() -> Iterator[Session]:
    session = Session(_engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_engine():
    return _engine
