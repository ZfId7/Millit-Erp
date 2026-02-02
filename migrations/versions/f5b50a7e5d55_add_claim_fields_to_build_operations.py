"""add claim fields to build_operations

Revision ID: f5b50a7e5d55
Revises: c15ba3adb6a4
Create Date: 2026-01-31 09:53:25.330911

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f5b50a7e5d55'
down_revision = 'c15ba3adb6a4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("build_operations") as batch:
        batch.add_column(sa.Column("claimed_by_user_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("claimed_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("claim_touched_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("allow_multi_user", sa.Boolean(), nullable=False, server_default=sa.text("0")))
        batch.add_column(sa.Column("claim_note", sa.String(length=255), nullable=True))

        batch.create_foreign_key(
            "fk_build_operations_claimed_by_user_id_users",
            "users",
            ["claimed_by_user_id"],
            ["id"],
        )

    # Optional but recommended: index for "My Active Ops"
    op.create_index(
        "ix_build_operations_claimed_by_user_id",
        "build_operations",
        ["claimed_by_user_id"],
    )


def downgrade():
    op.drop_index("ix_build_operations_claimed_by_user_id", table_name="build_operations")
    with op.batch_alter_table("build_operations") as batch:
        batch.drop_constraint("fk_build_operations_claimed_by_user_id_users", type_="foreignkey")
        batch.drop_column("claim_note")
        batch.drop_column("allow_multi_user")
        batch.drop_column("claim_touched_at")
        batch.drop_column("claimed_at")
        batch.drop_column("claimed_by_user_id")

    # ### end Alembic commands ###
