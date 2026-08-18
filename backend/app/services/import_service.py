"""Reusable CSV/Excel import module.

Deliberately generic: parse -> suggest column mapping -> validate -> commit.
It is exercised against synthetic CSVs today and is the same code path the
official PNP dataset will travel once its columns are known. Only the mapping
supplied at import time changes, not this module.

Validation outcomes follow the specification's three categories:

  valid    the row imports cleanly
  warning  the row imports, but something is worth the operator's attention
           (missing barangay, missing time, generalized coordinates)
  rejected the row cannot be imported without corrupting the analysis

Standardizations (for example "Pigkawayan" -> "Pigcawayan", or "Physical
Injuries" -> "Physical Injury") are applied but never silently: every one is
recorded and returned so the import summary can show exactly what changed.
"""
import io
from datetime import date, datetime

import pandas as pd
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy.orm import Session

from app.core.taxonomy import (
    CRIMES_AGAINST_PERSONS,
    INDEX_CRIME_TYPES,
    normalize_crime_type,
    normalize_municipality,
)
from app.models.incident import Incident
from app.models.municipality import Municipality

KNOWN_CRIME_TYPES = set(INDEX_CRIME_TYPES)

TARGET_FIELDS = [
    "incident_id",
    "crime_type",
    "incident_date",
    "incident_time",
    "municipality",
    "barangay",
    "general_location",
    "latitude",
    "longitude",
    "coordinate_source",
    "coordinate_precision",
    "reporting_station",
    "case_status_generalized",
    "offense_code",
    "notes_non_sensitive",
]

REQUIRED_FIELDS = {
    "incident_id",
    "crime_type",
    "incident_date",
    "municipality",
    "latitude",
    "longitude",
}

# Inbound header variants the mapping suggester recognizes automatically.
COLUMN_SYNONYMS: dict[str, list[str]] = {
    "incident_id": ["incident_id", "id", "case_id", "case_number", "blotter_no", "entry_no"],
    "crime_type": ["crime_type", "crime", "offense", "offense_type", "incident_type", "crime_category"],
    "incident_date": ["incident_date", "date", "date_committed", "date_of_incident", "date_reported"],
    "incident_time": ["incident_time", "time", "time_committed", "time_of_incident"],
    "municipality": ["municipality", "city_municipality", "citymun", "lgu", "town"],
    "barangay": ["barangay", "brgy", "barangay_name"],
    "general_location": ["general_location", "location", "location_description", "place", "address_general"],
    "latitude": ["latitude", "lat", "y", "ycoord", "y_coordinate"],
    "longitude": ["longitude", "lon", "lng", "x", "xcoord", "x_coordinate"],
    "coordinate_source": ["coordinate_source", "coord_source", "geocode_source"],
    "coordinate_precision": ["coordinate_precision", "coord_precision", "precision"],
    "reporting_station": ["reporting_station", "station", "police_station", "unit"],
    "case_status_generalized": ["case_status_generalized", "case_status", "status", "disposition"],
    "offense_code": ["offense_code", "code", "ra_number"],
    "notes_non_sensitive": ["notes_non_sensitive", "notes", "remarks"],
}

# Reasonable envelope around the PPALMA study area. Coordinates outside this
# are almost certainly transposed or mis-entered; point-in-polygon still runs
# separately and is the authoritative check.
STUDY_AREA_BOUNDS = {"min_lat": 6.4, "max_lat": 7.9, "min_lon": 124.0, "max_lon": 125.2}

MIN_YEAR = 2000
MAX_YEAR = date.today().year + 1


def parse_file(filename: str, content: bytes) -> pd.DataFrame:
    if filename.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(content))
    return pd.read_csv(io.BytesIO(content))


def suggest_mapping(columns: list[str]) -> dict[str, str]:
    """Best-effort automatic column mapping; the operator can always override."""
    normalized = {c.strip().lower().replace(" ", "_").replace("-", "_"): c for c in columns}
    mapping: dict[str, str] = {}
    for field, synonyms in COLUMN_SYNONYMS.items():
        for candidate in synonyms:
            if candidate in normalized:
                mapping[field] = normalized[candidate]
                break
    return mapping


def _clean(raw):
    """Normalize pandas' empty representations to None."""
    if raw is None:
        return None
    if isinstance(raw, float) and raw != raw:  # NaN
        return None
    if isinstance(raw, str):
        stripped = raw.strip()
        return stripped or None
    return raw


def validate_rows(
    rows: list[dict], mapping: dict[str, str], known_municipalities: set[str]
) -> tuple[list[dict], list[dict], list[dict]]:
    """Return (valid_rows, issues, standardizations).

    `issues` entries carry a `severity` of "warning" or "rejected"; a row is
    dropped only for a "rejected" issue.
    """
    valid_rows: list[dict] = []
    issues: list[dict] = []
    standardizations: list[dict] = []
    seen_incident_ids: dict[str, int] = {}

    def reject(row_num: int, field: str, message: str) -> None:
        issues.append({"row": row_num, "field": field, "severity": "rejected", "message": message})

    def warn(row_num: int, field: str, message: str) -> None:
        issues.append({"row": row_num, "field": field, "severity": "warning", "message": message})

    for idx, row in enumerate(rows):
        row_num = idx + 1
        parsed: dict = {}
        row_ok = True

        for field in TARGET_FIELDS:
            source_col = mapping.get(field)
            raw = _clean(row.get(source_col)) if source_col else None

            if raw is None:
                if field in REQUIRED_FIELDS:
                    reject(row_num, field, "Required field is missing")
                    row_ok = False
                elif field == "barangay":
                    warn(row_num, field, "Barangay is missing — imported without barangay detail")
                elif field == "incident_time":
                    warn(row_num, field, "Incident time is missing — date-only analysis for this row")
                parsed[field] = None
                continue

            if field == "incident_date":
                try:
                    parsed_date = pd.to_datetime(raw, dayfirst=False).date()
                except Exception:
                    reject(row_num, field, f"Unparseable date: {raw}")
                    row_ok = False
                    continue
                if not (MIN_YEAR <= parsed_date.year <= MAX_YEAR):
                    reject(
                        row_num,
                        field,
                        f"Date {parsed_date.isoformat()} falls outside the plausible range "
                        f"{MIN_YEAR}-{MAX_YEAR}",
                    )
                    row_ok = False
                    continue
                parsed[field] = parsed_date.isoformat()
                continue

            if field == "incident_time":
                try:
                    parsed[field] = pd.to_datetime(str(raw)).time().strftime("%H:%M")
                except Exception:
                    warn(row_num, field, f"Unreadable time '{raw}' — imported without a time")
                    parsed[field] = None
                continue

            if field in ("latitude", "longitude"):
                try:
                    parsed[field] = float(raw)
                except (TypeError, ValueError):
                    reject(row_num, field, f"Not a number: {raw}")
                    row_ok = False
                continue

            if field == "municipality":
                canonical, changed = normalize_municipality(raw)
                if canonical is None:
                    reject(
                        row_num,
                        field,
                        f"'{raw}' is not one of the six PPALMA municipalities "
                        f"({', '.join(sorted(known_municipalities))})",
                    )
                    row_ok = False
                    continue
                if changed:
                    standardizations.append(
                        {"row": row_num, "field": field, "from": str(raw), "to": canonical}
                    )
                parsed[field] = canonical
                continue

            if field == "crime_type":
                canonical, changed = normalize_crime_type(raw)
                if canonical is None:
                    reject(
                        row_num,
                        field,
                        f"'{raw}' is not one of the eight index crimes analyzed by this study "
                        f"({', '.join(INDEX_CRIME_TYPES)})",
                    )
                    row_ok = False
                    continue
                if changed:
                    standardizations.append(
                        {"row": row_num, "field": field, "from": str(raw), "to": canonical}
                    )
                parsed[field] = canonical
                continue

            parsed[field] = raw

        if not row_ok:
            continue

        lat, lon = parsed.get("latitude"), parsed.get("longitude")
        if lat is not None and not (-90 <= lat <= 90):
            reject(row_num, "latitude", f"Out of valid range: {lat}")
            row_ok = False
        if lon is not None and not (-180 <= lon <= 180):
            reject(row_num, "longitude", f"Out of valid range: {lon}")
            row_ok = False

        if row_ok and lat is not None and lon is not None:
            outside = not (
                STUDY_AREA_BOUNDS["min_lat"] <= lat <= STUDY_AREA_BOUNDS["max_lat"]
                and STUDY_AREA_BOUNDS["min_lon"] <= lon <= STUDY_AREA_BOUNDS["max_lon"]
            )
            if outside:
                reject(
                    row_num,
                    "latitude/longitude",
                    f"Coordinate ({lat}, {lon}) falls well outside the PPALMA study area — "
                    f"check for transposed latitude/longitude values",
                )
                row_ok = False

        if row_ok:
            precision = (parsed.get("coordinate_precision") or "").lower()
            if precision in ("barangay_level", "generalized", "approximate"):
                warn(
                    row_num,
                    "coordinate_precision",
                    f"Coordinate is '{precision}' — cluster placement for this row is approximate",
                )

        if row_ok:
            incident_id = str(parsed.get("incident_id"))
            if incident_id in seen_incident_ids:
                reject(
                    row_num,
                    "incident_id",
                    f"Duplicate incident_id within this file (first seen at row "
                    f"{seen_incident_ids[incident_id]})",
                )
                row_ok = False
            else:
                seen_incident_ids[incident_id] = row_num

        if row_ok:
            valid_rows.append(parsed)

    return valid_rows, issues, standardizations


def commit_rows(
    db: Session,
    valid_rows: list[dict],
    source: str = "official",
    dataset_id: int | None = None,
) -> tuple[int, int]:
    """Insert validated rows. Returns (inserted, skipped_existing)."""
    municipalities = {m.name: m.id for m in db.query(Municipality).all()}
    inserted = 0
    skipped = 0

    for row in valid_rows:
        if db.query(Incident).filter(Incident.incident_id == row["incident_id"]).first():
            skipped += 1
            continue

        incident_time = None
        if row.get("incident_time"):
            incident_time = datetime.strptime(row["incident_time"], "%H:%M").time()

        crime_type = row["crime_type"]
        point = Point(row["longitude"], row["latitude"])
        db.add(
            Incident(
                incident_id=row["incident_id"],
                crime_type=crime_type,
                incident_date=datetime.strptime(row["incident_date"], "%Y-%m-%d").date(),
                incident_time=incident_time,
                municipality_id=municipalities[row["municipality"]],
                municipality=row["municipality"],
                barangay=row.get("barangay") or "Unspecified",
                general_location=row.get("general_location"),
                latitude=row["latitude"],
                longitude=row["longitude"],
                geom=from_shape(point, srid=4326),
                crime_classification=(
                    "Crime Against Person"
                    if crime_type in CRIMES_AGAINST_PERSONS
                    else "Crime Against Property"
                ),
                index_nonindex_flag="index",
                coordinate_source=row.get("coordinate_source"),
                coordinate_precision=row.get("coordinate_precision"),
                reporting_station=row.get("reporting_station"),
                case_status_generalized=row.get("case_status_generalized"),
                offense_code=row.get("offense_code"),
                notes_non_sensitive=row.get("notes_non_sensitive"),
                dataset_id=dataset_id,
                source=source,
            )
        )
        inserted += 1

    db.commit()
    return inserted, skipped
