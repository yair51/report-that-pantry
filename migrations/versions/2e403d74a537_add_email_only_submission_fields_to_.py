"""Add email-only submission fields to Location and Report models

Revision ID: 2e403d74a537
Revises: a5ebe9fafb45
Create Date: 2025-06-29 20:49:26.683206

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2e403d74a537'
down_revision = 'a5ebe9fafb45'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('location', sa.Column('submitter_email', sa.String(length=150), nullable=True))
    op.add_column('location', sa.Column('submitter_name', sa.String(length=150), nullable=True))
    op.add_column('location', sa.Column('verification_token', sa.String(length=50), nullable=True))
    op.add_column('location', sa.Column('verified', sa.Boolean(), nullable=True))
    op.add_column('location', sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('location', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('report', sa.Column('submitted_by_email', sa.String(length=150), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('report', 'submitted_by_email')
    op.drop_column('location', 'created_at')
    op.drop_column('location', 'verified_at')
    op.drop_column('location', 'verified')
    op.drop_column('location', 'verification_token')
    op.drop_column('location', 'submitter_name')
    op.drop_column('location', 'submitter_email')
    # ### end Alembic commands ###
