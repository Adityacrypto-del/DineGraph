"""The `db` fixture runs each API test on SQLite and, when a Postgres server is given, on Postgres.

    DINEGRAPH_TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres pytest

Each Postgres test gets its own fresh database, dropped afterwards.
"""

import os
import uuid
from dataclasses import dataclass

import pytest

POSTGRES_URL = os.environ.get("DINEGRAPH_TEST_DATABASE_URL")


@dataclass
class Database:
    kind: str      # "sqlite" or "postgresql"
    options: dict  # create_app arguments that point at this database


@pytest.fixture(params=["sqlite", "postgresql"])
def db(request, tmp_path):
    if request.param == "sqlite":
        yield Database("sqlite", {"db_path": str(tmp_path / "test.sqlite")})
        return
    if not POSTGRES_URL:
        pytest.skip("set DINEGRAPH_TEST_DATABASE_URL to run the Postgres tests")
    import psycopg

    name = f"dinegraph_test_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(POSTGRES_URL, autocommit=True) as admin:
        admin.execute(f"CREATE DATABASE {name}")
    try:
        yield Database("postgresql", {"database_url": POSTGRES_URL.rsplit("/", 1)[0] + "/" + name})
    finally:
        with psycopg.connect(POSTGRES_URL, autocommit=True) as admin:
            admin.execute(f"DROP DATABASE {name} WITH (FORCE)")
