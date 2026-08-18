from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.persistence import PersistenceRecord
from app.services.persistence_service import recompute_persistence

router = APIRouter(prefix="/api/persistence", tags=["persistence"])


@router.get("")
def get_persistence(
    municipality: Optional[str] = None,
    barangay: Optional[str] = None,
    crime_type: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    settings = get_settings()

    query = db.query(PersistenceRecord)
    if municipality:
        query = query.filter(PersistenceRecord.municipality == municipality)
    query.delete(synchronize_session=False)
    db.commit()

    records = recompute_persistence(
        db,
        eps_km=settings.dbscan_eps_km,
        min_samples=settings.dbscan_min_samples,
        match_distance_km=settings.persistence_match_distance_km,
        score_threshold=settings.persistence_score_threshold,
        municipality=municipality,
        barangay=barangay,
        crime_type=crime_type,
    )
    db.add_all(records)
    db.commit()

    features = []
    for r in records:
        if category and category != "all" and r.category != category:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [r.centroid_lon, r.centroid_lat]},
                "properties": {
                    "persistence_id": r.id,
                    "municipality": r.municipality,
                    "category": r.category,
                    "periods_present": r.periods_present,
                    "period_count": len(r.periods_present),
                    "persistence_score": r.persistence_score,
                    "total_periods_analyzed": r.total_periods_analyzed,
                    "first_year": r.periods_present[0] if r.periods_present else None,
                    "latest_year": r.periods_present[-1] if r.periods_present else None,
                    "crime_type": r.crime_type,
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "metadata": {
            "eps_km": settings.dbscan_eps_km,
            "min_samples": settings.dbscan_min_samples,
            "match_distance_km": settings.persistence_match_distance_km,
            "persistence_score_threshold": settings.persistence_score_threshold,
        },
        "features": features,
    }
