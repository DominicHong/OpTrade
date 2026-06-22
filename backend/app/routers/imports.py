"""
Import API routes — Excel/CSV upload and import pipeline.

Single-step flow:
  POST /upload  — Parse, validate, and persist trades to database
"""

import os
import tempfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from app.database import get_session
from app.models import ImportErrorRecord, ImportLog
from app.schemas.import_ import (
    ImportConfirmResponse,
    ImportHistoryItem,
    ImportParsedRow,
)
from app.services.import_service import import_service

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])


@router.post("/upload")
async def upload_excel(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> ImportConfirmResponse:
    """
    Upload an Excel/CSV file, parse, validate, and import into database.

    Full pipeline: Parse → Validate → Execute Import → Return results.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Save uploaded file to temp location
    suffix = os.path.splitext(file.filename)[1] or ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Phase 1: Parse
        parsed = import_service.parse_file(tmp_path)

        # Phase 2: Validate
        validated = import_service.validate(parsed)

        # Create initial import log
        import_log = ImportLog(
            filename=file.filename,
            file_hash=parsed.file_hash,
            total_rows=parsed.total_rows,
            status="validated",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        session.add(import_log)
        session.commit()
        session.refresh(import_log)

        # Record validation errors
        for err in validated.errors:
            session.add(
                ImportErrorRecord(
                    import_log_id=import_log.id,
                    row_number=err.row_number,
                    error_type="validation",
                    error_message=err.message,
                )
            )
        session.commit()

        # Phase 3: Execute import — persist validated rows to database
        import_log = import_service.execute_import(
            parsed, validated, import_log, session
        )

        # Build parsed rows for preview (limit to first 100)
        preview_rows: list[ImportParsedRow] = []
        for i in range(min(len(parsed.rows), 100)):
            row = parsed.rows[i]
            trade_id = row.get("成交编号", "") or row.get("trade_id", "")
            errors: list[str] = []
            for err in validated.errors:
                if err.row_number == i + 3:
                    errors.append(err.message)
            preview_rows.append(
                ImportParsedRow(
                    row_number=i + 3,
                    trade_id=trade_id if trade_id else None,
                    data=row,
                    errors=errors,
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@router.post("/confirm", response_model=ImportConfirmResponse)
def confirm_import(
    import_log_id: int,
    session: Session = Depends(get_session),
) -> ImportConfirmResponse:
    """
    Confirm and persist a previously validated import.
    """
    import_log = session.get(ImportLog, import_log_id)
    if not import_log:
        raise HTTPException(status_code=404, detail="Import log not found")

    if import_log.status != "validated":
        raise HTTPException(status_code=409, detail=f"Import is in status '{import_log.status}', expected 'validated'")

    import_log.status = "processing"
    import_log.started_at = datetime.now(timezone.utc)
    session.add(import_log)
    session.commit()

    try:
        # Re-parse is needed — store the parsed data in-memory or re-upload
        # For now, this is a placeholder until full in-memory caching is implemented
        # In Phase 2 refinement, parsed data should be cached server-side
        raise HTTPException(
            status_code=501,
            detail="Confirm import requires server-side caching (Phase 2 refinement). "
                   "Please re-upload and the system will auto-confirm.",
        )
    except HTTPException:
        raise
    except Exception as e:
        import_log.status = "failed"
        import_log.error_message = str(e)
        session.add(import_log)
        session.commit()
        return ImportConfirmResponse(
            import_log_id=import_log.id,
            filename=import_log.filename,
            total_rows=import_log.total_rows,
            imported_rows=import_log.imported_rows,
            skipped_rows=import_log.skipped_rows,
            error_rows=import_log.error_rows,
            status="failed",
            error_message=str(e),
        )


@router.get("/columns")
def get_column_mapping() -> dict:
    """Get the expected column mapping reference for COMSTAR exports."""
    from app.utils.column_mapping import CSV_TO_TRADE_FIELD

    return {
        "mapping": CSV_TO_TRADE_FIELD,
        "total_columns": len(CSV_TO_TRADE_FIELD),
    }


@router.get("/history", response_model=list[ImportHistoryItem])
def get_import_history(
    session: Session = Depends(get_session),
) -> list[ImportHistoryItem]:
    """List import history."""
    logs = session.exec(
        select(ImportLog).order_by(ImportLog.created_at.desc()).limit(20)
    ).all()
    return [
        ImportHistoryItem(
            id=log.id,
            filename=log.filename,
            total_rows=log.total_rows,
            imported_rows=log.imported_rows,
            error_rows=log.error_rows,
            status=log.status,
            created_at=log.created_at,
        )
        for log in logs
    ]
