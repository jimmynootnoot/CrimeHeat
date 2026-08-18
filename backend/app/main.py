from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, clusters, dashboard, incidents, municipalities, persistence, reports, upload
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="PPALMA Crime Mapping Tool API",
    description="Development API backed by synthetic data until the official PNP dataset is released.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
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
