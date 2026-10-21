import csv
import io
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.incident import Incident
from app.services.evaluation_report import build_evaluation_workbook
from app.services.temporal_split_evaluation import run_temporal_split_evaluation

router = APIRouter(prefix="/api/reports", tags=["reports"])


class EvaluationReportInput(BaseModel):
    predictions_csv: str = Field(min_length=1, max_length=5_000_000)
    reference_csv: str = Field(min_length=1, max_length=5_000_000)
    functional_tests_csv: str = Field(min_length=1, max_length=5_000_000)
    reference_source: str
    validated_by: str = Field(min_length=1, max_length=500)
    scope: str = Field(min_length=1, max_length=1000)


@router.post('/evaluation')
def export_evaluation(payload: EvaluationReportInput, _=Depends(get_current_user)):
    try:
        content = build_evaluation_workbook(
            payload.predictions_csv, payload.reference_csv, payload.functional_tests_csv,
            payload.reference_source, payload.validated_by, payload.scope,
        )
    except (ValueError, csv.Error) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return StreamingResponse(
        iter([content.getvalue()]),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=ppalma_evaluation_report.xlsx'},
    )


class TemporalSplitInput(BaseModel):
    cutoff_date: date
    source: str = Field(default='official', pattern='^(official|geocoded|generalized|manually_verified)$')
    municipality: Optional[str] = None
    crime_type: Optional[str] = None
    eps_km: float = Field(default=1.0, gt=0, le=50)
    min_samples: int = Field(default=4, ge=2, le=50)
    cell_km: float = Field(default=1.0, gt=0, le=50)


@router.post('/evaluation/temporal-split')
def evaluation_temporal_split(
    payload: TemporalSplitInput, db: Session = Depends(get_db), _=Depends(get_current_user),
):
    """Algorithmic precision/recall/F1 via a temporal train/test split.

    Uses only incident-level data already covered by a PNP data request:
    hotspots are detected from incidents before the cutoff date, and scored
    against whether incidents actually occurred in the same grid cells on or
    after that date. No externally supplied reference labels are required.
    """
    try:
        result = run_temporal_split_evaluation(
            db, payload.cutoff_date, payload.source,
            municipality=payload.municipality, crime_type=payload.crime_type,
            eps_km=payload.eps_km, min_samples=payload.min_samples, cell_km=payload.cell_km,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


FIELDNAMES = [
    "incident_id",
    "crime_type",
    "incident_date",
    "incident_time",
    "municipality",
    "barangay",
    "general_location",
    "latitude",
    "longitude",
    "source",
]


def _filtered_incidents(
    db: Session,
    municipality: Optional[str],
    crime_type: Optional[str],
    year: Optional[int],
):
    query = db.query(Incident)
    if municipality:
        query = query.filter(Incident.municipality == municipality)
    if crime_type:
        query = query.filter(Incident.crime_type == crime_type)
    if year:
        query = query.filter(extract("year", Incident.incident_date) == year)
    return query.order_by(Incident.incident_date).all()


@router.get("")
def generate_report(
    format: str = Query("csv", pattern="^(csv|html)$"),
    municipality: Optional[str] = None,
    crime_type: Optional[str] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    rows = _filtered_incidents(db, municipality, crime_type, year)

    if format == "csv":
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=FIELDNAMES)
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    "incident_id": r.incident_id,
                    "crime_type": r.crime_type,
                    "incident_date": r.incident_date.isoformat(),
                    "incident_time": r.incident_time.isoformat() if r.incident_time else "",
                    "municipality": r.municipality,
                    "barangay": r.barangay,
                    "general_location": r.general_location or "",
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                    "source": r.source,
                }
            )
        buffer.seek(0)
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=ppalma_incident_report.csv"},
        )

    filter_summary = ", ".join(
        f"{k}={v}" for k, v in {"municipality": municipality, "crime_type": crime_type, "year": year}.items() if v
    ) or "All records"

    rows_html = "".join(
        f"<tr><td>{r.incident_id}</td><td>{r.crime_type}</td><td>{r.incident_date}</td>"
        f"<td>{r.municipality}</td><td>{r.barangay}</td><td>{r.source}</td></tr>"
        for r in rows
    )

    html = f"""
    <html>
    <head><title>PPALMA Crime Report</title></head>
    <body style="font-family: sans-serif; padding: 24px;">
      <h1>PPALMA Crime Incident Report</h1>
      <p>Generated {datetime.now().isoformat(timespec='seconds')} — Filters: {filter_summary} — {len(rows)} records</p>
      <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
        <thead><tr><th>Incident ID</th><th>Crime type</th><th>Date</th><th>Municipality</th><th>Barangay</th><th>Source</th></tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
