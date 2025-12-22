"""Add Rating and RiderStats tables for rider review system

Revision ID: 9c1e2d3f4a5b
Revises: b2c3d4e5f6a7
Create Date: 2025-12-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c1e2d3f4a5b'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create Rating table
    op.create_table(
        'ratings',
        sa.Column('rating_id', sa.Integer(), nullable=False),
        sa.Column('rider_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('comment', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['rider_id'], ['riders.rider_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('rating_id'),
        mysql_charset='utf8mb4',
        mysql_engine='InnoDB'
    )
    
    # Create indexes for Rating table
    op.create_index('idx_rider_user_unique', 'ratings', ['rider_id', 'user_id'], unique=True)
    op.create_index('idx_created_at', 'ratings', ['created_at'])
    op.create_index('idx_ratings_rider_id', 'ratings', ['rider_id'])
    op.create_index('idx_ratings_user_id', 'ratings', ['user_id'])
    
    # Create RiderStats table
    op.create_table(
        'rider_stats',
        sa.Column('stat_id', sa.Integer(), nullable=False),
        sa.Column('rider_id', sa.Integer(), nullable=False),
        sa.Column('total_rating_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_score_sum', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['rider_id'], ['riders.rider_id'], ),
        sa.PrimaryKeyConstraint('stat_id'),
        sa.UniqueConstraint('rider_id', name='uq_rider_stats_rider_id'),
        mysql_charset='utf8mb4',
        mysql_engine='InnoDB'
    )
    
    # Create indexes for RiderStats table
    op.create_index('idx_rider_updated_at', 'rider_stats', ['rider_id', 'updated_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_rider_updated_at', table_name='rider_stats')
    op.drop_index('idx_ratings_user_id', table_name='ratings')
    op.drop_index('idx_ratings_rider_id', table_name='ratings')
    op.drop_index('idx_created_at', table_name='ratings')
    op.drop_index('idx_rider_user_unique', table_name='ratings')
    
    # Drop tables
    op.drop_table('rider_stats')
    op.drop_table('ratings')
