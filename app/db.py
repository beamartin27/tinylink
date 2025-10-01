# app/db.py
import os
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

# Sentinel to express "no change" on updates
NOCHANGE = object()


# --- DB path handling ---------------------------------------------------------

def _default_db_path() -> Path:
    """
    Determine the DB file to use.
    - If APP_DB_PATH is set, use it (great for tests and containers).
    - Otherwise use project-root app.db (same as before).
    """
    env = os.getenv("APP_DB_PATH")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "app.db"


def _connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Connect to SQLite using the resolved DB path."""
    path = db_path or _default_db_path()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


# --- Schema / bootstrap -------------------------------------------------------

def init_db(db_path: Optional[Path] = None) -> None:
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


# --- Queries ------------------------------------------------------------------

def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    return dict(row) if row else None


def get_by_code(code: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    with _connect(db_path) as conn:
        cur = conn.execute("SELECT * FROM links WHERE short_code = ?", (code,))
        return _row_to_dict(cur.fetchone())


def list_links(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    with _connect(db_path) as conn:
        cur = conn.execute("SELECT * FROM links ORDER BY datetime(created_at) DESC")
        return [dict(r) for r in cur.fetchall()]


def insert_link(
    code: str,
    target_url: str,
    expires_at: Optional[Union[datetime, str]],
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    if isinstance(expires_at, datetime):
        expires_txt = expires_at.isoformat()
    elif isinstance(expires_at, str):
        expires_txt = expires_at
    else:
        expires_txt = None

    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO links (short_code, target_url, expires_at) VALUES (?, ?, ?)",
            (code, target_url, expires_txt),
        )
        conn.commit()
        cur = conn.execute("SELECT * FROM links WHERE short_code = ?", (code,))
        return dict(cur.fetchone())


def update_link(
    short_code: str,
    target_url: Union[str, None, object] = NOCHANGE,
    expires_at: Union[datetime, str, None, object] = NOCHANGE,
    db_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """
    Update only the fields that were passed (sentinel NOCHANGE means keep as-is).
    expires_at may be datetime, ISO string, None (to clear), or NOCHANGE.
    """
    with _connect(db_path) as conn:
        sets: List[str] = []
        params: List[Any] = []

        if target_url is not NOCHANGE:
            sets.append("target_url = ?")
            params.append(str(target_url) if target_url is not None else None)

        if expires_at is not NOCHANGE:
            sets.append("expires_at = ?")
            if expires_at is None:
                params.append(None)
            elif isinstance(expires_at, datetime):
                params.append(expires_at.isoformat())
            else:
                params.append(str(expires_at))

        if not sets:
            row = conn.execute(
                "SELECT * FROM links WHERE short_code = ?",
                (short_code,),
            ).fetchone()
            return dict(row) if row else None

        params.append(short_code)
        cur = conn.execute(
            f"UPDATE links SET {', '.join(sets)} WHERE short_code = ?",
            params,
        )
        conn.commit()
        if cur.rowcount == 0:
            return None

        row = conn.execute(
            "SELECT * FROM links WHERE short_code = ?",
            (short_code,),
        ).fetchone()
        return dict(row) if row else None


def delete_link(code: str, db_path: Optional[Path] = None) -> bool:
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM links WHERE short_code = ?", (code,))
        conn.commit()
        return cur.rowcount > 0


def exists_code(code: str, db_path: Optional[Path] = None) -> bool:
    with _connect(db_path) as conn:
        cur = conn.execute("SELECT 1 FROM links WHERE short_code = ? LIMIT 1", (code,))
        return cur.fetchone() is not None


def increment_click(code: str, db_path: Optional[Path] = None) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE links SET click_count = click_count + 1 WHERE short_code = ?",
            (code,),
        )
        conn.commit()


def update_last_access(
    code: str,
    dt: Union[datetime, str],
    db_path: Optional[Path] = None,
) -> None:
    """Accept datetime or ISO string for convenience."""
    iso = dt.isoformat() if isinstance(dt, datetime) else str(dt)
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE links SET last_access_at = ? WHERE short_code = ?",
            (iso, code),
        )
        conn.commit()