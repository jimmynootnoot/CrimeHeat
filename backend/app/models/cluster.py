from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DBSCANRun(Base):
    """One DBSCAN execution over a defined analytical scope.

    A run is scoped to a single temporal period. Multi-period analyses create
    one run per period, which is what allows clusters to be compared across
    periods later — cluster labels are only meaningful within a single run.
    """

    __tablename__ = "dbscan_runs"

    id: Mapped[int] = mapped_column(primary_key=True)

    # --- Scope ---
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    # "2016" | "2016-Q1" | "2016-01" — canonical period identifier.
    period_key: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    period_type: Mapped[str] = mapped_column(String(10), default="yearly")
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    crime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    municipality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id"), nullable=True, index=True)

    # --- Parameters ---
    eps_km: Mapped[float] = mapped_column(Float)
    min_samples: Mapped[int] = mapped_column(Integer)

    # --- Outcome summary ---
    total_incidents: Mapped[int] = mapped_column(Integer, default=0)
    cluster_count: Mapped[int] = mapped_column(Integer, default=0)
    clustered_count: Mapped[int] = mapped_column(Integer, default=0)
    core_count: Mapped[int] = mapped_column(Integer, default=0)
    border_count: Mapped[int] = mapped_column(Integer, default=0)
    noise_count: Mapped[int] = mapped_column(Integer, default=0)
    noise_percent: Mapped[float] = mapped_column(Float, default=0.0)
    # Non-fatal advisories raised during the run (too few records, all-noise,
    # single-cluster collapse, extreme parameters).
    warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Cluster(Base):
    """A single period-specific DBSCAN cluster.

    `cluster_label` is scikit-learn's label and is unique only within its run.
    Cross-period identity is established separately by the persistence matching
    service, never by comparing labels.

    `hull_geojson` is an approximate analytical extent (convex hull of member
    points). It is not an administrative or legal boundary and must be labeled
    as such wherever it is displayed.
    """

    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("dbscan_runs.id", ondelete="CASCADE"), index=True)
    cluster_label: Mapped[int] = mapped_column(Integer)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    period_key: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    crime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    municipality: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    point_count: Mapped[int] = mapped_column(Integer)
    core_count: Mapped[int] = mapped_column(Integer, default=0)
    border_count: Mapped[int] = mapped_column(Integer, default=0)

    centroid_lat: Mapped[float] = mapped_column(Float)
    centroid_lon: Mapped[float] = mapped_column(Float)
    centroid_geom = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    hull_geojson: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    hull_geom = mapped_column(Geometry(geometry_type="POLYGON", srid=4326), nullable=True)
    # [min_lon, min_lat, max_lon, max_lat]
    bbox: Mapped[list | None] = mapped_column(JSON, nullable=True)
    area_sq_km: Mapped[float | None] = mapped_column(Float, nullable=True)

    dominant_crime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    crime_type_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    barangays: Mapped[list | None] = mapped_column(JSON, nullable=True)
    first_incident_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_incident_date: Mapped[date | None] = mapped_column(Date, nullable=True)
