"""
Pytest fixtures for OpTrade tests.

Provides:
  - File-based SQLite test database (avoids in-memory connection issues)
  - Sample option trade data
  - Test client for FastAPI
"""

import os
import tempfile
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine
from fastapi.testclient import TestClient

from app.database import get_session
from app.main import create_app


@pytest.fixture(name="engine")
def engine_fixture():
    """Create a test database engine (file-based SQLite for connection persistence)."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="optrade_test_")
    os.close(fd)

    engine = create_engine(
        f"sqlite:///{path}",
        echo=False,
    )
    SQLModel.metadata.create_all(engine)

    yield engine

    # Cleanup
    engine.dispose()
    try:
        Path(path).unlink()
    except OSError:
        pass


@pytest.fixture(name="session")
def session_fixture(engine):
    """Create a new database session."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(engine):
    """Create a FastAPI TestClient that uses the test database."""

    def override_get_session():
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(name="sample_trade_data")
def sample_trade_fixture() -> dict:
    """Return a sample option trade dict for creating test records."""
    return {
        "trade_id": "TEST-001",
        "source_trade_id": "SRC-001",
        "option_type": "Plain Vanilla",
        "trade_type": "CALL",
        "direction": "买入",
        "strike": 7.1200,
        "ccy_pair": "USD/CNY",
        "notional1": 10000000.0,
        "notional2": 71200000.0,
        "premium_type": "Pips",
        "premium_rate": 15.0,
        "premium_amount": 15000.0,
        "premium_currency": "CNY",
        "spot_rate": 7.1150,
        "volatility": 0.0125,
        "counterparty_name": "示例银行A(SAMPLEA)",
        "venue": "CFETS",
        "exercise_status": "未行权",
        "delivery_status": "未交割",
        "tenor": "BROKEN",
        "timezone": "Beijing",
        "option_category": "fx_vanilla",
    }
