"""add modo to sesion

Revision ID: 9f1c2b3a4d5e
Revises: 83b27b8124bf
Create Date: 2026-11-06 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9f1c2b3a4d5e"
down_revision: str | None = "83b27b8124bf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("sesion", schema=None) as batch_op:
        batch_op.add_column(sa.Column("modo", sa.String(length=16), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sesion", schema=None) as batch_op:
        batch_op.drop_column("modo")
