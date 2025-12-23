"""Add Forum tables for community discussion system

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2025-12-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ForumPost table
    op.create_table(
        'forum_posts',
        sa.Column('post_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.String(10000), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('comment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['author_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('post_id'),
        mysql_charset='utf8mb4',
        mysql_engine='InnoDB'
    )

    # Create indexes for ForumPost table
    op.create_index('idx_post_created_at', 'forum_posts', ['created_at'])
    op.create_index('idx_author_created_at', 'forum_posts', ['author_id', 'created_at'])
    op.create_index('idx_forum_posts_author_id', 'forum_posts', ['author_id'])
    op.create_index('idx_forum_posts_is_deleted', 'forum_posts', ['is_deleted'])

    # Create ForumComment table
    op.create_table(
        'forum_comments',
        sa.Column('comment_id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('content', sa.String(2000), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('floor_number', sa.Integer(), nullable=True),
        sa.Column('parent_id', sa.BigInteger(), nullable=True),
        sa.Column('root_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['post_id'], ['forum_posts.post_id'], ),
        sa.ForeignKeyConstraint(['author_id'], ['users.user_id'], ),
        sa.ForeignKeyConstraint(['parent_id'], ['forum_comments.comment_id'], ),
        sa.ForeignKeyConstraint(['root_id'], ['forum_comments.comment_id'], ),
        sa.PrimaryKeyConstraint('comment_id'),
        mysql_charset='utf8mb4',
        mysql_engine='InnoDB'
    )

    # Create indexes for ForumComment table
    op.create_index('idx_comment_post_created_at', 'forum_comments', ['post_id', 'created_at'])
    op.create_index('idx_comment_root_id', 'forum_comments', ['root_id'])
    op.create_index('idx_forum_comments_post_id', 'forum_comments', ['post_id'])
    op.create_index('idx_forum_comments_author_id', 'forum_comments', ['author_id'])
    op.create_index('idx_forum_comments_floor_number', 'forum_comments', ['floor_number'])
    op.create_index('idx_forum_comments_parent_id', 'forum_comments', ['parent_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_forum_comments_parent_id', table_name='forum_comments')
    op.drop_index('idx_forum_comments_floor_number', table_name='forum_comments')
    op.drop_index('idx_forum_comments_author_id', table_name='forum_comments')
    op.drop_index('idx_forum_comments_post_id', table_name='forum_comments')
    op.drop_index('idx_comment_root_id', table_name='forum_comments')
    op.drop_index('idx_comment_post_created_at', table_name='forum_comments')

    # Drop indexes for ForumPost table
    op.drop_index('idx_forum_posts_is_deleted', table_name='forum_posts')
    op.drop_index('idx_author_created_at', table_name='forum_posts')
    op.drop_index('idx_forum_posts_author_id', table_name='forum_posts')
    op.drop_index('idx_post_created_at', table_name='forum_posts')

    # Drop tables
    op.drop_table('forum_comments')
    op.drop_table('forum_posts')
