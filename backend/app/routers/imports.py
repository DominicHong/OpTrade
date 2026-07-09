"""
Import API routes — Excel/CSV upload and import pipeline.

Single-step flow:
  POST /upload  — Parse, validate, and persist trades to database
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from app.database import get_session
from app.models import ImportLog
from app.schemas.import_ import (
    ImportConfirmResponse,
    ImportHistoryItem,
)
from app.services.import_pipeline import column_mapping_response, run_upload
from app.services.import_service import import_service
from app.utils.column_mapping import CSV_TO_OPTION_TRADE_FIELD
from app.utils.date_utils import utc_now

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])


@router.post("/upload")
async def upload_excel(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> ImportConfirmResponse:
    """Upload an Excel/CSV file, parse, validate, and import into database."""
    return await run_upload(
        file, import_service, session,
        import_type="option", default_suffix=".csv",
    )


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
    import_log.started_at = utc_now()
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
    return column_mapping_response(CSV_TO_OPTION_TRADE_FIELD)


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
