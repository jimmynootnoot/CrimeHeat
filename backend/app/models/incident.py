from datetime import date, datetime, time

from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Incident(Base):
    """An anonymized, incident-level crime record.

    Privacy constraint: this schema intentionally has no column capable of
    holding a victim, suspect, or witness identity, a contact number, or an
    exact residential address. `general_location` and `notes_non_sensitive` are
    generalized free text and are validated on import; narrative detail that
    could identify a person must not be stored here.
    """

    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    crime_type: Mapped[str] = mapped_column(String(100), index=True)
    incident_date: Mapped[date] = mapped_column(Date, index=True)
    incident_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    municipality_id: Mapped[int] = mapped_column(ForeignKey("municipalities.id"), index=True)
    municipality: Mapped[str] = mapped_column(String(100), index=True)
    barangay: Mapped[str] = mapped_column(String(150), index=True)
    # Generalized location description (specification's `location_description`).
    general_location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    geom = mapped_column(Geometry(geometry_type="POINT", srid=4326))

    # --- Optional descriptive fields (specification section 6) ---
    offense_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    crime_classification: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # "index" | "non_index" — this study analyzes index crimes.
    index_nonindex_flag: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    # How the coordinate was obtained: reported | geocoded | barangay_centroid | generalized
    coordinate_source: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    # exact | approximate | barangay_level — drives data-quality warnings.
    coordinate_precision: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reporting_station: Mapped[str | None] = mapped_column(String(150), nullable=True)
    case_status_generalized: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes_non_sensitive: Mapped[str | None] = mapped_column(Text, nullable=True)

    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(30), default="synthetic", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
