# app/repositories/sqlite.py
import sqlite3
from typing import Optional, Dict, Any, List
from .base import LinkRepository

class SqliteLinkRepository(LinkRepository):
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def init_schema(self) -> None:
        with self._conn() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS links (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              short_code TEXT UNIQUE NOT NULL,
              target_url TEXT NOT NULL,
              created_at TEXT NOT NULL,
              expires_at TEXT NULL,
              clicks INTEGER NOT NULL DEFAULT 0
            );
            """)

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with self._conn() as con:
            cur = con.execute(
                "INSERT INTO links(short_code, target_url, created_at, expires_at, clicks) VALUES (?,?,?,?,?)",
                (data["short_code"], data["target_url"], data["created_at"], data.get("expires_at"), data.get("clicks", 0))
            )
            new_id = cur.lastrowid
            row = con.execute("SELECT * FROM links WHERE id = ?", (new_id,)).fetchone()
        return self._row_to_dict(row)

    def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        with self._conn() as con:
            row = con.execute("SELECT * FROM links WHERE short_code = ?", (code,)).fetchone()
        return self._row_to_dict(row) if row else None

    def get_by_id(self, link_id: int) -> Optional[Dict[str, Any]]:
        with self._conn() as con:
            row = con.execute("SELECT * FROM links WHERE id = ?", (link_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def list(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        with self._conn() as con:
            rows = con.execute("SELECT * FROM links ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def update(self, link_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        fields = []
        values = []
        for k in ["short_code", "target_url", "expires_at", "clicks"]:
            if k in data:
                fields.append(f"{k} = ?")
                values.append(data[k])
        if not fields:
            # nothing to update; return current row
            current = self.get_by_id(link_id)
            if current is None:
                raise KeyError("link not found")
            return current
        values.append(link_id)
        with self._conn() as con:
            con.execute(f"UPDATE links SET {', '.join(fields)} WHERE id = ?", values)
            row = con.execute("SELECT * FROM links WHERE id = ?", (link_id,)).fetchone()
        if not row:
            raise KeyError("link not found")
        return self._row_to_dict(row)

    def delete(self, link_id: int) -> None:
        with self._conn() as con:
            con.execute("DELETE FROM links WHERE id = ?", (link_id,))

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        # sqlite3 row is a tuple unless row_factory is set; map positions:
        # (id, short_code, target_url, created_at, expires_at, clicks)
        return {
            "id": row[0],
            "short_code": row[1],
            "target_url": row[2],
            "created_at": row[3],
            "expires_at": row[4],
            "clicks": row[5],
        }
