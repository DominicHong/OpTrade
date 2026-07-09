"""Shared upload pipeline for the Excel import endpoints.

The option/spot/swap upload endpoints share an identical flow:
save to temp file -> parse -> validate -> create ImportLog -> execute ->
build preview rows -> error handling -> cleanup.  ``run_upload`` factors
this out so each router's upload handler is a one-liner.
"""

import os
import tempfile

from fastapi import HTTPException, UploadFile
from sqlmodel import Session

from app.models import ImportLog
from app.schemas.import_ import ImportConfirmResponse, ImportParsedRow
from app.utils.date_utils import utc_now


async def run_upload(
    file: UploadFile,
    service,
    session: Session,
    *,
    import_type: str,
    default_suffix: str = ".xls",
) -> ImportConfirmResponse:
    """Run the full parse -> validate -> import pipeline for an uploaded file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    suffix = os.path.splitext(file.filename)[1] or default_suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        parsed = service.parse_file(tmp_path)
        validated = service.validate(parsed)

        import_log = ImportLog(
            filename=file.filename,
            file_hash=parsed.file_hash,
            total_rows=parsed.total_rows,
            status="validated",
            started_at=utc_now(),
            completed_at=utc_now(),
            import_type=import_type,
        )
        session.add(import_log)
        session.commit()
        session.refresh(import_log)

        import_log = service.execute_import(parsed, validated, import_log, session)

        preview_rows: list[ImportParsedRow] = []
        row_count = min(len(parsed.rows), 100)
        for i in range(row_count):
            row = parsed.rows[i]
            trade_id = row.get("成交编号", "") or row.get("trade_id", "")
            row_errors: list[str] = []
            for err in validated.errors:
                if err.row_number == i + 3:
                    row_errors.append(err.message)
            preview_rows.append(
                ImportParsedRow(
                    row_number=i + 3,
                    trade_id=trade_id if trade_id else None,
                    data=row,
                    errors=row_errors,
                )
            )

        return ImportConfirmResponse(
            import_log_id=import_log.id,
            filename=file.filename,
            total_rows=import_log.total_rows,
            imported_rows=import_log.imported_rows,
            skipped_rows=import_log.skipped_rows,
            error_rows=import_log.error_rows,
            status=import_log.status,
            errors=[e.to_dict() for e in validated.errors[:50]],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def column_mapping_response(mapping_dict: dict[str, str]) -> dict:
    """Build the standard ``{mapping, total_columns}`` response for /columns."""
    return {
        "mapping": mapping_dict,
        "total_columns": len(mapping_dict),
    }
