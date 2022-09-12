"""empty message

Revision ID: d1c7188fd0a0
Revises: 03eb0785beaf
Create Date: 2022-09-11 17:38:55.463939

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1c7188fd0a0'
down_revision = '03eb0785beaf'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('notification', 'medium')
    op.add_column('notification', sa.Column('is_email', sa.Boolean(), nullable=True))
    op.add_column('notification', sa.Column('is_sms', sa.Boolean(), nullable=True))


def downgrade():
    op.add_column('notification', sa.Column('medium', sa.String(length=150), nullable=True))
