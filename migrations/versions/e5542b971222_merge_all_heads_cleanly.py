"""merge all heads cleanly

Revision ID: e5542b971222
Revises: 2cb479ff3f1e, cdda7607ba54, e71490912502
Create Date: 2026-02-16 09:47:53.828868

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5542b971222'
down_revision = ('2cb479ff3f1e', 'cdda7607ba54', 'e71490912502')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
