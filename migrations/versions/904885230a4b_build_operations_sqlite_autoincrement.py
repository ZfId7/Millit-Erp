"""build_operations sqlite autoincrement

Revision ID: 904885230a4b
Revises: 3ee7e9f1ad92
Create Date: 2026-02-01 20:13:21.784322

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '904885230a4b'
down_revision = '3ee7e9f1ad92'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
        "build_operations",
        recreate="always",
        table_kwargs={"sqlite_autoincrement": True},
    ) as batch_op:
        pass

def downgrade():
    with op.batch_alter_table(
        "build_operations",
        recreate="always",
        table_kwargs={"sqlite_autoincrement": False},
    ) as batch_op:
        pass
