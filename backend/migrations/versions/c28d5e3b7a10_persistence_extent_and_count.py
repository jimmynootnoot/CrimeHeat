"""persistence chain extent and incident count

Lets the map draw a recurring hotspot as the area it covers, sized by how many
incidents it holds, instead of as an identical pin at its latest centroid.

Revision ID: c28d5e3b7a10
Revises: b17c4f2a9d31
Create Date: 2026-09-15 23:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c28d5e3b7a10"
down_revision: Union[str, Sequence[str], None] = "b17c4f2a9d31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "persistence_records",
        sa.Column("incident_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "persistence_records",
        sa.Column("extent_geojson", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("persistence_records", "extent_geojson")
    op.drop_column("persistence_records", "incident_count")
