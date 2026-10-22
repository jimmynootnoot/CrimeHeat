import json
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import PNP_PERSONNEL_OR_ADMIN, get_current_user, require_role
from app.core.config import get_settings
from app.core.taxonomy import CANONICAL_MUNICIPALITIES, INDEX_CRIME_TYPES
from app.db.session import get_db
from app.models.dataset import DatasetUpload
from app.models.import_batch import ImportBatch
from app.models.municipality import Municipality
from app.models.user import User
from app.services import audit_service
from app.services.import_service import (
    REQUIRED_FIELDS,
    TARGET_FIELDS,
    commit_rows,
    parse_file,
    suggest_mapping,
    validate_rows,
)

router = APIRouter(prefix="/api/upload", tags=["upload"])

ALLOWED_EXTENSIONS = (".csv", ".xlsx", ".xls")


TEMPLATE_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "templates" / "crime_import_template.csv"
)


class MappingRequest(BaseModel):
    mapping: dict[str, str]


@router.get("/template")
def download_template(_=Depends(get_current_user)):
    """Download the CSV import template with example rows."""
    if not TEMPLATE_PATH.exists():
        raise HTTPException(404, "Import template file is missing from the data directory.")
    return FileResponse(
        TEMPLATE_PATH,
        media_type="text/csv",
        filename="crime_import_template.csv",
    )


@router.get("/schema")
def import_schema(_=Depends(get_current_user)):
    """Describe what the importer expects, so the UI can document it without
    duplicating the rules that live in the taxonomy and import service."""
    return {
        "required_fields": sorted(REQUIRED_FIELDS),
        "optional_fields": [f for f in TARGET_FIELDS if f not in REQUIRED_FIELDS],
        "crime_types": INDEX_CRIME_TYPES,
        "municipalities": CANONICAL_MUNICIPALITIES,
        "accepted_extensions": list(ALLOWED_EXTENSIONS),
        "max_upload_size_mb": get_settings().max_upload_size_mb,
        "notes": [
            "Only the eight index crimes listed above are accepted; other offense "
            "types are rejected rather than grouped into an 'Other' category.",
            "Barangay spellings are resolved to their official PSGC name: "
            "'BRGY. BALABAK', 'Brgy Balabak' and 'Poblacion I' / 'Poblacion 1' "
            "all match. 'Pigkawayan' is standardized to 'Pigcawayan'.",
            "Latitude/longitude are optional. A row without usable coordinates "
            "is placed at its barangay's official centroid and labeled "
            "barangay-level precision; a row with no usable location at all is rejected.",
            "A missing barangay is recovered from the coordinate, and a missing "
            "reference number is assigned one, so rows are not lost to blank cells.",
            "Ambiguous numeric dates are read in the order the file itself proves "
            "(a value like 25/12 makes the whole column day-first). When nothing "
            "in the column settles the order, the affected rows are flagged rather "
            "than quietly assigned one reading.",
            "Worksheets (.xlsx/.xls) are read with their real date and time cells "
            "intact. A title block above the header row is skipped automatically, "
            "and tabs sharing the same columns (one per year, say) are combined; "
            "tabs with different columns are left out and named in the summary.",
            "Every correction the importer applies is listed in the import "
            "summary rather than applied silently.",
            "Do not include victim, suspect, or witness names, contact numbers, "
            "or exact residential addresses — the schema has no field for them.",
        ],
    }


def _split_issues(issues: list[dict]) -> tuple[list[dict], list[dict]]:
    rejected = [i for i in issues if i.get("severity") == "rejected"]
    warnings = [i for i in issues if i.get("severity") == "warning"]
    return rejected, warnings


@router.post("/preview")
async def preview_upload(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role(*PNP_PERSONNEL_OR_ADMIN)),
):
    if not file.filename or not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(400, f"Unsupported file type. Accepted: {', '.join(ALLOWED_EXTENSIONS)}")

    content = await file.read()

    settings = get_settings()
    max_bytes = int(settings.max_upload_size_mb * 1024 * 1024)
    if len(content) > max_bytes:
        raise HTTPException(400, f"File exceeds the {settings.max_upload_size_mb:.0f} MB upload limit.")

    try:
        df, parse_notes = parse_file(file.filename, content)
    except Exception as exc:
        raise HTTPException(400, f"Could not parse file: {exc}") from exc

    if df.empty:
        raise HTTPException(400, "The file contains no data rows.")

    columns = list(df.columns.astype(str))
    # pandas can't hold Python None inside a numeric (float64) column — it silently
    # reverts to NaN, which Postgres's JSON column then rejects. Round-tripping
    # through to_json() lets pandas do that NaN -> null conversion correctly.
    # date_format='iso' keeps any datetime cell readable instead of epoch millis.
    rows = json.loads(df.to_json(orient="records", date_format="iso"))

    batch = ImportBatch(
        filename=file.filename,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        status="previewed",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    audit_service.record(
        db,
        audit_service.DATASET_UPLOADED,
        user=user,
        entity_type="import_batch",
        entity_id=batch.id,
        details={"filename": file.filename, "row_count": len(rows), "columns": len(columns)},
        request=request,
    )

    return {
        "batch_id": batch.id,
        "columns": columns,
        "sample_rows": rows[:10],
        "suggested_mapping": suggest_mapping(columns),
        "row_count": len(rows),
        "notes": parse_notes,
    }


@router.post("/{batch_id}/validate")
def validate_batch(
    batch_id: int,
    body: MappingRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(*PNP_PERSONNEL_OR_ADMIN)),
):
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Import batch not found")

    known_municipalities = {m.name for m in db.query(Municipality).all()}
    valid_rows, issues, standardizations = validate_rows(
        batch.rows, body.mapping, known_municipalities, id_prefix=f"B{batch.id}"
    )
    rejected, warnings = _split_issues(issues)

    batch.column_mapping = body.mapping
    batch.valid_count = len(valid_rows)
    batch.error_count = len(rejected)
    batch.status = "validated"

    upload_record = DatasetUpload(
        import_batch_id=batch.id,
        filename=batch.filename,
        uploaded_by_id=user.id,
        total_rows=batch.row_count,
        valid_rows=len(valid_rows),
        warning_rows=len(warnings),
        rejected_rows=len(rejected),
        validation_report=issues[:2000],
        standardizations=standardizations[:2000],
        status="validated",
    )
    db.add(upload_record)
    db.commit()

    audit_service.record(
        db,
        audit_service.DATASET_VALIDATED,
        user=user,
        entity_type="import_batch",
        entity_id=batch.id,
        details={
            "valid": len(valid_rows),
            "warnings": len(warnings),
            "rejected": len(rejected),
            "standardized": len(standardizations),
        },
        request=request,
    )

    return {
        "valid_count": len(valid_rows),
        "warning_count": len(warnings),
        "error_count": len(rejected),
        # Counts per field, so a province-wide export whose out-of-area records
        # are rejected by design reads as one expected line rather than as
        # thousands of individual failures.
        "rejected_by_field": dict(Counter(i["field"] for i in rejected).most_common()),
        "standardized_by_field": dict(Counter(s["field"] for s in standardizations).most_common()),
        # Kept under the key the existing frontend reads; rejected rows first so
        # the operator sees blocking problems before advisories.
        "errors": (rejected + warnings)[:500],
        "standardizations": standardizations[:500],
    }


@router.post("/{batch_id}/commit")
def commit_batch(
    batch_id: int,
    body: MappingRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(*PNP_PERSONNEL_OR_ADMIN)),
):
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Import batch not found")
    if batch.status == "committed":
        raise HTTPException(400, "This batch has already been imported.")

    known_municipalities = {m.name for m in db.query(Municipality).all()}
    valid_rows, issues, standardizations = validate_rows(
        batch.rows, body.mapping, known_municipalities, id_prefix=f"B{batch.id}"
    )
    if not valid_rows:
        raise HTTPException(400, "No valid rows to import.")

    inserted, skipped = commit_rows(db, valid_rows, source="official")

    batch.status = "committed"
    db.commit()

    audit_service.record(
        db,
        audit_service.DATASET_IMPORTED,
        user=user,
        entity_type="import_batch",
        entity_id=batch.id,
        details={
            "imported": inserted,
            "skipped_existing": skipped,
            "source": "official",
            "standardized": len(standardizations),
        },
        request=request,
    )

    return {
        "imported_count": inserted,
        "skipped_existing": skipped,
        "source": "official",
    }
