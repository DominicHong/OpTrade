# OpTrade — Desktop Options Trading & Risk Management System

FX Options trade management and risk analysis for Windows desktop, with future Web migration path.

## Tech Stack

- **Desktop Shell**: PyWebView
- **Frontend**: Vue 3 + TypeScript + Pinia + Vue Router
- **Backend**: FastAPI + SQLModel + SQLite
- **Pricing/Risk**: QuantLib-Python
- **Data Import**: openpyxl (Excel/CSV parsing)

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- (Optional) QuantLib C++ library for QuantLib-Python

### Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Start backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Desktop App

```bash
python -m backend.app.desktop.window
```

### One-Click Dev Startup

```bash
scripts\start_dev.bat
```

## API Documentation

Once running, visit http://127.0.0.1:8000/docs for interactive API docs (Swagger UI).

## Project Structure

```
backend/         — FastAPI backend
  app/
    models/      — SQLModel entities
    schemas/     — Pydantic request/response schemas
    routers/     — REST API endpoints
    services/    — Business logic (pricing, Greeks, import)
    utils/       — Helpers (column mapping, date parsing)
    desktop/     — PyWebView window launcher
  tests/         — pytest tests

frontend/        — Vue3 SPA
  src/
    api/         — Axios API wrappers
    pages/       — Page components
    components/  — Reusable components
    stores/      — Pinia stores
    types/       — TypeScript interfaces
```

## Features

- **Trade Management**: View, search, filter, and edit FX option trades
- **Excel Import**: COMSTAR CSV/Excel trade export pipeline with validation
- **Greeks Calculation**: Delta, Gamma, Vega, Theta, Rho via QuantLib
- **Scenario Analysis**: Spot shift, vol shift, time decay, 2D heatmap
- **Portfolio Analytics**: Aggregated risk metrics by portfolio
- **Dashboard**: Summary statistics, exposure breakdown

## Coding Constraints

1. Python: Native Type Hints only (`str | None`, `list[str]`) — no `typing` imports
2. Vue3: All components use `<script setup lang="ts">` syntax
3. QuantLib: ALL QuantLib code is isolated in `backend/app/services/`

## Build for Windows

### Prerequisites

- Install PyInstaller:
  ```cmd
  pip install pyinstaller
  ```

### One-Click Build

Run the build script:

```cmd
scripts\build_desktop.bat
```

### Manual Build

```cmd
cd frontend
npm run build
cd ..

pyinstaller --name "OpTrade" --windowed --icon "frontend/public/favicon.ico" --add-data "frontend/dist;frontend/dist" --add-data "frontend/public/favicon.ico;frontend/public/favicon.ico" --paths "backend" --collect-submodules "app" --collect-submodules "uvicorn" "backend/app/desktop/window.py"
```
