# app/services/codes_strategy.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Dict, Type

from . import codes  # existing codes.py (generate_code, generate_unique_code)


class CodeStrategy(ABC):
    """Abstraction for 'how do we generate a short code?'."""

    @abstractmethod
    def generate(self, exists_fn: Callable[[str], bool]) -> str:  # pragma: no cover - interface only
        """
        exists_fn(code) -> True if code already exists.
        Strategy must return a non-colliding code.
        """
        raise NotImplementedError


class RandomCodeStrategy(CodeStrategy):
    """Current behavior: random codes with collision retries."""

    def __init__(self, length: int = codes.LENGTH, max_tries: int = 5) -> None:
        self.length = length
        self.max_tries = max_tries

    def generate(self, exists_fn: Callable[[str], bool]) -> str:
        # Delegate to your existing function so tests on codes.py still describe reality.
        return codes.generate_unique_code(exists_fn, max_tries=self.max_tries, length=self.length,)


# If more strategies are ever added, register them here.
STRATEGIES: Dict[str, Type[CodeStrategy]] = {
    "random": RandomCodeStrategy,
    # "hash": HashCodeStrategy,  # example for the future
}
