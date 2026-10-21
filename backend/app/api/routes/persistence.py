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

    # The most recent period in scope — used to report latest-period presence
    # explicitly (SOP 2) rather than leaving it implied by the category.
    latest_analyzed_year = max(
        (r.periods_present[-1] for r in records if r.periods_present), default=None
    )

    features = []
    for r in records:
        if category and category != "all" and r.category != category:
            continue
        properties = {
            "persistence_id": r.id,
            "municipality": r.municipality,
            "category": r.category,
            "periods_present": r.periods_present,
            # SOP 2 calls this the recurrence frequency.
            "period_count": len(r.periods_present),
            "recurrence_frequency": len(r.periods_present),
            "persistence_score": r.persistence_score,
            # The study states persistence score as a percentage.
            "persistence_score_percent": round(r.persistence_score * 100, 2),
            "total_periods_analyzed": r.total_periods_analyzed,
            "first_year": r.periods_present[0] if r.periods_present else None,
            "latest_year": r.periods_present[-1] if r.periods_present else None,
            "present_in_latest_period": (
                bool(r.periods_present) and r.periods_present[-1] == latest_analyzed_year
            ),
            "crime_type": r.crime_type,
            "incident_count": r.incident_count,
            "centroid": [r.centroid_lon, r.centroid_lat],
        }

        # A chain is emitted as its extent polygon plus a label point at the
        # centroid, mirroring how clusters are emitted. The map shades the area
        # the hotspot covers and puts one small marker on it, instead of
        # reducing the hotspot to a pin.
        if r.extent_geojson:
            features.append({
                "type": "Feature",
                "geometry": r.extent_geojson,
                "properties": {**properties, "feature_kind": "extent"},
            })
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r.centroid_lon, r.centroid_lat]},
            "properties": {**properties, "feature_kind": "label"},
        })

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
