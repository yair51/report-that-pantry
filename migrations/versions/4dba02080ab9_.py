"""empty message

Revision ID: 4dba02080ab9
Revises: 521a6c6bdb14
Create Date: 2021-06-12 15:34:14.087498

"""
from alembic import op
import sqlalchemy as sa

from migrations.utils import column_exists


# revision identifiers, used by Alembic.
revision = '4dba02080ab9'
down_revision = '521a6c6bdb14'
branch_labels = None
depends_on = None


def upgrade():
    if not column_exists('location', 'name'):
        op.add_column('location', sa.Column('name', sa.String(length=150), nullable=True))


def downgrade():
    op.drop_column('location', 'name')