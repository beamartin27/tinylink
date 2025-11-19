# tests/unit/test_codes.py
from app.services import codes


def test_code_generator_collision():
    calls = {"n": 0}

    def fake_exists(code: str) -> bool:
        calls["n"] += 1
        # collide first two times, third is free
        return calls["n"] < 3

    code = codes.generate_unique_code(fake_exists, max_tries=5)

    assert isinstance(code, str)
    assert len(code) >= 6
    assert calls["n"] == 3
