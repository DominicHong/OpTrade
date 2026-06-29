from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class ImportLog(SQLModel, table=True):
    __tablename__ = "import_logs"

    id: int | None = Field(default=None, primary_key=True)
    filename: str = Field(max_length=500)
    file_hash: str | None = Field(default=None, max_length=64)
    total_rows: int = 0
    imported_rows: int = 0
    skipped_rows: int = 0
    error_rows: int = 0
    status: str = Field(default="pending", max_length=20)  # pending/processing/success/partial/failed
    import_type: str = Field(default="option", max_length=20)  # "option" or "spot"
    error_message: str | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ImportErrorRecord(SQLModel, table=True):
    __tablename__ = "import_error_records"

    id: int | None = Field(default=None, primary_key=True)
    import_log_id: int = Field(foreign_key="import_logs.id", index=True)
    row_number: int = 0
    trade_id_value: str | None = Field(default=None, max_length=200)
    error_type: str = Field(max_length=50)  # validation/duplicate/parse/missing_field
    error_message: str = Field()
    raw_data: str | None = Field(default=None)  # JSON string of the row
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
