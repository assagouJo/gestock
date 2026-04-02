"""modification des models bondecommande

Revision ID: 82a7a69e2896
Revises: 2d3dfba9e78f
Create Date: 2026-04-01 12:18:00.338619

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '82a7a69e2896'
down_revision = '2d3dfba9e78f'
branch_labels = None
depends_on = None


def upgrade():
    # 🔥 1. Insérer la compagnie par défaut
    op.execute("""
        INSERT INTO vendeur_compagnie (id, nom)
        VALUES (1, 'Compagnie par défaut')
        ON CONFLICT (id) DO NOTHING
    """)
    
    # 🔥 2. Insérer le vendeur par défaut (SEULEMENT avec les colonnes qui existent)
    # Note: La table vendeur a probablement seulement 'id', 'nom', et 'telephone'
    op.execute("""
        INSERT INTO vendeur (id, nom, telephone)
        VALUES (1, 'Vendeur par défaut', '00000000')
        ON CONFLICT (id) DO NOTHING
    """)
    
    # 🔥 3. Ajouter les colonnes dans bon_commande
    with op.batch_alter_table('bon_commande', schema=None) as batch_op:
        batch_op.add_column(sa.Column('vendeur_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('compagnie_id', sa.Integer(), nullable=True))
    
    # 🔥 4. Mettre à jour les données existantes
    op.execute("""
        UPDATE bon_commande 
        SET vendeur_id = 1,
            compagnie_id = 1
        WHERE vendeur_id IS NULL
    """)
    
    # 🔥 5. Ajouter les clés étrangères
    with op.batch_alter_table('bon_commande', schema=None) as batch_op:
        batch_op.create_foreign_key('fk_bon_commande_vendeur_id', 'vendeur', ['vendeur_id'], ['id'])
        batch_op.create_foreign_key('fk_bon_commande_compagnie_id', 'vendeur_compagnie', ['compagnie_id'], ['id'])
    
    # 🔥 6. Rendre les colonnes NOT NULL
    with op.batch_alter_table('bon_commande', schema=None) as batch_op:
        batch_op.alter_column('vendeur_id', nullable=False)
        batch_op.alter_column('compagnie_id', nullable=False)
    
    # 🔥 7. Ajouter la colonne dans ligne_bon_commande
    with op.batch_alter_table('ligne_bon_commande', schema=None) as batch_op:
        batch_op.add_column(sa.Column('compagnie_id', sa.Integer(), nullable=True))
    
    # Mettre à jour les données existantes
    op.execute("""
        UPDATE ligne_bon_commande 
        SET compagnie_id = 1
        WHERE compagnie_id IS NULL
    """)
    
    # Ajouter la clé étrangère et rendre NOT NULL
    with op.batch_alter_table('ligne_bon_commande', schema=None) as batch_op:
        batch_op.create_foreign_key('fk_ligne_bon_commande_compagnie_id', 'vendeur_compagnie', ['compagnie_id'], ['id'])
        batch_op.alter_column('compagnie_id', nullable=False)
    
    # 🔥 8. Ajouter la colonne dans produit
    with op.batch_alter_table('produit', schema=None) as batch_op:
        batch_op.add_column(sa.Column('compagnie_id', sa.Integer(), nullable=True))
    
    # Mettre à jour les données existantes
    op.execute("""
        UPDATE produit 
        SET compagnie_id = 1
        WHERE compagnie_id IS NULL
    """)
    
    # Ajouter la clé étrangère et rendre NOT NULL
    with op.batch_alter_table('produit', schema=None) as batch_op:
        batch_op.create_foreign_key('fk_produit_compagnie_id', 'vendeur_compagnie', ['compagnie_id'], ['id'])
        batch_op.alter_column('compagnie_id', nullable=False)
    
    # 🔥 9. Ajouter la colonne dans vendeur
    with op.batch_alter_table('vendeur', schema=None) as batch_op:
        batch_op.add_column(sa.Column('compagnie_id', sa.Integer(), nullable=True))
    
    # Mettre à jour les données existantes
    op.execute("""
        UPDATE vendeur 
        SET compagnie_id = 1
        WHERE compagnie_id IS NULL
    """)
    
    # Ajouter la clé étrangère et rendre NOT NULL
    with op.batch_alter_table('vendeur', schema=None) as batch_op:
        batch_op.create_foreign_key('fk_vendeur_compagnie_id', 'vendeur_compagnie', ['compagnie_id'], ['id'])
        batch_op.alter_column('compagnie_id', nullable=False)
    
    # 🔥 10. Ajouter l'index pour vente
    with op.batch_alter_table('vente', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_vente_bon_livraison_id'), ['bon_livraison_id'], unique=False)


def downgrade():
    # Supprimer l'index
    with op.batch_alter_table('vente', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_vente_bon_livraison_id'))
    
    # Supprimer la colonne dans vendeur
    with op.batch_alter_table('vendeur', schema=None) as batch_op:
        batch_op.drop_constraint('fk_vendeur_compagnie_id', type_='foreignkey')
        batch_op.drop_column('compagnie_id')
    
    # Supprimer la colonne dans produit
    with op.batch_alter_table('produit', schema=None) as batch_op:
        batch_op.drop_constraint('fk_produit_compagnie_id', type_='foreignkey')
        batch_op.drop_column('compagnie_id')
    
    # Supprimer la colonne dans ligne_bon_commande
    with op.batch_alter_table('ligne_bon_commande', schema=None) as batch_op:
        batch_op.drop_constraint('fk_ligne_bon_commande_compagnie_id', type_='foreignkey')
        batch_op.drop_column('compagnie_id')
    
    # Supprimer les colonnes dans bon_commande
    with op.batch_alter_table('bon_commande', schema=None) as batch_op:
        batch_op.drop_constraint('fk_bon_commande_compagnie_id', type_='foreignkey')
        batch_op.drop_constraint('fk_bon_commande_vendeur_id', type_='foreignkey')
        batch_op.drop_column('compagnie_id')
        batch_op.drop_column('vendeur_id')