"""empty message

Revision ID: 023f323c06b5
Revises: 73460ccb70de
Create Date: 2022-09-11 16:04:36.771102

"""
from alembic import op
import sqlalchemy as sa

from migrations.utils import column_exists

# revision identifiers, used by Alembic.
revision = '023f323c06b5'
down_revision = '73460ccb70de'
branch_labels = None
depends_on = None


def upgrade():
    if not column_exists('user', 'phone'):
        op.add_column('user', sa.Column('phone', sa.String(length=150), nullable=True))


def downgrade():
    op.drop_column('user', 'phone')
