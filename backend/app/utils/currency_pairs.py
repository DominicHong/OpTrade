"""Canonical currency-pair constants shared across the backend."""

from __future__ import annotations

SUPPORTED_CCY_PAIRS: set[str] = {
    "USD/CNY", "EUR/CNY", "HKD/CNY", "GBP/CNY", "JPY/CNY",
    "USD/HKD", "USD/JPY", "EUR/USD", "GBP/USD",
}

CNY_QUOTED_PAIRS: set[str] = {
    "USD/CNY", "EUR/CNY", "HKD/CNY", "GBP/CNY", "JPY/CNY",
}
