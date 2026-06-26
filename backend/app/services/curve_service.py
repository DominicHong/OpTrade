"""Curve Service — curve definition management and data access.

Coordinates database operations for the curve management module and
delegates crawling to the appropriate datasource service.
"""

from __future__ import annotations

import csv
import logging
from datetime import date, datetime
from io import StringIO

from fastapi import HTTPException
from sqlalchemy import Select, case
from sqlmodel import Session, col, delete, func, select

from app.models.curve import CurveDefinition, FxImpliedRate
from app.schemas.curve import (
    CrawlResult,
    CurveCoverageSummary,
    CurveDefinitionRead,
    FxImpliedRateFilterParams,
    FxImpliedRateListResponse,
    FxImpliedRateRead,
    UploadResult,
)

logger = logging.getLogger("optrade.service.curve")


class CurveService:
    """Service for curve management operations.

    Use ``get_curve_service()`` for FastAPI dependency injection.
    """

    # ------------------------------------------------------------------
    # Curve definitions
    # ------------------------------------------------------------------

    def list_definitions(self, session: Session) -> list[CurveDefinitionRead]:
        """Return all active (and inactive) curve definitions."""
        rows = session.exec(
            select(CurveDefinition).order_by(CurveDefinition.name)
        ).all()
        return [CurveDefinitionRead.model_validate(r) for r in rows]

    def get_definition(
        self, session: Session, curve_type: str,
    ) -> CurveDefinition | None:
        """Return the definition row for a given *curve_type*, or None."""
        return session.exec(
            select(CurveDefinition).where(
                CurveDefinition.curve_type == curve_type,
            )
        ).first()

    # ------------------------------------------------------------------
    # FX Implied Rate — queries
    # ------------------------------------------------------------------

    def query_fx_rates(
        self,
        session: Session,
        params: FxImpliedRateFilterParams,
    ) -> FxImpliedRateListResponse:
        """Paginated / filtered query of FX implied rate data."""
        base = _build_fx_rate_query(params)

        # Total count.
        total = session.exec(
            select(func.count()).select_from(base.subquery())
        ).one()

        # Paginated rows.
        offset = (params.page - 1) * params.page_size
        rows = session.exec(
            base.offset(offset).limit(params.page_size)
        ).all()

        return FxImpliedRateListResponse(
            data=[FxImpliedRateRead.model_validate(r) for r in rows],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    def export_fx_rates_csv(
        self,
        session: Session,
        params: FxImpliedRateFilterParams,
    ) -> str:
        """Export all matching FX implied rate rows as CSV text."""
        base = _build_fx_rate_query(params)
        rows = session.exec(base).all()

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "日期", "外币", "期限", "隐含利率(%)", "人民币利率(%)",
            "即期汇率", "掉期点(Pips)", "来源",
        ])
        for r in rows:
            writer.writerow([
                r.curve_date,
                r.foreign_currency,
                r.tenor,
                r.foreign_implied_rate,
                r.cny_risk_free_rate,
                r.spot_rate,
                r.swap_points,
                r.source,
            ])
        return output.getvalue()

    def get_coverage(self, session: Session) -> CurveCoverageSummary:
        """Return data-coverage statistics for the FX implied rate curve."""
        total = session.exec(
            select(func.count(FxImpliedRate.id))
        ).one()

        if total == 0:
            return CurveCoverageSummary()

        date_from: date | None = session.exec(
            select(func.min(FxImpliedRate.curve_date))
        ).one()
        date_to: date | None = session.exec(
            select(func.max(FxImpliedRate.curve_date))
        ).one()
        currency_count = session.exec(
            select(func.count(col(FxImpliedRate.foreign_currency).distinct()))
        ).one()
        currencies = session.exec(
            select(FxImpliedRate.foreign_currency).distinct().order_by(
                FxImpliedRate.foreign_currency,
            )
        ).all()
        tenors = session.exec(
            select(FxImpliedRate.tenor).distinct().order_by(
                FxImpliedRate.tenor,
            )
        ).all()
        sorted_tenors = _sort_tenors(list(tenors))
        last_updated: datetime | None = session.exec(
            select(func.max(FxImpliedRate.created_at))
        ).one()

        return CurveCoverageSummary(
            total_records=total,
            date_from=date_from,
            date_to=date_to,
            currency_count=currency_count,
            currencies=list(currencies),
            tenors=sorted_tenors,
            last_updated=last_updated,
        )

    def get_currencies(self, session: Session) -> list[str]:
        """Return distinct foreign currencies in the data set."""
        result = session.exec(
            select(FxImpliedRate.foreign_currency)
            .distinct()
            .order_by(FxImpliedRate.foreign_currency)
        ).all()
        return list(result)

    def get_tenors(self, session: Session) -> list[str]:
        """Return distinct tenors in the data set, sorted logically (1D→1W→...→3Y)."""
        result = session.exec(
            select(FxImpliedRate.tenor)
            .distinct()
            .order_by(FxImpliedRate.tenor)
        ).all()
        return _sort_tenors(list(result))

    # ------------------------------------------------------------------
    # Crawl trigger
    # ------------------------------------------------------------------

    async def trigger_crawl(self, session: Session) -> CrawlResult:
        """Launch a crawl for missing FX implied rate dates.

        Runs in a thread with its own event loop because uvicorn's
        SelectorEventLoop on Windows doesn't support asyncio subprocesses
        (needed by Playwright to launch the browser).  A fresh DB session
        is created inside the thread (the caller's session is not
        thread-safe).
        """
        import asyncio
        import concurrent.futures

        def _run_in_thread() -> dict:
            from app.database import Session as NewSession, engine as db_engine

            async def _crawl() -> dict:
                from app.services.datasources.china_money_crawler import (
                    ChinaMoneyCrawler,
                )
                crawler = ChinaMoneyCrawler(headless=True)
                with NewSession(db_engine) as s:
                    return await crawler.crawl_all_missing(s)

            return asyncio.run(_crawl())

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result_dict = await asyncio.get_event_loop().run_in_executor(
                pool, _run_in_thread,
            )
        return CrawlResult(**result_dict)

    # ------------------------------------------------------------------
    # Manual XLSX upload (fallback when crawl is unavailable)
    # ------------------------------------------------------------------

    def process_uploaded_xlsx(
        self, session: Session, xlsx_bytes: bytes,
    ) -> UploadResult:
        """Parse an uploaded chinamoney XLSX, clear existing data, then load.

        The upload replaces all existing FX implied rate rows with the
        parsed content of the supplied file.
        """
        from app.services.datasources.china_money_crawler import (
            ChinaMoneyCrawler,
        )

        records = ChinaMoneyCrawler.parse_xlsx(xlsx_bytes)
        added = self._replace_all_rates(session, records)
        return UploadResult(
            records_added=added,
            message=f"已清空原有数据并导入 {added} 条记录（共解析 {len(records)} 行）。",
        )

    @staticmethod
    def _replace_all_rates(session: Session, records: list[dict]) -> int:
        """Delete all existing FX implied rate rows and insert the new records."""
        # Clear existing data
        session.exec(delete(FxImpliedRate))
        session.commit()

        added = 0
        for rec in records:
            if not all(
                k in rec for k in ("curve_date", "foreign_currency", "tenor")
            ):
                continue
            rate = FxImpliedRate(
                curve_date=rec["curve_date"],
                foreign_currency=rec["foreign_currency"],
                tenor=rec["tenor"],
                foreign_implied_rate=rec.get("foreign_implied_rate"),
                cny_risk_free_rate=rec.get("cny_risk_free_rate"),
                spot_rate=rec.get("spot_rate"),
                swap_points=rec.get("swap_points"),
                source="chinamoney",
            )
            session.add(rate)
            added += 1

        if added:
            session.commit()
        return added


    # ------------------------------------------------------------------
    # Curve parameter resolution for Greeks
    # ------------------------------------------------------------------

    def _find_nearest_curve_date(
        self,
        session: Session,
        valuation_date: date,
        foreign_currency: str,
    ) -> date | None:
        """Find the nearest ``curve_date <= valuation_date`` for a currency.

        Falls back to the earliest available date if no data exists on or
        before *valuation_date*.  Returns ``None`` when no data exists for
        that currency at all.
        """
        # Prefer exact or <= valuation_date
        row = session.exec(
            select(func.max(FxImpliedRate.curve_date)).where(
                FxImpliedRate.curve_date <= valuation_date,
                FxImpliedRate.foreign_currency == foreign_currency,
            )
        ).first()
        if row is not None:
            return row

        # Fallback: earliest date for this currency
        row = session.exec(
            select(func.min(FxImpliedRate.curve_date)).where(
                FxImpliedRate.foreign_currency == foreign_currency,
            )
        ).first()
        return row

    def _get_curve_data_for_date(
        self,
        session: Session,
        curve_date: date,
        foreign_currency: str,
    ) -> tuple[list[str], list[float | None], list[float | None], float | None]:
        """Return curve data for a specific date and currency.

        Returns:
            ``(tenors, foreign_implied_rates, cny_risk_free_rates, spot_rate)``.
            Tenors are sorted by year-fraction ascending.  *spot_rate* is
            taken from the first row (should be identical across tenors for
            a given date).
        """
        rows = session.exec(
            select(FxImpliedRate).where(
                FxImpliedRate.curve_date == curve_date,
                FxImpliedRate.foreign_currency == foreign_currency,
            )
        ).all()

        if not rows:
            return ([], [], [], None)

        # Sort by year-fraction
        from app.utils.curve_helpers import tenor_to_years
        rows_sorted = sorted(rows, key=lambda r: tenor_to_years(r.tenor))

        tenors = [r.tenor for r in rows_sorted]
        foreign_rates = [r.foreign_implied_rate for r in rows_sorted]
        cny_rates = [r.cny_risk_free_rate for r in rows_sorted]
        # Spot rate should be the same for all tenors on a given date
        spot = rows[0].spot_rate

        return (tenors, foreign_rates, cny_rates, spot)

    def _get_historical_spot_rates(
        self,
        session: Session,
        valuation_date: date,
        foreign_currency: str,
        lookback: int = 500,
    ) -> list[float]:
        """Return historical spot rates in chronological order (oldest first).

        Used for calculating historical volatility.  Selects distinct
        ``(curve_date, spot_rate)`` pairs for the given currency, up to
        *lookback* days before *valuation_date*.
        """
        rows = session.exec(
            select(
                FxImpliedRate.curve_date,
                FxImpliedRate.spot_rate,
            )
            .where(
                FxImpliedRate.curve_date <= valuation_date,
                FxImpliedRate.foreign_currency == foreign_currency,
            )
            .distinct()
            .order_by(FxImpliedRate.curve_date.asc())
        ).all()

        # Take one spot rate per date (use the first non-None value)
        seen: set[date] = set()
        rates: list[float] = []
        for curve_date, spot in rows:
            if curve_date in seen or spot is None:
                continue
            seen.add(curve_date)
            rates.append(spot)

        # Return last *lookback* entries (most recent data)
        if len(rates) > lookback:
            rates = rates[-lookback:]

        return rates

    def resolve_valuation_params(
        self,
        session: Session,
        valuation_date: date,
        foreign_currency: str,
        remaining_maturity_years: float,
    ) -> dict | None:
        """Resolve all valuation parameters from curve data.

        Args:
            session: Database session.
            valuation_date: Target valuation date.
            foreign_currency: Foreign currency code (e.g. ``"USD"``).
            remaining_maturity_years: Option remaining maturity in years,
                used for rate interpolation.

        Returns:
            ``{"rf_rate_base", "rf_rate_quote", "spot_rate", "volatility",
            "curve_date"}`` or ``None`` if no curve data is available.
            All rate values are **decimals** (divided by 100 from the stored
            percentage values).
        """
        from app.utils.curve_helpers import (
            interpolate_rate,
            calc_historical_volatility,
        )

        curve_date = self._find_nearest_curve_date(
            session, valuation_date, foreign_currency
        )
        if curve_date is None:
            return None

        tenors, foreign_rates, cny_rates, spot = self._get_curve_data_for_date(
            session, curve_date, foreign_currency
        )
        if not tenors:
            return None

        # Interpolate rates at remaining_maturity_years.
        # Stored as percentages (e.g. 4.5 = 4.5 %) → divide by 100 for decimal.
        raw_foreign = interpolate_rate(remaining_maturity_years, tenors, foreign_rates)
        raw_cny = interpolate_rate(remaining_maturity_years, tenors, cny_rates)

        rf_rate_base = raw_foreign / 100.0 if raw_foreign is not None else None
        rf_rate_quote = raw_cny / 100.0 if raw_cny is not None else None

        # Historical volatility
        spot_history = self._get_historical_spot_rates(
            session, valuation_date, foreign_currency
        )
        volatility = calc_historical_volatility(spot_history)

        return {
            "rf_rate_base": rf_rate_base,
            "rf_rate_quote": rf_rate_quote,
            "spot_rate": spot,
            "volatility": volatility,
            "curve_date": curve_date,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

# Mapping from tenor string → sortable tuple of (unit_rank, count).
_TENOR_ORDER: dict[str, tuple[int, int]] = {
    "D": (0, 1),
    "W": (1, 7),
    "M": (2, 30),
    "Y": (3, 365),
}


def _tenor_sort_key(t: str) -> tuple[int, float]:
    """Return a sortable key for a tenor label (e.g. ``1D`` → (0, 1))."""
    if len(t) >= 2 and t[-1] in _TENOR_ORDER:
        num_str = t[:-1]
        unit = t[-1]
        rank, multiplier = _TENOR_ORDER[unit]
        try:
            value = float(num_str) * multiplier
        except ValueError:
            value = 9999.0
        return (rank, value)
    return (99, 9999.0)


def _sort_tenors(tenors: list[str]) -> list[str]:
    """Sort tenor labels in logical duration order."""
    return sorted(tenors, key=_tenor_sort_key)


def _build_fx_rate_query(
    params: FxImpliedRateFilterParams,
) -> Select[tuple[FxImpliedRate, ...]]:
    """Build a filtered and sorted select statement for FxImpliedRate."""
    base = select(FxImpliedRate)

    conditions: list = []
    if params.date_from:
        conditions.append(FxImpliedRate.curve_date >= params.date_from)
    if params.date_to:
        conditions.append(FxImpliedRate.curve_date <= params.date_to)
    if params.currency:
        conditions.append(
            FxImpliedRate.foreign_currency == params.currency.upper(),
        )
    if params.tenor:
        conditions.append(FxImpliedRate.tenor == params.tenor)

    if conditions:
        base = base.where(*conditions)

    sort_column = _get_sort_column(params.sort_by)
    primary_order = (
        sort_column.desc()
        if params.sort_order.lower() == "desc"
        else sort_column.asc()
    )
    order_terms: list = [primary_order]
    if params.sort_by == "curve_date":
        order_terms.extend([_usd_first_order(), FxImpliedRate.tenor])

    return base.order_by(*order_terms)


def _get_sort_column(sort_by: str):
    """Return the FxImpliedRate column to order by, defaulting to curve_date."""
    allowed = {
        "curve_date": FxImpliedRate.curve_date,
        "foreign_currency": FxImpliedRate.foreign_currency,
        "tenor": FxImpliedRate.tenor,
        "foreign_implied_rate": FxImpliedRate.foreign_implied_rate,
        "cny_risk_free_rate": FxImpliedRate.cny_risk_free_rate,
        "spot_rate": FxImpliedRate.spot_rate,
        "swap_points": FxImpliedRate.swap_points,
    }
    return allowed.get(sort_by, FxImpliedRate.curve_date)


def _usd_first_order():
    """Return an ordering clause that places USD before other currencies."""
    return case((FxImpliedRate.foreign_currency == "USD", 0), else_=1).asc()


# ------------------------------------------------------------------
# FastAPI dependency
# ------------------------------------------------------------------

_curve_service: CurveService | None = None


def get_curve_service() -> CurveService:
    """FastAPI dependency: provide a singleton CurveService."""
    global _curve_service
    if _curve_service is None:
        _curve_service = CurveService()
    return _curve_service
