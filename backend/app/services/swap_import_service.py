"""
Swap import service — full pipeline from Excel file to SwapTrade database records.

Stages:
  1. Parse: Read Excel, map Chinese headers to SwapTrade model fields
  2. Validate: Check required fields, types, derive ccy1/ccy2
  3. Execute: Find-or-create Portfolio/Counterparty, insert SwapTrades

Reuses shared infrastructure: excel_parser, date_utils, Portfolio/Counterparty models.
"""

from pathlib import Path

from sqlmodel import Session, select

from app.models import ImportLog
from app.utils.ccy_utils import split_ccy_pair
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
from app.utils.swap_column_mapping import (
    CSV_TO_SWAP_FIELD,
    SWAP_DATE_FIELDS,
    SWAP_DATETIME_FIELDS,
    SWAP_FLOAT_FIELDS,
    SWAP_REQUIRED_FIELDS,
    SWAP_SIGNATURE_HEADERS,
)


class SwapImportService:
    """Orchestrates the FX swap trade Excel import pipeline."""

    def parse_file(self, file_path: str | Path) -> ParsedImportData:
        """Parse an Excel file (.xls/.xlsx) and return structured data."""
        file_path = Path(file_path)
        filename = file_path.name
        file_hash = compute_file_hash(file_path)

        suffix = file_path.suffix.lower()
        if suffix in (".xlsx", ".xls"):
            rows = read_excel_file(file_path)
        else:
            raise ValueError("掉期导入仅支持 .xls/.xlsx 文件格式")

        # Determine effective column mapping (only headers present in the file)
        available_headers = set(rows[0].keys()) if rows else set()
        effective_mapping: dict[str, str] = {}
        for csv_header, field_name in CSV_TO_SWAP_FIELD.items():
            if csv_header in available_headers:
                effective_mapping[csv_header] = field_name

        # File type detection: reject non-swap files
        if available_headers:
            matched_signatures = [
                h for h in SWAP_SIGNATURE_HEADERS if h in available_headers
            ]
            if len(matched_signatures) == 0:
                raise ValueError(
                    "文件不含掉期交易特征字段（如近端成交价、远端成交价、近端起息日等），"
                    "可能上传了期权或即期流水文件。请选择对应的导入类型。"
                )

        return ParsedImportData(
            filename=filename,
            file_hash=file_hash,
            rows=rows,
            column_mapping=effective_mapping,
        )

    def validate(self, parsed: ParsedImportData) -> ImportValidationResult:
        """Validate parsed swap trade data: types, required fields."""
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

                if field_name in SWAP_DATE_FIELDS:
                    parsed_value = parse_chinese_date(raw_value)
                elif field_name in SWAP_DATETIME_FIELDS:
                    parsed_value = parse_chinese_datetime(raw_value)
                elif field_name in SWAP_FLOAT_FIELDS:
                    parsed_value = parse_float(raw_value)
                else:
                    parsed_value = raw_value if raw_value else None

                mapped[field_name] = parsed_value

            # Check required fields
            for required_field in SWAP_REQUIRED_FIELDS:
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

            # Derive ccy1 and ccy2 from ccy_pair (e.g. "USD/JPY" → ccy1="USD", ccy2="JPY")
            ccy_pair = mapped.get("ccy_pair")
            if ccy_pair and isinstance(ccy_pair, str):
                ccy1, ccy2 = split_ccy_pair(ccy_pair)
                if ccy1 and ccy2:
                    mapped["ccy1"] = ccy1
                    mapped["ccy2"] = ccy2

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
        Checks for duplicate trade_id within swap_trades.
        """
        from app.models import Counterparty, Portfolio, SwapTrade

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
                        select(SwapTrade).where(SwapTrade.trade_id == trade_id_val)
                    ).first()
                    if existing:
                        skipped += 1
                        continue

                # Create swap trade — only set attributes that exist on the model
                trade = SwapTrade()
                for field_name, value in row_data.items():
                    if hasattr(SwapTrade, field_name):
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
        import_log.import_type = "swap"
        session.add(import_log)
        session.commit()

        return import_log


# Singleton
swap_import_service = SwapImportService()
