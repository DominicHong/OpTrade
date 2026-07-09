"""
Spot import service — Excel pipeline for SpotTrade records.

Delegates the shared parse/validate/execute flow to BaseImportService and
overrides only the event_type validation, ccy1/ccy2 derivation and
direction derivation in validation.
"""

from app.models import SpotTrade
from app.services.base_import_service import BaseImportService
from app.utils.ccy_utils import split_ccy_pair
from app.utils.excel_parser import ValidationError
from app.utils.spot_column_mapping import (
    CSV_TO_SPOT_FIELD,
    SPOT_DATE_FIELDS,
    SPOT_DATETIME_FIELDS,
    SPOT_FLOAT_FIELDS,
    SPOT_REQUIRED_FIELDS,
    SPOT_SIGNATURE_HEADERS,
)


class SpotImportService(BaseImportService):
    """Orchestrates the FX spot trade Excel import pipeline."""

    csv_to_field = CSV_TO_SPOT_FIELD
    signature_headers = SPOT_SIGNATURE_HEADERS
    signature_threshold = 1
    wrong_file_type_msg = (
        "文件不含即期交易特征字段（如成交价、起息日等），"
        "可能上传了期权流水文件。请选择「期权 from ComStar」导入类型。"
    )
    excel_only = True
    non_excel_msg = "即期导入仅支持 .xls/.xlsx 文件格式"
    date_fields = SPOT_DATE_FIELDS
    datetime_fields = SPOT_DATETIME_FIELDS
    float_fields = SPOT_FLOAT_FIELDS
    required_fields = SPOT_REQUIRED_FIELDS
    trade_model = SpotTrade
    import_type_label = "spot"

    def _extra_validate(self, mapped: dict, row_number: int) -> list[ValidationError]:
        errors: list[ValidationError] = []

        # Validate event_type constraint: must be "正常" or "期权行权衍生"
        event_type = mapped.get("event_type")
        if event_type is not None and event_type not in ("正常", "期权行权衍生"):
            errors.append(
                ValidationError(
                    row_number=row_number,
                    field="event_type",
                    message=f"交易事件类型必须为'正常'或'期权行权衍生'，实际值: '{event_type}'",
                    value=str(event_type),
                )
            )

        # Derive ccy1 and ccy2 from ccy_pair (e.g. "USD/CNY" -> ccy1="USD", ccy2="CNY")
        ccy_pair = mapped.get("ccy_pair")
        if ccy_pair and isinstance(ccy_pair, str):
            ccy1, ccy2 = split_ccy_pair(ccy_pair)
            if ccy1 and ccy2:
                mapped["ccy1"] = ccy1
                mapped["ccy2"] = ccy2

        # Derive direction from amount signs if not explicitly set
        if not mapped.get("direction"):
            ccy1_amount = mapped.get("ccy1_amount")
            if ccy1_amount is not None and isinstance(ccy1_amount, (int, float)):
                if ccy1_amount > 0:
                    mapped["direction"] = "买入"
                elif ccy1_amount < 0:
                    mapped["direction"] = "卖出"

        return errors


# Singleton
spot_import_service = SpotImportService()
