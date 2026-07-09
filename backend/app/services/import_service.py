"""
Option import service — Excel/CSV pipeline for OptionTrade records.

Delegates the shared parse/validate/execute flow to BaseImportService and
overrides only the option-specific bits: volatility percent->fraction
scaling, option-category detection and barrier/asian child-table creation.
"""

from sqlmodel import Session

from app.models import AsianOptionDetails, BarrierOptionDetails, OptionTrade
from app.services.base_import_service import BaseImportService
from app.utils.column_mapping import (
    BOOL_FIELDS,
    CSV_TO_OPTION_TRADE_FIELD,
    DATE_FIELDS,
    DATETIME_FIELDS,
    FLOAT_FIELDS,
    OPTIONS_SIGNATURE_HEADERS,
    REQUIRED_FIELDS,
)


class ImportService(BaseImportService):
    """Orchestrates the option Excel import pipeline."""

    csv_to_field = CSV_TO_OPTION_TRADE_FIELD
    signature_headers = OPTIONS_SIGNATURE_HEADERS
    signature_threshold = 2
    wrong_file_type_msg = (
        "文件不含期权交易特征字段（如执行价、期权类型、行权日、期权费率等），"
        "可能上传了即期流水文件。请选择「即期 from ComStar」导入类型。"
    )
    excel_only = False
    date_fields = DATE_FIELDS
    datetime_fields = DATETIME_FIELDS
    float_fields = FLOAT_FIELDS
    bool_fields = BOOL_FIELDS
    required_fields = REQUIRED_FIELDS
    trade_model = OptionTrade
    import_type_label = "option"

    def _transform_parsed_value(self, field_name: str, value) -> object:
        # COMSTAR exports volatility in annualized percent (e.g. 1.43 = 1.43%)
        if field_name == "volatility" and value is not None:
            return value / 100.0
        return value

    def _determine_option_category(self, row_data: dict) -> str:
        """Determine option_category from row data based on populated fields.

        Barrier fields populated -> "barrier"
        Asian/Averaging fields populated -> "asian"
        Otherwise -> "fx_vanilla" (default)
        """
        barrier_fields = {"barrier_type", "barrier_direction", "barrier_level"}
        asian_fields = {
            "asian_sub_type", "averaging_method", "averaging_frequency",
            "averaging_rounding_method", "averaging_decimal_places",
            "reference_holiday", "observation_start_date", "observation_end_date",
            "averaging_start_date", "averaging_end_date",
        }

        has_barrier = any(row_data.get(f) is not None for f in barrier_fields)
        has_asian = any(row_data.get(f) is not None for f in asian_fields)

        if has_barrier:
            return "barrier"
        elif has_asian:
            return "asian"
        return "fx_vanilla"

    def _create_trade(self, row_data: dict, session: Session) -> None:
        option_category = self._determine_option_category(row_data)
        row_data["option_category"] = option_category

        option_trade = OptionTrade()
        for field_name, value in row_data.items():
            if hasattr(OptionTrade, field_name):
                setattr(option_trade, field_name, value)

        session.add(option_trade)
        session.flush()  # ensure PK is generated for child tables

        if option_category == "barrier":
            barrier_detail = BarrierOptionDetails(id=option_trade.id)
            for field_name, value in row_data.items():
                if hasattr(BarrierOptionDetails, field_name):
                    setattr(barrier_detail, field_name, value)
            session.add(barrier_detail)
        elif option_category == "asian":
            asian_detail = AsianOptionDetails(id=option_trade.id)
            for field_name, value in row_data.items():
                if hasattr(AsianOptionDetails, field_name):
                    setattr(asian_detail, field_name, value)
            session.add(asian_detail)


# Singleton
import_service = ImportService()
