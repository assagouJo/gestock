"""compagnie_id NOT NULL sur proforma et kit_proforma

Revision ID: 5f6cf13c7aa4
Revises: 0e668059d764
Create Date: 2026-09-02 09:16:04.720960

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f6cf13c7aa4'
down_revision = '0e668059d764'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('kit_proforma', schema=None) as batch_op:
        batch_op.alter_column('compagnie_id', existing_type=sa.Integer(), nullable=False)

    with op.batch_alter_table('proforma', schema=None) as batch_op:
        batch_op.alter_column('compagnie_id', existing_type=sa.Integer(), nullable=False)


def downgrade():
    with op.batch_alter_table('proforma', schema=None) as batch_op:
        batch_op.alter_column('compagnie_id', existing_type=sa.Integer(), nullable=True)

    with op.batch_alter_table('kit_proforma', schema=None) as batch_op:
        batch_op.alter_column('compagnie_id', existing_type=sa.Integer(), nullable=True)
