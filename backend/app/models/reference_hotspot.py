from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReferenceHotspot(Base):
    """An authorized reference polygon used as ground truth for evaluation.

    Precision, recall, and F1-score are supervised metrics: they require a
    reference classification to compare against. DBSCAN is unsupervised, so
    without these labels those metrics are undefined and the system must refuse
    to report them rather than invent a baseline.

    `label_source` records where the ground truth came from:
      - "synthetic_demo" : generated alongside the synthetic dataset. Results
                           derived from these are demonstration-only and must
                           never be presented as PNP validation.
      - "expert_validated" / "authorized_pnp" : supplied by an authorized party
                           once official data are in use.
    """

    __tablename__ = "reference_hotspots"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    municipality: Mapped[str] = mapped_column(String(100), index=True)
    label_source: Mapped[str] = mapped_column(String(30), index=True, default="synthetic_demo")
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id"), nullable=True, index=True)
    period_key: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    geom = mapped_column(Geometry(geometry_type="POLYGON", srid=4326))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
