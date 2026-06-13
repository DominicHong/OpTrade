# OpTrade — Desktop Options Trading & Risk Management System

## Project Overview

OpTrade is a Windows desktop application for FX options trade management and risk analysis.
It imports trade records from COMSTAR CSV/Excel exports and provides portfolio-level
risk metrics (Greeks), scenario analysis (spot/vol/time shifts), and dashboards.

**Tech Stack**: PyWebView + Vue3 + TypeScript + FastAPI + SQLModel + SQLite + QuantLib

## Architecture

```
PyWebView Shell (desktop window)
    └── hosts Vue3 SPA at localhost:5173 (dev) or localhost:8000/static (prod)
        ├── Frontend: Vue3 + TypeScript + Pinia + Vue Router
        └── Backend:  FastAPI REST API → Services → SQLModel/SQLite + QuantLib
```

- **Frontend** is a standard Vue3 SPA. It has NO PyWebView dependency.
- **Backend** is a FastAPI app with services layer separating QuantLib from API routes.
- **Future Web migration**: build frontend to static files, serve via FastAPI, remove PyWebView.

## Coding Constraints

1. **Python**: Native Type Hints only (`str | None`, `list[str]`, `dict[str, float]`). NO `typing` imports.
2. **Vue3**: All components must use `<script setup lang="ts">` syntax.
3. **QuantLib**: ALL QuantLib code must live in `backend/app/services/`. Routes NEVER import QuantLib directly.

## Project Structure

```
backend/           — FastAPI backend
  app/
    models/        — SQLModel entities (Trade, Portfolio, Counterparty, CalculationResult, etc.)
    schemas/       — Pydantic request/response schemas
    routers/       — API route handlers
    services/      — Business logic (pricing, Greeks, import, scenarios)
    utils/         — Helpers (column_mapping, date_utils, quantlib_helpers)
    desktop/       — PyWebView window launcher
  tests/           — pytest tests

frontend/          — Vue3 SPA
  src/
    api/           — Axios API wrappers
    router/        — Vue Router config
    stores/        — Pinia stores
    pages/         — Page components (Dashboard, TradeList, TradeDetail, Import, Portfolio, Scenario)
    components/    — Reusable components (layout, shared, trade, risk, portfolio, import)
    types/         — TypeScript interfaces
    utils/         — Formatting helpers, constants
```

## Key Files

- `backend/app/models/trade.py` — Central entity with ~80 fields mapping COMSTAR CSV export
- `backend/app/utils/column_mapping.py` — Chinese CSV header → model field mapping
- `backend/app/models/__init__.py` — Import order matters for SQLModel table creation
- `frontend/src/App.vue` — Application shell, wraps AppLayout
- `frontend/src/router/index.ts` — All routes (uses hash mode for PyWebView compat)

## Development

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Or use:
scripts/start_dev.bat
```
