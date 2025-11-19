# tests/unit/test_codes_strategy.py
from app.services.codes_strategy import RandomCodeStrategy


def test_random_code_strategy_returns_string_of_min_length():
    strategy = RandomCodeStrategy(length=6, max_tries=3)

    # exists_fn always returns False → no collisions
    code = strategy.generate(lambda c: False)

    assert isinstance(code, str)
    assert len(code) >= 6
