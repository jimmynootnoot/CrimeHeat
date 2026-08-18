from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.incident import Incident
from app.models.municipality import Municipality
from app.models.persistence import PersistenceRecord

router = APIRouter(prefix="/api/municipalities", tags=["municipalities"])


@router.get("")
def list_municipalities(db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(Municipality).order_by(Municipality.name).all()
    return [{"id": m.id, "psgc_code": m.psgc_code, "name": m.name} for m in rows]


@router.get("/{name}/stats")
def municipality_stats(name: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    municipality = db.query(Municipality).filter(func.lower(Municipality.name) == name.lower()).first()
    if not municipality:
        raise HTTPException(404, f"Unknown municipality: {name}")

    total = db.query(Incident).filter(Incident.municipality_id == municipality.id).count()

    by_crime_type = dict(
        db.query(Incident.crime_type, func.count(Incident.id))
        .filter(Incident.municipality_id == municipality.id)
        .group_by(Incident.crime_type)
        .all()
    )

    by_year = dict(
        db.query(func.extract("year", Incident.incident_date), func.count(Incident.id))
        .filter(Incident.municipality_id == municipality.id)
        .group_by(func.extract("year", Incident.incident_date))
        .all()
    )
    by_year = {str(int(k)): v for k, v in by_year.items()}

    active_persistent = (
        db.query(PersistenceRecord)
        .filter(
            func.lower(PersistenceRecord.municipality) == name.lower(),
            PersistenceRecord.category == "persistent",
        )
        .count()
    )

    return {
        "municipality_id": municipality.id,
        "name": municipality.name,
        "total_incidents": total,
        "incidents_by_crime_type": by_crime_type,
        "incidents_by_year": by_year,
        "active_persistent_clusters": active_persistent,
    }
