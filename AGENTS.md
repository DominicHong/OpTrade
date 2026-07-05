# AGENTS.md

Compact guidance for OpenCode sessions working in this repo — captures only
what an agent would otherwise get wrong.

## Commands

```bash
# Dev (from repo root): starts backend :8000 + frontend :3000
scripts/start_dev.bat

# Backend dev server (run from repo root, NOT backend/)
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend dev (from frontend/) — port is 3000, not 5173
npm run dev

# Desktop (PyWebView) — from repo root
python -m backend.app.desktop.window

# Tests (MUST run from backend/)
cd backend
pytest                                              # all
pytest tests/test_greeks_service.py                 # one file
pytest tests/test_greeks_service.py::TestVanillaGreeks::test_atm_call_greeks  # one test

# Frontend typecheck + build (from frontend/) — no separate lint/typecheck script
npm run build      # runs vue-tsc --noEmit && vite build

# Windows desktop packaging (from repo root)
scripts/build_desktop.bat
```

## Critical gotchas

- **Two import contexts for the backend.** Tests run with `cwd=backend/` and import as `app.*` (`pyproject.toml` sets `pythonpath=["."]`; `conftest.py` does `from app.main import create_app`). The dev server / desktop run from the repo root and import as `backend.app.main:app`. Running pytest from the repo root will fail with `ModuleNotFoundError: app`. The `.vscode/settings.json` already pins `python.testing.cwd = ${workspaceFolder}/backend`.
- **Frontend dev port is 3000** (`frontend/vite.config.ts`). `start_dev.bat` echo text and `config.py` `frontend_dev_url` stalely say 5173. `desktop/window.py` correctly uses 3000. CORS in `main.py` allows `*`, so it works regardless — but use 3000 when pointing a browser at the dev server.
- **No lint / formatter / typecheck / CI is configured.** There is no ruff, flake8, mypy, eslint, or `.github/workflows`. Verification = `pytest` (backend) and `npm run build` (frontend). `npm run build` is the only typecheck — `vue-tsc --noEmit` runs before `vite build`.

## Architecture

- **Stack wiring**: PyWebView shell loads the Vue3 SPA (dev: Vite on `:3000`; prod: FastAPI serves `frontend/dist/` on `:8000`). The SPA calls FastAPI at `/api/v1/*` → services layer → SQLModel/SQLite + QuantLib.
- **Frontend is a standalone Vue3 SPA with NO PyWebView dependency** — it can be developed and built without the desktop shell. PyWebView just loads a URL.
- **Import pipeline**: COMSTAR CSV/Excel exports use **Chinese column headers**, mapped to model fields in `backend/app/utils/column_mapping.py` (`CSV_TO_OPTION_TRADE_FIELD`). `OptionTrade` (in `models/core.py`) carries the fields matching the COMSTAR export.
- **Option type extension pattern**: `OptionTrade` is the base table (`option_category` defaults to `fx_vanilla`); `BarrierOptionDetails` and `AsianOptionDetails` are 1:1 child tables with FK → `option_trades.id`. New option types add a new child table with the same pattern. All live in `models/core.py` (consolidated to avoid circular imports).
- **Key files**: `backend/app/models/core.py` (central entities), `backend/app/utils/column_mapping.py` (Chinese CSV → field mapping), `backend/app/models/__init__.py` (import order matters for table creation), `frontend/src/router/index.ts` (all routes, hash mode).

## Architecture constraints (enforced, not stylistic)

- **QuantLib is confined to `backend/app/services/` and `backend/app/utils/quantlib_helpers.py`.** Routers MUST NEVER import QuantLib directly.
- **Python: native type hints only** (`str | None`, `list[str]`, `dict[str, float]`). No `typing` imports.
- **Vue3: `<script setup lang="ts">` only.** Frontend uses `@` alias → `frontend/src/` (vite + tsconfig paths).
- **Router uses `createWebHashHistory`** (hash mode) for PyWebView compatibility. Do not switch to HTML5 history mode — file:// and PyWebView can't serve deep links.
- **Greeks use a fixed anchor date** `_ANCHOR_DATE = ql.Date(15, 6, 2020)` in `services/greeks_service.py` for reproducibility. Do not replace with `ql.Date.todaysDate()` — results are intentionally clock-independent.
- **Use English if possible for all documentation, comments, and code**

## API & frontend wiring

- All routers mount under `/api/v1/...` (e.g. `/api/v1/option-trades`). Health check at `/api/health`.
- Frontend axios baseURL defaults to `/api/v1` (relative). In dev, Vite proxies `/api` → `http://127.0.0.1:8000` (`vite.config.ts`). In prod, FastAPI serves the built SPA from `frontend/dist/` at `/` and the API at `/api/v1/*`. The frontend never hardcodes the backend host — do not add one.
- `main.py` serves `frontend/dist/` when present (or from `sys._MEIPASS/frontend/dist` when frozen by PyInstaller); otherwise returns a JSON root.

## Database

- SQLite at `data/optrade.db` (path is absolute relative to project root, so CWD-independent). `data/` is gitignored; the DB and `data/` dir are auto-created on startup.
- Tables auto-created via `SQLModel.metadata.create_all` in the FastAPI lifespan — no migration tool. Adding a model requires importing it in `backend/app/models/__init__.py` (import order matters for table creation; core models are consolidated in `core.py` to avoid circular imports).
- Tests use a **temp file-based SQLite**, not in-memory (see `conftest.py` comment — in-memory had connection-persistence issues). The `client` fixture overrides `get_session` and uses `create_app()`.

## Config & env

- `backend/app/config.py`: `pydantic_settings.BaseSettings` with `env_prefix="OPTRADE_"`, reads `.env` (gitignored). Relevant keys: `OPTRADE_DEBUG`, `OPTRADE_FRONTEND_URL` (overrides the URL PyWebView loads), `OPTRADE_DATABASE_URL`, `OPTRADE_HOST`, `OPTRADE_PORT`.

## PyInstaller / playwright

- `scripts/build_desktop.bat` builds `frontend/` first, then runs PyInstaller with `--exclude-module playwright`. Playwright + MS Edge are used only at runtime by `services/datasources/china_money_crawler.py` to auto-crawl chinamoney.com.cn. In packaged builds that auto-crawl is unavailable; manual XLSX upload (`ChinaMoneyCrawler.parse_xlsx`, openpyxl) still works via the `/api/v1/curves` upload endpoint.

## Domain reference

- `doc/option_rules.md` defines premium-calc formulas (`premium_type` × `premium_currency` matrix) and Greeks units/conventions (e.g. QuantLib gamma is per 1-unit spot move; Bloomberg gamma is per 1% — they differ by `100/spot`). Consult it before touching premium or Greeks math.

## Gitignore notes

- `data/` (DB + scratch) and `backend/tests/test_greeks_validation.py` (local dev scratch test) are gitignored — do not commit them.
