import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.incident import Incident

router = APIRouter(prefix="/api/reports", tags=["reports"])

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
    settings = get_settings()
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

    is_synthetic = settings.data_source == "synthetic"
    banner = (
        '<p style="background:#fbbf24;color:#451a03;padding:8px 12px;font-weight:600;">'
        "Development Mode — Synthetic Data Only. This report is for internal development/testing "
        "and must not be cited as an official PNP finding.</p>"
        if is_synthetic
        else ""
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
      {banner}
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
