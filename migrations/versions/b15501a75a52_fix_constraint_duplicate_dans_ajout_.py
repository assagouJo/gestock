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

    # Supprimer anciennes contraintes
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

    # 🔥 1️⃣ Fusionner les doublons (addition des quantités)
    op.execute("""
        UPDATE stock s1
        SET quantite = s1.quantite + s2.extra_quantite
        FROM (
            SELECT MIN(id) as keep_id,
                   produit_id,
                   magasin_id,
                   type_conditionnement,
                   SUM(quantite) - MIN(quantite) as extra_quantite
            FROM stock
            GROUP BY produit_id, magasin_id, type_conditionnement
            HAVING COUNT(*) > 1
        ) s2
        WHERE s1.id = s2.keep_id;
    """)

    # 🔥 2️⃣ Supprimer les doublons restants
    op.execute("""
        DELETE FROM stock
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM stock
            GROUP BY produit_id, magasin_id, type_conditionnement
        );
    """)

    # 🔥 3️⃣ Créer la contrainte propre
    op.create_unique_constraint(
        "uix_produit_lot_magasin_conditionnement",
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
