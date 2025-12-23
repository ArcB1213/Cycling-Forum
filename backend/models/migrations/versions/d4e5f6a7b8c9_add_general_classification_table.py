"""Add GeneralClassification table

Revision ID: d4e5f6a7b8c9
Revises: 9c1e2d3f4a5b
Create Date: 2025-12-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = '9c1e2d3f4a5b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create GeneralClassification table
    op.create_table(
        'general_classifications',
        sa.Column('gc_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('edition_id', sa.Integer(), nullable=False),
        sa.Column('rider_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('time_in_seconds', sa.Integer(), nullable=False),
        sa.Column('gap_in_seconds', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['edition_id'], ['editions.edition_id'], ),
        sa.ForeignKeyConstraint(['rider_id'], ['riders.rider_id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.team_id'], ),
        sa.PrimaryKeyConstraint('gc_id'),
        mysql_charset='utf8mb4',
        mysql_engine='InnoDB'
    )
    
    # Create indexes
    op.create_index('idx_gc_edition_rank', 'general_classifications', ['edition_id', 'rank'])
    op.create_index('idx_gc_rider', 'general_classifications', ['rider_id'])


def downgrade() -> None:
    op.drop_index('idx_gc_rider', table_name='general_classifications')
    op.drop_index('idx_gc_edition_rank', table_name='general_classifications')
    op.drop_table('general_classifications')
