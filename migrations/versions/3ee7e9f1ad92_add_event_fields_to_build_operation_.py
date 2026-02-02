"""add event fields to build_operation_progress

Revision ID: 3ee7e9f1ad92
Revises: f5b50a7e5d55
Create Date: 2026-01-31 10:00:45.147490

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3ee7e9f1ad92'
down_revision = 'f5b50a7e5d55'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("build_operation_progress") as batch:
        batch.add_column(sa.Column("event_type", sa.String(length=50), nullable=False, server_default="progress"))
        batch.add_column(sa.Column("actor_role", sa.String(length=32), nullable=True))  # editor|contributor|admin_override|system
        batch.add_column(sa.Column("event_note", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("is_override", sa.Boolean(), nullable=False, server_default=sa.text("0")))

    op.create_index(
        "ix_bop_event_type",
        "build_operation_progress",
        ["event_type"],
    )


def downgrade():
    op.drop_index("ix_bop_event_type", table_name="build_operation_progress")
    with op.batch_alter_table("build_operation_progress") as batch:
        batch.drop_column("is_override")
        batch.drop_column("event_note")
        batch.drop_column("actor_role")
        batch.drop_column("event_type")

    # ### end Alembic commands ###
