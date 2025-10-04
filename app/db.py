# app/db.py
import os
import sqlite3 # sqlite3 is a .py file that you can import (that is called a module)
from pathlib import Path # pathlib is a package (contains several .py files and a __init.py__), from there you import Path, which is a module inside of it
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
        return Path(env) # Path: from pathlib. It’s an object for filesystem paths
    return Path(__file__).resolve().parent.parent / "app.db" # special (double-underscore) variable that Python sets to the current file’s path (here, db.py).


def _connect(db_path: Optional[Path] = None) -> sqlite3.Connection: # As sqlite3 is a module, sqlite3.Connection accesses the class Connection from that module
    """Connect to SQLite using the resolved DB path."""
    path = db_path or _default_db_path()
    conn = sqlite3.connect(str(path)) # returns a sqlite3.Connection object (the DB connection).
    conn.row_factory = sqlite3.Row # row_factory is a connection attribute that tells SQLite how to build row results.
    # sqlite3.Row is a factory class provided by the sqlite3 module: it makes rows behave like dicts and tuples (you can do row["short_code"] or row[0]).
    return conn


# --- Schema / bootstrap -------------------------------------------------------

def init_db(db_path: Optional[Path] = None) -> None:
    with _connect(db_path) as conn: # with block auto-closes the connection
        conn.executescript( # executescript allows multiple statements;
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
        conn.commit() # Send to sqlite3


# --- Queries ------------------------------------------------------------------

def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]: # Format sqlite3 row to dict
    return dict(row) if row else None


def get_by_code(code: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    with _connect(db_path) as conn: # Stablish db connection
        """
        execute(...) already sends the SQL to the database.
        cur is a cursor object (like a pointer into the result set).
        You then “pull” rows with cur.fetchone() or cur.fetchall().
        """
        cur = conn.execute("SELECT * FROM links WHERE short_code = ?", (code,)) # talk to db in sql, Parameterized SQL (the ? avoids SQL injection).
        return _row_to_dict(cur.fetchone()) # return dict formatted row


def list_links(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    with _connect(db_path) as conn:
        cur = conn.execute("SELECT * FROM links ORDER BY datetime(created_at) DESC") # Lists all links, newest first. datetime(created_at) lets SQLite sort correctly.
        return [dict(r) for r in cur.fetchall()] # return all the records in dict style


def insert_link(code: str,
    target_url: str,
    expires_at: Optional[Union[datetime, str]],
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    if isinstance(expires_at, datetime): # Handle both datetime type and str type
        expires_txt = expires_at.isoformat()
    elif isinstance(expires_at, str):
        expires_txt = expires_at
    else:
        expires_txt = None

    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO links (short_code, target_url, expires_at) VALUES (?, ?, ?)",
            (code, target_url, expires_txt), # insert with the dynamic values
        )
        conn.commit()
        cur = conn.execute("SELECT * FROM links WHERE short_code = ?", (code,)) # Extract the inserted link data
        return dict(cur.fetchone()) # format to dict


def update_link(
    short_code: str,
    target_url: Union[str, None, object] = NOCHANGE, # Handle different data types and no modification
    expires_at: Union[datetime, str, None, object] = NOCHANGE,
    db_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """
    Update only the fields that were passed (sentinel NOCHANGE means keep as-is).
    expires_at may be datetime, ISO string, None (to clear), or NOCHANGE.
    """
    with _connect(db_path) as conn:
        sets: List[str] = [] # sets will hold SQL fragments for the SET clause (e.g., "target_url = ?")
        params: List[Any] = [] # params will hold the parameter values corresponding to those ? placeholders.

        if target_url is not NOCHANGE:
            sets.append("target_url = ?")
            params.append(str(target_url) if target_url is not None else None) # If it’s None, append None so SQL sets it to NULL (clear the column).

        if expires_at is not NOCHANGE:
            sets.append("expires_at = ?")
            if expires_at is None:
                params.append(None)
            elif isinstance(expires_at, datetime): # Handle both possible datatypes, normalize the value
                params.append(expires_at.isoformat())
            else:
                params.append(str(expires_at))

        if not sets: # If no fields were requested to update (both were NOCHANGE), don’t do an UPDATE at all.
            row = conn.execute(
                "SELECT * FROM links WHERE short_code = ?",
                (short_code,),
            ).fetchone()
            return dict(row) if row else None

        params.append(short_code)
        cur = conn.execute(
            f"UPDATE links SET {', '.join(sets)} WHERE short_code = ?", # sets contains target_url = ? and expires_at = ?
            params, # params contains target url, expires at and short code, which replace the three ???
        )
        conn.commit()
        if cur.rowcount == 0:
            return None # If no rows were affected, there is no such short_code → return None.

        row = conn.execute(
            "SELECT * FROM links WHERE short_code = ?",
            (short_code,),
        ).fetchone()
        return dict(row) if row else None # Re-select and return the fresh, updated row.


def delete_link(code: str, db_path: Optional[Path] = None) -> bool:
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM links WHERE short_code = ?", (code,))
        conn.commit()
        return cur.rowcount > 0 # cur.rowcount is the number of rows affected by the DELETE, if >0 success.


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


def update_last_access(code: str, dt: Union[datetime, str], db_path: Optional[Path] = None,) -> None: # With union we accept multiple types of the same parameter
    """Accept datetime or ISO string for convenience."""
    iso = dt.isoformat() if isinstance(dt, datetime) else str(dt)
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE links SET last_access_at = ? WHERE short_code = ?",
            (iso, code),
        )
        conn.commit()