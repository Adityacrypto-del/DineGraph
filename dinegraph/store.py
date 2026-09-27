"""SQLite storage for the backend: the menu with stock and prices, and order records.

The LangGraph checkpointer keeps full session state in the same database file,
in its own tables. The orders table here is a flat summary that is easy to list
and report on.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone

from .menu import MENU, PRICES

SCHEMA = """
CREATE TABLE IF NOT EXISTS menu_items (
    dish      TEXT PRIMARY KEY,
    quantity  INTEGER NOT NULL CHECK (quantity >= 0),
    price     INTEGER NOT NULL CHECK (price >= 0)
);
CREATE TABLE IF NOT EXISTS orders (
    session_id      TEXT PRIMARY KEY,
    status          TEXT NOT NULL,
    final_result    TEXT NOT NULL,
    items           TEXT NOT NULL,        -- JSON list of order items
    bill_total      INTEGER NOT NULL,
    payment_method  TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    table_no        INTEGER,              -- table number, NULL for orders not from a table
    stage           TEXT NOT NULL DEFAULT ''  -- next graph node, '' once the session has ended
);
CREATE INDEX IF NOT EXISTS orders_updated ON orders (updated_at);
CREATE TABLE IF NOT EXISTS order_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    at          TEXT NOT NULL,
    step        TEXT NOT NULL,            -- the graph node that ran
    status      TEXT NOT NULL,            -- order status after that node
    detail      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS order_events_session ON order_events (session_id, id);
"""

# columns added after the first release, created on older databases at startup
MIGRATIONS = {
    "orders": {"table_no": "INTEGER", "stage": "TEXT NOT NULL DEFAULT ''"},
}

FINISHED = ("PAID", "FAILED", "CANCELLED")


def _now() -> str:
    # microseconds, so orders saved within the same second still sort newest first
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class Store:
    def __init__(self, conn: sqlite3.Connection, seed_menu: dict[str, int] | None = None,
                 seed_prices: dict[str, int] | None = None):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock, self.conn:
            self.conn.executescript(SCHEMA)
            for table, columns in MIGRATIONS.items():
                have = {r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})")}
                for name, decl in columns.items():
                    if name not in have:
                        self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
            empty = self.conn.execute("SELECT COUNT(*) FROM menu_items").fetchone()[0] == 0
            if empty:  # first run: load the default menu
                menu = MENU if seed_menu is None else seed_menu
                prices = PRICES if seed_prices is None else seed_prices
                self.conn.executemany(
                    "INSERT INTO menu_items (dish, quantity, price) VALUES (?, ?, ?)",
                    [(d, q, prices.get(d, 0)) for d, q in menu.items()],
                )

    # ------------------------------------------------------------ Inventory interface

    def menu(self) -> dict[str, int]:
        with self.lock:
            rows = self.conn.execute("SELECT dish, quantity FROM menu_items ORDER BY rowid")
            return {r["dish"]: r["quantity"] for r in rows}

    def prices(self) -> dict[str, int]:
        with self.lock:
            rows = self.conn.execute("SELECT dish, price FROM menu_items ORDER BY rowid")
            return {r["dish"]: r["price"] for r in rows}

    def reserve(self, items: dict[str, int]) -> bool:
        with self.lock, self.conn:  # one transaction: all dishes or none
            stock = self.menu()
            if any(stock.get(d, 0) < q for d, q in items.items()):
                return False
            self.conn.executemany(
                "UPDATE menu_items SET quantity = quantity - ? WHERE dish = ?",
                [(q, d) for d, q in items.items()],
            )
            return True

    def release(self, items: dict[str, int]) -> None:
        with self.lock, self.conn:
            self.conn.executemany(
                "UPDATE menu_items SET quantity = quantity + ? WHERE dish = ?",
                [(q, d) for d, q in items.items()],
            )

    # ------------------------------------------------------------ menu admin

    def menu_items(self) -> list[dict]:
        with self.lock:
            rows = self.conn.execute("SELECT dish, quantity, price FROM menu_items ORDER BY rowid")
            return [dict(r) for r in rows]

    def get_item(self, dish: str) -> dict | None:
        with self.lock:
            row = self.conn.execute(
                "SELECT dish, quantity, price FROM menu_items WHERE lower(dish) = lower(?)", (dish,)
            ).fetchone()
            return dict(row) if row else None

    def upsert_item(self, dish: str, quantity: int | None, price: int | None) -> dict:
        """Create a dish, or change its quantity and/or price. New dishes need both."""
        with self.lock, self.conn:
            current = self.get_item(dish)
            if current is None:
                if quantity is None or price is None:
                    raise ValueError("A new dish needs both quantity and price.")
                self.conn.execute("INSERT INTO menu_items (dish, quantity, price) VALUES (?, ?, ?)",
                                  (dish, quantity, price))
            else:
                dish = current["dish"]
                self.conn.execute(
                    "UPDATE menu_items SET quantity = ?, price = ? WHERE dish = ?",
                    (current["quantity"] if quantity is None else quantity,
                     current["price"] if price is None else price, dish),
                )
            return self.get_item(dish)

    def delete_item(self, dish: str) -> bool:
        with self.lock, self.conn:
            cur = self.conn.execute("DELETE FROM menu_items WHERE lower(dish) = lower(?)", (dish,))
            return cur.rowcount > 0

    # ------------------------------------------------------------ orders

    def save_order(self, session_id: str, state: dict, stage: str = "") -> None:
        """Upsert the order record. `stage` is the graph node that runs next ('' when finished)."""
        now = _now()
        with self.lock, self.conn:
            self.conn.execute(
                """INSERT INTO orders (session_id, status, final_result, items, bill_total,
                                       payment_method, created_at, updated_at, table_no, stage)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT (session_id) DO UPDATE SET
                     status = excluded.status, final_result = excluded.final_result,
                     items = excluded.items, bill_total = excluded.bill_total,
                     payment_method = excluded.payment_method, updated_at = excluded.updated_at,
                     table_no = excluded.table_no, stage = excluded.stage""",
                (session_id, state["status"], state["final_result"], json.dumps(state["order"]),
                 state["bill_total"], state["payment_method"], now, now, state.get("table"), stage),
            )

    def active_orders(self) -> list[dict]:
        """Orders still in progress, oldest first: what the kitchen screen shows."""
        marks = ", ".join("?" * len(FINISHED))
        with self.lock:
            rows = self.conn.execute(
                f"SELECT * FROM orders WHERE status NOT IN ({marks}) ORDER BY created_at, rowid", FINISHED)
            return [self._order(r) for r in rows]

    # ------------------------------------------------------------ order events

    def add_event(self, session_id: str, step: str, status: str, detail: str) -> None:
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT INTO order_events (session_id, at, step, status, detail) VALUES (?, ?, ?, ?, ?)",
                (session_id, _now(), step, status, detail),
            )

    def events(self, session_id: str) -> list[dict]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT at, step, status, detail FROM order_events WHERE session_id = ? ORDER BY id",
                (session_id,))
            return [dict(r) for r in rows]

    def list_orders(self, status: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
        sql = "SELECT * FROM orders"
        args: list = []
        if status:
            sql += " WHERE status = ?"
            args.append(status)
        sql += " ORDER BY updated_at DESC, rowid DESC LIMIT ? OFFSET ?"
        args += [limit, offset]
        with self.lock:
            return [self._order(r) for r in self.conn.execute(sql, args)]

    def get_order(self, session_id: str) -> dict | None:
        with self.lock:
            row = self.conn.execute("SELECT * FROM orders WHERE session_id = ?", (session_id,)).fetchone()
            return self._order(row) if row else None

    def stats(self) -> dict:
        with self.lock:
            by_status = {r["status"]: r["n"] for r in self.conn.execute(
                "SELECT status, COUNT(*) AS n FROM orders GROUP BY status")}
            revenue = self.conn.execute(
                "SELECT COALESCE(SUM(bill_total), 0) FROM orders WHERE status = 'PAID'").fetchone()[0]
            by_method = {r["payment_method"]: r["total"] for r in self.conn.execute(
                "SELECT payment_method, SUM(bill_total) AS total FROM orders "
                "WHERE status = 'PAID' GROUP BY payment_method")}
        return {
            "total_orders": sum(by_status.values()),
            "completed": by_status.get("PAID", 0),
            "failed": by_status.get("FAILED", 0),
            "cancelled": by_status.get("CANCELLED", 0),
            "in_progress": sum(n for s, n in by_status.items() if s not in FINISHED),
            "revenue": revenue,
            "revenue_by_method": by_method,
        }

    @staticmethod
    def _order(row: sqlite3.Row) -> dict:
        d = dict(row)
        d["items"] = json.loads(d["items"])
        d["table"] = d.pop("table_no")
        return d
