"""Database storage for the backend: the menu with stock and prices, and order records.

Works on SQLite (the default, one local file) and Postgres (set DATABASE_URL).
The LangGraph checkpointer keeps full session state in the same database, in its
own tables. The orders table here is a flat summary that is easy to list and
report on.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import (CheckConstraint, Column, Engine, Integer, MetaData, String, Table, Text,
                        create_engine, event, func, inspect, select, text)
from sqlalchemy.dialects import postgresql, sqlite

from .menu import MENU, PRICES

metadata = MetaData()

menu_items = Table(
    "menu_items", metadata,
    Column("dish", String, primary_key=True),
    Column("quantity", Integer, CheckConstraint("quantity >= 0"), nullable=False),
    Column("price", Integer, CheckConstraint("price >= 0"), nullable=False),
    Column("position", Integer),  # menu order, since Postgres has no rowid
)

orders = Table(
    "orders", metadata,
    Column("session_id", String, primary_key=True),
    Column("status", String, nullable=False),
    Column("final_result", Text, nullable=False),
    Column("items", Text, nullable=False),  # JSON list of order items
    Column("bill_total", Integer, nullable=False),
    Column("payment_method", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False, index=True),
    Column("table_no", Integer),  # table number, NULL for orders not from a table
    Column("stage", String, nullable=False, server_default=""),  # next graph node, '' once ended
)

order_events = Table(
    "order_events", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("session_id", String, nullable=False, index=True),
    Column("at", String, nullable=False),
    Column("step", String, nullable=False),  # the graph node that ran
    Column("status", String, nullable=False),  # order status after that node
    Column("detail", Text, nullable=False),
)

# columns added after the first release, created on older databases at startup
MIGRATIONS = {
    "orders": {"table_no": "INTEGER", "stage": "TEXT NOT NULL DEFAULT ''"},
    "menu_items": {"position": "INTEGER"},
}

FINISHED = ("PAID", "FAILED", "CANCELLED")


def _now() -> str:
    # microseconds, so orders saved within the same second still sort newest first
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def sqlalchemy_url(url: str) -> str:
    """Use the psycopg 3 driver for Postgres URLs given in the usual postgres:// form."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def make_engine(url: str) -> Engine:
    """An engine for a SQLAlchemy URL, e.g. sqlite:///dinegraph.sqlite or postgresql://..."""
    url = sqlalchemy_url(url)
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30})

        @event.listens_for(engine, "connect")
        def _wal(conn, _record):
            conn.execute("PRAGMA journal_mode=WAL")  # readers don't block the writer

        return engine
    return create_engine(url, pool_pre_ping=True)


class Store:
    def __init__(self, engine: Engine, seed_menu: dict[str, int] | None = None,
                 seed_prices: dict[str, int] | None = None):
        self.engine = engine
        insert = postgresql.insert if engine.dialect.name == "postgresql" else sqlite.insert
        self._insert = insert
        metadata.create_all(engine)
        with engine.begin() as conn:
            existing = inspect(conn)
            for table, columns in MIGRATIONS.items():
                have = {c["name"] for c in existing.get_columns(table)}
                for name, decl in columns.items():
                    if name not in have:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {decl}"))
                        if (table, name) == ("menu_items", "position"):  # keep the old order
                            conn.execute(text("UPDATE menu_items SET position = rowid"))
            if conn.execute(select(func.count()).select_from(menu_items)).scalar() == 0:
                menu = MENU if seed_menu is None else seed_menu  # first run: load the default menu
                prices = PRICES if seed_prices is None else seed_prices
                if menu:
                    conn.execute(menu_items.insert(), [
                        {"dish": d, "quantity": q, "price": prices.get(d, 0), "position": i}
                        for i, (d, q) in enumerate(menu.items(), 1)])

    # ------------------------------------------------------------ Inventory interface

    def menu(self) -> dict[str, int]:
        return {r["dish"]: r["quantity"] for r in self.menu_items()}

    def prices(self) -> dict[str, int]:
        return {r["dish"]: r["price"] for r in self.menu_items()}

    def reserve(self, items: dict[str, int]) -> bool:
        """Take stock for every dish, or for none. Safe with several server processes."""
        with self.engine.connect() as conn:
            trans = conn.begin()
            for dish, qty in items.items():
                cur = conn.execute(
                    menu_items.update()
                    .where(menu_items.c.dish == dish, menu_items.c.quantity >= qty)
                    .values(quantity=menu_items.c.quantity - qty))
                if cur.rowcount != 1:
                    trans.rollback()
                    return False
            trans.commit()
            return True

    def release(self, items: dict[str, int]) -> None:
        with self.engine.begin() as conn:
            for dish, qty in items.items():
                conn.execute(menu_items.update().where(menu_items.c.dish == dish)
                             .values(quantity=menu_items.c.quantity + qty))

    # ------------------------------------------------------------ menu admin

    def menu_items(self) -> list[dict]:
        query = (select(menu_items.c.dish, menu_items.c.quantity, menu_items.c.price)
                 .order_by(menu_items.c.position, menu_items.c.dish))
        with self.engine.connect() as conn:
            return [dict(r._mapping) for r in conn.execute(query)]

    def get_item(self, dish: str, conn=None) -> dict | None:
        query = (select(menu_items.c.dish, menu_items.c.quantity, menu_items.c.price)
                 .where(func.lower(menu_items.c.dish) == dish.lower()))
        if conn is None:
            with self.engine.connect() as conn:
                row = conn.execute(query).first()
        else:
            row = conn.execute(query).first()
        return dict(row._mapping) if row else None

    def upsert_item(self, dish: str, quantity: int | None, price: int | None) -> dict:
        """Create a dish, or change its quantity and/or price. New dishes need both."""
        with self.engine.begin() as conn:
            current = self.get_item(dish, conn)
            if current is None:
                if quantity is None or price is None:
                    raise ValueError("A new dish needs both quantity and price.")
                last = conn.execute(select(func.coalesce(func.max(menu_items.c.position), 0))).scalar()
                conn.execute(menu_items.insert().values(dish=dish, quantity=quantity, price=price,
                                                        position=last + 1))
            else:
                dish = current["dish"]
                conn.execute(menu_items.update().where(menu_items.c.dish == dish).values(
                    quantity=current["quantity"] if quantity is None else quantity,
                    price=current["price"] if price is None else price))
            return self.get_item(dish, conn)

    def delete_item(self, dish: str) -> bool:
        with self.engine.begin() as conn:
            cur = conn.execute(menu_items.delete().where(func.lower(menu_items.c.dish) == dish.lower()))
            return cur.rowcount > 0

    # ------------------------------------------------------------ orders

    def save_order(self, session_id: str, state: dict, stage: str = "") -> None:
        """Upsert the order record. `stage` is the graph node that runs next ('' when finished)."""
        now = _now()
        values = {
            "session_id": session_id, "status": state["status"], "final_result": state["final_result"],
            "items": json.dumps(state["order"]), "bill_total": state["bill_total"],
            "payment_method": state["payment_method"], "created_at": now, "updated_at": now,
            "table_no": state.get("table"), "stage": stage,
        }
        query = self._insert(orders).values(**values)
        query = query.on_conflict_do_update(
            index_elements=[orders.c.session_id],
            set_={k: query.excluded[k] for k in values if k not in ("session_id", "created_at")})
        with self.engine.begin() as conn:
            conn.execute(query)

    def active_orders(self) -> list[dict]:
        """Orders still in progress, oldest first: what the kitchen screen shows."""
        query = (select(orders).where(orders.c.status.not_in(FINISHED))
                 .order_by(orders.c.created_at, orders.c.session_id))
        with self.engine.connect() as conn:
            return [self._order(r) for r in conn.execute(query)]

    # ------------------------------------------------------------ order events

    def add_event(self, session_id: str, step: str, status: str, detail: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(order_events.insert().values(session_id=session_id, at=_now(), step=step,
                                                      status=status, detail=detail))

    def events(self, session_id: str) -> list[dict]:
        c = order_events.c
        query = select(c.at, c.step, c.status, c.detail).where(c.session_id == session_id).order_by(c.id)
        with self.engine.connect() as conn:
            return [dict(r._mapping) for r in conn.execute(query)]

    def list_orders(self, status: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
        query = select(orders)
        if status:
            query = query.where(orders.c.status == status)
        query = (query.order_by(orders.c.updated_at.desc(), orders.c.session_id.desc())
                 .limit(limit).offset(offset))
        with self.engine.connect() as conn:
            return [self._order(r) for r in conn.execute(query)]

    def get_order(self, session_id: str) -> dict | None:
        with self.engine.connect() as conn:
            row = conn.execute(select(orders).where(orders.c.session_id == session_id)).first()
            return self._order(row) if row else None

    def stats(self) -> dict:
        paid = orders.c.status == "PAID"
        with self.engine.connect() as conn:
            by_status = dict(conn.execute(
                select(orders.c.status, func.count()).group_by(orders.c.status)).all())
            revenue = conn.execute(
                select(func.coalesce(func.sum(orders.c.bill_total), 0)).where(paid)).scalar()
            by_method = dict(conn.execute(
                select(orders.c.payment_method, func.sum(orders.c.bill_total))
                .where(paid).group_by(orders.c.payment_method)).all())
        return {
            "total_orders": sum(by_status.values()),
            "completed": by_status.get("PAID", 0),
            "failed": by_status.get("FAILED", 0),
            "cancelled": by_status.get("CANCELLED", 0),
            "in_progress": sum(n for s, n in by_status.items() if s not in FINISHED),
            "revenue": int(revenue),
            "revenue_by_method": {m: int(t) for m, t in by_method.items()},
        }

    @staticmethod
    def _order(row) -> dict:
        d = dict(row._mapping)
        d["items"] = json.loads(d["items"])
        d["table"] = d.pop("table_no")
        return d
