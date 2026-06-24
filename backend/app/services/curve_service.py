"""Curve Service — curve definition management and data access.

Coordinates database operations for the curve management module and
delegates crawling to the appropriate datasource service.
"""

from __future__ import annotations

import logging
from datetime import date, datetime

from fastapi import HTTPException
from sqlmodel import Session, col, func, select

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

        # Total count.
        total = session.exec(
            select(func.count()).select_from(base.subquery())
        ).one()

        # Paginated rows.
        offset = (params.page - 1) * params.page_size
        rows = session.exec(
            base.order_by(
                FxImpliedRate.curve_date.desc(),
                FxImpliedRate.foreign_currency,
                FxImpliedRate.tenor,
            )
            .offset(offset)
            .limit(params.page_size)
        ).all()

        return FxImpliedRateListResponse(
            data=[FxImpliedRateRead.model_validate(r) for r in rows],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

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
        """Parse an uploaded chinamoney XLSX and upsert its data."""
        from app.services.datasources.china_money_crawler import (
            ChinaMoneyCrawler,
        )

        records = ChinaMoneyCrawler.parse_xlsx(xlsx_bytes)
        added = ChinaMoneyCrawler._upsert_rates(session, records)
        return UploadResult(
            records_added=added,
            message=f"Processed {len(records)} rows from XLSX, {added} new records added.",
        )


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
