from datetime import datetime

from pydantic import BaseModel


class ImportParsedRow(BaseModel):
    """A single parsed row from the Excel file."""

    row_number: int
    trade_id: str | None = None
    option_category: str = "fx_vanilla"
    data: dict[str, str]  # column_name -> raw value
    errors: list[str] = []


class ImportPreviewResponse(BaseModel):
    """Response after parsing an uploaded file."""

    import_log_id: int
    filename: str
    total_rows: int
    valid_rows: int
    error_rows: int
    column_mapping: dict[str, str]  # CSV header -> field name
    parsed_rows: list[ImportParsedRow]
    errors: list[dict] = []


class ImportConfirmResponse(BaseModel):
    """Response after confirming and executing import."""

    import_log_id: int
    filename: str
    total_rows: int
    imported_rows: int
    skipped_rows: int
    error_rows: int
    status: str
    errors: list[dict] = []
    error_message: str | None = None


class ImportHistoryItem(BaseModel):
    id: int
    filename: str
    total_rows: int
    imported_rows: int
    error_rows: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
