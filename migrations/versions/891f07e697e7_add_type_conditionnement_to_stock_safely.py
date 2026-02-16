from alembic import op
import sqlalchemy as sa

revision = 'NOUVEL_ID_ICI'  # laisse celui généré
down_revision = 'f84e101b7149'
branch_labels = None
depends_on = None


def upgrade():
    # 1️⃣ Créer le type ENUM PostgreSQL
    type_conditionnement_enum = sa.Enum(
        'carton',
        'paquet',
        'unite',
        name='typeconditionnement'
    )

    type_conditionnement_enum.create(op.get_bind(), checkfirst=True)

    # 2️⃣ Ajouter la colonne
    with op.batch_alter_table('stock') as batch_op:
        batch_op.add_column(
            sa.Column(
                'type_conditionnement',
                type_conditionnement_enum,
                nullable=True
            )
        )


def downgrade():
    with op.batch_alter_table('stock') as batch_op:
        batch_op.drop_column('type_conditionnement')

    sa.Enum(name='typeconditionnement').drop(op.get_bind(), checkfirst=True)
