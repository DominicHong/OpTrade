"""Factory functions for creating test Trade records."""

from datetime import date

from app.models import Trade


def create_sample_trade(**overrides) -> Trade:
    """Create a Trade instance with sensible defaults for testing."""
    defaults = {
        "trade_id": "TEST-001",
        "source_trade_id": "SRC-001",
        "option_type": "Plain Vanilla",
        "trade_type": "CALL",
        "direction": "买入",
        "strike": 7.1200,
        "ccy_pair": "USD/CNY",
        "notional1": 10000000.0,
        "notional2": 71200000.0,
        "trade_date": date(2026, 6, 8),
        "expiry_date": date(2026, 6, 16),
        "delivery_date": date(2026, 6, 16),
        "premium_amount": 15000.0,
        "premium_currency": "CNY",
        "spot_rate": 7.1150,
        "volatility": 0.0125,
        "counterparty_name": "示例银行A(SAMPLEA)",
        "venue": "CFETS",
        "exercise_status": "未行权",
        "delivery_status": "未交割",
    }
    defaults.update(overrides)
    return Trade(**defaults)
