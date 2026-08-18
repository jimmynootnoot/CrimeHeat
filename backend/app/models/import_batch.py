from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ImportBatch(Base):
    """Audit trail + staging area for the reusable CSV/Excel import module.

    Rows are parsed once at upload time and cached here as JSON so the
    column-mapping and validation steps can re-run cheaply without re-parsing
    the source file. This is the same table Stage 2 will use to import the
    official PNP dataset.
    """

    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    columns: Mapped[list] = mapped_column(JSON)
    rows: Mapped[list] = mapped_column(JSON)
    column_mapping: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer)
    valid_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="previewed")  # previewed|validated|committed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
