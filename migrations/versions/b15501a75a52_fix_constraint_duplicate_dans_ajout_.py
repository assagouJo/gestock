"""fix constraint duplicate dans ajout stock

Revision ID: b15501a75a52
Revises: 56728bd31654
Create Date: 2026-02-20 10:07:07.144435

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b15501a75a52'
down_revision = '56728bd31654'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('stock') as batch_op:
        # Supprimer ancienne contrainte si elle existe
        batch_op.drop_constraint('uix_produit_lot', type_='unique')

        # Supprimer aussi si PostgreSQL l’a générée automatiquement
        try:
            batch_op.drop_constraint('stock_produit_id_numero_lot_key', type_='unique')
        except:
            pass

        # Créer nouvelle contrainte propre
        batch_op.create_unique_constraint(
            'uix_stock_unique',
            ['produit_id', 'magasin_id', 'type_conditionnement']
        )

    # ### end Alembic commands ###


def downgrade():
    with op.batch_alter_table('stock') as batch_op:
        batch_op.drop_constraint('uix_stock_unique', type_='unique')

        batch_op.create_unique_constraint(
            'uix_produit_lot',
            ['produit_id', 'numero_lot']
        )
    # ### end Alembic commands ###
