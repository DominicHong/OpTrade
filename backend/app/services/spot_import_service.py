"""
Spot import service — full pipeline from Excel file to SpotTrade database records.

Stages:
  1. Parse: Read Excel, map Chinese headers to SpotTrade model fields
  2. Validate: Check required fields, types, event_type constraint, derive ccy1/ccy2
  3. Execute: Find-or-create Portfolio/Counterparty, insert SpotTrades

Reuses shared infrastructure: excel_parser, date_utils, Portfolio/Counterparty models.
"""

from pathlib import Path

from sqlmodel import Session, select

from app.models import ImportLog
from app.utils.date_utils import (
    parse_chinese_date,
    parse_chinese_datetime,
    parse_float,
)
from app.utils.excel_parser import (
    ImportValidationResult,
    ParsedImportData,
    ValidationError,
    compute_file_hash,
    read_excel_file,
)
from app.utils.spot_column_mapping import (
    CSV_TO_SPOT_FIELD,
    SPOT_DATE_FIELDS,
    SPOT_DATETIME_FIELDS,
    SPOT_FLOAT_FIELDS,
    SPOT_REQUIRED_FIELDS,
)


class SpotImportService:
    """Orchestrates the FX spot trade Excel import pipeline."""

    def parse_file(self, file_path: str | Path) -> ParsedImportData:
        """Parse an Excel file (.xls/.xlsx) and return structured data."""
        file_path = Path(file_path)
        filename = file_path.name
        file_hash = compute_file_hash(file_path)

        suffix = file_path.suffix.lower()
        if suffix in (".xlsx", ".xls"):
            rows = read_excel_file(file_path)
        else:
            raise ValueError("即期导入仅支持 .xls/.xlsx 文件格式")

        # Determine effective column mapping (only headers present in the file)
        available_headers = set(rows[0].keys()) if rows else set()
        effective_mapping: dict[str, str] = {}
        for csv_header, field_name in CSV_TO_SPOT_FIELD.items():
            if csv_header in available_headers:
                effective_mapping[csv_header] = field_name

        return ParsedImportData(
            filename=filename,
            file_hash=file_hash,
            rows=rows,
            column_mapping=effective_mapping,
        )

    def validate(self, parsed: ParsedImportData) -> ImportValidationResult:
        """Validate parsed spot trade data: types, required fields, event_type."""
        result = ImportValidationResult()

        for idx, row in enumerate(parsed.rows):
            row_number = idx + 3  # Excel rows start at line 3 (row 1=title, row 2=headers)
            mapped: dict = {}
            row_errors: list[ValidationError] = []

            # Map Chinese headers to model fields with type parsing
            for csv_header, raw_value in row.items():
                field_name = parsed.column_mapping.get(csv_header)
                if field_name is None:
                    continue  # Skip unmapped columns

                if field_name in SPOT_DATE_FIELDS:
                    parsed_value = parse_chinese_date(raw_value)
                elif field_name in SPOT_DATETIME_FIELDS:
                    parsed_value = parse_chinese_datetime(raw_value)
                elif field_name in SPOT_FLOAT_FIELDS:
                    parsed_value = parse_float(raw_value)
                else:
                    parsed_value = raw_value if raw_value else None

                mapped[field_name] = parsed_value

            # Validate event_type constraint: must be "正常" or "期权行权衍生"
            event_type = mapped.get("event_type")
            if event_type is not None and event_type not in ("正常", "期权行权衍生"):
                row_errors.append(
                    ValidationError(
                        row_number=row_number,
                        field="event_type",
                        message=f"交易事件类型必须为'正常'或'期权行权衍生'，实际值: '{event_type}'",
                        value=str(event_type),
                    )
                )

            # Check required fields
            for required_field in SPOT_REQUIRED_FIELDS:
                val = mapped.get(required_field)
                if val is None or (isinstance(val, str) and val == ""):
                    row_errors.append(
                        ValidationError(
                            row_number=row_number,
                            field=required_field,
                            message=f"必填字段 '{required_field}' 不能为空",
                            value="",
                        )
                    )

            # Derive ccy1 and ccy2 from ccy_pair (e.g. "USD/CNY" → ccy1="USD", ccy2="CNY")
            ccy_pair = mapped.get("ccy_pair")
            if ccy_pair and isinstance(ccy_pair, str):
                parts = ccy_pair.split("/")
                if len(parts) == 2:
                    mapped["ccy1"] = parts[0].strip()
                    mapped["ccy2"] = parts[1].strip()

            # Derive direction from amount signs if not explicitly set
            if not mapped.get("direction"):
                ccy1_amount = mapped.get("ccy1_amount")
                if ccy1_amount is not None and isinstance(ccy1_amount, (int, float)):
                    if ccy1_amount > 0:
                        mapped["direction"] = "买入"
                    elif ccy1_amount < 0:
                        mapped["direction"] = "卖出"

            if row_errors:
                for err in row_errors:
                    result.errors.append(err)
            else:
                result.valid_rows.append(mapped)

        return result

    def execute_import(
        self,
        parsed: ParsedImportData,
        validated: ImportValidationResult,
        import_log: ImportLog,
        session: Session,
    ) -> ImportLog:
        """
        Persist validated rows to the database.
        Creates Portfolio and Counterparty records as needed.
        Checks for duplicate trade_id within spot_trades.
        """
        from app.models import Counterparty, Portfolio, SpotTrade

        imported = 0
        skipped = 0

        for row_data in validated.valid_rows:
            try:
                # Find or create Portfolio
                portfolio_name = row_data.get("portfolio_name")
                portfolio: Portfolio | None = None
                if portfolio_name:
                    portfolio = session.exec(
                        select(Portfolio).where(Portfolio.name == portfolio_name)
                    ).first()
                    if not portfolio:
                        portfolio = Portfolio(name=portfolio_name)
                        session.add(portfolio)
                        session.flush()
                    row_data["portfolio_id"] = portfolio.id

                # Find or create Counterparty
                counterparty_name = row_data.get("counterparty_name")
                counterparty: Counterparty | None = None
                if counterparty_name:
                    counterparty = session.exec(
                        select(Counterparty).where(Counterparty.name == counterparty_name)
                    ).first()
                    if not counterparty:
                        counterparty = Counterparty(name=counterparty_name)
                        session.add(counterparty)
                        session.flush()
                    row_data["counterparty_id"] = counterparty.id

                # Check for duplicate trade_id
                trade_id_val = row_data.get("trade_id")
                if trade_id_val:
                    existing = session.exec(
                        select(SpotTrade).where(SpotTrade.trade_id == trade_id_val)
                    ).first()
                    if existing:
                        skipped += 1
                        continue

                # Create spot trade — only set attributes that exist on the model
                trade = SpotTrade()
                for field_name, value in row_data.items():
                    if hasattr(SpotTrade, field_name):
                        setattr(trade, field_name, value)

                session.add(trade)
                imported += 1

            except Exception:
                skipped += 1
                continue

        session.commit()

        import_log.imported_rows = imported
        import_log.skipped_rows = skipped
        import_log.error_rows = validated.error_count
        import_log.status = "success" if validated.error_count == 0 else "partial"
        import_log.import_type = "spot"
        session.add(import_log)
        session.commit()

        return import_log


# Singleton
spot_import_service = SpotImportService()
