# tests/unit/test_link_service.py
from datetime import datetime, timedelta, UTC

import pytest

from app.services.link_service import LinkService, _NOCHANGE


class FakeLinkRepository:
    """
    Simple in-memory implementation of LinkRepository for unit tests.
    No SQLite, no FastAPI – just a dict.
    """
    def __init__(self) -> None:
        self._data: dict[int, dict] = {}
        self._next_id = 1

    def init_schema(self) -> None:
        # Not needed for the fake
        pass

    def create(self, data: dict) -> dict:
        link_id = self._next_id
        self._next_id += 1

        rec = {
            "id": link_id,
            "short_code": data["short_code"],
            "target_url": data["target_url"],
            "created_at": data["created_at"],
            "expires_at": data.get("expires_at"),
            "clicks": data.get("clicks", 0),
            "last_access_at": data.get("last_access_at"),
        }
        self._data[link_id] = rec
        return rec

    def get_by_code(self, code: str) -> dict | None:
        for rec in self._data.values():
            if rec["short_code"] == code:
                return rec
        return None

    def get_by_id(self, link_id: int) -> dict | None:
        return self._data.get(link_id)

    def list(self, limit: int = 100, offset: int = 0) -> list[dict]:
        rows = sorted(self._data.values(), key=lambda r: r["id"], reverse=True)
        return rows[offset : offset + limit]

    def update(self, link_id: int, data: dict) -> dict:
        rec = self._data[link_id].copy()
        rec.update(data)
        self._data[link_id] = rec
        return rec

    def delete(self, link_id: int) -> None:
        del self._data[link_id]


class FixedCodeStrategy:
    """
    Deterministic strategy so tests don’t depend on randomness.
    """
    def __init__(self, code: str) -> None:
        self.code = code

    def generate(self, exists_fn) -> str:
        if exists_fn(self.code):
            raise RuntimeError("code already exists in fake repo")
        return self.code


def make_service(base_url: str = "http://short.test"):
    repo = FakeLinkRepository()
    strategy = FixedCodeStrategy("abc123")
    svc = LinkService(repo=repo, base_url=base_url, code_strategy=strategy)
    return svc, repo


def test_create_valid_url_persists_and_shapes_output():
    # Arrange
    svc, repo = make_service()

    # Act
    out = svc.create("https://example.com")

    # Assert
    assert out["short_code"] == "abc123"
    assert out["short_url"] == "http://short.test/abc123"
    assert out["target_url"] == "https://example.com"
    # repo got one record
    assert len(repo._data) == 1


def test_create_invalid_url_raises_value_error():
    svc, _ = make_service()

    with pytest.raises(ValueError):
        svc.create("notaurl")  # missing http/https


def test_resolve_increments_clicks_and_sets_last_access():
    svc, repo = make_service()
    created = svc.create("https://example.com")
    code = created["short_code"]

    # Act
    resolved = svc.resolve(code)

    # Assert
    assert resolved["click_count"] == 1
    assert resolved["last_access_at"] is not None

    # Second resolve should bump to 2
    resolved2 = svc.resolve(code)
    assert resolved2["click_count"] == 2


def test_resolve_expired_link_raises_permission_error():
    svc, repo = make_service()

    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    # Insert directly into fake repo with expired expiry
    repo.create(
        {
            "short_code": "expired",
            "target_url": "https://example.com",
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": past,
            "clicks": 0,
        }
    )

    with pytest.raises(PermissionError):
        svc.resolve("expired")


def test_update_respects_nochange_sentinel_for_target_url():
    svc, _ = make_service()
    created = svc.create("https://example.com")
    code = created["short_code"]

    new_expiry_str = (datetime.now(UTC) + timedelta(days=1)).isoformat()

    # Act: only change expiry, keep target_url as-is via _NOCHANGE
    updated = svc.update(
        code,
        target_url_sentinel=_NOCHANGE,
        expires_at_sentinel=new_expiry_str,
    )

    # Assert
    assert updated["target_url"] == created["target_url"]
    assert updated["expires_at"].isoformat() == new_expiry_str


def test_delete_missing_code_raises_keyerror():
    svc, _ = make_service()

    with pytest.raises(KeyError):
        svc.delete("does-not-exist")
