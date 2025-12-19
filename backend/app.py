from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

# 导入数据库会话
from models.database import get_db

# 导入模型
from models.models import Race, Edition, Stage, StageResult, Rider, Team

# 导入 Pydantic 响应模型
from schemas import (
    RaceBase, EditionBase, TeamBase, RiderBase, StageBase,
    EditionsResponse, StagesResponse, StageResultsResponse,
    RiderStatsResponse, RiderRacesResponse, RiderWinsResponse,
    RaceRecord, WinRecord
)

# 导入缓存工具
from cache import cache_response, invalidate_cache, get_cache_stats

# 创建 FastAPI 应用实例
app = FastAPI(
    title="三大环赛数据 API",
    description="提供环法、环意、环西等赛事数据的 RESTful API",
    version="2.0.0"
)

# 配置 CORS - 允许所有来源访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ API 路由 ============

@app.get("/", tags=["Root"])
def index():
    """欢迎页面"""
    return {"message": "欢迎来到三大环赛数据 API！", "docs": "/docs"}


@app.get("/api/races", response_model=List[RaceBase], tags=["Races"])
@cache_response("races", expire=600)
def get_races(db: Session = Depends(get_db)):
    """获取所有赛事 (例如: 环法, 环意)"""
    races = db.query(Race).order_by(Race.race_id).all()
    return [race.to_dict() for race in races]


@app.get("/api/races/{race_id}/editions", response_model=EditionsResponse, tags=["Races"])
@cache_response("race_editions", expire=600)
def get_editions(race_id: int, db: Session = Depends(get_db)):
    """获取某一赛事的所有届数 (年份)"""
    race = db.query(Race).filter(Race.race_id == race_id).first()
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")
    
    editions = db.query(Edition).filter(Edition.race_id == race.race_id).order_by(Edition.year.desc()).all()
    return {"race": race.race_name, "editions": [e.to_dict() for e in editions]}


@app.get("/api/editions/{edition_id}/stages", response_model=StagesResponse, tags=["Editions"])
@cache_response("edition_stages", expire=1800)
def get_stages(edition_id: int, db: Session = Depends(get_db)):
    """获取某一届赛事的所有赛段"""
    edition = db.query(Edition).filter(Edition.edition_id == edition_id).first()
    if not edition:
        raise HTTPException(status_code=404, detail="Edition not found")
    
    stages = db.query(Stage).filter(Stage.edition_id == edition.edition_id).order_by(Stage.stage_number).all()
    return {
        "edition_year": edition.year,
        "race_name": edition.race.race_name,
        "stages": [s.to_dict() for s in stages]
    }


@app.get("/api/stages/{stage_id}/results", response_model=StageResultsResponse, tags=["Stages"])
@cache_response("stage_results", expire=3600)
def get_stage_results(stage_id: int, db: Session = Depends(get_db)):
    """获取某一赛段的完整成绩单 (按排名)"""
    stage = db.query(Stage).filter(Stage.stage_id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    results = db.query(StageResult).filter(StageResult.stage_id == stage.stage_id).order_by(StageResult.rank).all()
    
    # 手动构建包含关联信息的结果
    results_with_relations = []
    for res in results:
        results_with_relations.append({
            "result_id": res.result_id,
            "stage_id": res.stage_id,
            "rider_id": res.rider_id,
            "team_id": res.team_id,
            "rank": res.rank,
            "time_in_seconds": res.time_in_seconds,
            "rider_name": res.rider.rider_name if res.rider else None,
            "team_name": res.team.team_name if res.team else None
        })
    
    return {"stage_info": stage.to_dict(), "results": results_with_relations}


@app.get("/api/riders", response_model=List[RiderBase], tags=["Riders"])
@cache_response("riders", expire=300)
def get_riders(db: Session = Depends(get_db)):
    """获取所有车手列表"""
    riders = db.query(Rider).order_by(Rider.rider_name).all()
    return [rider.to_dict() for rider in riders]


@app.get("/api/riders/{rider_id}", response_model=RiderStatsResponse, tags=["Riders"])
@cache_response("rider_detail", expire=600)
def get_rider_detail(rider_id: int, db: Session = Depends(get_db)):
    """获取单个车手的详细统计信息"""
    rider = db.query(Rider).filter(Rider.rider_id == rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    
    # 统计参赛场次（不同赛段数量）
    total_races = db.query(StageResult.stage_id).filter(StageResult.rider_id == rider.rider_id).distinct().count()
    
    # 统计赛段冠军数（rank=1）
    stage_wins = db.query(StageResult).filter(StageResult.rider_id == rider.rider_id, StageResult.rank == 1).count()
    
    # 获取效力过的所有车队（去重）
    team_ids = db.query(StageResult.team_id).filter(StageResult.rider_id == rider.rider_id).distinct().all()
    teams = [db.query(Team).filter(Team.team_id == tid[0]).first() for tid in team_ids]
    teams = [t.to_dict() for t in teams if t]  # 转换为字典并过滤 None
    
    return {
        "rider": rider.to_dict(),
        "stats": {
            "total_races": total_races,
            "stage_wins": stage_wins,
            "teams": teams
        }
    }   


@app.get("/api/riders/{rider_id}/races", response_model=RiderRacesResponse, tags=["Riders"])
@cache_response("rider_races", expire=1800)
def get_rider_races(rider_id: int, db: Session = Depends(get_db)):
    """获取车手的所有参赛记录"""
    rider = db.query(Rider).filter(Rider.rider_id == rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    
    # 获取该车手所有参赛记录，按年份和赛段排序
    results = (db.query(StageResult)
               .filter(StageResult.rider_id == rider.rider_id)
               .join(Stage, StageResult.stage_id == Stage.stage_id)
               .join(Edition, Stage.edition_id == Edition.edition_id)
               .join(Race, Edition.race_id == Race.race_id)
               .order_by(Edition.year.desc(), Stage.stage_number)
               .all())
    
    race_records = []
    for result in results:
        stage = result.stage
        edition = stage.edition
        race = edition.race
        team = result.team
        
        race_records.append({
            "result_id": result.result_id,
            "race_name": race.race_name,
            "year": edition.year,
            "stage_number": float(stage.stage_number),
            "stage_route": stage.stage_route,
            "rank": result.rank,
            "time_in_seconds": result.time_in_seconds,
            "team_name": team.team_name if team else "Unknown"
        })
    
    return {"rider": rider.to_dict(), "race_records": race_records}


@app.get("/api/riders/{rider_id}/wins", response_model=RiderWinsResponse, tags=["Riders"])
@cache_response("rider_wins", expire=1800)
def get_rider_wins(rider_id: int, db: Session = Depends(get_db)):
    """获取车手的所有赛段冠军记录"""
    rider = db.query(Rider).filter(Rider.rider_id == rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    
    # 获取所有rank=1的记录
    wins = (db.query(StageResult)
            .filter(StageResult.rider_id == rider.rider_id, StageResult.rank == 1)
            .join(Stage, StageResult.stage_id == Stage.stage_id)
            .join(Edition, Stage.edition_id == Edition.edition_id)
            .join(Race, Edition.race_id == Race.race_id)
            .order_by(Edition.year.desc(), Stage.stage_number)
            .all())
    
    win_records = []
    for win in wins:
        stage = win.stage
        edition = stage.edition
        race = edition.race
        team = win.team
        
        win_records.append({
            "result_id": win.result_id,
            "race_name": race.race_name,
            "year": edition.year,
            "stage_number": float(stage.stage_number),
            "stage_route": stage.stage_route,
            "time_in_seconds": win.time_in_seconds,
            "team_name": team.team_name if team else "Unknown"
        })
    
    return {"rider": rider.to_dict(), "win_records": win_records}


# ============ 缓存管理端点 ============

@app.get("/api/cache/stats", tags=["Admin"])
def get_cache_statistics():
    """获取缓存统计信息"""
    return get_cache_stats()


@app.post("/api/cache/clear", tags=["Admin"])
def clear_cache(pattern: str = "*"):
    """清除缓存（管理员功能）"""
    count = invalidate_cache(pattern)
    return {"message": f"已清除 {count} 个缓存键", "pattern": pattern}