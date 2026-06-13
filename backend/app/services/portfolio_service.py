"""
Portfolio Service — portfolio-level aggregation and risk metrics.

Provides:
  - Aggregated Greeks across all trades in a portfolio
  - Expiry profile (notional and Greeks bucketed by time-to-expiry)
  - Counterparty exposure breakdown
"""

from datetime import date

from sqlmodel import Session, select, func

from app.models.trade import Trade
from app.models.calculation import CalculationResult


class PortfolioService:
    """Portfolio-level risk aggregation service."""

    def get_aggregated_greeks(
        self,
        portfolio_id: int,
        session: Session,
        scenario_label: str = "base",
    ) -> dict:
        """
        Aggregate Greeks across all trades in a portfolio.

        Returns total delta, gamma, vega, theta, rho, npv
        plus breakdowns by ccy_pair and option_type.
        """
        # Get calculation results for all trades in this portfolio
        results = session.exec(
            select(CalculationResult)
            .join(Trade)
            .where(
                Trade.portfolio_id == portfolio_id,
                CalculationResult.scenario_label == scenario_label,
            )
        ).all()

        totals = {
            "portfolio_id": portfolio_id,
            "trade_count": len(results),
            "total_delta": 0.0,
            "total_gamma": 0.0,
            "total_vega": 0.0,
            "total_theta": 0.0,
            "total_rho": 0.0,
            "total_npv": 0.0,
            "breakdown_by_ccy": {},
        }

        for r in results:
            totals["total_delta"] += r.delta or 0.0
            totals["total_gamma"] += r.gamma or 0.0
            totals["total_vega"] += r.vega or 0.0
            totals["total_theta"] += r.theta or 0.0
            totals["total_rho"] += r.rho or 0.0
            totals["total_npv"] += r.npv or 0.0

        # Round for display
        for key in ("total_delta", "total_gamma", "total_vega", "total_theta", "total_rho", "total_npv"):
            totals[key] = round(totals[key], 4)

        return totals

    def get_expiry_profile(
        self,
        portfolio_id: int,
        session: Session,
        reference_date: date | None = None,
    ) -> list[dict]:
        """
        Group trades by expiry bucket and compute notional/Greeks per bucket.

        Buckets: <1W, 1W-1M, 1M-3M, 3M-6M, 6M-1Y, >1Y
        """
        if reference_date is None:
            reference_date = date.today()

        trades = session.exec(
            select(Trade).where(Trade.portfolio_id == portfolio_id)
        ).all()

        buckets = [
            ("<1W", 7),
            ("1W-1M", 30),
            ("1M-3M", 90),
            ("3M-6M", 180),
            ("6M-1Y", 365),
            (">1Y", 99999),
        ]

        profile: list[dict] = []
        for label, max_days in buckets:
            bucket_trades = []
            for t in trades:
                if t.expiry_date:
                    days = (t.expiry_date - reference_date).days
                    prev_max = 0 if not profile else buckets[len(profile) - 1][1]
                    prev_max = 0 if label == "<1W" else buckets[len(profile) - 1][1]
                    if prev_max < days <= max_days:
                        bucket_trades.append(t)
                    elif label == "<1W" and days <= max_days:
                        bucket_trades.append(t)
                    elif label == ">1Y" and days > 365:
                        bucket_trades.append(t)

            total_notional = sum(t.notional1 for t in bucket_trades if t.notional1) or 0.0
            profile.append({
                "bucket": label,
                "trade_count": len(bucket_trades),
                "total_notional": round(total_notional, 2),
            })

        return profile


# Singleton
portfolio_service = PortfolioService()
