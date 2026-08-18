from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PersistenceRun(Base):
    """One cross-period cluster-matching execution.

    Every parameter that influenced the result is stored on the run, so any
    figure shown in the interface or a generated report can be traced back to
    the exact configuration that produced it.
    """

    __tablename__ = "persistence_runs"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Analytical scope
    period_type: Mapped[str] = mapped_column(String(10), default="yearly")  # yearly|quarterly|monthly
    period_start: Mapped[str | None] = mapped_column(String(20), nullable=True)
    period_end: Mapped[str | None] = mapped_column(String(20), nullable=True)
    municipality: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    crime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id"), nullable=True, index=True)

    # DBSCAN parameters used for the per-period runs
    eps_km: Mapped[float] = mapped_column(Float)
    min_samples: Mapped[int] = mapped_column(Integer)

    # Matching parameters (specification section 11)
    match_distance_km: Mapped[float] = mapped_column(Float)
    min_spatial_overlap_percent: Mapped[float] = mapped_column(Float, default=0.0)
    persistence_min_periods: Mapped[int] = mapped_column(Integer, default=2)
    active_latest_period_required: Mapped[bool] = mapped_column(default=True)

    # Outcome summary
    total_periods_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    periods_analyzed: Mapped[list | None] = mapped_column(JSON, nullable=True)
    chain_count: Mapped[int] = mapped_column(Integer, default=0)

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PersistentCluster(Base):
    """A chain of period-specific clusters matched across time.

    `public_id` is the human-facing chain identifier (e.g. "PC-MID-001").
    Period-specific DBSCAN cluster labels are deliberately NOT reused as chain
    identity — cluster 1 in 2016 is unrelated to cluster 1 in 2017 — so chains
    are assigned their own stable IDs at match time.
    """

    __tablename__ = "persistent_clusters"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("persistence_runs.id", ondelete="CASCADE"), index=True)
    public_id: Mapped[str] = mapped_column(String(30), index=True)

    municipality: Mapped[str] = mapped_column(String(100), index=True)
    barangays: Mapped[list | None] = mapped_column(JSON, nullable=True)
    dominant_crime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    periods_present: Mapped[list] = mapped_column(JSON)
    period_count: Mapped[int] = mapped_column(Integer)
    total_periods_analyzed: Mapped[int] = mapped_column(Integer)
    persistence_score: Mapped[float] = mapped_column(Float, index=True)
    # temporary | intermittent | historical_persistent | active_persistent
    category: Mapped[str] = mapped_column(String(30), index=True)
    present_in_latest_period: Mapped[bool] = mapped_column(default=False, index=True)

    first_period: Mapped[str | None] = mapped_column(String(20), nullable=True)
    latest_period: Mapped[str | None] = mapped_column(String(20), nullable=True)
    total_incidents: Mapped[int] = mapped_column(Integer, default=0)
    avg_incidents_per_active_period: Mapped[float] = mapped_column(Float, default=0.0)

    centroid_lat: Mapped[float] = mapped_column(Float)
    centroid_lon: Mapped[float] = mapped_column(Float)
    centroid_geom = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PersistentClusterMembership(Base):
    """Links one period-specific DBSCAN cluster into a persistent chain.

    This is the join that lets the cluster-history timeline show, for a given
    chain, exactly which period-specific cluster represented it in each period —
    and records the match evidence (centroid distance, hull overlap) so the
    matching decision is auditable rather than opaque.
    """

    __tablename__ = "persistent_cluster_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    persistent_cluster_id: Mapped[int] = mapped_column(
        ForeignKey("persistent_clusters.id", ondelete="CASCADE"), index=True
    )
    cluster_id: Mapped[int] = mapped_column(ForeignKey("clusters.id", ondelete="CASCADE"), index=True)
    period_key: Mapped[str] = mapped_column(String(20), index=True)
    incident_count: Mapped[int] = mapped_column(Integer, default=0)

    # Match evidence against the previous period's cluster in this chain.
    matched_distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    matched_overlap_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
