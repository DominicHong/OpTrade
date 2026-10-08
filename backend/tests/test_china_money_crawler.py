"""Tests for the chinamoney crawler date-range chunking.

The live site accepts at most one month per Excel export; longer missing
ranges must be split into multiple windows, otherwise the export only
triggers a "只提供一个月历史数据查询和下载" alert and never downloads.
"""

import asyncio
from datetime import date, timedelta

from sqlmodel import select

from app.models.curve import FxImpliedRate
from app.services.datasources.china_money_crawler import (
    _INITIAL_SEED_DAYS,
    _MAX_EXPORT_DAYS,
    ChinaMoneyCrawler,
    _split_into_export_chunks,
)


class TestSplitIntoExportChunks:
    def test_empty_input(self):
        assert _split_into_export_chunks([]) == []

    def test_single_chunk_when_within_limit(self):
        days = [date(2026, 1, 1) + timedelta(days=i) for i in range(_MAX_EXPORT_DAYS)]
        assert _split_into_export_chunks(days) == [
            (date(2026, 1, 1), date(2026, 1, 31)),
        ]

    def test_long_range_is_split_and_fully_covered(self):
        days = [date(2026, 1, 1) + timedelta(days=i) for i in range(91)]
        chunks = _split_into_export_chunks(days)

        assert chunks == [
            (date(2026, 1, 1), date(2026, 1, 31)),
            (date(2026, 2, 1), date(2026, 3, 3)),
            (date(2026, 3, 4), date(2026, 4, 1)),
        ]
        for date_from, date_to in chunks:
            assert (date_to - date_from).days + 1 <= _MAX_EXPORT_DAYS

        covered = sum((date_to - date_from).days + 1 for date_from, date_to in chunks)
        assert covered == len(days)


class TestCrawlAllMissing:
    def test_downloads_one_export_per_chunk_and_imports_all(self, session, monkeypatch):
        crawler = ChinaMoneyCrawler(headless=True)
        recorded_chunks: list[tuple[date, date]] = []

        async def fake_download(self, chunks):
            recorded_chunks.extend(chunks)
            return [
                f"{date_from.isoformat()}_{date_to.isoformat()}".encode()
                for date_from, date_to in chunks
            ]

        def fake_parse(xlsx_bytes: bytes) -> list[dict]:
            date_from, _ = xlsx_bytes.decode().split("_")
            return [
                {
                    "curve_date": date.fromisoformat(date_from),
                    "foreign_currency": "USD",
                    "tenor": "1M",
                    "foreign_implied_rate": 4.0,
                }
            ]

        monkeypatch.setattr(
            ChinaMoneyCrawler, "_download_chunks_via_browser", fake_download,
        )
        monkeypatch.setattr(
            ChinaMoneyCrawler, "parse_xlsx", staticmethod(fake_parse),
        )

        result = asyncio.run(crawler.crawl_all_missing(session))

        # Empty DB → seed the last _INITIAL_SEED_DAYS + today, split into chunks.
        expected_missing_days = _INITIAL_SEED_DAYS + 1
        assert result["status"] == "success"
        assert len(recorded_chunks) >= 2
        total_covered = sum(
            (date_to - date_from).days + 1 for date_from, date_to in recorded_chunks
        )
        assert total_covered == expected_missing_days
        for date_from, date_to in recorded_chunks:
            assert (date_to - date_from).days + 1 <= _MAX_EXPORT_DAYS

        stored = session.exec(select(FxImpliedRate)).all()
        assert len(stored) == len(recorded_chunks)
        assert result["records_added"] == len(recorded_chunks)

    def test_crawl_skipped_when_up_to_date(self, session, monkeypatch):
        crawler = ChinaMoneyCrawler(headless=True)
        session.add(
            FxImpliedRate(
                curve_date=date.today(),
                foreign_currency="USD",
                tenor="1M",
            )
        )
        session.commit()

        async def fail_if_called(self, chunks):  # pragma: no cover
            raise AssertionError("browser download must not run when up to date")

        monkeypatch.setattr(
            ChinaMoneyCrawler, "_download_chunks_via_browser", fail_if_called,
        )

        result = asyncio.run(crawler.crawl_all_missing(session))

        assert result["status"] == "success"
        assert result["records_added"] == 0
        assert result["dates_fetched"] == []
