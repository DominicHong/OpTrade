"""
Scenario Service — sensitivity analysis and scenario computation.

Computes:
  - Spot shift: P&L under parallel spot shifts (in basis points)
  - Vol shift: P&L under parallel volatility shifts
  - Time decay: Greeks and NPV at forward dates
  - Heatmap: 2D spot × vol grid of portfolio-level NPV changes
"""

from datetime import date, timedelta


class ScenarioService:
    """Scenario analysis engine. Delegates Greeks computation to GreeksService."""

    def __init__(self) -> None:
        from app.services.greeks_service import greeks_service

        self.greeks = greeks_service

    def spot_shift(
        self,
        option_type: str,
        direction: str,
        base_spot: float,
        strike: float,
        base_vol: float,
        time_to_expiry_years: float,
        rf_rate_base: float = 0.03,
        rf_rate_quote: float = 0.03,
        shifts_bps: list[float] | None = None,
    ) -> list[dict]:
        """
        Compute Greeks/NPV under parallel spot rate shifts.

        Args:
            shifts_bps: List of spot shifts in basis points (e.g., [-500, -200, 0, 200, 500])
                         where -500 means spot × (1 - 500/10000) = spot × 0.95
        """
        if shifts_bps is None:
            shifts_bps = [-500, -200, -100, 0, 100, 200, 500]

        results: list[dict] = []
        for shift_bp in shifts_bps:
            shifted_spot = base_spot * (1 + shift_bp / 10000.0)
            greeks = self.greeks.calculate_vanilla_greeks(
                option_type=option_type,
                direction=direction,
                spot=shifted_spot,
                strike=strike,
                volatility=base_vol,
                time_to_expiry_years=time_to_expiry_years,
                rf_rate_base=rf_rate_base,
                rf_rate_quote=rf_rate_quote,
            )
            results.append({
                "shift_bps": shift_bp,
                "shifted_spot": round(shifted_spot, 4),
                **greeks,
            })

        return results

    def vol_shift(
        self,
        option_type: str,
        direction: str,
        spot: float,
        strike: float,
        base_vol: float,
        time_to_expiry_years: float,
        rf_rate_base: float = 0.03,
        rf_rate_quote: float = 0.03,
        shifts_vol: list[float] | None = None,
    ) -> list[dict]:
        """
        Compute Greeks/NPV under parallel volatility shifts.

        Args:
            shifts_vol: Absolute vol shifts (e.g., [-0.05, -0.02, 0, 0.02, 0.05])
        """
        if shifts_vol is None:
            shifts_vol = [-0.05, -0.02, -0.01, 0, 0.01, 0.02, 0.05]

        results: list[dict] = []
        for shift in shifts_vol:
            shifted_vol = base_vol + shift
            if shifted_vol <= 0.001:  # vol must be positive
                shifted_vol = 0.001

            greeks = self.greeks.calculate_vanilla_greeks(
                option_type=option_type,
                direction=direction,
                spot=spot,
                strike=strike,
                volatility=shifted_vol,
                time_to_expiry_years=time_to_expiry_years,
                rf_rate_base=rf_rate_base,
                rf_rate_quote=rf_rate_quote,
            )
            results.append({
                "shift_vol": shift,
                "shifted_vol": round(shifted_vol, 4),
                **greeks,
            })

        return results

    def time_decay(
        self,
        option_type: str,
        direction: str,
        spot: float,
        strike: float,
        volatility: float,
        time_to_expiry_years: float,
        rf_rate_base: float = 0.03,
        rf_rate_quote: float = 0.03,
        days_forward: list[int] | None = None,
    ) -> list[dict]:
        """
        Compute Greeks/NPV at future dates (time decay profile).

        Args:
            days_forward: Days to step forward (e.g., [0, 7, 30, 60, 90])
        """
        if days_forward is None:
            days_forward = [0, 7, 30, 60, 90]

        results: list[dict] = []
        for days in days_forward:
            years_remaining = time_to_expiry_years - (days / 365.0)
            if years_remaining < 0:
                years_remaining = 0.0

            greeks = self.greeks.calculate_vanilla_greeks(
                option_type=option_type,
                direction=direction,
                spot=spot,
                strike=strike,
                volatility=volatility,
                time_to_expiry_years=years_remaining,
                rf_rate_base=rf_rate_base,
                rf_rate_quote=rf_rate_quote,
            )
            results.append({
                "days_forward": days,
                "years_remaining": round(years_remaining, 4),
                **greeks,
            })

        return results

    def heatmap(
        self,
        option_type: str,
        direction: str,
        base_spot: float,
        strike: float,
        base_vol: float,
        time_to_expiry_years: float,
        rf_rate_base: float = 0.03,
        rf_rate_quote: float = 0.03,
        spot_shifts: list[float] | None = None,
        vol_shifts: list[float] | None = None,
    ) -> dict:
        """
        Generate 2D spot × vol heatmap of NPV values.

        Returns:
            {
                "spot_shifts": [...],
                "vol_shifts": [...],
                "values": [[npv_00, npv_01, ...], ...],
                "base_greeks": {...}
            }
        """
        if spot_shifts is None:
            spot_shifts = [-500, -200, -100, 0, 100, 200, 500]
        if vol_shifts is None:
            vol_shifts = [-0.05, -0.02, -0.01, 0, 0.01, 0.02, 0.05]

        # Base Greeks at current market
        base_greeks = self.greeks.calculate_vanilla_greeks(
            option_type=option_type,
            direction=direction,
            spot=base_spot,
            strike=strike,
            volatility=base_vol,
            time_to_expiry_years=time_to_expiry_years,
            rf_rate_base=rf_rate_base,
            rf_rate_quote=rf_rate_quote,
        )

        values: list[list[float]] = []
        for vol_shift in vol_shifts:
            row: list[float] = []
            shifted_vol = max(base_vol + vol_shift, 0.001)
            for spot_shift in spot_shifts:
                shifted_spot = base_spot * (1 + spot_shift / 10000.0)
                greeks = self.greeks.calculate_vanilla_greeks(
                    option_type=option_type,
                    direction=direction,
                    spot=shifted_spot,
                    strike=strike,
                    volatility=shifted_vol,
                    time_to_expiry_years=time_to_expiry_years,
                    rf_rate_base=rf_rate_base,
                    rf_rate_quote=rf_rate_quote,
                )
                row.append(greeks.get("npv") or 0.0)
            values.append(row)

        return {
            "spot_shifts": spot_shifts,
            "vol_shifts": vol_shifts,
            "values": values,
            "base_greeks": base_greeks,
        }


# Singleton
scenario_service = ScenarioService()
