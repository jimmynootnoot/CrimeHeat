from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IncidentClusterMembership(Base):
    """Per-incident DBSCAN outcome for one analysis run.

    Storing membership (rather than recomputing DBSCAN on every request) is what
    makes three things possible: distinguishing core from border points,
    retrieving a past run's exact result, and evaluating clustering output
    against reference labels.

    `point_type` is one of:
      - "core"   : has at least min_samples neighbours within eps
      - "border" : within eps of a core point but not itself core
      - "noise"  : assigned to no cluster (cluster_id is NULL)

    scikit-learn's DBSCAN exposes core samples via `core_sample_indices_`;
    border points are the clustered points not in that set.
    """

    __tablename__ = "incident_cluster_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("dbscan_runs.id", ondelete="CASCADE"), index=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), index=True)
    cluster_id: Mapped[int | None] = mapped_column(
        ForeignKey("clusters.id", ondelete="CASCADE"), nullable=True, index=True
    )
    cluster_label: Mapped[int] = mapped_column(Integer)  # -1 for noise
    point_type: Mapped[str] = mapped_column(String(10), index=True)
    period_key: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
