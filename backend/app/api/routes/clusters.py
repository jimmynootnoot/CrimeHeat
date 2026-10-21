from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.services.clustering import run_dbscan

router = APIRouter(prefix="/api/clusters", tags=["clusters"])


@router.get("")
def get_clusters(
    year: Optional[int] = None,
    crime_type: Optional[str] = None,
    municipality: Optional[str] = None,
    barangay: Optional[str] = None,
    eps_km: Optional[float] = None,
    min_samples: Optional[int] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    settings = get_settings()
    return run_dbscan(
        db,
        year=year,
        crime_type=crime_type,
        municipality=municipality,
        barangay=barangay,
        eps_km=eps_km or settings.dbscan_eps_km,
        min_samples=min_samples or settings.dbscan_min_samples,
    )
