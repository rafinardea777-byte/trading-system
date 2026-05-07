"""הגירה: signals.json הישן ↦ SQLite החדש.

שימוש:
    python scripts/migrate_old_signals.py path/to/signals.json
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.storage import Signal, get_session, init_db
from app.storage.repository import upsert_signal


def migrate(path: Path) -> int:
    init_db()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print("[ERROR] expected JSON array")
        return 1

    imported = 0
    with get_session() as session:
        for s in data:
            symbol = s.get("symbol")
            if not symbol:
                continue
            price = float(s.get("price", 0))
            sig = Signal(
                symbol=symbol,
                price=price,
                rsi=float(s.get("rsi", 0)),
                volume_ratio=float(s.get("volume_ratio", 0)),
                ma_fast=0,
                ma_slow=0,
                strength=0,
                target_1=price * (1 + settings.target_1_pct),
                target_2=price * (1 + settings.target_2_pct),
                stop_loss=price * (1 - settings.stop_loss_pct),
                created_at=datetime.utcnow(),
                status="closed",  # היסטורי
            )
            upsert_signal(session, sig)
            imported += 1

    print(f"[OK] imported {imported} signals from {path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(migrate(Path(sys.argv[1])))
