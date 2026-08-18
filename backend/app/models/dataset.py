from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Dataset(Base):
    """A named, versioned collection of incident records.

    Incidents belong to a dataset so synthetic and official records can coexist
    in the database while remaining strictly separable in every query, chart,
    and report. Mixing the two in a published finding is prohibited by the
    study's academic rules, so `source` is recorded here as well as per-incident.
    """

    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # synthetic | official | geocoded | generalized | manually_verified
    source: Mapped[str] = mapped_column(String(30), index=True, default="synthetic")
    version: Mapped[str] = mapped_column(String(50), default="1.0")
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DatasetUpload(Base):
    """One upload attempt against a dataset, with its validation outcome.

    Retains the per-upload counts (valid / warning / rejected) and the full
    validation report so the Dataset Management screen can show upload history
    and re-export rejected rows without re-running validation.
    """

    __tablename__ = "dataset_uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id"), nullable=True, index=True)
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    warning_rows: Mapped[int] = mapped_column(Integer, default=0)
    rejected_rows: Mapped[int] = mapped_column(Integer, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, default=0)

    # Full per-row validation report: [{row, field, severity, message, ...}]
    validation_report: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Standardizations applied (e.g. "Pigkawayan" -> "Pigcawayan"), surfaced
    # in the import summary rather than applied silently.
    standardizations: Mapped[list | None] = mapped_column(JSON, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
