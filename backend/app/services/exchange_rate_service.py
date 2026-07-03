"""Exchange Rate Service — multi-source spot rate management for multi-currency P&L.

Sources:
  - ``fx_implied_curve``: derives 5 CNY-quoted pairs (USD/CNY, EUR/CNY,
    HKD/CNY, GBP/CNY, JPY/CNY) directly from the ``fx_implied_rates`` table.
  - ``cross_derived``: derives 4 cross pairs (USD/HKD, USD/JPY, EUR/USD,
    GBP/USD) by dividing two CNY-quoted rates.
  - ``manual`` / ``upload``: user-provided rows for any pair.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import date

from fastapi import HTTPException
from sqlalchemy import Select
from sqlmodel import Session, func, select

from app.models.curve import FxImpliedRate
from app.models.exchange_rate import ExchangeRate
from app.schemas.exchange_rate import (
    ExchangeRateCoverageSummary,
    ExchangeRateFilterParams,
    ExchangeRateImportResult,
    ExchangeRateListResponse,
    ExchangeRateManualCreate,
    ExchangeRateRead,
    ExchangeRateUploadResult,
)

logger = logging.getLogger("optrade.service.exchange_rate")


# 9 supported pairs (AUD/USD deferred — no AUD/CNY source available)
SUPPORTED_CCY_PAIRS: set[str] = {
    "USD/CNY", "EUR/CNY", "HKD/CNY", "GBP/CNY", "JPY/CNY",
    "USD/HKD", "USD/JPY", "EUR/USD", "GBP/USD",
}

# Direct CNY-quoted pairs → pulled straight from fx_implied_rates.spot_rate
_DIRECT_CNY_PAIRS: list[str] = ["USD/CNY", "EUR/CNY", "HKD/CNY", "GBP/CNY", "JPY/CNY"]

# Cross-derived pairs → (pair, numerator_pair, denominator_pair)
_CROSS_PAIR_FORMULAS: list[tuple[str, str, str]] = [
    ("USD/HKD", "USD/CNY", "HKD/CNY"),
    ("USD/JPY", "USD/CNY", "JPY/CNY"),
    ("EUR/USD", "EUR/CNY", "USD/CNY"),
    ("GBP/USD", "GBP/CNY", "USD/CNY"),
]


class ExchangeRateService:
    """Service for exchange rate management and lookup."""

    # ------------------------------------------------------------------
    # Query / list
    # ------------------------------------------------------------------

    def query_rates(
        self,
        session: Session,
        params: ExchangeRateFilterParams,
    ) -> ExchangeRateListResponse:
        """Paginated / filtered query of exchange rates."""
        base = _build_rate_query(params)

        total = session.exec(
            select(func.count()).select_from(base.subquery())
        ).one()

        offset = (params.page - 1) * params.page_size
        rows = session.exec(base.offset(offset).limit(params.page_size)).all()

        return ExchangeRateListResponse(
            data=[ExchangeRateRead.model_validate(r) for r in rows],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    def export_rates_csv(
        self,
        session: Session,
        params: ExchangeRateFilterParams,
    ) -> str:
        """Export all matching exchange rate rows as CSV text."""
        base = _build_rate_query(params)
        rows = session.exec(base).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["日期", "货币对", "汇率", "来源", "来源引用", "创建时间"])
        for r in rows:
            writer.writerow([
                r.rate_date,
                r.ccy_pair,
                r.rate,
                r.source,
                r.source_ref,
                r.created_at,
            ])
        return output.getvalue()

    def get_coverage(self, session: Session) -> ExchangeRateCoverageSummary:
        """Return data-coverage statistics for exchange rates."""
        total = session.exec(select(func.count(ExchangeRate.id))).one()
        if total == 0:
            return ExchangeRateCoverageSummary()

        date_from = session.exec(select(func.min(ExchangeRate.rate_date))).one()
        date_to = session.exec(select(func.max(ExchangeRate.rate_date))).one()
        ccy_pairs = session.exec(
            select(ExchangeRate.ccy_pair).distinct().order_by(ExchangeRate.ccy_pair)
        ).all()
        last_updated = session.exec(select(func.max(ExchangeRate.created_at))).one()

        return ExchangeRateCoverageSummary(
            total_records=total,
            date_from=date_from,
            date_to=date_to,
            ccy_pairs=list(ccy_pairs),
            last_updated=last_updated,
        )

    def get_ccy_pairs(self, session: Session) -> list[str]:
        """Return distinct currency pairs present in the data."""
        result = session.exec(
            select(ExchangeRate.ccy_pair).distinct().order_by(ExchangeRate.ccy_pair)
        ).all()
        return list(result)

    # ------------------------------------------------------------------
    # Lookup (used by portfolio_service for P&L conversion)
    # ------------------------------------------------------------------

    def get_rate(
        self,
        session: Session,
        ccy_pair: str,
        rate_date: date,
    ) -> float | None:
        """Return the spot rate for *ccy_pair* on (or nearest <=) *rate_date*.

        Falls back to cross-rate derivation from two CNY-quoted components
        when no direct row exists for the requested pair.  Returns ``None``
        if no rate can be resolved.
        """
        ccy_pair = ccy_pair.upper()

        # 1. Try direct lookup: most recent row on or before rate_date
        row = session.exec(
            select(ExchangeRate)
            .where(
                ExchangeRate.ccy_pair == ccy_pair,
                ExchangeRate.rate_date <= rate_date,
            )
            .order_by(ExchangeRate.rate_date.desc())
        ).first()
        if row is not None:
            return row.rate

        # 2. Fall back: future rate (rare, but useful when loading today's
        #    analysis before today's exchange_rate row is imported)
        row = session.exec(
            select(ExchangeRate)
            .where(ExchangeRate.ccy_pair == ccy_pair)
            .order_by(ExchangeRate.rate_date.asc())
        ).first()
        if row is not None:
            return row.rate

        # 3. Cross-rate derivation from CNY components (e.g. USD/HKD = USD/CNY ÷ HKD/CNY)
        for pair, num, den in _CROSS_PAIR_FORMULAS:
            if pair == ccy_pair:
                num_rate = self.get_rate(session, num, rate_date)
                den_rate = self.get_rate(session, den, rate_date)
                if num_rate is not None and den_rate is not None and den_rate != 0:
                    return num_rate / den_rate
                break

        # 4. Final fallback: derive from fx_implied_rates directly (so the
        #    system works even before the user imports ExchangeRate rows)
        return self._lookup_from_fx_implied(session, ccy_pair, rate_date)

    def get_rate_to_cny(
        self,
        session: Session,
        currency: str,
        rate_date: date,
    ) -> float | None:
        """Return the CNY value of 1 unit of *currency* on *rate_date*.

        - ``CNY`` → 1.0
        - ``USD`` → USD/CNY rate
        - For any other currency ``X``, looks up ``X/CNY``; if absent, tries
          the inverse ``CNY/X``, then falls back to a USD bridge.
        """
        currency = currency.upper()
        if currency == "CNY":
            return 1.0

        # Direct: X/CNY
        rate = self.get_rate(session, f"{currency}/CNY", rate_date)
        if rate is not None:
            return rate

        # Inverse: CNY/X exists → 1 / rate
        inv = self._lookup_raw(session, f"CNY/{currency}", rate_date)
        if inv is not None and inv != 0:
            return 1.0 / inv

        # Bridge via USD: X→USD→CNY
        x_to_usd = self.get_rate(session, f"{currency}/USD", rate_date)
        usd_to_cny = self.get_rate(session, "USD/CNY", rate_date)
        if x_to_usd is not None and usd_to_cny is not None:
            return x_to_usd * usd_to_cny

        # Inverse bridge: USD/X exists → 1 / (USD/X) × USD/CNY
        usd_to_x = self._lookup_raw(session, f"USD/{currency}", rate_date)
        if usd_to_x is not None and usd_to_x != 0 and usd_to_cny is not None:
            return usd_to_cny / usd_to_x

        return None

    def _lookup_raw(
        self,
        session: Session,
        ccy_pair: str,
        rate_date: date,
    ) -> float | None:
        """Direct table lookup only (no cross-rate derivation)."""
        row = session.exec(
            select(ExchangeRate)
            .where(
                ExchangeRate.ccy_pair == ccy_pair.upper(),
                ExchangeRate.rate_date <= rate_date,
            )
            .order_by(ExchangeRate.rate_date.desc())
        ).first()
        return row.rate if row is not None else None

    def _lookup_from_fx_implied(
        self,
        session: Session,
        ccy_pair: str,
        rate_date: date,
    ) -> float | None:
        """Fallback: resolve a rate directly from fx_implied_rates.spot_rate.

        Handles 5 direct CNY pairs and 4 cross-derived pairs by reading the
        FX implied rate curve.  Returns ``None`` when data is unavailable.
        """
        ccy_pair = ccy_pair.upper()

        # Direct CNY pair → look up foreign_currency spot
        if ccy_pair in _DIRECT_CNY_PAIRS:
            foreign_ccy = ccy_pair.split("/")[0]
            return self._fx_implied_spot(session, rate_date, foreign_ccy)

        # Cross pair → derive from two CNY-quoted spots
        for pair, num, den in _CROSS_PAIR_FORMULAS:
            if pair == ccy_pair:
                num_ccy = num.split("/")[0]
                den_ccy = den.split("/")[0]
                num_rate = self._fx_implied_spot(session, rate_date, num_ccy)
                den_rate = self._fx_implied_spot(session, rate_date, den_ccy)
                if num_rate is not None and den_rate is not None and den_rate != 0:
                    return num_rate / den_rate
                break

        return None

    @staticmethod
    def _fx_implied_spot(
        session: Session,
        target_date: date,
        foreign_currency: str,
    ) -> float | None:
        """Return the spot_rate from fx_implied_rates for the nearest date <= target."""
        # Prefer exact or <= target_date
        curve_date = session.exec(
            select(func.max(FxImpliedRate.curve_date)).where(
                FxImpliedRate.curve_date <= target_date,
                FxImpliedRate.foreign_currency == foreign_currency.upper(),
            )
        ).first()
        if curve_date is None:
            # Fallback: earliest available date for this currency
            curve_date = session.exec(
                select(func.min(FxImpliedRate.curve_date)).where(
                    FxImpliedRate.foreign_currency == foreign_currency.upper(),
                )
            ).first()
        if curve_date is None:
            return None

        row = session.exec(
            select(FxImpliedRate.spot_rate)
            .where(
                FxImpliedRate.curve_date == curve_date,
                FxImpliedRate.foreign_currency == foreign_currency.upper(),
            )
            .where(FxImpliedRate.spot_rate.is_not(None))
            .limit(1)
        ).first()
        return row

    # ------------------------------------------------------------------
    # Import: from FX implied rate curve
    # ------------------------------------------------------------------

    def import_from_fx_implied_curve(
        self,
        session: Session,
        rate_date: date,
    ) -> ExchangeRateImportResult:
        """Derive 9 exchange rates for *rate_date* from the FX implied rate curve.

        Pulls spot rates for USD/EUR/HKD/GBP/JPY against CNY from
        ``fx_implied_rates`` (using the nearest curve date <= *rate_date*),
        then derives the 4 cross pairs by division.

        Upserts: existing rows for ``(rate_date, ccy_pair)`` are updated.
        """
        direct_rates: dict[str, float] = {}
        for pair in _DIRECT_CNY_PAIRS:
            foreign_ccy = pair.split("/")[0]
            spot = self._fx_implied_spot(session, rate_date, foreign_ccy)
            if spot is None:
                logger.warning(
                    "import_from_fx_implied_curve: no spot for %s/CNY on %s",
                    foreign_ccy, rate_date,
                )
                continue
            direct_rates[pair] = spot

        if not direct_rates:
            return ExchangeRateImportResult(
                message=f"FX implied curve 中无 {rate_date} 当日或之前的数据，未导入任何汇率。",
            )

        added = 0
        updated = 0

        # 1. Direct CNY pairs
        for pair, rate in direct_rates.items():
            foreign_ccy = pair.split("/")[0]
            a, u = self._upsert(
                session, rate_date, pair, rate,
                source="fx_implied_curve",
                source_ref=f"fx_implied_rate:{foreign_ccy}@{rate_date}",
            )
            added += a
            updated += u

        # 2. Cross-derived pairs
        for pair, num, den in _CROSS_PAIR_FORMULAS:
            num_rate = direct_rates.get(num)
            den_rate = direct_rates.get(den)
            if num_rate is None or den_rate is None or den_rate == 0:
                continue
            cross_rate = num_rate / den_rate
            a, u = self._upsert(
                session, rate_date, pair, cross_rate,
                source="cross_derived",
                source_ref=f"{num} ÷ {den}",
            )
            added += a
            updated += u

        session.commit()
        return ExchangeRateImportResult(
            records_added=added,
            records_updated=updated,
            message=f"已导入 {added} 条新增 / 更新 {updated} 条汇率记录（基于 {rate_date}）。",
        )

    def import_many_dates_from_fx_implied(
        self,
        session: Session,
        dates: list[date],
    ) -> ExchangeRateImportResult:
        """Run :meth:`import_from_fx_implied_curve` for multiple dates.

        Useful for backfilling when the user wants every historical curve
        date to have a corresponding exchange_rate row.
        """
        total_added = 0
        total_updated = 0
        skipped = 0
        for d in dates:
            r = self.import_from_fx_implied_curve(session, d)
            total_added += r.records_added
            total_updated += r.records_updated
            if r.records_added == 0 and r.records_updated == 0:
                skipped += 1

        return ExchangeRateImportResult(
            records_added=total_added,
            records_updated=total_updated,
            skipped=skipped,
            message=(
                f"批量导入完成：新增 {total_added} 条 / 更新 {total_updated} 条 / "
                f"跳过 {skipped} 个日期。"
            ),
        )

    # ------------------------------------------------------------------
    # Manual entry & upload
    # ------------------------------------------------------------------

    def create_manual(
        self,
        session: Session,
        payload: ExchangeRateManualCreate,
    ) -> ExchangeRateRead:
        """Insert (or update) a single manually-entered exchange rate."""
        ccy_pair = payload.ccy_pair.upper()
        if ccy_pair not in SUPPORTED_CCY_PAIRS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported currency pair: {ccy_pair}. "
                       f"Supported: {sorted(SUPPORTED_CCY_PAIRS)}",
            )
        added, _ = self._upsert(
            session, payload.rate_date, ccy_pair, payload.rate,
            source=payload.source or "manual",
            source_ref=payload.source_ref,
        )
        session.commit()

        row = session.exec(
            select(ExchangeRate).where(
                ExchangeRate.rate_date == payload.rate_date,
                ExchangeRate.ccy_pair == ccy_pair,
            )
        ).first()
        return ExchangeRateRead.model_validate(row)

    def process_uploaded_csv(
        self,
        session: Session,
        csv_bytes: bytes,
    ) -> ExchangeRateUploadResult:
        """Parse an uploaded CSV file with columns: 日期, 货币对, 汇率 [, 来源].

        Skips rows whose ccy_pair is not in :data:`SUPPORTED_CCY_PAIRS`.
        Upserts each valid row.
        """
        try:
            text = csv_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = csv_bytes.decode("gbk", errors="replace")

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return ExchangeRateUploadResult(message="CSV 文件为空或格式不正确。")

        # Normalize header names
        header_map = {h.strip().lower(): h for h in reader.fieldnames}
        date_col = header_map.get("日期") or header_map.get("date") or header_map.get("rate_date")
        pair_col = header_map.get("货币对") or header_map.get("ccy_pair") or header_map.get("pair")
        rate_col = header_map.get("汇率") or header_map.get("rate")
        source_col = header_map.get("来源") or header_map.get("source")

        if not (date_col and pair_col and rate_col):
            return ExchangeRateUploadResult(
                message="CSV 缺少必要列：日期 / 货币对 / 汇率。",
            )

        added = 0
        updated = 0
        skipped = 0

        for row in reader:
            try:
                rate_date = date.fromisoformat(str(row[date_col]).strip())
                ccy_pair = str(row[pair_col]).strip().upper()
                rate = float(str(row[rate_col]).strip())
            except (ValueError, KeyError, TypeError):
                skipped += 1
                continue

            if ccy_pair not in SUPPORTED_CCY_PAIRS:
                skipped += 1
                continue

            source = "upload"
            if source_col and row.get(source_col):
                source = str(row[source_col]).strip()

            a, u = self._upsert(session, rate_date, ccy_pair, rate, source=source)
            added += a
            updated += u

        session.commit()
        return ExchangeRateUploadResult(
            records_added=added,
            records_updated=updated,
            skipped=skipped,
            message=f"导入完成：新增 {added} / 更新 {updated} / 跳过 {skipped} 行。",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _upsert(
        session: Session,
        rate_date: date,
        ccy_pair: str,
        rate: float,
        source: str,
        source_ref: str | None = None,
    ) -> tuple[int, int]:
        """Insert or update a single row.  Returns (added, updated) counts."""
        existing = session.exec(
            select(ExchangeRate).where(
                ExchangeRate.rate_date == rate_date,
                ExchangeRate.ccy_pair == ccy_pair,
            )
        ).first()

        if existing is not None:
            existing.rate = rate
            existing.source = source
            existing.source_ref = source_ref
            session.add(existing)
            return (0, 1)

        session.add(ExchangeRate(
            rate_date=rate_date,
            ccy_pair=ccy_pair,
            rate=rate,
            source=source,
            source_ref=source_ref,
        ))
        return (1, 0)


# ------------------------------------------------------------------
# Query builder (module-level for reuse)
# ------------------------------------------------------------------


def _build_rate_query(
    params: ExchangeRateFilterParams,
) -> Select[tuple[ExchangeRate, ...]]:
    """Build a filtered and sorted select statement for ExchangeRate."""
    base = select(ExchangeRate)

    conditions: list = []
    if params.date_from:
        conditions.append(ExchangeRate.rate_date >= params.date_from)
    if params.date_to:
        conditions.append(ExchangeRate.rate_date <= params.date_to)
    if params.ccy_pair:
        conditions.append(ExchangeRate.ccy_pair == params.ccy_pair.upper())
    if params.source:
        conditions.append(ExchangeRate.source == params.source)

    if conditions:
        base = base.where(*conditions)

    sort_column = _get_sort_column(params.sort_by)
    order = (
        sort_column.desc() if params.sort_order.lower() == "desc" else sort_column.asc()
    )
    # Secondary sort by ccy_pair for stable ordering on same date
    return base.order_by(order, ExchangeRate.ccy_pair.asc())


def _get_sort_column(sort_by: str):
    allowed = {
        "rate_date": ExchangeRate.rate_date,
        "ccy_pair": ExchangeRate.ccy_pair,
        "rate": ExchangeRate.rate,
        "source": ExchangeRate.source,
        "created_at": ExchangeRate.created_at,
    }
    return allowed.get(sort_by, ExchangeRate.rate_date)


# ------------------------------------------------------------------
# FastAPI dependency
# ------------------------------------------------------------------

_exchange_rate_service: ExchangeRateService | None = None


def get_exchange_rate_service() -> ExchangeRateService:
    """FastAPI dependency: provide a singleton ExchangeRateService."""
    global _exchange_rate_service
    if _exchange_rate_service is None:
        _exchange_rate_service = ExchangeRateService()
    return _exchange_rate_service
