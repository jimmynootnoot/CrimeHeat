from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Role(Base):
    """Reference table for the three study-defined access levels.

    Authorization is enforced in code via `app.api.deps.require_role`; this
    table exists so the User Management screen can present role names and
    descriptions without hardcoding them in the frontend, and so a future
    deployment can add a role without a code change.
    """

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
