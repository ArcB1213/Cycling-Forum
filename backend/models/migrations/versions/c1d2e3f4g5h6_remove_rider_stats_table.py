"""Remove rider_stats table - migrate to real-time calculation

Revision ID: c1d2e3f4g5h6
Revises: 9c1e2d3f4a5b
Create Date: 2026-01-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4g5h6'
down_revision = 'ff82bbf9b5f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """移除 rider_stats 表，改用实时统计"""
    # 删除索引
    op.drop_index('idx_rider_updated_at', table_name='rider_stats')

    # 删除表
    op.drop_table('rider_stats')


def downgrade() -> None:
    """回滚：重新创建 rider_stats 表（紧急回滚用）"""
    # 重新创建 RiderStats 表
    op.create_table(
        'rider_stats',
        sa.Column('stat_id', sa.Integer(), nullable=False),
        sa.Column('rider_id', sa.Integer(), nullable=False),
        sa.Column('total_rating_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_score_sum', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['rider_id'], ['riders.rider_id']),
        sa.PrimaryKeyConstraint('stat_id'),
        sa.UniqueConstraint('rider_id', name='uq_rider_stats_rider_id'),
        mysql_charset='utf8mb4',
        mysql_engine='InnoDB'
    )

    # 重建索引
    op.create_index('idx_rider_updated_at', 'rider_stats', ['rider_id', 'updated_at'])

    # 填充初始数据（从 ratings 表计算）
    op.execute("""
        INSERT INTO rider_stats (rider_id, total_rating_count, total_score_sum, version, updated_at)
        SELECT
            rider_id,
            COUNT(*) as total_rating_count,
            SUM(score) as total_score_sum,
            0 as version,
            NOW() as updated_at
        FROM ratings
        GROUP BY rider_id
    """)
