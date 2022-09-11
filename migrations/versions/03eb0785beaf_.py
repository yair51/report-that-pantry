"""empty message

Revision ID: 03eb0785beaf
Revises: 023f323c06b5
Create Date: 2022-09-11 16:52:24.711316

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '03eb0785beaf'
down_revision = '023f323c06b5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('location', sa.Column('latlong', sa.String(length=150), nullable=True))


def downgrade():
    op.drop_column('location', 'latlong')