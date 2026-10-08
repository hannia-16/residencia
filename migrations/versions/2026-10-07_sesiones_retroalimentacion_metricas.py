"""sesiones retroalimentacion metricas

Revision ID: 83b27b8124bf
Revises: c8a6d32245fc
Create Date: 2026-10-07 20:58:09.468893

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "83b27b8124bf"
down_revision: str | None = "c8a6d32245fc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "metrica",
        sa.Column("id_metrica", sa.Uuid(), nullable=False),
        sa.Column("id_usuario", sa.Uuid(), nullable=False),
        sa.Column("escenario", sa.String(length=64), nullable=False),
        sa.Column("nivel", sa.String(length=8), nullable=False),
        sa.Column("fecha_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duracion", sa.Integer(), nullable=False),
        sa.Column("errores", sa.JSON(), nullable=False),
        sa.Column("resumen_ia", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["id_usuario"],
            ["user.id"],
            name=op.f("metrica_id_usuario_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id_metrica", name=op.f("metrica_pkey")),
    )
    with op.batch_alter_table("metrica", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("metrica_id_usuario_idx"), ["id_usuario"], unique=False
        )

    op.create_table(
        "sesion",
        sa.Column("id_sesion", sa.Uuid(), nullable=False),
        sa.Column("id_usuario", sa.Uuid(), nullable=False),
        sa.Column("escenario", sa.String(length=64), nullable=False),
        sa.Column("nivel", sa.String(length=8), nullable=False),
        sa.Column(
            "estado", sa.String(length=16), server_default="activa", nullable=False
        ),
        sa.Column(
            "fecha_inicio",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("fecha_fin", sa.DateTime(timezone=True), nullable=True),
        sa.Column("historial", sa.JSON(), nullable=False),
        sa.Column("resumen_desempeno", sa.JSON(), nullable=True),
        sa.Column("evaluacion_sistema", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_usuario"],
            ["user.id"],
            name=op.f("sesion_id_usuario_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id_sesion", name=op.f("sesion_pkey")),
    )
    with op.batch_alter_table("sesion", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("sesion_estado_idx"), ["estado"], unique=False)
        batch_op.create_index(
            batch_op.f("sesion_id_usuario_idx"), ["id_usuario"], unique=False
        )

    op.create_table(
        "retroalimentacion",
        sa.Column("id_retroalimentacion", sa.Uuid(), nullable=False),
        sa.Column("id_sesion", sa.Uuid(), nullable=False),
        sa.Column("entrada_usuario", sa.Text(), nullable=False),
        sa.Column("correccion_ia", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["id_sesion"],
            ["sesion.id_sesion"],
            name=op.f("retroalimentacion_id_sesion_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id_retroalimentacion", name=op.f("retroalimentacion_pkey")
        ),
    )
    with op.batch_alter_table("retroalimentacion", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("retroalimentacion_id_sesion_idx"), ["id_sesion"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("retroalimentacion", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("retroalimentacion_id_sesion_idx"))

    op.drop_table("retroalimentacion")
    with op.batch_alter_table("sesion", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("sesion_id_usuario_idx"))
        batch_op.drop_index(batch_op.f("sesion_estado_idx"))

    op.drop_table("sesion")
    with op.batch_alter_table("metrica", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("metrica_id_usuario_idx"))

    op.drop_table("metrica")
