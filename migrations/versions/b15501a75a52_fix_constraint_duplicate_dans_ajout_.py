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
    # Supprimer toutes les anciennes contraintes possibles
    op.execute("""
        ALTER TABLE stock 
        DROP CONSTRAINT IF EXISTS uix_produit_lot_magasin_conditionnement;
    """)

    op.execute("""
        ALTER TABLE stock 
        DROP CONSTRAINT IF EXISTS uix_produit_lot;
    """)

    op.execute("""
        ALTER TABLE stock 
        DROP CONSTRAINT IF EXISTS stock_produit_id_numero_lot_key;
    """)

    # Créer la nouvelle contrainte propre
    op.create_unique_constraint(
        "uix_stock_unique",
        "stock",
        ["produit_id", "magasin_id", "type_conditionnement"]
    )
    # ### end Alembic commands ###


def downgrade():
    op.drop_constraint("uix_stock_unique", "stock", type_="unique")

    op.create_unique_constraint(
        "uix_produit_lot",
        "stock",
        ["produit_id", "numero_lot"]
    )
    # ### end Alembic commands ###
