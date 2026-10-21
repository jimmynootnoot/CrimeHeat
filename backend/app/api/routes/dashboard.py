from fastapi import APIRouter, Depends
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.cluster import DBSCANRun
from app.models.incident import Incident
from app.models.municipality import Municipality
from app.models.persistence import PersistenceRecord
from app.services.clustering import run_dbscan

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db), _=Depends(get_current_user)):
    settings = get_settings()

    total = db.query(Incident).count()
    official = db.query(Incident).filter(Incident.source == "official").count()

    crime_type_breakdown = dict(
        db.query(Incident.crime_type, func.count(Incident.id)).group_by(Incident.crime_type).all()
    )
    municipality_breakdown = dict(
        db.query(Incident.municipality, func.count(Incident.id)).group_by(Incident.municipality).all()
    )
    year_breakdown = dict(
        db.query(func.extract("year", Incident.incident_date), func.count(Incident.id))
        .group_by(extract("year", Incident.incident_date))
        .all()
    )
    year_breakdown = {str(int(k)): v for k, v in year_breakdown.items()}

    persistence_category_breakdown = dict(
        db.query(PersistenceRecord.category, func.count(PersistenceRecord.id))
        .group_by(PersistenceRecord.category)
        .all()
    )
    active_persistent = persistence_category_breakdown.get("active_persistent", 0)

    # One whole-dataset DBSCAN pass (no year/crime_type/municipality filter) purely to
    # surface a headline noise ratio on the dashboard — not tied to any specific map view.
    noise_ratio = None
    if total > 0:
        whole_dataset = run_dbscan(
            db, eps_km=settings.dbscan_eps_km, min_samples=settings.dbscan_min_samples
        )
        noise_ratio = whole_dataset["metadata"]["noise_ratio"]

    latest_run_at = db.query(func.max(DBSCANRun.created_at)).scalar()
    latest_persistence_at = db.query(func.max(PersistenceRecord.created_at)).scalar()
    latest_analysis_candidates = [t for t in (latest_run_at, latest_persistence_at) if t is not None]
    latest_analysis_at = max(latest_analysis_candidates).isoformat() if latest_analysis_candidates else None

    return {
        "total_incidents": total,
        "official_incidents": official,
        "crime_type_breakdown": crime_type_breakdown,
        "municipality_breakdown": municipality_breakdown,
        "year_breakdown": year_breakdown,
        "municipality_count": db.query(Municipality).count(),
        "distinct_year_count": len(year_breakdown),
        "persistence_category_breakdown": persistence_category_breakdown,
        "active_persistent_hotspots": active_persistent,
        "noise_ratio": noise_ratio,
        "latest_analysis_at": latest_analysis_at,
    }
