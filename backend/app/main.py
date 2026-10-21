from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, clusters, dashboard, incidents, municipalities, persistence, reports, upload
from app.core.config import get_settings

settings = get_settings()


def _frontend_origins(configured_origin: str) -> list[str]:
    """Accept equivalent loopback hostnames during local development."""
    origin = configured_origin.rstrip("/")
    parsed = urlsplit(origin)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        return [origin]

    port = f":{parsed.port}" if parsed.port else ""
    return [
        f"{parsed.scheme}://localhost{port}",
        f"{parsed.scheme}://127.0.0.1{port}",
        f"{parsed.scheme}://[::1]{port}",
    ]

app = FastAPI(
    title="PPALMA Crime Mapping Tool API",
    description="Spatio-temporal crime hotspot analysis over the official PNP incident dataset.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins(settings.frontend_origin),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(municipalities.router)
app.include_router(incidents.router)
app.include_router(upload.router)
app.include_router(clusters.router)
app.include_router(persistence.router)
app.include_router(reports.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"status": "ok", "data_source": settings.data_source}
