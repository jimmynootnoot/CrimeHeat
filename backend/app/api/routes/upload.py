import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ONLY, ANALYST_OR_ADMIN, get_current_user, require_role
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
            "'Pigkawayan' is accepted and standardized to 'Pigcawayan'. Every "
            "standardization is reported in the import summary.",
            "Coordinates are validated against the six PPALMA municipality "
            "polygons; records outside the study area are rejected.",
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
    user: User = Depends(require_role(*ANALYST_OR_ADMIN)),
):
    if not file.filename or not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(400, f"Unsupported file type. Accepted: {', '.join(ALLOWED_EXTENSIONS)}")

    content = await file.read()

    settings = get_settings()
    max_bytes = int(settings.max_upload_size_mb * 1024 * 1024)
    if len(content) > max_bytes:
        raise HTTPException(400, f"File exceeds the {settings.max_upload_size_mb:.0f} MB upload limit.")

    try:
        df = parse_file(file.filename, content)
    except Exception as exc:
        raise HTTPException(400, f"Could not parse file: {exc}") from exc

    if df.empty:
        raise HTTPException(400, "The file contains no data rows.")

    columns = list(df.columns.astype(str))
    # pandas can't hold Python None inside a numeric (float64) column — it silently
    # reverts to NaN, which Postgres's JSON column then rejects. Round-tripping
    # through to_json() lets pandas do that NaN -> null conversion correctly.
    rows = json.loads(df.to_json(orient="records"))

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
    }


@router.post("/{batch_id}/validate")
def validate_batch(
    batch_id: int,
    body: MappingRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(*ANALYST_OR_ADMIN)),
):
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Import batch not found")

    known_municipalities = {m.name for m in db.query(Municipality).all()}
    valid_rows, issues, standardizations = validate_rows(
        batch.rows, body.mapping, known_municipalities
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
    user: User = Depends(require_role(*ADMIN_ONLY)),
):
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Import batch not found")
    if batch.status == "committed":
        raise HTTPException(400, "This batch has already been imported.")

    known_municipalities = {m.name for m in db.query(Municipality).all()}
    valid_rows, issues, standardizations = validate_rows(
        batch.rows, body.mapping, known_municipalities
    )
    if not valid_rows:
        raise HTTPException(400, "No valid rows to import.")

    settings = get_settings()
    # An import while the system is in synthetic mode is still tagged
    # 'synthetic'; real records must only be loaded with DATA_SOURCE=official,
    # so the two can never be conflated by an operator's mistake.
    source = "synthetic" if settings.data_source == "synthetic" else "official"
    inserted, skipped = commit_rows(db, valid_rows, source=source)

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
            "source": source,
            "standardized": len(standardizations),
        },
        request=request,
    )

    return {
        "imported_count": inserted,
        "skipped_existing": skipped,
        "source": source,
    }
