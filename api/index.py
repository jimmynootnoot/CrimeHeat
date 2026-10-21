"""Vercel entry point for the FastAPI backend."""

from pathlib import Path
import sys

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402,F401


FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"

if FRONTEND_INDEX.is_file():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{frontend_path:path}", include_in_schema=False)
    async def serve_frontend(frontend_path: str):
        """Serve built files when present and otherwise return the SPA shell."""
        candidate = (FRONTEND_DIST / frontend_path).resolve()
        if FRONTEND_DIST.resolve() in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_INDEX)
