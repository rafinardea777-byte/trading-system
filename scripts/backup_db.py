"""DB Backup - שימוש ב-SQLite Online Backup API (לא נחסם ע"י WAL).

הפעלה: python scripts/backup_db.py
תזמון: scripts/install_backup_task.ps1 רושם משימה יומית ב-02:00
"""
import gzip
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# נתיבים
ROOT = Path(__file__).resolve().parents[1]
DB_FILE = ROOT / "data" / "trading.db"
BACKUP_DIR = Path(os.path.expanduser("~")) / "Desktop" / "TradingPro-Backups"
KEEP_DAYS = 14


def main() -> int:
    if not DB_FILE.exists():
        print(f"[!] DB file not found: {DB_FILE}")
        return 1

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    tmp_backup = BACKUP_DIR / f"trading_{stamp}.db"
    final_backup = BACKUP_DIR / f"trading_{stamp}.db.gz"

    # SQLite Online Backup - לא תופס lock על המקור, עובד גם כש-WAL פעיל
    src = sqlite3.connect(str(DB_FILE))
    dest = sqlite3.connect(str(tmp_backup))
    try:
        with dest:
            src.backup(dest)
    finally:
        src.close()
        dest.close()

    # דחיסה ב-gzip
    with open(tmp_backup, "rb") as f_in, gzip.open(final_backup, "wb", compresslevel=9) as f_out:
        f_out.writelines(f_in)
    tmp_backup.unlink()

    orig_size = DB_FILE.stat().st_size / 1024
    new_size = final_backup.stat().st_size / 1024
    print(f"[OK] backup: {final_backup.name} ({new_size:.1f} KB from {orig_size:.1f} KB)")

    # Rotation - מחיקת ישנים מ-KEEP_DAYS
    cutoff = datetime.now() - timedelta(days=KEEP_DAYS)
    deleted = 0
    for f in BACKUP_DIR.glob("trading_*.db.gz"):
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink()
            deleted += 1
    if deleted:
        print(f"[OK] rotated: deleted {deleted} backups older than {KEEP_DAYS} days")

    backups = list(BACKUP_DIR.glob("trading_*.db.gz"))
    total_mb = sum(f.stat().st_size for f in backups) / 1024 / 1024
    print(f"[i] total: {len(backups)} backups, {total_mb:.2f} MB")
    print(f"[i] dir: {BACKUP_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
