"""Base class for the Excel import pipeline (option/spot/swap).

The three import services share an identical parse -> validate -> execute
flow that differs only in column-mapping constants, signature headers, the
trade model and a few entity-specific hooks.  This base class encapsulates
the shared logic; subclasses declare their constants as class attributes
and override the small hooks where needed:

- ``_transform_parsed_value``  — option scales volatility from percent to fraction.
- ``_extra_validate``          — swap/spot derive ccy1/ccy2; spot validates event_type
                                  and derives direction.
- ``_create_trade``            — option creates barrier/asian child detail tables.
"""

from pathlib import Path

from sqlmodel import Session, select

from app.models import Counterparty, Portfolio
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


class BaseImportService:
    """Orchestrates the Excel import pipeline for a single trade type."""

    # --- Subclasses override these class attributes -------------------------
    csv_to_field: dict[str, str] = {}
    signature_headers: list[str] = []
    signature_threshold: int = 1
    wrong_file_type_msg: str = ""
    excel_only: bool = False
    non_excel_msg: str = ""
    date_fields: set[str] = set()
    datetime_fields: set[str] = set()
    float_fields: set[str] = set()
    bool_fields: set[str] = set()
    required_fields: list[str] = []
    trade_model: type = None
    import_type_label: str = ""

    # --- Pipeline -----------------------------------------------------------

    def parse_file(self, file_path: str | Path) -> ParsedImportData:
        """Parse a CSV or Excel file and return structured data."""
        file_path = Path(file_path)
        filename = file_path.name
        file_hash = compute_file_hash(file_path)

        suffix = file_path.suffix.lower()
        if suffix in (".xlsx", ".xls"):
            rows = read_excel_file(file_path)
        elif self.excel_only:
            raise ValueError(self.non_excel_msg)
        else:
            rows = read_csv_file(file_path)

        available_headers = set(rows[0].keys()) if rows else set()
        effective_mapping: dict[str, str] = {}
        for csv_header, field_name in self.csv_to_field.items():
            if csv_header in available_headers:
                effective_mapping[csv_header] = field_name

        if available_headers:
            matched_signatures = [
                h for h in self.signature_headers if h in available_headers
            ]
            if len(matched_signatures) < self.signature_threshold:
                raise ValueError(self.wrong_file_type_msg)

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
            row_number = idx + 3  # data rows start at line 3
            mapped: dict = {}
            row_errors: list[ValidationError] = []

            for csv_header, raw_value in row.items():
                field_name = parsed.column_mapping.get(csv_header)
                if field_name is None:
                    continue

                if field_name in self.date_fields:
                    parsed_value = parse_chinese_date(raw_value)
                elif field_name in self.datetime_fields:
                    parsed_value = parse_chinese_datetime(raw_value)
                elif field_name in self.float_fields:
                    parsed_value = parse_float(raw_value)
                elif field_name in self.bool_fields:
                    parsed_value = parse_bool_chinese(raw_value)
                    if parsed_value is None:
                        parsed_value = False
                else:
                    parsed_value = raw_value if raw_value else None

                parsed_value = self._transform_parsed_value(field_name, parsed_value)
                mapped[field_name] = parsed_value

            for required_field in self.required_fields:
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

            row_errors.extend(self._extra_validate(mapped, row_number))

            if row_errors:
                result.errors.extend(row_errors)
            else:
                result.valid_rows.append(mapped)

        return result

    def execute_import(
        self,
        parsed: ParsedImportData,
        validated: ImportValidationResult,
        import_log,
        session: Session,
    ):
        """Persist validated rows to the database.

        Creates Portfolio and Counterparty records as needed and skips
        duplicate trade_ids.
        """
        imported = 0
        skipped = 0

        for row_data in validated.valid_rows:
            try:
                self._find_or_create_relations(row_data, session)

                trade_id_val = row_data.get("trade_id")
                if trade_id_val:
                    existing = session.exec(
                        select(self.trade_model).where(
                            self.trade_model.trade_id == trade_id_val
                        )
                    ).first()
                    if existing:
                        skipped += 1
                        continue

                self._create_trade(row_data, session)
                imported += 1

            except Exception:
                skipped += 1
                continue

        session.commit()

        import_log.imported_rows = imported
        import_log.skipped_rows = skipped
        import_log.error_rows = validated.error_count
        import_log.status = "success" if validated.error_count == 0 else "partial"
        import_log.import_type = self.import_type_label
        session.add(import_log)
        session.commit()

        return import_log

    # --- Hooks (overridable) -----------------------------------------------

    def _transform_parsed_value(self, field_name: str, value) -> object:
        """Hook for subclasses to transform a parsed field value."""
        return value

    def _extra_validate(self, mapped: dict, row_number: int) -> list[ValidationError]:
        """Hook for subclass-specific validation/derivation.  May mutate *mapped*."""
        return []

    def _create_trade(self, row_data: dict, session: Session) -> None:
        """Create a trade record from *row_data* (base: generic setattr loop)."""
        trade = self.trade_model()
        for field_name, value in row_data.items():
            if hasattr(self.trade_model, field_name):
                setattr(trade, field_name, value)
        session.add(trade)

    # --- Shared helpers -----------------------------------------------------

    def _find_or_create_relations(self, row_data: dict, session: Session) -> None:
        """Find-or-create Portfolio and Counterparty, populating their FK ids."""
        portfolio_name = row_data.get("portfolio_name")
        if portfolio_name:
            portfolio = session.exec(
                select(Portfolio).where(Portfolio.name == portfolio_name)
            ).first()
            if not portfolio:
                portfolio = Portfolio(name=portfolio_name)
                session.add(portfolio)
                session.flush()
            row_data["portfolio_id"] = portfolio.id

        counterparty_name = row_data.get("counterparty_name")
        if counterparty_name:
            counterparty = session.exec(
                select(Counterparty).where(Counterparty.name == counterparty_name)
            ).first()
            if not counterparty:
                counterparty = Counterparty(name=counterparty_name)
                session.add(counterparty)
                session.flush()
            row_data["counterparty_id"] = counterparty.id
