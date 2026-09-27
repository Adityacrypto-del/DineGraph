"""Copy a DineGraph SQLite database into an empty Postgres database.

    python scripts/sqlite_to_postgres.py dinegraph.sqlite postgresql://user:pass@host:5432/dinegraph

Copies the menu with stock and prices, order records, order events and the saved
LangGraph sessions, so orders still in progress can carry on. The SQLite file is
only read, never changed. Stop the backend first so nothing is written mid-copy.
"""
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.checkpoint.sqlite import SqliteSaver  # noqa: E402
from sqlalchemy import func, insert, select  # noqa: E402

from dinegraph.api import postgres_checkpointer  # noqa: E402
from dinegraph.store import Store, make_engine, menu_items, order_events, orders  # noqa: E402


def copy_tables(source: Store, target: Store) -> None:
    with source.engine.connect() as src, target.engine.begin() as dst:
        for table in (menu_items, orders, order_events):
            rows = [dict(r._mapping) for r in src.execute(select(table))]
            if rows:
                dst.execute(insert(table), rows)
            print(f"  {table.name}: {len(rows)} rows")
        if dst.dialect.name == "postgresql":  # new events continue after the copied ids
            dst.exec_driver_sql("SELECT setval(pg_get_serial_sequence('order_events', 'id'), "
                                "COALESCE((SELECT MAX(id) FROM order_events), 0) + 1, false)")


def copy_sessions(sqlite_path: str, url: str) -> None:
    source = SqliteSaver(sqlite3.connect(sqlite_path))
    target = postgres_checkpointer(url)
    saved = list(source.list(None))
    saved.reverse()  # oldest first, so each checkpoint's parent is already there
    for item in saved:
        conf = item.parent_config or {"configurable": {
            "thread_id": item.config["configurable"]["thread_id"],
            "checkpoint_ns": item.config["configurable"].get("checkpoint_ns", "")}}
        target.put(conf, item.checkpoint, item.metadata, item.checkpoint["channel_versions"])
        by_task = defaultdict(list)
        for task_id, channel, value in item.pending_writes or []:
            by_task[task_id].append((channel, value))
        for task_id, writes in by_task.items():
            target.put_writes(item.config, writes, task_id)
    threads = {i.config["configurable"]["thread_id"] for i in saved}
    print(f"  sessions: {len(threads)} ({len(saved)} checkpoints)")


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    sqlite_path, url = sys.argv[1], sys.argv[2]
    if not Path(sqlite_path).exists():
        print(f"{sqlite_path} does not exist.")
        return 1
    source = Store(make_engine(f"sqlite:///{sqlite_path}"))  # also upgrades an old file's columns
    target = Store(make_engine(url), seed_menu={})  # creates the tables, loads no menu
    with target.engine.connect() as conn:
        if any(conn.execute(select(func.count()).select_from(t)).scalar()
               for t in (menu_items, orders, order_events)):
            print("The Postgres database already has DineGraph data. Use an empty database.")
            return 1
    print(f"Copying {sqlite_path} to Postgres:")
    copy_tables(source, target)
    copy_sessions(sqlite_path, url)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
