"""Add latitude and longitude to Location

Revision ID: d13be35f8f81
Revises: f3f98d063af7
Create Date: 2024-08-25 10:24:16.538574

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd13be35f8f81'
down_revision = 'f3f98d063af7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('location', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('location', sa.Column('longitude', sa.Float(), nullable=True))
    # op.drop_column('report', 'identified_items')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('report', sa.Column('identified_items', sa.VARCHAR(length=1000), autoincrement=False, nullable=True))
    op.drop_column('location', 'longitude')
    op.drop_column('location', 'latitude')
    # ### end Alembic commands ###
