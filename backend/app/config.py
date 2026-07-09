from pydantic_settings import BaseSettings
from pathlib import Path

# Project root: backend/app/config.py -> backend -> project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application configuration loaded from environment / .env file."""

    app_name: str = "OpTrade"
    app_version: str = "0.3.0"
    debug: bool = False

    # Database — absolute path under project root so it is consistent regardless of CWD
    database_url: str = f"sqlite:///{_PROJECT_ROOT / 'data' / 'optrade.db'}"

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # Frontend (for PyWebView)
    frontend_dev_url: str = "http://localhost:5173"
    frontend_dist_dir: str = ""

    # File paths
    data_dir: str = str(_PROJECT_ROOT / "data")

    model_config = {"env_prefix": "OPTRADE_", "env_file": ".env"}


settings = Settings()

# Ensure data directory exists
Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
