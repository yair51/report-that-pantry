"""empty_migration_for_timezone

Revision ID: f3f98d063af7
Revises: 
Create Date: 2024-06-21 15:21:51.040963

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3f98d063af7'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Change the column type to TIMESTAMP WITH TIME ZONE
    op.alter_column('report', 'time', type_=sa.DateTime(timezone=True), existing_type=sa.DateTime(), postgresql_using="time AT TIME ZONE 'UTC'")

def downgrade():
    # Revert the column type back to TIMESTAMP WITHOUT TIME ZONE
    op.alter_column('report', 'time', type_=sa.DateTime(), existing_type=sa.DateTime(timezone=True))

