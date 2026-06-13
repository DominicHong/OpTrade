from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: create tables on startup."""
    create_db_and_tables()
    yield


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
    from app.routers import trades, portfolios, counterparties, calculations, scenarios, imports, dashboard, market_data

    app.include_router(trades.router)
    app.include_router(portfolios.router)
    app.include_router(counterparties.router)
    app.include_router(calculations.router)
    app.include_router(scenarios.router)
    app.include_router(imports.router)
    app.include_router(dashboard.router)
    app.include_router(market_data.router)

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
