import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

# Single, consistent DB path (project root: app.db)
DEFAULT_DB_PATH = Path("app.db")

# Sentinel to express "no change" on updates
NOCHANGE = object()


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
    expires_txt = expires_at.isoformat() if isinstance(expires_at, datetime) else None
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO links (short_code, target_url, expires_at) VALUES (?, ?, ?)",
            (code, target_url, expires_txt),
        )
        conn.commit()
        cur = conn.execute("SELECT * FROM links WHERE short_code = ?", (code,))
        return dict(cur.fetchone())


def update_link(short_code: str, target_url=NOCHANGE, expires_at=NOCHANGE, db_path: Path = DEFAULT_DB_PATH):
    """
    Update only the fields that were passed (sentinel NOCHANGE means keep as-is).
    expires_at may be datetime, None (to clear), or NOCHANGE.
    """
    with _connect(db_path) as conn:
        sets, params = [], []

        if target_url is not NOCHANGE:
            sets.append("target_url = ?")
            params.append(str(target_url) if target_url is not None else None)

        if expires_at is not NOCHANGE:
            sets.append("expires_at = ?")
            if expires_at is None:
                params.append(None)  # clear
            elif isinstance(expires_at, datetime):
                params.append(expires_at.isoformat())
            else:
                # if Pydantic passed a string (rare), normalize to str
                params.append(str(expires_at))

        if not sets:
            row = conn.execute("SELECT * FROM links WHERE short_code = ?", (short_code,)).fetchone()
            return dict(row) if row else None

        params.append(short_code)
        cur = conn.execute(f"UPDATE links SET {', '.join(sets)} WHERE short_code = ?", params)
        conn.commit()
        if cur.rowcount == 0:
            return None

        row = conn.execute("SELECT * FROM links WHERE short_code = ?", (short_code,)).fetchone()
        return dict(row) if row else None


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


def update_last_access(code: str, dt: Union[datetime, str], db_path: Path = DEFAULT_DB_PATH) -> None:
    """Accept datetime or ISO string for convenience."""
    if isinstance(dt, datetime):
        dt = dt.isoformat()
    with _connect(db_path) as conn:
        conn.execute("UPDATE links SET last_access_at = ? WHERE short_code = ?", (dt, code))
        conn.commit()
