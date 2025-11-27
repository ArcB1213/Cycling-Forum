from sqlalchemy import Numeric
# 从 extensions.py 导入 db 实例
from models.extensions import db

# 注意：这里不再有 app, Flask, Migrate 的代码

class Race(db.Model):
    __tablename__ = 'races'
    race_id = db.Column(db.Integer, primary_key=True)
    race_name = db.Column(db.String(100), unique=True, nullable=False)
    editions = db.relationship('Edition', back_populates='race', lazy=True)

    def to_dict(self):
        return {
            'race_id': self.race_id,
            'race_name': self.race_name,
        }

class Edition(db.Model):
    __tablename__ = 'editions'
    edition_id = db.Column(db.Integer, primary_key=True)
    race_id = db.Column(db.Integer, db.ForeignKey('races.race_id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    
    race = db.relationship('Race', back_populates='editions')
    stages = db.relationship('Stage', back_populates='edition', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'edition_id': self.edition_id,
            'race_id': self.race_id,
            'year': self.year,
        }

class Team(db.Model):
    __tablename__ = 'teams'
    team_id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String(200), unique=True, nullable=False)
    results = db.relationship('StageResult', back_populates='team', lazy=True)

    def to_dict(self):
        return {
            'team_id': self.team_id,
            'team_name': self.team_name,
        }

class Rider(db.Model):
    __tablename__ = 'riders'
    rider_id = db.Column(db.Integer, primary_key=True)
    rider_name = db.Column(db.String(200), unique=True, nullable=False)
    results = db.relationship('StageResult', back_populates='rider', lazy=True)

    def to_dict(self):
        return {
            'rider_id': self.rider_id,
            'rider_name': self.rider_name,
        }

class Stage(db.Model):
    __tablename__ = 'stages'
    stage_id = db.Column(db.Integer, primary_key=True)
    edition_id = db.Column(db.Integer, db.ForeignKey('editions.edition_id'), nullable=False, index=True) # 保留索引
    stage_number = db.Column(db.Numeric(4, 1), nullable=False) 
    stage_route = db.Column(db.String(200), nullable=True)
    
    edition = db.relationship('Edition', back_populates='stages')
    results = db.relationship('StageResult', back_populates='stage', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'stage_id': self.stage_id,
            'edition_id': self.edition_id,
            'stage_number': float(self.stage_number), # 将 Decimal 转为 float
            'stage_route': self.stage_route,
        }

class StageResult(db.Model):
    __tablename__ = 'stage_results'
    result_id = db.Column(db.Integer, primary_key=True)
    stage_id = db.Column(db.Integer, db.ForeignKey('stages.stage_id'), nullable=False)
    rider_id = db.Column(db.Integer, db.ForeignKey('riders.rider_id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.team_id'), nullable=False)
    rank = db.Column(db.Integer, nullable=False)
    time_in_seconds = db.Column(db.Integer, nullable=False)
    
    stage = db.relationship('Stage', back_populates='results')
    rider = db.relationship('Rider', back_populates='results')
    team = db.relationship('Team', back_populates='results')

    __table_args__ = (
        db.Index('idx_stage_rank', 'stage_id', 'rank'), 
        db.Index('idx_rider_stage', 'rider_id', 'stage_id'), 
        db.Index('idx_team_rank', 'team_id', 'rank'),
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
            # 仅当需要时才加载关联数据，避免性能问题
            data['rider_name'] = self.rider.rider_name if self.rider else None
            data['team_name'] = self.team.team_name if self.team else None
        if include_stage:
            data['stage'] = self.stage.to_dict() if self.stage else None
        return data