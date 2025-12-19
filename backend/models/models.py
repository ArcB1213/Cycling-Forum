"""
数据库模型定义 - 使用纯 SQLAlchemy 2.0
兼容 MySQL
"""
from sqlalchemy import Integer, String, Numeric, ForeignKey, Index, BigInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import List, Optional
from decimal import Decimal


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
        return data