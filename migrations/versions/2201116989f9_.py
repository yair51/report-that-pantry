"""empty message

Revision ID: 2201116989f9
Revises: 4462ffd5d3ce
Create Date: 2021-07-09 17:32:09.510093

"""
from alembic import op
import sqlalchemy as sa

from migrations.utils import column_exists

# revision identifiers, used by Alembic.
revision = '2201116989f9'
down_revision = '4462ffd5d3ce'
branch_labels = None
depends_on = None


def upgrade():
    if not column_exists('notification', 'medium'):
        op.add_column('notification', sa.Column('medium', sa.String(length=150), nullable=True))


def downgrade():
    op.drop_column('notification', 'medium')
