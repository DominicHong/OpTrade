from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models.market_data import MarketDataSnapshot

router = APIRouter(prefix="/api/v1/market-data", tags=["market-data"])


@router.get("")
def list_market_data(
    ccy_pair: str | None = None,
    session: Session = Depends(get_session),
) -> list[dict]:
    """List market data snapshots, optionally filtered by currency pair."""
    query = select(MarketDataSnapshot)
    if ccy_pair:
        query = query.where(MarketDataSnapshot.ccy_pair == ccy_pair)
    query = query.order_by(MarketDataSnapshot.snapshot_date.desc()).limit(50)

    snapshots = session.exec(query).all()
    return [
        {
            "id": s.id,
            "ccy_pair": s.ccy_pair,
            "spot": s.spot,
            "volatility": s.volatility,
            "snapshot_date": str(s.snapshot_date) if s.snapshot_date else None,
            "source": s.source,
        }
        for s in snapshots
    ]


@router.post("", status_code=201)
def add_market_data(
    ccy_pair: str,
    spot: float | None = None,
    volatility: float | None = None,
    source: str | None = None,
    session: Session = Depends(get_session),
) -> dict:
    """Add a market data snapshot."""
    snapshot = MarketDataSnapshot(
        ccy_pair=ccy_pair,
        spot=spot,
        volatility=volatility,
        source=source,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return {"id": snapshot.id, "ccy_pair": snapshot.ccy_pair, "status": "created"}
