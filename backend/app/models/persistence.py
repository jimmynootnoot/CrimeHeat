from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PersistenceRecord(Base):
    """A chain of spatially-matched DBSCAN clusters recurring across periods."""

    __tablename__ = "persistence_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    municipality: Mapped[str] = mapped_column(String(100), index=True)
    barangay: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    crime_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    # temporary|intermittent|historical_persistent|active_persistent
    category: Mapped[str] = mapped_column(String(30), index=True)
    periods_present: Mapped[list] = mapped_column(JSON)  # list[int] years
    persistence_score: Mapped[float] = mapped_column(Float)  # periods_present / total_periods_analyzed
    total_periods_analyzed: Mapped[int] = mapped_column()
    centroid_lat: Mapped[float] = mapped_column(Float)
    centroid_lon: Mapped[float] = mapped_column(Float)
    # Total member incidents across every period the chain appeared in — the
    # magnitude behind the score, so a 100% chain of 8 incidents is not drawn
    # identically to a 100% chain of 200.
    incident_count: Mapped[int] = mapped_column(Integer, default=0)
    # Convex hull of those members: the area the hotspot actually covers,
    # rather than the single centroid the map used to reduce it to.
    extent_geojson: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
