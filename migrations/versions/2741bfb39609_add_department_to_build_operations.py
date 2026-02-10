"""add department to build_operations

Revision ID: 2741bfb39609
Revises: 07637c66f458
Create Date: 2026-02-06 06:53:06.234298

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2741bfb39609'
down_revision = '07637c66f458'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("build_operations") as batch:
        batch.add_column(
            sa.Column("department", sa.String(length=32), nullable=False, server_default="manufacturing")
        )

    # Backfill safety (should already be set by server_default, but explicit is fine)
    op.execute("""
        UPDATE build_operations
        SET department = 'manufacturing'
        WHERE department IS NULL OR department = '';
    """)

def downgrade():
    with op.batch_alter_table("build_operations") as batch:
        batch.drop_column("department")

    # ### end Alembic commands ###
