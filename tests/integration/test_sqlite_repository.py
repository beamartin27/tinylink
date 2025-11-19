# tests/integration/test_sqlite_repository.py
from datetime import datetime, UTC

from app.repositories.sqlite import SqliteLinkRepository


def make_repo(tmp_path):
    db_file = tmp_path / "repo_test.db"
    repo = SqliteLinkRepository(str(db_file))
    repo.init_schema()
    return repo


def test_create_and_get_by_code(tmp_path):
    repo = make_repo(tmp_path)

    created = repo.create(
        {
            "short_code": "abc123",
            "target_url": "https://example.com",
            "created_at": datetime.now(UTC),
            "expires_at": None,
            "clicks": 0,
        }
    )

    fetched = repo.get_by_code("abc123")
    assert fetched is not None
    assert fetched["id"] == created["id"]
    assert fetched["short_code"] == "abc123"
    assert fetched["target_url"] == "https://example.com"


def test_update_and_delete(tmp_path):
    repo = make_repo(tmp_path)

    created = repo.create(
        {
            "short_code": "to-update",
            "target_url": "https://old.example",
            "created_at": datetime.now(UTC),
            "expires_at": None,
            "clicks": 0,
        }
    )

    # Update target + clicks
    updated = repo.update(
        created["id"],
        {"target_url": "https://new.example", "clicks": 5},
    )
    assert updated["target_url"] == "https://new.example"
    assert updated["clicks"] == 5

    # Delete
    repo.delete(created["id"])
    assert repo.get_by_id(created["id"]) is None
