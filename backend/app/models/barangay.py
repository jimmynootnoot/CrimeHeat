from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Barangay(Base):
    """Barangay reference list per municipality.

    Attribute-only: the study's boundary source publishes barangay names but the
    system does not carry barangay polygons, so there is no geometry column
    here. Barangay-level point-in-polygon validation is therefore not possible;
    validation stops at the municipality boundary. Populated from
    data/boundaries/ppalma_barangays.json.
    """

    __tablename__ = "barangays"

    id: Mapped[int] = mapped_column(primary_key=True)
    municipality_id: Mapped[int] = mapped_column(ForeignKey("municipalities.id"), index=True)
    municipality: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
