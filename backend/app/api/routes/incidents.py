from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import extract, func, or_
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ONLY, get_current_user, require_role
from app.db.session import get_db
from app.models.barangay import Barangay
from app.models.incident import Incident
from app.models.user import User
from app.services import audit_service
from app.services.locality import barangay_centroid

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
            # "year_only" means the source gave no incident date: the day above
            # is a placeholder and must not be displayed as an observed date.
            "date_precision": r.date_precision,
            "incident_time": r.incident_time.isoformat() if r.incident_time else None,
            "municipality": r.municipality,
            "barangay": r.barangay,
            "general_location": r.general_location,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "coordinate_precision": r.coordinate_precision,
            "source": r.source,
        }
        for r in rows
    ]
    return {"items": items, "total": total}


@router.get("/summary")
def incident_summary(
    municipality: Optional[str] = None,
    barangay: Optional[str] = None,
    crime_type: Optional[str] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """Map counts and incident extent for the selected scope, without a DBSCAN run."""
    query = db.query(Incident.municipality, func.count(Incident.id))
    if municipality:
        query = query.filter(Incident.municipality == municipality)
    if barangay:
        query = query.filter(Incident.barangay == barangay)
    if crime_type:
        query = query.filter(Incident.crime_type == crime_type)
    if year:
        query = query.filter(extract("year", Incident.incident_date) == year)
    counts = dict(query.group_by(Incident.municipality).all())

    extent_query = db.query(
        func.min(Incident.longitude),
        func.min(Incident.latitude),
        func.max(Incident.longitude),
        func.max(Incident.latitude),
    )
    if municipality:
        extent_query = extent_query.filter(Incident.municipality == municipality)
    if barangay:
        extent_query = extent_query.filter(Incident.barangay == barangay)
    if crime_type:
        extent_query = extent_query.filter(Incident.crime_type == crime_type)
    if year:
        extent_query = extent_query.filter(extract("year", Incident.incident_date) == year)
    min_lon, min_lat, max_lon, max_lat = extent_query.one()
    bounds = None if min_lon is None else [min_lon, min_lat, max_lon, max_lat]
    focus = barangay_centroid(municipality, barangay) if municipality and barangay else None

    return {
        "municipality_breakdown": counts,
        "total_incidents": sum(counts.values()),
        "bounds": bounds,
        "focus": list(focus) if focus else None,
    }


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
        db.query(Barangay.name)
        .filter(Barangay.municipality == municipality)
        .order_by(Barangay.name)
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
