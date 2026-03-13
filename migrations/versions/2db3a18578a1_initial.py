"""initial

Revision ID: 2db3a18578a1
Revises: 
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa
from app import db

revision = '2db3a18578a1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    db.create_all()


def downgrade():
    db.drop_all()