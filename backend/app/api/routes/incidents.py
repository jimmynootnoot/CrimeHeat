from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import extract, func, or_
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ONLY, get_current_user, require_role
from app.db.session import get_db
from app.models.incident import Incident
from app.models.user import User
from app.services import audit_service

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("")
def list_incidents(
    municipality: Optional[str] = None,
    barangay: Optional[str] = None,
    crime_type: Optional[str] = None,
    year: Optional[int] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    query = db.query(Incident)
    if municipality:
        query = query.filter(Incident.municipality == municipality)
    if barangay:
        query = query.filter(Incident.barangay == barangay)
    if crime_type:
        query = query.filter(Incident.crime_type == crime_type)
    if year:
        query = query.filter(extract("year", Incident.incident_date) == year)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Incident.incident_id.ilike(like),
                Incident.barangay.ilike(like),
                Incident.general_location.ilike(like),
            )
        )

    total = query.count()
    page_size = min(page_size, 2000)
    rows = (
        query.order_by(Incident.incident_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        {
            "id": r.id,
            "incident_id": r.incident_id,
            "crime_type": r.crime_type,
            "incident_date": r.incident_date.isoformat(),
            "incident_time": r.incident_time.isoformat() if r.incident_time else None,
            "municipality": r.municipality,
            "barangay": r.barangay,
            "general_location": r.general_location,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "source": r.source,
        }
        for r in rows
    ]
    return {"items": items, "total": total}


@router.get("/years")
def list_years(db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = (
        db.query(extract("year", Incident.incident_date))
        .distinct()
        .order_by(extract("year", Incident.incident_date))
        .all()
    )
    return [int(r[0]) for r in rows]


@router.get("/barangays")
def list_barangays(municipality: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = (
        db.query(Incident.barangay)
        .filter(Incident.municipality == municipality)
        .distinct()
        .order_by(Incident.barangay)
        .all()
    )
    return [r[0] for r in rows]


@router.delete("/{incident_id}", status_code=204)
def delete_incident(
    incident_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(*ADMIN_ONLY)),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(404, "Incident not found")

    reference = incident.incident_id
    db.delete(incident)
    db.commit()
    audit_service.record(
        db,
        audit_service.INCIDENT_DELETED,
        user=user,
        entity_type="incident",
        entity_id=reference,
        request=request,
    )
