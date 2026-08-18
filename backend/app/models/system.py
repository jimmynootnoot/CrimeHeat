from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SystemSetting(Base):
    """A single configurable analytical or presentation parameter.

    Settings are stored as typed key/value rows rather than a wide table so a
    new parameter can be added without a migration. Environment variables
    provide the boot defaults; a row here overrides them at runtime. Every
    change is written to the audit log, since analytical parameters directly
    affect reported findings.
    """

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(String(20), default="string")  # string|float|int|bool|json
    category: Mapped[str] = mapped_column(String(50), default="general", index=True)
    label: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuditLog(Base):
    """Append-only record of consequential actions.

    Covers authentication, dataset changes, analytical runs, parameter changes,
    and report generation. Deliberately stores no request bodies — an incident
    payload could contain free text, and the system's privacy rules forbid
    persisting anything that might carry personal information into a log.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Non-sensitive structured context only (counts, parameters, IDs).
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="success", index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class GeneratedReport(Base):
    """Metadata for a generated analytical report.

    The filter set, analytical parameters, and dataset source in effect at
    generation time are captured so a report remains reproducible and its
    provenance stays auditable after settings change.
    """

    __tablename__ = "generated_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    report_type: Mapped[str] = mapped_column(String(50), default="analytical", index=True)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id"), nullable=True)
    dataset_source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    dbscan_run_id: Mapped[int | None] = mapped_column(ForeignKey("dbscan_runs.id"), nullable=True)
    persistence_run_id: Mapped[int | None] = mapped_column(ForeignKey("persistence_runs.id"), nullable=True)

    filters_applied: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parameters_used: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    incident_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    generated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
