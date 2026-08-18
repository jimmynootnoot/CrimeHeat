from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AlgorithmEvaluation(Base):
    """Result of one algorithm-evaluation execution.

    Two distinct families of metric are stored here, and they must not be
    conflated in reporting:

    External (supervised) — precision / recall / F1 / confusion matrix. These
    require reference hotspot labels. When no authorized labels exist the
    fields stay NULL and `external_available` is False; the interface then
    states the metric is unavailable rather than substituting a proxy.

    Internal (unsupervised) — noise ratio, stability under subsampling,
    Adjusted Rand Index, silhouette, and parameter sensitivity. These need no
    ground truth but none of them is an "accuracy" figure, and silhouette in
    particular assumes convex clusters, which DBSCAN does not produce; it is
    retained only as a supplementary indicator.
    """

    __tablename__ = "algorithm_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    dbscan_run_id: Mapped[int | None] = mapped_column(ForeignKey("dbscan_runs.id"), nullable=True, index=True)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id"), nullable=True, index=True)

    # How the study area was discretized for external comparison.
    evaluation_unit: Mapped[str] = mapped_column(String(30), default="grid_cell")
    grid_cell_size_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    label_source: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # --- External metrics (require reference labels) ---
    external_available: Mapped[bool] = mapped_column(default=False)
    true_positives: Mapped[int | None] = mapped_column(Integer, nullable=True)
    false_positives: Mapped[int | None] = mapped_column(Integer, nullable=True)
    false_negatives: Mapped[int | None] = mapped_column(Integer, nullable=True)
    true_negatives: Mapped[int | None] = mapped_column(Integer, nullable=True)
    precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    f1_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Internal / stability metrics ---
    noise_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    cluster_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stability_mean_ari: Mapped[float | None] = mapped_column(Float, nullable=True)
    stability_std_ari: Mapped[float | None] = mapped_column(Float, nullable=True)
    silhouette_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sensitivity_results: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # --- Weighted effectiveness (specification section 21) ---
    algorithmic_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    functional_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_effectiveness: Mapped[float | None] = mapped_column(Float, nullable=True)
    # The weights actually applied, stored so a past result stays interpretable
    # even if the configured weights change later.
    weights_used: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FunctionalTestCase(Base):
    """A functional (system) test case and its most recent outcome.

    Deliberately separate from algorithm evaluation: functional testing measures
    whether the software behaves as specified, while algorithm evaluation
    measures clustering quality. The study's 90/10 weighting combines them but
    they are never reported as the same thing.
    """

    __tablename__ = "functional_test_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    module: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(255))
    preconditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    steps: Mapped[str] = mapped_column(Text)
    expected_result: Mapped[str] = mapped_column(Text)
    actual_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    # passed | failed | blocked | not_run
    status: Mapped[str] = mapped_column(String(20), default="not_run", index=True)
    date_tested: Mapped[date | None] = mapped_column(Date, nullable=True)
    tester: Mapped[str | None] = mapped_column(String(150), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
