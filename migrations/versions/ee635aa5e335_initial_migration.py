"""initial migration

Revision ID: ee635aa5e335
Revises: 
Create Date: 2022-09-12 20:26:09.269437

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ee635aa5e335'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('notification')
    op.add_column('organization', sa.Column('state', sa.String(length=150), nullable=True))
    op.create_unique_constraint(None, 'organization', ['state'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'organization', type_='unique')
    op.drop_column('organization', 'state')
    op.create_table('notification',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('location_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['location_id'], ['location.id'], name='notification_location_id_fkey'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='notification_user_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='notification_pkey')
    )
    # ### end Alembic commands ###