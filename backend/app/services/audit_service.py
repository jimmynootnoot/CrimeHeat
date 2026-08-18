"""Audit logging for consequential actions.

Privacy constraint: this writes structured, non-sensitive context only —
counts, parameters, entity identifiers. Request bodies are never logged. An
incident payload can contain free-text location or note fields, and persisting
those into a log would create a second, unreviewed copy of data the system is
otherwise careful to keep anonymized.

Logging must never break the action it is recording. `record()` swallows its
own failures and rolls back only its own write, so an audit-table problem
cannot take down a working endpoint.
"""
import logging

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.system import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)

# Action vocabulary — kept as constants so filters in the Audit Logs screen can
# rely on stable values rather than free-typed strings.
LOGIN_SUCCESS = "login.success"
LOGIN_FAILED = "login.failed"
LOGOUT = "logout"
USER_CREATED = "user.created"
USER_UPDATED = "user.updated"
USER_DELETED = "user.deleted"
DATASET_UPLOADED = "dataset.uploaded"
DATASET_VALIDATED = "dataset.validated"
DATASET_IMPORTED = "dataset.imported"
DATASET_DELETED = "dataset.deleted"
INCIDENT_DELETED = "incident.deleted"
DBSCAN_RUN = "analysis.dbscan"
PERSISTENCE_RUN = "analysis.persistence"
EVALUATION_RUN = "analysis.evaluation"
SETTINGS_CHANGED = "settings.changed"
REPORT_GENERATED = "report.generated"


def client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def record(
    db: Session,
    action: str,
    *,
    user: User | None = None,
    user_email: str | None = None,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    details: dict | None = None,
    status: str = "success",
    request: Request | None = None,
    commit: bool = True,
) -> None:
    """Append one audit entry.

    Set `commit=False` when the caller owns the surrounding transaction and
    will commit the log alongside its own changes.
    """
    try:
        entry = AuditLog(
            user_id=user.id if user else None,
            user_email=user.email if user else user_email,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details,
            status=status,
            ip_address=client_ip(request),
        )
        db.add(entry)
        if commit:
            db.commit()
    except Exception:
        # Never let auditing break the operation being audited.
        logger.exception("Failed to write audit log entry for action=%s", action)
        if commit:
            try:
                db.rollback()
            except Exception:
                logger.exception("Audit log rollback also failed")
