"""add qty_required to build_operations

Revision ID: 07637c66f458
Revises: 904885230a4b
Create Date: 2026-02-01 21:12:01.671815

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '07637c66f458'
down_revision = '904885230a4b'
branch_labels = None
depends_on = None


from alembic import op
import sqlalchemy as sa


def upgrade():
    # 1) Add the column (SQLite-safe via batch mode)
    with op.batch_alter_table("build_operations") as batch:
        batch.add_column(
            sa.Column("qty_required", sa.Float(), nullable=False, server_default="0")
        )

    # 2) Backfill from builds.qty_ordered
    op.execute("""
        UPDATE build_operations
        SET qty_required = (
            SELECT COALESCE(b.qty_ordered, 0)
            FROM builds b
            WHERE b.id = build_operations.build_id
        )
    """)

    # Optional (later): if you want to remove the server default,
    # SQLite makes that annoying; it's fine to leave it for now.


def downgrade():
    with op.batch_alter_table("build_operations") as batch:
        batch.drop_column("qty_required")


    # ### end Alembic commands ###
