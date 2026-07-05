# OpTrade — Desktop Options Trading & Risk Management System

FX Options trade management and risk analysis for Windows desktop, with a future Web migration path.

## Tech Stack

- **Desktop Shell**: PyWebView
- **Frontend**: Vue 3 + TypeScript + Pinia + Vue Router
- **Backend**: FastAPI + SQLModel + SQLite
- **Pricing/Risk**: QuantLib-Python
- **Data Import**: openpyxl / xlrd (Excel/CSV parsing)

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- (Optional) QuantLib C++ library for QuantLib-Python

### Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Start backend (from repo root, NOT backend/)
cd ..
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev      # serves on http://127.0.0.1:3000
```

### Desktop App

```bash
python -m backend.app.desktop.window
```

### One-Click Dev Startup

```bash
scripts\start_dev.bat      # backend :8000 + frontend :3000
```

## Testing

Tests run with pytest and **must be run from `backend/`** (the import path is `app.*`, not `backend.app.*`):

```bash
cd backend
pytest                                              # all tests
pytest tests/test_greeks_service.py                 # one file
pytest tests/test_greeks_service.py::TestVanillaGreeks::test_atm_call_greeks  # one test
```

The frontend has no separate lint/typecheck script — `npm run build` runs `vue-tsc --noEmit` before `vite build`, so it doubles as the typecheck:

```bash
cd frontend
npm run build
```

## API Documentation

Once running, visit http://127.0.0.1:8000/docs for interactive API docs (Swagger UI). Health check at `/api/health`.

## Project Structure

```
backend/         — FastAPI backend
  app/
    models/      — SQLModel entities (core.py: OptionTrade, Portfolio, Counterparty, SpotTrade, barrier/asian details)
    schemas/     — Pydantic request/response schemas
    routers/     — REST API endpoints (all mounted under /api/v1/*)
    services/    — Business logic (pricing, Greeks, import, scenarios, curves) — only place QuantLib is used
    utils/       — Helpers (column_mapping, date_utils, quantlib_helpers, excel_parser)
    desktop/     — PyWebView window launcher
  tests/         — pytest tests (conftest.py provides engine/session/client fixtures)

frontend/        — Vue3 SPA (no PyWebView dependency)
  src/
    api/         — Axios API wrappers
    pages/       — Page components (Dashboard, OptionTradeList, OptionTradeDetail, Portfolio, Scenario, CurveManagement, ExchangeRateManagement)
    components/  — Reusable components (layout, shared, trade, risk, portfolio)
    stores/      — Pinia stores
    router/      — Vue Router config (hash mode for PyWebView compat)
    types/       — TypeScript interfaces
```

## Features

- **Trade Management**: View, search, filter, and edit FX option trades
- **Excel Import**: COMSTAR CSV/Excel trade export pipeline with validation (Chinese column headers mapped via `utils/column_mapping.py`)
- **Greeks Calculation**: Delta, Gamma, Vega, Theta, Rho via QuantLib
- **Scenario Analysis**: Spot shift, vol shift, time decay, 2D heatmap
- **Portfolio Analytics**: Aggregated risk metrics by portfolio
- **Curve Management**: FX implied rate curves from chinamoney.com.cn (auto-crawl via Playwright or manual XLSX upload)
- **Dashboard**: Summary statistics, exposure breakdown

## Coding Constraints

1. **Python**: Native Type Hints only (`str | None`, `list[str]`) — no `typing` imports
2. **Vue3**: All components use `<script setup lang="ts">` syntax
3. **QuantLib**: Confined to `backend/app/services/` and `backend/app/utils/quantlib_helpers.py` — routes never import it directly
4. **Router**: Uses `createWebHashHistory` (hash mode) for PyWebView compatibility

## Configuration

Settings are loaded via `pydantic_settings.BaseSettings` with env prefix `OPTRADE_` (reads a gitignored `.env`). Relevant keys:

| Env var | Purpose |
| --- | --- |
| `OPTRADE_DEBUG` | Enable SQL echo / debug mode |
| `OPTRADE_FRONTEND_URL` | Override the URL PyWebView loads |
| `OPTRADE_DATABASE_URL` | Override the SQLite DB URL (default `data/optrade.db`) |
| `OPTRADE_HOST` / `OPTRADE_PORT` | Backend bind address (default `127.0.0.1:8000`) |

## Build for Windows

### Prerequisites

```cmd
pip install pyinstaller
```

### One-Click Build

```cmd
scripts\build_desktop.bat
```

This builds the frontend, then packages with PyInstaller. Playwright is excluded (`--exclude-module playwright`), so the chinamoney auto-crawl feature is unavailable in packaged builds — manual XLSX upload still works via the `/api/v1/curves` upload endpoint.

### Manual Build

```cmd
cd frontend
npm run build
cd ..

pyinstaller --name "OpTrade" --windowed --icon "frontend/public/favicon.ico" --add-data "frontend/dist;frontend/dist" --add-data "frontend/public/favicon.ico;frontend/public/favicon.ico" --paths "backend" --collect-submodules "app" --collect-submodules "uvicorn" "backend/app/desktop/window.py"
```

See `AGENTS.md` for repo-specific gotchas an agent working in this codebase should know.
