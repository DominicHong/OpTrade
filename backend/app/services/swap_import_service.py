"""
Swap import service — Excel pipeline for SwapTrade records.

Delegates the shared parse/validate/execute flow to BaseImportService and
overrides only the ccy1/ccy2 derivation in validation.
"""

from app.models import SwapTrade
from app.services.base_import_service import BaseImportService
from app.utils.ccy_utils import split_ccy_pair
from app.utils.excel_parser import ValidationError
from app.utils.swap_column_mapping import (
    CSV_TO_SWAP_FIELD,
    SWAP_DATE_FIELDS,
    SWAP_DATETIME_FIELDS,
    SWAP_FLOAT_FIELDS,
    SWAP_REQUIRED_FIELDS,
    SWAP_SIGNATURE_HEADERS,
)


class SwapImportService(BaseImportService):
    """Orchestrates the FX swap trade Excel import pipeline."""

    csv_to_field = CSV_TO_SWAP_FIELD
    signature_headers = SWAP_SIGNATURE_HEADERS
    signature_threshold = 1
    wrong_file_type_msg = (
        "文件不含掉期交易特征字段（如近端成交价、远端成交价、近端起息日等），"
        "可能上传了期权或即期流水文件。请选择对应的导入类型。"
    )
    excel_only = True
    non_excel_msg = "掉期导入仅支持 .xls/.xlsx 文件格式"
    date_fields = SWAP_DATE_FIELDS
    datetime_fields = SWAP_DATETIME_FIELDS
    float_fields = SWAP_FLOAT_FIELDS
    required_fields = SWAP_REQUIRED_FIELDS
    trade_model = SwapTrade
    import_type_label = "swap"

    def _extra_validate(self, mapped: dict, row_number: int) -> list[ValidationError]:
        # Derive ccy1 and ccy2 from ccy_pair (e.g. "USD/JPY" -> ccy1="USD", ccy2="JPY")
        ccy_pair = mapped.get("ccy_pair")
        if ccy_pair and isinstance(ccy_pair, str):
            ccy1, ccy2 = split_ccy_pair(ccy_pair)
            if ccy1 and ccy2:
                mapped["ccy1"] = ccy1
                mapped["ccy2"] = ccy2
        return []


# Singleton
swap_import_service = SwapImportService()
