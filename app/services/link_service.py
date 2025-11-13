from typing import Optional, Dict, Any, List
from datetime import datetime, UTC
from ..repositories.base import LinkRepository
from .codes import generate_unique_code  # your original code strategy

class LinkService:
    def __init__(self, repo: LinkRepository, base_url: str):
        self.repo = repo
        self.base_url = base_url.rstrip("/")

    # --- helpers ---
    def _short_url(self, code: str) -> str:
        return f"{self.base_url}/{code}"

    def _parse_iso(self, x: Optional[str]) -> Optional[datetime]:
        if not x:
            return None
        try:
            return datetime.fromisoformat(x)
        except Exception:
            return None

    # --- operations ---
    def create(self, target_url: str, expires_at: Optional[str] = None) -> Dict[str, Any]:
        # light validation (pydantic also validates in models)
        if not target_url or not str(target_url).startswith(("http://", "https://")):
            raise ValueError("Invalid target_url")

        code = generate_unique_code(lambda c: self.repo.get_by_code(c) is not None)
        now_iso = datetime.now(UTC).isoformat()

        rec = self.repo.create({
            "short_code": code,
            "target_url": str(target_url),
            "created_at": now_iso,
            "expires_at": expires_at,
            "clicks": 0,
        })
        rec_out = self._shape(rec)
        return rec_out

    def list(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return [self._shape(r) for r in self.repo.list(limit=limit, offset=offset)]

    def get(self, code: str) -> Dict[str, Any]:
        rec = self.repo.get_by_code(code)
        if not rec:
            raise KeyError("not found")
        return self._shape(rec)

    def update(self, code: str, *, target_url_sentinel, expires_at_sentinel) -> Dict[str, Any]:
        rec = self.repo.get_by_code(code)
        if not rec:
            raise KeyError("not found")

        update_data = {}
        if target_url_sentinel is not _NOCHANGE:
            if target_url_sentinel is None:
                update_data["target_url"] = None
            else:
                if not str(target_url_sentinel).startswith(("http://", "https://")):
                    raise ValueError("Invalid target_url")
                update_data["target_url"] = str(target_url_sentinel)
        if expires_at_sentinel is not _NOCHANGE:
            update_data["expires_at"] = expires_at_sentinel

        updated = self.repo.update(rec["id"], update_data)
        return self._shape(updated)

    def delete(self, code: str) -> None:
        rec = self.repo.get_by_code(code)
        if not rec:
            raise KeyError("not found")
        self.repo.delete(rec["id"])

    def resolve(self, code: str) -> Dict[str, Any]:
        rec = self.repo.get_by_code(code)
        if not rec:
            raise KeyError("not found")

        # expiry
        expires = rec.get("expires_at")
        if expires:
            try:
                exp_dt = datetime.fromisoformat(expires)
                # If naive, treat as UTC (your tests send ISO strings; this keeps it safe)
                if exp_dt.tzinfo is None:
                    exp_dt = exp_dt.replace(tzinfo=UTC)
                if exp_dt <= datetime.now(UTC):
                    raise PermissionError("expired")
            except Exception:
                raise PermissionError("expired")

        # increment clicks + stamp last access
        now_iso = datetime.now(UTC).isoformat()
        updated = self.repo.update(
            rec["id"],
            {
                "clicks": rec.get("clicks", 0) + 1,
                "last_access_at": now_iso,
            },
        )
        return updated

    # shape into the public schema your UI expects
    def _shape(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "short_code": rec["short_code"],
            "target_url": rec["target_url"],
            "short_url": self._short_url(rec["short_code"]),
            "created_at": self._parse_iso(rec.get("created_at")),
            "expires_at": self._parse_iso(rec.get("expires_at")),
            "click_count": rec.get("clicks", 0),
            "last_access_at": self._parse_iso(rec.get("last_access_at")),
        }

class _NoChange: 
    pass
_NOCHANGE = _NoChange() # sentinel idea so we can distinguish “don’t touch this field” from “set to null”
