"""
Curve helper utilities — tenor conversion, rate interpolation, historical volatility.

Pure functions with no database or service dependencies.  Designed to be
unit-testable without any fixtures.
"""

import math

from app.utils.ccy_utils import split_ccy_pair


# ---------------------------------------------------------------------------
# Tenor → year-fraction conversion
# ---------------------------------------------------------------------------

_TENOR_UNIT_YEARS: dict[str, float] = {
    "D": 1.0 / 365,
    "W": 7.0 / 365,
    "M": 30.0 / 365,
    "Y": 1.0,
}


def tenor_to_years(tenor: str) -> float:
    """Convert a tenor label (e.g. ``"1M"``, ``"3Y"``) to a year fraction.

    Uses simple conventions: D→1/365, W→7/365, M→30/365, Y→1.

    Raises:
        ValueError: if the tenor has an unknown unit or unparseable prefix.
    """
    tenor = tenor.strip()
    if len(tenor) < 2:
        raise ValueError(f"Invalid tenor format: {tenor!r}")
    unit = tenor[-1].upper()
    if unit not in _TENOR_UNIT_YEARS:
        raise ValueError(f"Unknown tenor unit {unit!r} in {tenor!r}")
    try:
        count = float(tenor[:-1])
    except ValueError:
        raise ValueError(f"Invalid tenor format: {tenor!r}") from None
    return count * _TENOR_UNIT_YEARS[unit]


# ---------------------------------------------------------------------------
# Rate interpolation
# ---------------------------------------------------------------------------


def interpolate_rate(
    remaining_years: float,
    tenors: list[str],
    rates: list[float | None],
) -> float | None:
    """Linearly interpolate a rate at *remaining_years* between tenor points.

    Tenors and rates are paired by index.  ``None`` entries in *rates* are
    skipped.  Flat extrapolation is used beyond the first/last valid tenor.

    Returns:
        Interpolated rate, or ``None`` if there are zero valid data points.
    """
    # Build sorted list of (year_fraction, rate) for valid points
    points: list[tuple[float, float]] = []
    for t, r in zip(tenors, rates):
        if r is None:
            continue
        try:
            yf = tenor_to_years(t)
        except ValueError:
            continue
        points.append((yf, r))

    if not points:
        return None

    points.sort(key=lambda p: p[0])

    if len(points) == 1:
        return points[0][1]

    # Below first point → flat extrapolation
    if remaining_years <= points[0][0]:
        return points[0][1]

    # Above last point → flat extrapolation
    if remaining_years >= points[-1][0]:
        return points[-1][1]

    # Find bracket and interpolate
    for i in range(len(points) - 1):
        t0, r0 = points[i]
        t1, r1 = points[i + 1]
        if t0 <= remaining_years <= t1:
            if t1 == t0:
                return (r0 + r1) / 2.0
            frac = (remaining_years - t0) / (t1 - t0)
            return r0 + frac * (r1 - r0)

    # Should never reach here, but be safe
    return None


# ---------------------------------------------------------------------------
# Historical volatility
# ---------------------------------------------------------------------------


def calc_historical_volatility(spot_rates: list[float]) -> float | None:
    """Compute annualised historical volatility from a time-series of spot rates.

    *spot_rates* must be in chronological order (oldest first).  Daily log
    returns are computed, then annualised with :math:`\\sigma_d \\times
    \\sqrt{252}`.

    Returns:
        Annualised volatility as a decimal (e.g. 0.12 for 12 %), or ``None``
        if fewer than 2 data points are available.
    """
    if len(spot_rates) < 2:
        return None

    log_returns: list[float] = []
    for i in range(1, len(spot_rates)):
        if spot_rates[i - 1] <= 0 or spot_rates[i] <= 0:
            continue
        log_returns.append(math.log(spot_rates[i] / spot_rates[i - 1]))

    if len(log_returns) < 2:
        return None

    mean = sum(log_returns) / len(log_returns)
    variance = sum((r - mean) ** 2 for r in log_returns) / (len(log_returns) - 1)
    daily_vol = math.sqrt(variance)
    annual_vol = daily_vol * math.sqrt(252)

    if math.isnan(annual_vol) or annual_vol <= 0:
        return None

    return annual_vol


# ---------------------------------------------------------------------------
# Currency extraction
# ---------------------------------------------------------------------------


def extract_foreign_currency(ccy_pair: str) -> str | None:
    """Extract the foreign (base) currency from a currency pair string.

    ``"USD/CNY"`` → ``"USD"``.  Returns ``None`` when the quote currency is
    **not** CNY, because the FX implied rate curve only covers CNY-quoted
    pairs (USD/CNY, EUR/CNY, GBP/CNY, JPY/CNY, HKD/CNY).

    Raises:
        ValueError: if *ccy_pair* is not in ``"XXX/YYY"`` format.
    """
    normalized = (ccy_pair or "").strip().upper()
    ccy1, ccy2 = split_ccy_pair(normalized)
    if ccy1 is None or ccy2 is None:
        raise ValueError(f"Invalid ccy_pair format: {normalized!r}")

    if ccy2 != "CNY":
        return None  # Curve only covers CNY-quoted pairs
    return ccy1
