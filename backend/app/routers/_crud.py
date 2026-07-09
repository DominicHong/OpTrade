"""Generic CRUD router factory for trade entities.

The three trade routers (option/spot/swap) share identical batch-delete,
get, create, update and delete endpoints that differ only in the model,
schemas, entity label and optional ccy1/ccy2 derivation hooks.  This module
factors that boilerplate into ``build_crud_router``.

The per-entity ``list`` endpoint is kept in each router file because the
filter query parameters differ between entities (and must be declared
explicitly for correct OpenAPI generation).  Two helpers --
``apply_to_both`` and ``build_list_response`` -- remove the remaining
duplication from the list endpoints.
"""

from dataclasses import dataclass, field
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, func, select

from app.database import get_session
from app.utils.ccy_utils import split_ccy_pair
from app.utils.portfolio_resolver import resolve_portfolio


class BatchDeleteRequest(BaseModel):
    ids: list[int]


@dataclass
class CrudConfig:
    """Configuration for the generated CRUD router."""

    model: type[SQLModel]
    read_schema: type[BaseModel]
    create_schema: type[BaseModel]
    update_schema: type[BaseModel]
    list_response_schema: type[BaseModel]
    prefix: str
    tags: list[str]
    entity_label: str
    default_sort: str
    default_sort_order: str = "asc"
    pre_create_hook: Callable[[dict], dict] | None = None
    pre_update_hook: Callable[[dict], dict] | None = None


def build_crud_router(cfg: CrudConfig) -> APIRouter:
    """Build an APIRouter with the five standard CRUD endpoints."""
    router = APIRouter(prefix=cfg.prefix, tags=cfg.tags)
    model = cfg.model
    ReadSchema = cfg.read_schema
    CreateSchema = cfg.create_schema
    UpdateSchema = cfg.update_schema

    @router.post("/batch-delete")
    def batch_delete(
        req: BatchDeleteRequest,
        session: Session = Depends(get_session),
    ) -> dict[str, str]:
        if not req.ids:
            raise HTTPException(
                status_code=400,
                detail=f"No {cfg.entity_label} IDs provided",
            )
        deleted = 0
        for tid in req.ids:
            trade = session.get(model, tid)
            if trade:
                session.delete(trade)
                deleted += 1
        session.commit()
        return {"status": "deleted", "count": str(deleted)}

    @router.get("/{id}", response_model=ReadSchema)
    def get_one(
        id: int,
        session: Session = Depends(get_session),
    ) -> ReadSchema:
        trade = session.get(model, id)
        if not trade:
            raise HTTPException(
                status_code=404,
                detail=f"{cfg.entity_label} {id} not found",
            )
        return ReadSchema.model_validate(trade)

    @router.post("", response_model=ReadSchema, status_code=201)
    def create_one(
        data: CreateSchema,
        session: Session = Depends(get_session),
    ) -> ReadSchema:
        existing = session.exec(
            select(model).where(model.trade_id == data.trade_id)
        ).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"{cfg.entity_label} with trade_id '{data.trade_id}' already exists",
            )
        pid, pname = resolve_portfolio(session, data.portfolio_id, data.portfolio_name)
        trade_data = data.model_dump()
        trade_data["portfolio_id"] = pid
        trade_data["portfolio_name"] = pname
        if cfg.pre_create_hook:
            trade_data = cfg.pre_create_hook(trade_data)
        trade = model(**trade_data)
        session.add(trade)
        session.commit()
        session.refresh(trade)
        return ReadSchema.model_validate(trade)

    @router.put("/{id}", response_model=ReadSchema)
    def update_one(
        id: int,
        update: UpdateSchema,
        session: Session = Depends(get_session),
    ) -> ReadSchema:
        trade = session.get(model, id)
        if not trade:
            raise HTTPException(
                status_code=404,
                detail=f"{cfg.entity_label} {id} not found",
            )
        update_data = update.model_dump(exclude_unset=True)
        if "portfolio_id" in update_data or "portfolio_name" in update_data:
            resolved_id, resolved_name = resolve_portfolio(
                session,
                update_data.get("portfolio_id"),
                update_data.get("portfolio_name"),
            )
            update_data["portfolio_id"] = resolved_id
            update_data["portfolio_name"] = resolved_name
        if cfg.pre_update_hook:
            update_data = cfg.pre_update_hook(update_data)
        for key, value in update_data.items():
            setattr(trade, key, value)
        session.add(trade)
        session.commit()
        session.refresh(trade)
        return ReadSchema.model_validate(trade)

    @router.delete("/{id}")
    def delete_one(
        id: int,
        session: Session = Depends(get_session),
    ) -> dict[str, str]:
        trade = session.get(model, id)
        if not trade:
            raise HTTPException(
                status_code=404,
                detail=f"{cfg.entity_label} {id} not found",
            )
        session.delete(trade)
        session.commit()
        return {"status": "deleted", "trade_id": str(id)}

    return router


# ---------------------------------------------------------------------------
# List-endpoint helpers
# ---------------------------------------------------------------------------


def apply_to_both(query, count_query, condition):
    """Apply a ``where`` condition to both the data query and the count query."""
    return query.where(condition), count_query.where(condition)


def build_list_response(
    session: Session,
    model: type[SQLModel],
    read_schema: type[BaseModel],
    list_response_schema: type[BaseModel],
    query,
    count_query,
    *,
    sort_by: str,
    sort_order: str,
    default_sort_col,
    page: int,
    page_size: int,
):
    """Finalise a list query: count, sort, paginate, and build the response."""
    total = session.exec(count_query).one()
    sort_column = getattr(model, sort_by, default_sort_col)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column)
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    trades = session.exec(query).all()
    return list_response_schema(
        data=[read_schema.model_validate(t) for t in trades],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# ccy1/ccy2 derivation hooks (shared by swap and spot routers)
# ---------------------------------------------------------------------------


def derive_ccy_if_missing(trade_data: dict) -> dict:
    """Derive ccy1/ccy2 from ccy_pair when not already populated (create)."""
    if trade_data.get("ccy_pair") and not (
        trade_data.get("ccy1") and trade_data.get("ccy2")
    ):
        ccy1, ccy2 = split_ccy_pair(trade_data["ccy_pair"])
        if ccy1 and ccy2:
            trade_data["ccy1"] = ccy1
            trade_data["ccy2"] = ccy2
    return trade_data


def derive_ccy_if_pair_changed(update_data: dict) -> dict:
    """Derive ccy1/ccy2 whenever ccy_pair is provided (update)."""
    if update_data.get("ccy_pair"):
        ccy1, ccy2 = split_ccy_pair(update_data["ccy_pair"])
        if ccy1 and ccy2:
            update_data["ccy1"] = ccy1
            update_data["ccy2"] = ccy2
    return update_data
