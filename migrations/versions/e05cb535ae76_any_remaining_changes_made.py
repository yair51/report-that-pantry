"""any remaining changes made

Revision ID: e05cb535ae76
Revises: d13be35f8f81
Create Date: 2024-08-29 20:10:31.083324

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e05cb535ae76'
down_revision = 'd13be35f8f81'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('location', 'name',
               existing_type=sa.VARCHAR(length=150),
               nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('location', 'name',
               existing_type=sa.VARCHAR(length=150),
               nullable=True)
    # ### end Alembic commands ###
