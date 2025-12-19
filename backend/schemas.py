"""
Pydantic 响应模型定义
用于 FastAPI 的自动序列化和 API 文档生成
"""
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

# ============ 基础模型 ============

class RaceBase(BaseModel):
    """赛事基础模型"""
    race_id: int
    race_name: str
    
    model_config = ConfigDict(from_attributes=True)


class EditionBase(BaseModel):
    """届次基础模型"""
    edition_id: int
    race_id: int
    year: int
    
    model_config = ConfigDict(from_attributes=True)


class TeamBase(BaseModel):
    """车队基础模型"""
    team_id: int
    team_name: str
    
    model_config = ConfigDict(from_attributes=True)


class RiderBase(BaseModel):
    """车手基础模型"""
    rider_id: int
    rider_name: str
    
    model_config = ConfigDict(from_attributes=True)


class StageBase(BaseModel):
    """赛段基础模型"""
    stage_id: int
    edition_id: int
    stage_number: float
    stage_route: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class StageResultBase(BaseModel):
    """赛段成绩基础模型"""
    result_id: int
    stage_id: int
    rider_id: int
    team_id: int
    rank: int
    time_in_seconds: int
    
    model_config = ConfigDict(from_attributes=True)


# ============ 扩展模型（包含关联信息）============

class StageResultWithRelations(StageResultBase):
    """包含车手和车队名称的赛段成绩"""
    rider_name: Optional[str] = None
    team_name: Optional[str] = None


# ============ API 响应模型 ============

class EditionsResponse(BaseModel):
    """赛事届次列表响应"""
    race: str
    editions: List[EditionBase]


class StagesResponse(BaseModel):
    """赛段列表响应"""
    edition_year: int
    race_name: str
    stages: List[StageBase]


class StageResultsResponse(BaseModel):
    """赛段成绩响应"""
    stage_info: StageBase
    results: List[StageResultWithRelations]


class RiderStatsResponse(BaseModel):
    """车手统计响应"""
    rider: RiderBase
    stats: dict  # {"total_races": int, "stage_wins": int, "teams": List[TeamBase]}


class RaceRecord(BaseModel):
    """参赛记录"""
    result_id: int
    race_name: str
    year: int
    stage_number: float
    stage_route: Optional[str]
    rank: int
    time_in_seconds: int
    team_name: str


class RiderRacesResponse(BaseModel):
    """车手参赛记录响应"""
    rider: RiderBase
    race_records: List[RaceRecord]


class WinRecord(BaseModel):
    """冠军记录"""
    result_id: int
    race_name: str
    year: int
    stage_number: float
    stage_route: Optional[str]
    time_in_seconds: int
    team_name: str


class RiderWinsResponse(BaseModel):
    """车手冠军记录响应"""
    rider: RiderBase
    win_records: List[WinRecord]
