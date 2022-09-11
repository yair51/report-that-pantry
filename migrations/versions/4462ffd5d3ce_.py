"""empty message

Revision ID: 4462ffd5d3ce
Revises: 019332189b97
Create Date: 2021-06-12 17:46:47.152121

"""
from alembic import op
import sqlalchemy as sa

from migrations.utils import column_exists

# revision identifiers, used by Alembic.
revision = '4462ffd5d3ce'
down_revision = '019332189b97'
branch_labels = None
depends_on = None


def upgrade():
    if not column_exists('user', 'last_name'):
        op.add_column('user', sa.Column('last_name', sa.String(length=150), nullable=True))
    if not column_exists('user', 'organization_id'):
        op.add_column('user', sa.Column('organization_id', sa.Integer(), nullable=True))
        op.create_foreign_key(None, 'user', 'organization', ['organization_id'], ['id'])


def downgrade():
    op.drop_constraint(None, 'user', type_='foreignkey')
    op.drop_column('user', 'organization_id')
    op.drop_column('user', 'last_name')
