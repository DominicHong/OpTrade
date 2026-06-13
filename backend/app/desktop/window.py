"""
PyWebView desktop window launcher.

Launches the FastAPI backend and opens the frontend in a native window.
For future Web migration: replace this file with a standard HTTP server deployment.
"""

import os
import sys
import threading
import time
from pathlib import Path

import uvicorn
import webview

# Ensure the backend directory is on sys.path so that `app` package is importable
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent.parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# Explicitly import app.main so PyInstaller static analysis can detect it
# (uvicorn.run() uses string-based dynamic import which PyInstaller misses)
import app.main  # noqa: F401

# Path to the application icon (used for taskbar / window icon on Windows)
_ICON_PATH = str(Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "public" / "favicon.ico")


def run_backend(host: str, port: int) -> None:
    """Start the FastAPI backend server in a background thread."""
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level="info",
    )


def get_frontend_url() -> str:
    """Determine the frontend URL based on environment."""
    dev_url = os.environ.get("OPTRADE_FRONTEND_URL", "")
    if dev_url:
        return dev_url

    # Production mode: if frontend has been built, FastAPI serves it
    import sys
    if hasattr(sys, '_MEIPASS'):
        dist_dir = Path(sys._MEIPASS) / "frontend" / "dist"
    else:
        dist_dir = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"
    if dist_dir.is_dir():
        return f"http://localhost:8000"

    # Dev mode: Vite dev server
    return "http://localhost:3000"


def main() -> None:
    """Launch the desktop application."""
    from app.config import settings

    host = settings.host
    port = settings.port

    # Start FastAPI backend in a background thread
    backend_thread = threading.Thread(
        target=run_backend,
        args=(host, port),
        daemon=True,
    )
    backend_thread.start()

    # Wait for backend to be ready before opening the window
    import urllib.request
    for _ in range(30):  # up to 15 seconds
        try:
            urllib.request.urlopen(f"http://{host}:{port}/api/health")
            break
        except Exception:
            time.sleep(0.5)

    # Determine frontend URL
    frontend_url = get_frontend_url()

    # Create and show PyWebView window
    window = webview.create_window(
        title=f"{settings.app_name} v{settings.app_version}",
        url=frontend_url,
        width=1400,
        height=900,
        min_size=(1024, 768),
        resizable=True,
        fullscreen=False,
    )

    webview.start(
        debug=settings.debug,
        icon=_ICON_PATH,
    )


if __name__ == "__main__":
    main()
