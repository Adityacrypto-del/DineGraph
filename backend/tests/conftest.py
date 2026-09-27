"""The `db` fixture gives each API test its own fresh Postgres database, dropped afterwards.

By default the tests use the local server from the README's Docker command. Point them
elsewhere with DINEGRAPH_TEST_DATABASE_URL (any database on the server; it is only used
to create and drop the test databases):

    DINEGRAPH_TEST_DATABASE_URL=postgresql://user:pass@host:5432/postgres pytest
"""

import os
import uuid

import psycopg
import pytest

SERVER_URL = os.environ.get("DINEGRAPH_TEST_DATABASE_URL",
                            "postgresql://postgres:dinegraph@localhost:5432/postgres")


@pytest.fixture(scope="session")
def postgres_server():
    try:
        psycopg.connect(SERVER_URL, connect_timeout=3).close()
    except psycopg.OperationalError as exc:
        pytest.fail(f"Cannot reach Postgres at {SERVER_URL}. Start it (see README, Database) "
                    f"or set DINEGRAPH_TEST_DATABASE_URL.\n{exc}", pytrace=False)
    return SERVER_URL


@pytest.fixture
def db(postgres_server):
    """The URL of a new, empty database."""
    name = f"dinegraph_test_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(postgres_server, autocommit=True) as admin:
        admin.execute(f"CREATE DATABASE {name}")
    try:
        yield postgres_server.rsplit("/", 1)[0] + "/" + name
    finally:
        with psycopg.connect(postgres_server, autocommit=True) as admin:
            admin.execute(f"DROP DATABASE {name} WITH (FORCE)")
