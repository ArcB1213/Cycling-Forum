"""add_forum_performance_indexes

Revision ID: ff82bbf9b5f3
Revises: e5f6a7b8c9d0
Create Date: 2025-12-23 16:49:36.509894

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ff82bbf9b5f3'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    """添加论坛性能优化索引
    
    优化目标：
    1. 软删除字段查询优化
    2. 评论树查询优化（parent_id, root_id）
    3. 帖子列表查询优化（复合索引）
    """
    # 1. 帖子表优化索引
    # 用于帖子列表查询（按创建时间倒序，过滤软删除）
    op.create_index(
        'idx_forum_posts_deleted_created',
        'forum_posts',
        ['is_deleted', sa.text('created_at DESC')],
        unique=False
    )
    
    # 2. 评论表优化索引
    # 用于查询帖子的评论（过滤软删除 + 帖子ID + 父评论ID）
    op.create_index(
        'idx_forum_comments_query',
        'forum_comments',
        ['is_deleted', 'post_id', 'parent_id'],
        unique=False
    )
    
    # 用于通过 root_id 快速查找所有子回复（批量查询优化）
    op.create_index(
        'idx_forum_comments_root_created',
        'forum_comments',
        ['root_id', sa.text('created_at ASC')],
        unique=False
    )
    
    # 用于查询某评论的直接回复
    op.create_index(
        'idx_forum_comments_parent_created',
        'forum_comments',
        ['parent_id', sa.text('created_at ASC')],
        unique=False
    )
    
    # 用于通过作者查询评论
    op.create_index(
        'idx_forum_comments_author',
        'forum_comments',
        ['author_id', 'is_deleted'],
        unique=False
    )


def downgrade():
    """删除论坛性能优化索引"""
    op.drop_index('idx_forum_comments_author', table_name='forum_comments')
    op.drop_index('idx_forum_comments_parent_created', table_name='forum_comments')
    op.drop_index('idx_forum_comments_root_created', table_name='forum_comments')
    op.drop_index('idx_forum_comments_query', table_name='forum_comments')
    op.drop_index('idx_forum_posts_deleted_created', table_name='forum_posts')
