"""
Market Data Service — manages market data snapshots for pricing.

Provides latest spot, volatility, and risk-free rates per currency pair.
These feed into the Greeks and Pricing services.
"""

from sqlmodel import Session, select

from app.models import MarketDataSnapshot


class MarketDataService:
    """Market data management and retrieval for pricing inputs."""

    def get_latest_for_ccy_pair(self, ccy_pair: str, session: Session) -> MarketDataSnapshot | None:
        """Get the most recent market data snapshot for a currency pair."""
        return session.exec(
            select(MarketDataSnapshot)
            .where(MarketDataSnapshot.ccy_pair == ccy_pair)
            .order_by(MarketDataSnapshot.snapshot_date.desc())
        ).first()

    def get_latest_spot(self, ccy_pair: str, session: Session) -> float | None:
        """Get the latest spot rate for a currency pair."""
        snapshot = self.get_latest_for_ccy_pair(ccy_pair, session)
        return snapshot.spot if snapshot else None

    def get_latest_vol(self, ccy_pair: str, session: Session) -> float | None:
        """Get the latest volatility for a currency pair."""
        snapshot = self.get_latest_for_ccy_pair(ccy_pair, session)
        return snapshot.volatility if snapshot else None

    def get_latest_rates(self, ccy_pair: str, session: Session) -> dict[str, float | None]:
        """Get latest spot, vol, and rates for a currency pair."""
        snapshot = self.get_latest_for_ccy_pair(ccy_pair, session)
        if snapshot:
            return {
                "spot": snapshot.spot,
                "volatility": snapshot.volatility,
                "rf_rate_base": snapshot.rf_rate_base,
                "rf_rate_quote": snapshot.rf_rate_quote,
            }
        return {"spot": None, "volatility": None, "rf_rate_base": None, "rf_rate_quote": None}


# Singleton
market_data_service = MarketDataService()
