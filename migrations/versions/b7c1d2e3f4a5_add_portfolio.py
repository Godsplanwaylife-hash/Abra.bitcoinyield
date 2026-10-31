"""add portfolio holdings

Revision ID: b7c1d2e3f4a5
Revises: aaf6d9a56ef8
"""
from alembic import op
import sqlalchemy as sa

revision = "b7c1d2e3f4a5"
down_revision = "aaf6d9a56ef8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("btc_units", sa.Float(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("eth_units", sa.Float(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("cost_basis", sa.Float(), nullable=False, server_default="0"))


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("cost_basis")
        batch_op.drop_column("eth_units")
        batch_op.drop_column("btc_units")
