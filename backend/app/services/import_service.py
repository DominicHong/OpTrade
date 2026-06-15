"""
Import service — full pipeline from Excel file to database records.

Stages:
  1. Parse: Read CSV/Excel, map Chinese headers to model fields
  2. Validate: Check required fields, types, business rules, duplicates
  3. Execute: Find-or-create Portfolio/Counterparty, bulk insert Trades
"""

from pathlib import Path

from sqlmodel import Session, select

from app.models.import_log import ImportLog
from app.utils.column_mapping import (
    BOOL_FIELDS,
    CSV_TO_TRADE_FIELD,
    DATE_FIELDS,
    DATETIME_FIELDS,
    FLOAT_FIELDS,
    REQUIRED_FIELDS,
)
from app.utils.date_utils import (
    parse_bool_chinese,
    parse_chinese_date,
    parse_chinese_datetime,
    parse_float,
)
from app.utils.excel_parser import (
    ImportValidationResult,
    ParsedImportData,
    ValidationError,
    compute_file_hash,
    read_csv_file,
    read_excel_file,
)


class ImportService:
    """Orchestrates the Excel import pipeline."""

    def parse_file(self, file_path: str | Path) -> ParsedImportData:
        """Parse a CSV or Excel file and return structured data."""
        file_path = Path(file_path)
        filename = file_path.name
        file_hash = compute_file_hash(file_path)

        suffix = file_path.suffix.lower()
        if suffix in (".xlsx", ".xls"):
            rows = read_excel_file(file_path)
        else:
            rows = read_csv_file(file_path)

        # Determine effective column mapping (only headers present in the file)
        available_headers = set(rows[0].keys()) if rows else set()
        effective_mapping: dict[str, str] = {}
        for csv_header, field_name in CSV_TO_TRADE_FIELD.items():
            if csv_header in available_headers:
                effective_mapping[csv_header] = field_name

        return ParsedImportData(
            filename=filename,
            file_hash=file_hash,
            rows=rows,
            column_mapping=effective_mapping,
        )

    def validate(self, parsed: ParsedImportData) -> ImportValidationResult:
        """Validate parsed data: types, required fields, business rules."""
        result = ImportValidationResult()

        for idx, row in enumerate(parsed.rows):
            row_number = idx + 3  # CSV rows start at line 3
            mapped: dict = {}
            row_errors: list[ValidationError] = []

            # Map CSV headers to field names
            for csv_header, raw_value in row.items():
                field_name = parsed.column_mapping.get(csv_header)
                if field_name is None:
                    continue  # Skip unmapped columns

                # Parse value based on field type
                if field_name in DATE_FIELDS:
                    parsed_value = parse_chinese_date(raw_value)
                elif field_name in DATETIME_FIELDS:
                    parsed_value = parse_chinese_datetime(raw_value)
                elif field_name in FLOAT_FIELDS:
                    parsed_value = parse_float(raw_value)
                    # COMSTAR exports volatility in annualized percent (e.g. 1.43 = 1.43%)
                    if field_name == "volatility" and parsed_value is not None:
                        parsed_value = parsed_value / 100.0
                elif field_name in BOOL_FIELDS:
                    parsed_value = parse_bool_chinese(raw_value)
                    if parsed_value is None:
                        parsed_value = False
                else:
                    parsed_value = raw_value if raw_value else None

                mapped[field_name] = parsed_value

            # Check required fields
            for required_field in REQUIRED_FIELDS:
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
        """
        from app.models.counterparty import Counterparty
        from app.models.portfolio import Portfolio
        from app.models.trade import Trade

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
                        select(Trade).where(Trade.trade_id == trade_id_val)
                    ).first()
                    if existing:
                        skipped += 1
                        continue

                # Create trade
                trade = Trade()
                for field_name, value in row_data.items():
                    if hasattr(Trade, field_name):
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
        session.add(import_log)
        session.commit()

        return import_log


# Singleton
import_service = ImportService()
