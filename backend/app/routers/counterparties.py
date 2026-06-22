from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Counterparty

router = APIRouter(prefix="/api/v1/counterparties", tags=["counterparties"])


@router.get("")
def list_counterparties(
    session: Session = Depends(get_session),
) -> list[dict]:
    """List all counterparties."""
    cps = session.exec(select(Counterparty)).all()
    return [
        {"id": c.id, "name": c.name, "short_name": c.short_name} for c in cps
    ]


@router.post("", status_code=201)
def create_counterparty(
    name: str,
    short_name: str | None = None,
    session: Session = Depends(get_session),
) -> dict:
    """Create a counterparty."""
    existing = session.exec(
        select(Counterparty).where(Counterparty.name == name)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Counterparty already exists")

    cp = Counterparty(name=name, short_name=short_name)
    session.add(cp)
    session.commit()
    session.refresh(cp)
    return {"id": cp.id, "name": cp.name, "short_name": cp.short_name}
