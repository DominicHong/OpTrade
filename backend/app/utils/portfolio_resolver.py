"""Shared portfolio resolution helper for trade routers."""

from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import Portfolio


def resolve_portfolio(
    session: Session,
    portfolio_id: int | None,
    portfolio_name: str | None,
) -> tuple[int | None, str | None]:
    """Resolve *portfolio_name* to *portfolio_id*.

    Errors if a name is given but not found.  Returns the
    ``(portfolio_id, portfolio_name)`` tuple (``(None, None)`` when neither
    is provided).
    """
    if portfolio_id is not None:
        portfolio = session.get(Portfolio, portfolio_id)
        if not portfolio:
            raise HTTPException(
                status_code=404,
                detail=f"Portfolio with id {portfolio_id} not found",
            )
        return portfolio.id, portfolio.name

    if portfolio_name:
        portfolio = session.exec(
            select(Portfolio).where(Portfolio.name == portfolio_name)
        ).first()
        if not portfolio:
            raise HTTPException(
                status_code=404,
                detail=f"投组 '{portfolio_name}' 不存在，请先在投组管理页面创建该投组",
            )
        return portfolio.id, portfolio.name

    return None, None
