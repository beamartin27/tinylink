import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "app.db"

def _connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS links (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              short_code TEXT NOT NULL UNIQUE,
              target_url TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              click_count INTEGER NOT NULL DEFAULT 0,
              last_access_at TEXT,
              expires_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_links_short_code ON links(short_code);
            """
        )
        conn.commit()

def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return dict(row) if row else None

def get_by_code(code: str, db_path: Path = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    with _connect(db_path) as conn:
        cur = conn.execute("SELECT * FROM links WHERE short_code = ?", (code,))
        row = cur.fetchone()
        return _row_to_dict(row)

def list_links(db_path: Path = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    with _connect(db_path) as conn:
        cur = conn.execute("SELECT * FROM links ORDER BY datetime(created_at) DESC")
        return [dict(r) for r in cur.fetchall()]

def insert_link(code: str, target_url: str, expires_at: Optional[datetime], db_path: Path = DEFAULT_DB_PATH) -> Dict[str, Any]:
    expires_txt = expires_at.isoformat() if expires_at else None
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO links (short_code, target_url, expires_at) VALUES (?, ?, ?)",
            (code, target_url, expires_txt),
        )
        conn.commit()
        cur = conn.execute("SELECT * FROM links WHERE short_code = ?", (code,))
        return dict(cur.fetchone())

def update_link(code: str, target_url: Optional[str], expires_at: Optional[datetime], db_path: Path = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    with _connect(db_path) as conn:
        sets, vals = [], []
        if target_url is not None:
            sets.append("target_url = ?")
            vals.append(target_url)
        if expires_at is not None:
            sets.append("expires_at = ?")
            vals.append(expires_at.isoformat())
        if not sets:
            return get_by_code(code, db_path)
        vals.append(code)
        cur = conn.execute(f"UPDATE links SET {', '.join(sets)} WHERE short_code = ?", vals)
        conn.commit()
        if cur.rowcount == 0:
            return None
        return get_by_code(code, db_path)

def delete_link(code: str, db_path: Path = DEFAULT_DB_PATH) -> bool:
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM links WHERE short_code = ?", (code,))
        conn.commit()
        return cur.rowcount > 0

def exists_code(code: str, db_path: Path = DEFAULT_DB_PATH) -> bool:
    with _connect(db_path) as conn:
        cur = conn.execute("SELECT 1 FROM links WHERE short_code = ? LIMIT 1", (code,))
        return cur.fetchone() is not None

def increment_click(code: str, db_path: Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("UPDATE links SET click_count = click_count + 1 WHERE short_code = ?", (code,))
        conn.commit()

def update_last_access(code: str, dt: datetime, db_path: Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("UPDATE links SET last_access_at = ? WHERE short_code = ?", (dt.isoformat(), code))
        conn.commit()
