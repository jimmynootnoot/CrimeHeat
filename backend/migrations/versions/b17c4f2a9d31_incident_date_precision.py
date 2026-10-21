"""incident date precision

Marks records whose source supplied only a year rather than an incident date,
so year-based analysis stays valid while day-level reads are not mistaken for
real observations.

Revision ID: b17c4f2a9d31
Revises: 8006646cd2fa
Create Date: 2026-09-15 23:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b17c4f2a9d31"
down_revision: Union[str, Sequence[str], None] = "8006646cd2fa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "incidents",
        sa.Column(
            "date_precision",
            sa.String(length=20),
            nullable=False,
            server_default="exact",
        ),
    )
    op.create_index("ix_incidents_date_precision", "incidents", ["date_precision"])


def downgrade() -> None:
    op.drop_index("ix_incidents_date_precision", table_name="incidents")
    op.drop_column("incidents", "date_precision")
