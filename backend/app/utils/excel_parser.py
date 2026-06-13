"""
Excel file parser for importing trade records.

Supports .csv (COMSTAR export format) and .xlsx/.xls files.
CSV files are read with GB2312/GBK encoding for Chinese characters.
Excel files are read via openpyxl (.xlsx) or xlrd (.xls).
"""

import csv
import hashlib
import io
from pathlib import Path

import openpyxl
import xlrd


def read_csv_file(file_path: str | Path) -> list[dict[str, str]]:
    """
    Read a COMSTAR CSV export file.

    The COMSTAR CSV format:
    - Line 1: metadata/header row (skipped)
    - Line 2: Chinese column headers
    - Line 3+: data rows
    - Encoding: GB2312/GBK

    Returns list of rows as dict[str, str] (header → raw value).
    """
    file_path = Path(file_path)

    # Try multiple encodings
    encodings = ["gb2312", "gbk", "gb18030", "utf-8-sig", "utf-8"]

    raw_bytes = file_path.read_bytes()
    text: str | None = None

    for enc in encodings:
        try:
            text = raw_bytes.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if text is None:
        raise ValueError(f"Unable to decode file {file_path} with any known encoding")

    lines = text.splitlines()

    # Skip line 1 (metadata), use line 2 as header, data starts at line 3
    if len(lines) < 2:
        raise ValueError("CSV file has insufficient rows (need at least a header row)")

    header_line = lines[1] if len(lines) >= 2 else lines[0]
    reader = csv.reader(io.StringIO("\n".join(lines[1:])))  # start from header line
    headers_raw = next(reader)
    headers = [h.strip() for h in headers_raw]

    rows: list[dict[str, str]] = []
    for line_num, row in enumerate(reader, start=3):
        if not any(cell.strip() for cell in row):  # skip completely empty rows
            continue
        row_dict: dict[str, str] = {}
        for i, header in enumerate(headers):
            value = row[i].strip() if i < len(row) else ""
            row_dict[header] = value
        rows.append(row_dict)

    return rows


def read_excel_file(file_path: str | Path) -> list[dict[str, str]]:
    """
    Read an Excel file (.xlsx or .xls) with COMSTAR format.

    Same layout as CSV:
    - Row 1: metadata/header row (skipped)
    - Row 2: Chinese column headers
    - Row 3+: data rows

    Returns list of rows as dict[str, str] (header → raw value).
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    if suffix == ".xlsx":
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        ws = wb.active
        all_rows: list[list[str]] = []
        for row in ws.iter_rows(values_only=True):
            all_rows.append([str(cell) if cell is not None else "" for cell in row])
        wb.close()
    elif suffix == ".xls":
        wb = xlrd.open_workbook(file_path)
        ws = wb.sheet_by_index(0)
        all_rows = []
        for row_idx in range(ws.nrows):
            all_rows.append([str(ws.cell_value(row_idx, col_idx)) for col_idx in range(ws.ncols)])
    else:
        raise ValueError(f"Unsupported Excel format: {suffix}")

    if len(all_rows) < 2:
        raise ValueError("Excel file has insufficient rows (need at least a header row)")

    # Skip row 1 (metadata), use row 2 as header, data starts at row 3
    headers = [h.strip() for h in all_rows[1]]

    rows: list[dict[str, str]] = []
    for row_values in all_rows[2:]:
        if not any(cell.strip() for cell in row_values):
            continue
        row_dict: dict[str, str] = {}
        for i, header in enumerate(headers):
            value = row_values[i].strip() if i < len(row_values) else ""
            row_dict[header] = value
        rows.append(row_dict)

    return rows


def compute_file_hash(file_path: str | Path) -> str:
    """Compute SHA256 hash of a file for deduplication."""
    return hashlib.sha256(Path(file_path).read_bytes()).hexdigest()


class ParsedImportData:
    """Container for parsed import data."""

    def __init__(
        self,
        filename: str,
        file_hash: str,
        rows: list[dict[str, str]],
        column_mapping: dict[str, str],
    ) -> None:
        self.filename = filename
        self.file_hash = file_hash
        self.rows = rows
        self.column_mapping = column_mapping

    @property
    def total_rows(self) -> int:
        return len(self.rows)


class ValidationError:
    """A single validation error for an import row."""

    def __init__(self, row_number: int, field: str, message: str, value: str = "") -> None:
        self.row_number = row_number
        self.field = field
        self.message = message
        self.value = value

    def to_dict(self) -> dict:
        return {
            "row_number": self.row_number,
            "field": self.field,
            "message": self.message,
            "value": self.value,
        }


class ImportValidationResult:
    """Result of validating parsed import data."""

    def __init__(self) -> None:
        self.valid_rows: list[dict] = []
        self.errors: list[ValidationError] = []
        self.warnings: list[ValidationError] = []

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def valid_count(self) -> int:
        return len(self.valid_rows)
