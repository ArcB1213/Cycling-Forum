"""
数据库模型定义 - 使用纯 SQLAlchemy 2.0
兼容 MySQL
"""
from sqlalchemy import Integer, String, Numeric, ForeignKey, Index, BigInteger, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import List, Optional
from decimal import Decimal
from datetime import datetime


class Base(DeclarativeBase):
    """所有模型的基类"""
    pass


class Race(Base):
    __tablename__ = 'races'
    
    race_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    race_name: Mapped[str] = mapped_column(
        String(100), 
        unique=True, 
        nullable=False
    )
    
    # 关系
    editions: Mapped[List["Edition"]] = relationship(back_populates='race', lazy='select')

    def to_dict(self):
        return {
            'race_id': self.race_id,
            'race_name': self.race_name,
        }


class Edition(Base):
    __tablename__ = 'editions'
    
    edition_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(ForeignKey('races.race_id'), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # 关系
    race: Mapped["Race"] = relationship(back_populates='editions')
    stages: Mapped[List["Stage"]] = relationship(
        back_populates='edition', 
        lazy='select',
        cascade="all, delete-orphan"
    )
    gc_results: Mapped[List["GeneralClassification"]] = relationship(
        back_populates='edition',
        lazy='select',
        cascade="all, delete-orphan"
    )
    
    # MySQL: 复合唯一索引
    __table_args__ = (
        Index('idx_race_year', 'race_id', 'year', unique=True),
    )

    def to_dict(self):
        return {
            'edition_id': self.edition_id,
            'race_id': self.race_id,
            'year': self.year,
        }


class Team(Base):
    __tablename__ = 'teams'
    
    team_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_name: Mapped[str] = mapped_column(
        String(200), 
        unique=True, 
        nullable=False
    )
    
    # 关系
    results: Mapped[List["StageResult"]] = relationship(back_populates='team', lazy='select')
    gc_results: Mapped[List["GeneralClassification"]] = relationship(back_populates='team', lazy='select')

    def to_dict(self):
        return {
            'team_id': self.team_id,
            'team_name': self.team_name,
        }


class Rider(Base):
    __tablename__ = 'riders'
    
    rider_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rider_name: Mapped[str] = mapped_column(
        String(200), 
        unique=True, 
        nullable=False
    )
    
    # 关系
    results: Mapped[List["StageResult"]] = relationship(back_populates='rider', lazy='select')
    gc_results: Mapped[List["GeneralClassification"]] = relationship(back_populates='rider', lazy='select')
    ratings: Mapped[List["Rating"]] = relationship(
        back_populates='rider',
        lazy='select',
        cascade="all, delete-orphan"
    )
    stats: Mapped[Optional["RiderStats"]] = relationship(
        back_populates='rider',
        lazy='select',
        uselist=False,
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            'rider_id': self.rider_id,
            'rider_name': self.rider_name,
        }


class Stage(Base):
    __tablename__ = 'stages'
    
    stage_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    edition_id: Mapped[int] = mapped_column(
        ForeignKey('editions.edition_id'), 
        nullable=False, 
        index=True
    )
    stage_number: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    stage_route: Mapped[Optional[str]] = mapped_column(
        String(200), 
        nullable=True
    )
    
    # 关系
    edition: Mapped["Edition"] = relationship(back_populates='stages')
    results: Mapped[List["StageResult"]] = relationship(
        back_populates='stage',
        lazy='select',
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            'stage_id': self.stage_id,
            'edition_id': self.edition_id,
            'stage_number': float(self.stage_number),
            'stage_route': self.stage_route,
        }


class StageResult(Base):
    __tablename__ = 'stage_results'
    
    result_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stage_id: Mapped[int] = mapped_column(ForeignKey('stages.stage_id'), nullable=False)
    rider_id: Mapped[int] = mapped_column(ForeignKey('riders.rider_id'), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey('teams.team_id'), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    time_in_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 关系
    stage: Mapped["Stage"] = relationship(back_populates='results')
    rider: Mapped["Rider"] = relationship(back_populates='results')
    team: Mapped["Team"] = relationship(back_populates='results')

    # 复合索引（MySQL 优化）
    __table_args__ = (
        Index('idx_stage_rank', 'stage_id', 'rank'),
        Index('idx_rider_stage', 'rider_id', 'stage_id'),
        Index('idx_team_rank', 'team_id', 'rank'),
        Index('idx_rider_rank', 'rider_id', 'rank'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )

    def to_dict(self, include_relations=False, include_stage=False):
        data = {
            'result_id': self.result_id,
            'stage_id': self.stage_id,
            'rider_id': self.rider_id,
            'team_id': self.team_id,
            'rank': self.rank,
            'time_in_seconds': self.time_in_seconds,
        }
        if include_relations:
            data['rider_name'] = self.rider.rider_name if self.rider else None
            data['team_name'] = self.team.team_name if self.team else None
        if include_stage:
            data['stage'] = self.stage.to_dict() if self.stage else None


class User(Base):
    """用户模型 - 用于认证和授权"""
    __tablename__ = 'users'
    
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    nickname: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, default="/src/assets/default.jpg")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    # 邮箱验证相关字段
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    verification_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verification_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 密码重置相关字段
    reset_password_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reset_password_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 关系
    ratings: Mapped[List["Rating"]] = relationship(
        back_populates='user',
        lazy='select',
        cascade="all, delete-orphan"
    )
    forum_posts: Mapped[List["ForumPost"]] = relationship(
        back_populates='author',
        lazy='select',
        cascade="all, delete-orphan"
    )
    forum_comments: Mapped[List["ForumComment"]] = relationship(
        back_populates='author',
        lazy='select',
        cascade="all, delete-orphan"
    )
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'email': self.email,
            'nickname': self.nickname,
            'avatar': self.avatar,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_verified': self.is_verified,
        }


class Rating(Base):
    """车手评分/评价模型"""
    __tablename__ = 'ratings'
    
    rating_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rider_id: Mapped[int] = mapped_column(ForeignKey('riders.rider_id'), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.user_id'), nullable=False, index=True)
    
    # 评分：1-5 分
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 评价内容（可选）
    comment: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    rider: Mapped["Rider"] = relationship(back_populates='ratings')
    user: Mapped["User"] = relationship(back_populates='ratings')
    
    # 唯一约束：每个用户对每个车手仅限评价一次
    __table_args__ = (
        Index('idx_rider_user_unique', 'rider_id', 'user_id', unique=True),
        Index('idx_created_at', 'created_at'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )
    
    def to_dict(self):
        return {
            'rating_id': self.rating_id,
            'rider_id': self.rider_id,
            'user_id': self.user_id,
            'score': self.score,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user_nickname': self.user.nickname if self.user else None,
        }


class RiderStats(Base):
    """车手评分统计汇总表（乐观锁）"""
    __tablename__ = 'rider_stats'
    
    stat_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rider_id: Mapped[int] = mapped_column(ForeignKey('riders.rider_id'), nullable=False, unique=True, index=True)
    
    # 统计数据
    total_rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_score_sum: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # 乐观锁版本号：每次更新时递增
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # 时间戳
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    rider: Mapped["Rider"] = relationship(back_populates='stats')
    
    __table_args__ = (
        Index('idx_rider_updated_at', 'rider_id', 'updated_at'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )
    
    def to_dict(self):
        avg_score = (
            round(self.total_score_sum / self.total_rating_count, 2)
            if self.total_rating_count > 0
            else 0
        )
        return {
            'stat_id': self.stat_id,
            'rider_id': self.rider_id,
            'total_rating_count': self.total_rating_count,
            'average_score': avg_score,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class GeneralClassification(Base):
    """总成绩排名 (GC)"""
    __tablename__ = 'general_classifications'
    
    gc_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    edition_id: Mapped[int] = mapped_column(ForeignKey('editions.edition_id'), nullable=False, index=True)
    rider_id: Mapped[int] = mapped_column(ForeignKey('riders.rider_id'), nullable=False, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey('teams.team_id'), nullable=False)
    
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    time_in_seconds: Mapped[int] = mapped_column(Integer, nullable=False) # 总用时
    gap_in_seconds: Mapped[int] = mapped_column(Integer, nullable=True) # 与第一名的时间差
    
    # 关系
    edition: Mapped["Edition"] = relationship(back_populates='gc_results')
    rider: Mapped["Rider"] = relationship(back_populates='gc_results')
    team: Mapped["Team"] = relationship(back_populates='gc_results')

    __table_args__ = (
        Index('idx_gc_edition_rank', 'edition_id', 'rank'),
        Index('idx_gc_rider', 'rider_id'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )

    def to_dict(self, include_relations=False):
        data = {
            'gc_id': self.gc_id,
            'edition_id': self.edition_id,
            'rider_id': self.rider_id,
            'team_id': self.team_id,
            'rank': self.rank,
            'time_in_seconds': self.time_in_seconds,
            'gap_in_seconds': self.gap_in_seconds
        }
        if include_relations:
            data['rider_name'] = self.rider.rider_name if self.rider else None
            data['team_name'] = self.team.team_name if self.team else None
            data['race_name'] = self.edition.race.race_name if self.edition and self.edition.race else None
            data['year'] = self.edition.year if self.edition else None
        return data


class ForumPost(Base):
    """论坛帖子表"""
    __tablename__ = 'forum_posts'

    # 基础字段
    post_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(String(10000), nullable=False)

    # 关联字段
    author_id: Mapped[int] = mapped_column(ForeignKey('users.user_id'), nullable=False, index=True)

    # 统计字段（Write-Back 策略：Redis 异步更新）
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 软删除
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # 关系
    author: Mapped["User"] = relationship(back_populates='forum_posts')
    comments: Mapped[List["ForumComment"]] = relationship(
        back_populates='post',
        lazy='select',
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_post_created_at', 'created_at'),
        Index('idx_author_created_at', 'author_id', 'created_at'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )

    def to_dict(self):
        return {
            'post_id': self.post_id,
            'title': self.title,
            'content': self.content,
            'author_id': self.author_id,
            'view_count': self.view_count,
            'comment_count': self.comment_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ForumComment(Base):
    """论坛评论表 - 支持多级嵌套"""
    __tablename__ = 'forum_comments'

    # 基础字段
    comment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(String(2000), nullable=False)

    # 关联字段
    post_id: Mapped[int] = mapped_column(ForeignKey('forum_posts.post_id'), nullable=False, index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.user_id'), nullable=False, index=True)

    # 多级嵌套支持
    # floor_number: 一级评论（楼层号），从 1 开始
    floor_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    # parent_id: 父评论 ID（NULL 表示一级评论）
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey('forum_comments.comment_id'), nullable=True, index=True)
    # root_id: 根评论 ID（指向一级评论，用于快速查询某个楼层的所有子回复）
    root_id: Mapped[Optional[int]] = mapped_column(ForeignKey('forum_comments.comment_id'), nullable=True, index=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 软删除
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 关系
    post: Mapped["ForumPost"] = relationship(back_populates='comments')
    author: Mapped["User"] = relationship(back_populates='forum_comments')
    parent: Mapped[Optional["ForumComment"]] = relationship(
        back_populates='replies',
        remote_side=[comment_id],
        foreign_keys=[parent_id]
    )
    replies: Mapped[List["ForumComment"]] = relationship(
        back_populates='parent',
        cascade="all, delete-orphan",
        foreign_keys=[parent_id]
    )

    __table_args__ = (
        Index('idx_comment_post_created_at', 'post_id', 'created_at'),
        Index('idx_comment_root_id', 'root_id'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )

    def to_dict(self):
        return {
            'comment_id': self.comment_id,
            'content': self.content,
            'post_id': self.post_id,
            'author_id': self.author_id,
            'floor_number': self.floor_number,
            'parent_id': self.parent_id,
            'root_id': self.root_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'author_nickname': self.author.nickname if self.author else None,
            'author_avatar': self.author.avatar if self.author else None,
        }