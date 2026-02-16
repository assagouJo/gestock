"""add vendeur and compagnie to vente

Revision ID: cdda7607ba54
Revises: e71490912502
Create Date: 2026-02-16 09:30:38.003956

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cdda7607ba54'
down_revision = '7ad526af2e5e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('vente') as batch_op:
        batch_op.add_column(
            sa.Column('vendeur_id', sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('compagnie_id', sa.Integer(), nullable=True)
        )

        batch_op.create_foreign_key(
            'fk_vente_vendeur',
            'vendeur',
            ['vendeur_id'],
            ['id']
        )

        batch_op.create_foreign_key(
            'fk_vente_compagnie',
            'vendeur_compagnie',
            ['compagnie_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('vente') as batch_op:
        batch_op.drop_constraint('fk_vente_vendeur', type_='foreignkey')
        batch_op.drop_constraint('fk_vente_compagnie', type_='foreignkey')
        batch_op.drop_column('vendeur_id')
        batch_op.drop_column('compagnie_id')
