"""Stock and prices, behind one small interface the graph can use.

InMemoryInventory backs the command-line chat and the graph tests.
The backend uses Store from store.py, which saves to Postgres.
"""

from __future__ import annotations

import threading
from typing import Protocol

from .menu import MENU, PRICES


class Inventory(Protocol):
    def menu(self) -> dict[str, int]:
        """Dish -> quantity available right now."""
        ...

    def prices(self) -> dict[str, int]:
        """Dish -> price per plate."""
        ...

    def reserve(self, items: dict[str, int]) -> bool:
        """Take dish -> quantity out of stock. All or nothing; False if any dish is short."""
        ...

    def release(self, items: dict[str, int]) -> None:
        """Put reserved quantities back."""
        ...


class InMemoryInventory:
    def __init__(self, menu: dict[str, int] | None = None, prices: dict[str, int] | None = None):
        self._menu = dict(MENU if menu is None else menu)   # copied, so callers' dicts never change
        self._prices = dict(PRICES if prices is None else prices)
        self._lock = threading.Lock()

    def menu(self) -> dict[str, int]:
        with self._lock:
            return dict(self._menu)

    def prices(self) -> dict[str, int]:
        with self._lock:
            return dict(self._prices)

    def reserve(self, items: dict[str, int]) -> bool:
        with self._lock:
            if any(self._menu.get(d, 0) < q for d, q in items.items()):
                return False
            for d, q in items.items():
                self._menu[d] -= q
            return True

    def release(self, items: dict[str, int]) -> None:
        with self._lock:
            for d, q in items.items():
                if d in self._menu:
                    self._menu[d] += q
