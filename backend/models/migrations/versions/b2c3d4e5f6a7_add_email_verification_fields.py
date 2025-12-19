"""add email verification and password reset fields to users table

Revision ID: b2c3d4e5f6a7
Revises: 1dde565034a3
Create Date: 2025-12-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = '1dde565034a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加邮箱验证相关字段
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('verification_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('verification_token_expires_at', sa.DateTime(), nullable=True))
    
    # 添加密码重置相关字段
    op.add_column('users', sa.Column('reset_password_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('reset_password_token_expires_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'reset_password_token_expires_at')
    op.drop_column('users', 'reset_password_token')
    op.drop_column('users', 'verification_token_expires_at')
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'is_verified')
