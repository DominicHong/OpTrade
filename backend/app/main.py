import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Session, create_db_and_tables, engine

logger = logging.getLogger("optrade.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: create tables and seed data."""
    create_db_and_tables()
    _seed_curve_definitions()
    yield


def _seed_curve_definitions() -> None:
    """Insert default curve definitions if they don't already exist."""
    from sqlmodel import select

    from app.models.curve import CurveDefinition

    with Session(engine) as session:
        existing = session.exec(
            select(CurveDefinition).where(
                CurveDefinition.curve_type == "fx_implied_rate",
            )
        ).first()
        if not existing:
            session.add(
                CurveDefinition(
                    name="外币隐含利率曲线",
                    curve_type="fx_implied_rate",
                    description="外币隐含利率曲线 — 数据来源：中国货币网 chinamoney.com.cn",
                    source_url="https://www.chinamoney.com.cn/chinese/bkcurvuiruuh/",
                    parameters=(
                        '{"ccy_pair":"全部",'
                        '"cny_rate":"FR007利率互换收盘曲线",'
                        '"spot_rate":"即期询价报价均值",'
                        '"swap_point":"掉期点"}'
                    ),
                    is_active=True,
                )
            )
            session.commit()
            logger.info("Seeded default curve definition: fx_implied_rate")


def create_app() -> FastAPI:
    """Factory: build and configure the FastAPI application."""

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # CORS — allow frontend dev server and PyWebView origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "*",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    from app.routers import option_trades, portfolios, counterparties, calculations, scenarios, imports, dashboard, curves, spot_trades

    app.include_router(option_trades.router)
    app.include_router(portfolios.router)
    app.include_router(counterparties.router)
    app.include_router(calculations.router)
    app.include_router(scenarios.router)
    app.include_router(imports.router)
    app.include_router(dashboard.router)
    app.include_router(curves.router)
    app.include_router(spot_trades.router)
    app.include_router(spot_trades.import_router)

    @app.get("/api/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    # Serve built frontend as static files (production / desktop mode)
    import sys
    if hasattr(sys, '_MEIPASS'):
        dist_dir = Path(sys._MEIPASS) / "frontend" / "dist"
    else:
        dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if dist_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")
    else:
        @app.get("/")
        def root() -> dict[str, str]:
            return {"app": settings.app_name, "version": settings.app_version}

    return app


app = create_app()
