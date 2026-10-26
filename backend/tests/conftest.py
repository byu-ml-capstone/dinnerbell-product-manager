"""Tests run against Postgres (TEST-1). Point DATABASE_URL at a throwaway database: every session drops and
rebuilds the schema with Alembic, and every test truncates all tables."""

import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://appuser:apppass@localhost:5432/appdb")
# CI never calls a real AI or GitHub API (TEST-4).
for key in (
    "OPENAI_API_KEY",
    "ANALYSIS_LLM_BASE_URL",
    "ANALYSIS_LLM_API_KEY",
    "ANALYSIS_LLM_MODEL",
    "REVIEW_LLM_BASE_URL",
    "REVIEW_LLM_API_KEY",
    "REVIEW_LLM_MODEL",
    "GITHUB_TOKEN",
):
    os.environ[key] = ""
os.environ["SEED_DEMO_DATA"] = "false"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import clock, github_status  # noqa: E402

from .helpers import PASSWORD, ok, register  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def database():
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_state():
    yield
    app.dependency_overrides.clear()
    github_status.clear_cache()
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def make_client():
    clients: list[TestClient] = []

    def factory() -> TestClient:
        client = TestClient(app)
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client.close()


@pytest.fixture
def client(make_client) -> TestClient:
    """A client logged in as alice."""
    logged_in = make_client()
    register(logged_in, "alice", "Alice Anders")
    return logged_in


@pytest.fixture
def other_client(make_client) -> TestClient:
    """A second user (bob) who isn't in alice's projects unless added."""
    logged_in = make_client()
    register(logged_in, "bob", "Bob Brown")
    return logged_in


@pytest.fixture
def freeze_clock(monkeypatch):
    """Call freeze_clock(datetime) to set what clock.now() returns."""
    state = {}
    monkeypatch.setattr(clock, "now", lambda: state["now"])

    def set_now(value):
        state["now"] = value

    return set_now


@pytest.fixture
def travel(freeze_clock, client):
    """Freeze the clock at a moment and log alice in again, since sessions expire after 14 days."""

    def go(moment):
        freeze_clock(moment)
        ok(client.post("/api/auth/login", json={"username": "alice", "password": PASSWORD}))

    return go
