# app/repositories/sqlite.py
from typing import Dict, Any, List, Optional
import sqlite3
from pathlib import Path

class SqliteLinkRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def init_schema(self) -> None:
        # Safe to call always. Matches legacy schema in app/db.py
        with self._conn() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS links(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  short_code   TEXT UNIQUE NOT NULL,
                  target_url   TEXT NOT NULL,
                  created_at   TEXT NOT NULL,
                  expires_at   TEXT,
                  click_count  INTEGER NOT NULL DEFAULT 0,
                  last_access_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_links_code ON links(short_code);
                """
            )

    # ---------- helpers ----------
    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        # Map DB's click_count -> API's clicks
        return {
            "id": row["id"],
            "short_code": row["short_code"],
            "target_url": row["target_url"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
            "clicks": row["click_count"],
            "last_access_at": row["last_access_at"],
        }

    # ---------- CRUD ----------
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Accepts 'clicks' in data; writes 'click_count' to DB
        clicks = data.get("clicks", 0)
        with self._conn() as con:
            cur = con.execute(
                "INSERT INTO links(short_code, target_url, created_at, expires_at, click_count) VALUES (?,?,?,?,?)",
                (data["short_code"], data["target_url"], data["created_at"], data.get("expires_at"), clicks),
            )
            new_id = cur.lastrowid
            row = con.execute("SELECT * FROM links WHERE id=?", (new_id,)).fetchone()
            return self._row_to_dict(row)

    def list(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT * FROM links ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        with self._conn() as con:
            row = con.execute("SELECT * FROM links WHERE short_code=?", (code,)).fetchone()
            return self._row_to_dict(row) if row else None

    def update(self, link_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        # Translate 'clicks' -> 'click_count' if present
        sets = []
        params: list[Any] = []

        if "target_url" in data:
            sets.append("target_url=?")
            params.append(data["target_url"])
        if "expires_at" in data:
            sets.append("expires_at=?")
            params.append(data["expires_at"])
        if "clicks" in data:
            sets.append("click_count=?")
            params.append(data["clicks"])
        if "last_access_at" in data:
            sets.append("last_access_at=?")
            params.append(data["last_access_at"])

        if not sets:
            # nothing to update; return current row
            with self._conn() as con:
                row = con.execute("SELECT * FROM links WHERE id=?", (link_id,)).fetchone()
                return self._row_to_dict(row)

        sql = f"UPDATE links SET {', '.join(sets)} WHERE id=?"
        params.append(link_id)

        with self._conn() as con:
            con.execute(sql, tuple(params))
            row = con.execute("SELECT * FROM links WHERE id=?", (link_id,)).fetchone()
            return self._row_to_dict(row)

    def delete(self, link_id: int) -> None:
        with self._conn() as con:
            con.execute("DELETE FROM links WHERE id=?", (link_id,))
