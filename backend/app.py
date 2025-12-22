from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, text
from sqlalchemy.exc import IntegrityError, OperationalError
from typing import List, Optional
from contextlib import asynccontextmanager
import re
import os
import shutil
import uuid
import asyncio
from pathlib import Path
from datetime import datetime

# 导入数据库会话（同步和异步）
from models.database import get_db, get_async_db,close_db_connections

# 导入模型
from models.models import Race, Edition, Stage, StageResult, Rider, Team, User, Rating, RiderStats

# 导入 Pydantic 响应模型
from schemas import (
    RaceBase, EditionBase, TeamBase, RiderBase, StageBase,
    EditionsResponse, StagesResponse, StageResultsResponse,
    RiderStatsResponse, RiderRacesResponse, RiderWinsResponse,
    RaceRecord, WinRecord,
    UserRegister, UserLogin, UserResponse, TokenResponse, RefreshTokenRequest,
    EmailVerificationRequest, EmailVerificationResponse, VerifyEmailRequest,
    ForgotPasswordRequest, ResetPasswordRequest, MessageResponse, RegisterResponse,
    PaginationMeta, PaginatedRidersResponse, PaginatedStageResultsResponse,
    UpdateNicknameRequest, UpdatePasswordRequest,
    RatingBase, RatingCreate, RatingResponse, RiderRatingStatsResponse,
    RiderDetailWithRatingsResponse, PaginatedRatingsResponse
)

# 导入缓存工具
from cache import cache_response, invalidate_cache, get_cache_stats

# 导入认证工具
from auth import (
    get_password_hash, verify_password, 
    create_access_token, create_refresh_token, 
    get_current_user, get_current_user_async, get_optional_current_user_async, verify_refresh_token,
    generate_verification_token, generate_reset_password_token,
    get_verification_token_expiry, get_reset_password_token_expiry,
    is_token_expired
)

# 导入邮件服务
from email_service import send_verification_email, send_password_reset_email

# 导入限流器
from rate_limiter import limiter, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# 导入缓存相关
from cache import close_async_redis
from cache_warmup import preload_all_caches

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("🚀 应用启动...")
    
    # 初始化异步 Redis 连接
    try:
        from cache import get_async_redis
        await get_async_redis()
        print("✓ Redis 异步客户端初始化完成")
    except Exception as e:
        print(f"✗ Redis 异步客户端初始化失败: {e}")
    
    # 缓存预热
    try:
        async for db in get_async_db():
            await preload_all_caches(db)
            break
    except Exception as e:
        print(f"⚠️  缓存预热失败: {e}")
    
    yield
    
    # 关闭时
    print("🛑 应用关闭，清理 Redis 连接...")
    await close_async_redis()
    await close_db_connections()


# 创建 FastAPI 应用实例
app = FastAPI(
    title="三大环赛数据 API",
    description="提供环法、环意、环西等赛事数据的 RESTful API",
    version="2.0.0",
    lifespan=lifespan
)

# 配置 CORS - 允许所有来源访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置限流器
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# 创建上传目录
UPLOAD_DIR = Path("uploads/avatars")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 挂载静态文件服务（用于访问上传的头像）
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ============ 文件操作辅助函数 ============

def delete_old_avatar(avatar_path: str) -> None:
    """
    删除旧头像文件
    
    Args:
        avatar_path: 相对路径，例如 "/uploads/avatars/uuid.jpg"
    
    注意：
        - 不删除默认头像 ("default")
        - 如果文件不存在不抛出异常
    """
    # 检查是否是默认头像
    if not avatar_path or avatar_path == "default":
        return
    
    try:
        # 从相对路径提取文件名
        # 处理格式："/uploads/avatars/filename.ext" 或 "uploads/avatars/filename.ext"
        if "/" in avatar_path:
            filename = avatar_path.split("/")[-1]
        else:
            filename = avatar_path
        
        # 构建完整文件路径
        file_path = UPLOAD_DIR / filename
        
        # 安全检查：确保路径在上传目录内
        if file_path.parent != UPLOAD_DIR:
            print(f"[WARN] 试图删除目录外的文件: {file_path}")
            return
        
        # 删除文件
        if file_path.exists():
            file_path.unlink()
            print(f"[INFO] 已删除旧头像: {filename}")
        else:
            print(f"[WARN] 旧头像文件不存在: {filename}")
    except Exception as e:
        print(f"[ERROR] 删除旧头像失败: {str(e)}")


# ============ API 路由 ============

@app.get("/", tags=["Root"])
def index():
    """欢迎页面"""
    return {"message": "欢迎来到三大环赛数据 API！", "docs": "/docs"}


# ============ 异步 API 路由（高并发优化）============

@app.get("/api/async/races", response_model=List[RaceBase], tags=["Races (Async)"])
@cache_response("races_async", expire=600)
async def get_races_async(db: AsyncSession = Depends(get_async_db)):
    """获取所有赛事 (例如: 环法, 环意) - 异步版本（推荐用于高并发）"""
    result = await db.execute(select(Race).order_by(Race.race_id))
    races = result.scalars().all()
    return [race.to_dict() for race in races]


@app.get("/api/async/races/{race_id}/editions", response_model=EditionsResponse, tags=["Races (Async)"])
@cache_response("race_editions_async", expire=600)
async def get_editions_async(race_id: int, db: AsyncSession = Depends(get_async_db)):
    """获取某一赛事的所有届数 (年份) - 异步版本（推荐用于高并发）"""
    # 查询 Race
    result = await db.execute(select(Race).filter(Race.race_id == race_id))
    race = result.scalar_one_or_none()
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")
    
    # 查询 Editions
    result = await db.execute(
        select(Edition)
        .filter(Edition.race_id == race.race_id)
        .order_by(Edition.year.desc())
    )
    editions = result.scalars().all()
    return {"race": race.race_name, "editions": [e.to_dict() for e in editions]}


@app.get("/api/async/editions/{edition_id}/stages", response_model=StagesResponse, tags=["Editions (Async)"])
@cache_response("edition_stages_async", expire=1800)
async def get_stages_async(edition_id: int, db: AsyncSession = Depends(get_async_db)):
    """获取某一届赛事的所有赛段 - 异步版本（推荐用于高并发）"""
    # 预加载 race 关联，避免懒加载问题
    result = await db.execute(
        select(Edition)
        .options(selectinload(Edition.race))
        .filter(Edition.edition_id == edition_id)
    )
    edition = result.scalar_one_or_none()
    if not edition:
        raise HTTPException(status_code=404, detail="Edition not found")
    
    # 查询 Stages
    result = await db.execute(
        select(Stage)
        .filter(Stage.edition_id == edition.edition_id)
        .order_by(Stage.stage_number)
    )
    stages = result.scalars().all()
    
    return {
        "edition_year": edition.year,
        "race_name": edition.race.race_name if edition.race else None,
        "stages": [s.to_dict() for s in stages]
    }


@app.get("/api/async/stages/{stage_id}/results", response_model=PaginatedStageResultsResponse, tags=["Stages (Async)"])
@cache_response("stage_results_async", expire=3600)
async def get_stage_results_async(stage_id: int, page: int = 1, limit: int = 20, db: AsyncSession = Depends(get_async_db)):
    """获取某一赛段的完整成绩单 (按排名) - 异步版本（推荐用于高并发）"""
    result = await db.execute(select(Stage).filter(Stage.stage_id == stage_id))
    stage = result.scalar_one_or_none()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    # 计算总记录数
    count_result = await db.execute(
        select(func.count()).select_from(StageResult).filter(StageResult.stage_id == stage.stage_id)
    )
    total = count_result.scalar() or 0
    
    # 计算分页参数
    total_pages = (total + limit - 1) // limit
    offset = (page - 1) * limit
    
    # 使用 selectinload 预加载关联数据，避免 N+1 查询问题
    result = await db.execute(
        select(StageResult)
        .options(
            selectinload(StageResult.rider),
            selectinload(StageResult.team)
        )
        .filter(StageResult.stage_id == stage.stage_id)
        .order_by(StageResult.rank)
        .offset(offset)
        .limit(limit)
    )
    results = result.scalars().all()
    
    # 构建包含关联信息的结果
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
    
    return {
        "stage_info": stage.to_dict(),
        "data": results_with_relations,
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


# ============ 异步骑手相关 API ============

@app.get("/api/async/riders", response_model=PaginatedRidersResponse, tags=["Riders (Async)"])
@cache_response("riders_async", expire=300)
async def get_riders_async(page: int = 1, limit: int = 16, search: str = None, db: AsyncSession = Depends(get_async_db)):
    """获取所有车手列表 - 异步版本（推荐用于高并发）
    
    参数:
    - page: 页码，从 1 开始
    - limit: 每页记录数，默认 16
    - search: 可选，搜索车手姓名（模糊匹配）
    """
    # 构建查询条件
    query = select(Rider)
    count_query = select(func.count()).select_from(Rider)
    
    # 如果有搜索词，添加模糊查询条件
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(Rider.rider_name.ilike(search_pattern))
        count_query = count_query.filter(Rider.rider_name.ilike(search_pattern))
    
    # 计算总记录数
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # 计算分页参数
    total_pages = (total + limit - 1) // limit
    offset = (page - 1) * limit
    
    # 查询分页数据
    result = await db.execute(
        query.order_by(Rider.rider_name).offset(offset).limit(limit)
    )
    riders = result.scalars().all()
    
    return {
        "data": [rider.to_dict() for rider in riders],
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


@app.get("/api/async/riders/{rider_id}", response_model=RiderStatsResponse, tags=["Riders (Async)"])
@cache_response("rider_detail_async", expire=600)
async def get_rider_detail_async(rider_id: int, db: AsyncSession = Depends(get_async_db)):
    """获取单个车手的详细统计信息 - 异步版本（推荐用于高并发）"""
    result = await db.execute(select(Rider).filter(Rider.rider_id == rider_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    
    # 统计参赛场次（不同赛段数量）
    result = await db.execute(
        select(StageResult.stage_id)
        .filter(StageResult.rider_id == rider.rider_id)
        .distinct()
    )
    total_races = len(result.all())
    
    # 统计赛段冠军数（rank=1）
    result = await db.execute(
        select(StageResult)
        .filter(StageResult.rider_id == rider.rider_id, StageResult.rank == 1)
    )
    stage_wins = len(result.all())
    
    # 获取效力过的所有车队（去重）
    result = await db.execute(
        select(StageResult.team_id)
        .filter(StageResult.rider_id == rider.rider_id)
        .distinct()
    )
    team_ids = [tid[0] for tid in result.all()]
    
    # 批量查询车队信息
    teams = []
    if team_ids:
        result = await db.execute(
            select(Team).filter(Team.team_id.in_(team_ids))
        )
        teams = [t.to_dict() for t in result.scalars().all()]
    
    return {
        "rider": rider.to_dict(),
        "stats": {
            "total_races": total_races,
            "stage_wins": stage_wins,
            "teams": teams
        }
    }


@app.get("/api/async/riders/{rider_id}/races", response_model=RiderRacesResponse, tags=["Riders (Async)"])
@cache_response("rider_races_async", expire=1800)
async def get_rider_races_async(
    rider_id: int, 
    page: int = 1, 
    limit: int = 20, 
    db: AsyncSession = Depends(get_async_db)
):
    """获取车手的所有参赛记录 - 异步版本（推荐用于高并发）
    
    参数:
    - page: 页码，从 1 开始
    - limit: 每页记录数，默认 20
    """
    result = await db.execute(select(Rider).filter(Rider.rider_id == rider_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    
    # 计算总记录数
    count_result = await db.execute(
        select(func.count())
        .select_from(StageResult)
        .filter(StageResult.rider_id == rider.rider_id)
    )
    total = count_result.scalar() or 0
    
    # 计算分页参数
    total_pages = (total + limit - 1) // limit
    offset = (page - 1) * limit
    
    # 预加载所有关联数据，避免 N+1 查询
    result = await db.execute(
        select(StageResult)
        .options(
            selectinload(StageResult.stage).selectinload(Stage.edition).selectinload(Edition.race),
            selectinload(StageResult.team)
        )
        .filter(StageResult.rider_id == rider.rider_id)
        .join(Stage, StageResult.stage_id == Stage.stage_id)
        .join(Edition, Stage.edition_id == Edition.edition_id)
        .order_by(Edition.year.desc(), Stage.stage_number)
        .offset(offset)
        .limit(limit)
    )
    results = result.scalars().all()
    
    race_records = []
    for result_item in results:
        stage = result_item.stage
        edition = stage.edition
        race = edition.race
        team = result_item.team
        
        race_records.append({
            "result_id": result_item.result_id,
            "race_name": race.race_name,
            "year": edition.year,
            "stage_number": float(stage.stage_number),
            "stage_route": stage.stage_route,
            "rank": result_item.rank,
            "time_in_seconds": result_item.time_in_seconds,
            "team_name": team.team_name if team else "Unknown"
        })
    
    return {
        "rider": rider.to_dict(), 
        "data": race_records,
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


@app.get("/api/async/riders/{rider_id}/wins", response_model=RiderWinsResponse, tags=["Riders (Async)"])
@cache_response("rider_wins_async", expire=1800)
async def get_rider_wins_async(rider_id: int, db: AsyncSession = Depends(get_async_db)):
    """获取车手的所有赛段冠军记录 - 异步版本（推荐用于高并发）"""
    result = await db.execute(select(Rider).filter(Rider.rider_id == rider_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    
    # 预加载所有关联数据
    result = await db.execute(
        select(StageResult)
        .options(
            selectinload(StageResult.stage).selectinload(Stage.edition).selectinload(Edition.race),
            selectinload(StageResult.team)
        )
        .filter(StageResult.rider_id == rider.rider_id, StageResult.rank == 1)
        .join(Stage, StageResult.stage_id == Stage.stage_id)
        .join(Edition, Stage.edition_id == Edition.edition_id)
        .order_by(Edition.year.desc(), Stage.stage_number)
    )
    wins = result.scalars().all()
    
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


# ============ 异步认证相关 API ============

@app.post("/api/async/auth/register", response_model=RegisterResponse, tags=["Authentication (Async)"])
@limiter.limit("2/minute")
async def register_user_async(request: Request, response: Response, user_data: UserRegister, db: AsyncSession = Depends(get_async_db)):
    """用户注册 - 异步版本（推荐用于高并发）
    限流：每个 IP 每分钟最多 2 次请求
    """
    # 验证邮箱格式
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, user_data.email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    
    # 检查邮箱是否已存在
    result = await db.execute(select(User).filter(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        if not existing_user.is_verified and is_token_expired(existing_user.verification_token_expires_at):
            await db.delete(existing_user)
            await db.commit()
        else:
            raise HTTPException(status_code=400, detail="该邮箱已被注册")
    
    # 检查昵称是否已存在
    result = await db.execute(select(User).filter(User.nickname == user_data.nickname))
    existing_nickname = result.scalar_one_or_none()
    if existing_nickname:
        if not existing_nickname.is_verified and is_token_expired(existing_nickname.verification_token_expires_at):
            await db.delete(existing_nickname)
            await db.commit()
        else:
            raise HTTPException(status_code=400, detail="该昵称已被使用")
    
    # 生成验证令牌
    verification_token = generate_verification_token()
    verification_expires = get_verification_token_expiry()
    
    # 在线程池中执行密码哈希（CPU密集型操作）
    loop = asyncio.get_event_loop()
    hashed_password = await loop.run_in_executor(None, get_password_hash, user_data.password)
    
    # 创建新用户
    new_user = User(
        email=user_data.email,
        nickname=user_data.nickname,
        hashed_password=hashed_password,
        avatar=user_data.avatar or "default",
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires_at=verification_expires
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # 发送验证邮件（在线程池中执行，避免阻塞）
    email_sent = await loop.run_in_executor(
        None,
        send_verification_email,
        new_user.email,
        new_user.nickname,
        verification_token
    )
    
    if not email_sent:
        await db.delete(new_user)
        await db.commit()
        raise HTTPException(status_code=500, detail="发送验证邮件失败，请稍后重试")
    
    return RegisterResponse(
        message="注册成功！请查收邮件并点击链接验证您的邮箱。",
        email=new_user.email,
        requires_verification=True
    )


@app.post("/api/async/auth/login", response_model=TokenResponse, tags=["Authentication (Async)"])
@limiter.limit("10/minute")
async def login_user_async(request: Request, response: Response, login_data: UserLogin, db: AsyncSession = Depends(get_async_db)):
    """用户登录 - 异步版本（推荐用于高并发）
    限流：每个 IP 每分钟最多 10 次请求
    """
    # 查找用户
    result = await db.execute(select(User).filter(User.email == login_data.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    
    # 检查邮箱是否已验证
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="请先验证您的邮箱后再登录")
    
    # 在线程池中验证密码（CPU密集型操作）
    loop = asyncio.get_event_loop()
    password_valid = await loop.run_in_executor(
        None,
        verify_password,
        login_data.password,
        user.hashed_password
    )
    
    if not password_valid:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    
    # 生成 Token
    access_token = create_access_token(data={"sub": str(user.user_id)})
    refresh_token = create_refresh_token(data={"sub": str(user.user_id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }


@app.post("/api/async/auth/verify-email", response_model=MessageResponse, tags=["Authentication (Async)"])
@limiter.limit("5/minute")
async def verify_email_async(request: Request, response: Response, verify_data: VerifyEmailRequest, db: AsyncSession = Depends(get_async_db)):
    """验证邮箱 - 异步版本
    限流：每个 IP 每分钟最多 5 次请求
    """
    result = await db.execute(select(User).filter(User.verification_token == verify_data.token))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=400, detail="无效的验证链接")
    
    if user.is_verified:
        return MessageResponse(message="邮箱已验证，无需重复验证", success=True)
    
    if is_token_expired(user.verification_token_expires_at):
        raise HTTPException(status_code=400, detail="验证链接已过期，请重新发送验证邮件")
    
    # 验证成功
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    await db.commit()
    
    return MessageResponse(message="邮箱验证成功！现在可以登录了。", success=True)


@app.post("/api/async/auth/refresh", response_model=TokenResponse, tags=["Authentication (Async)"])
async def refresh_access_token_async(refresh_data: RefreshTokenRequest, db: AsyncSession = Depends(get_async_db)):
    """使用 Refresh Token 刷新 Access Token - 异步版本（推荐用于高并发）
    
    功能：
    - 验证 Refresh Token 的有效性
    - 生成新的 Access Token 和 Refresh Token
    - 高频调用场景（前端 token 过期自动刷新）
    """
    user_id = verify_refresh_token(refresh_data.refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的 Refresh Token")
    
    result = await db.execute(select(User).filter(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    # 生成新的 Token（sub 必须是字符串）
    access_token = create_access_token(data={"sub": str(user.user_id)})
    refresh_token = create_refresh_token(data={"sub": str(user.user_id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }


@app.post("/api/async/auth/resend-verification", response_model=MessageResponse, tags=["Authentication (Async)"])
@limiter.limit("3/hour")
async def resend_verification_email_async(request: Request, response: Response, email_data: EmailVerificationRequest, db: AsyncSession = Depends(get_async_db)):
    """重新发送验证邮件 - 异步版本（推荐用于高并发）
    
    功能：
    - 为未验证用户重新发送邮箱验证邮件
    - 使用线程池执行邮件发送，避免阻塞事件循环
    
    限流：每个 IP 每小时最多 3 次请求
    """
    result = await db.execute(select(User).filter(User.email == email_data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        # 为了安全，不透露邮箱是否存在
        return MessageResponse(message="如果该邮箱已注册，验证邮件将发送到该地址。", success=True)
    
    if user.is_verified:
        raise HTTPException(status_code=400, detail="该邮箱已验证，无需重复验证")
    
    # 生成新的验证令牌
    verification_token = generate_verification_token()
    verification_expires = get_verification_token_expiry()
    
    user.verification_token = verification_token
    user.verification_token_expires_at = verification_expires
    await db.commit()
    
    # 在线程池中发送验证邮件（避免阻塞）
    loop = asyncio.get_event_loop()
    email_sent = await loop.run_in_executor(
        None,
        send_verification_email,
        user.email,
        user.nickname,
        verification_token
    )
    
    if not email_sent:
        raise HTTPException(status_code=500, detail="发送验证邮件失败，请稍后重试")
    
    return MessageResponse(message="验证邮件已发送，请查收。", success=True)


@app.post("/api/async/auth/forgot-password", response_model=MessageResponse, tags=["Authentication (Async)"])
@limiter.limit("10/hour")
async def forgot_password_async(request: Request, response: Response, forgot_data: ForgotPasswordRequest, db: AsyncSession = Depends(get_async_db)):
    """发送密码重置邮件 - 异步版本（推荐用于高并发）
    
    功能：
    - 验证用户邮箱并发送密码重置链接
    - 使用线程池执行邮件发送，避免阻塞事件循环
    
    限流：每个 IP 每小时最多 10 次请求
    """
    result = await db.execute(select(User).filter(User.email == forgot_data.email))
    user = result.scalar_one_or_none()
    
    # 为了安全，无论邮箱是否存在都返回相同的消息
    if not user or not user.is_verified:
        return MessageResponse(message="如果该邮箱已注册并验证，密码重置邮件将发送到该地址。", success=True)
    
    # 生成密码重置令牌
    reset_token = generate_reset_password_token()
    reset_expires = get_reset_password_token_expiry()
    
    user.reset_password_token = reset_token
    user.reset_password_token_expires_at = reset_expires
    await db.commit()
    
    # 在线程池中发送密码重置邮件（避免阻塞）
    loop = asyncio.get_event_loop()
    email_sent = await loop.run_in_executor(
        None,
        send_password_reset_email,
        user.email,
        user.nickname,
        reset_token
    )
    
    if not email_sent:
        raise HTTPException(status_code=500, detail="发送邮件失败，请稍后重试")
    
    return MessageResponse(message="如果该邮箱已注册并验证，密码重置邮件将发送到该地址。", success=True)


# ============ 原同步路由继续保持（向后兼容）============

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


# ============ 用户认证端点 ============
@app.post("/api/auth/reset-password", response_model=MessageResponse, tags=["Authentication"])
def reset_password(reset_data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """使用令牌重置密码"""
    user = db.query(User).filter(User.reset_password_token == reset_data.token).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="无效的重置链接")
    
    # 检查令牌是否过期
    if is_token_expired(user.reset_password_token_expires_at):
        raise HTTPException(status_code=400, detail="重置链接已过期，请重新申请")
    
    # 更新密码
    user.hashed_password = get_password_hash(reset_data.new_password)
    user.reset_password_token = None
    user.reset_password_token_expires_at = None
    db.commit()
    
    return MessageResponse(message="密码重置成功！现在可以使用新密码登录了。", success=True)


@app.get("/api/auth/me", response_model=UserResponse, tags=["Authentication"])
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user


@app.put("/api/auth/update-nickname", response_model=UserResponse, tags=["Authentication"])
def update_nickname(
    update_data: UpdateNicknameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改用户昵称"""
    # 检查昵称是否已被使用
    existing_user = db.query(User).filter(
        User.nickname == update_data.nickname,
        User.user_id != current_user.user_id
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="该昵称已被使用")
    
    # 更新昵称
    current_user.nickname = update_data.nickname
    db.commit()
    db.refresh(current_user)
    
    return current_user


@app.put("/api/auth/update-password", response_model=MessageResponse, tags=["Authentication"])
def update_password(
    update_data: UpdatePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改密码"""
    # 验证当前密码
    if not verify_password(update_data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="当前密码错误")
    
    # 检查新密码是否与当前密码相同
    if verify_password(update_data.new_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")
    
    # 更新密码
    current_user.hashed_password = get_password_hash(update_data.new_password)
    db.commit()
    
    return MessageResponse(message="密码修改成功", success=True)


# ============ 文件上传端点 ============

@app.post("/api/upload/avatar", tags=["Upload"])
async def upload_avatar(file: UploadFile = File(...)):
    """上传用户头像"""
    # 验证文件类型
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="只支持 JPG、PNG、GIF、WebP 格式的图片")
    
    # 验证文件大小 (5MB)
    MAX_SIZE = 5 * 1024 * 1024
    if file.size and file.size > MAX_SIZE:
        raise HTTPException(status_code=400, detail="文件大小不能超过 5MB")
    
    # 生成安全的文件名
    ext = file.filename.split(".")[-1] if file.filename else "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = UPLOAD_DIR / filename
    
    # 保存文件
    try:
        with filepath.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")
    
    # 返回完整的可访问 URL（包含后端服务器地址）
    avatar_url = f"http://127.0.0.1:8000/uploads/avatars/{filename}"
    return {"avatar_url": avatar_url}


@app.post("/api/auth/update-avatar", response_model=UserResponse, tags=["Authentication"])
async def update_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传并更新用户头像
    
    功能：
    - 验证图片格式和大小
    - 删除旧头像文件（默认头像除外）
    - 保存新头像
    
    支持格式：JPG, PNG, GIF, WebP
    最大大小：5MB
    """
    # 验证文件类型
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="只支持 JPG、PNG、GIF、WebP 格式的图片")
    
    # 验证文件大小 (5MB)
    MAX_SIZE = 5 * 1024 * 1024
    if file.size and file.size > MAX_SIZE:
        raise HTTPException(status_code=400, detail="文件大小不能超过 5MB")
    
    # 保存旧头像路径（用于删除）
    old_avatar = current_user.avatar
    
    # 生成安全的文件名
    ext = file.filename.split(".")[-1] if file.filename else "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = UPLOAD_DIR / filename
    
    # 保存文件
    try:
        with filepath.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")
    
    # 更新用户头像路径 (存储相对路径)
    avatar_path = f"/uploads/avatars/{filename}"
    current_user.avatar = avatar_path
    db.commit()
    db.refresh(current_user)
    
    # 异步删除旧头像（不阻塞响应）
    if old_avatar and old_avatar != "default":
        delete_old_avatar(old_avatar)
    
    return current_user


# ============ 车手评分系统 API ============

@app.post("/api/riders/{rider_id}/ratings", response_model=RatingResponse, tags=["Ratings"])
@limiter.limit("5/minute")
async def submit_rating(
    request: Request, 
    response: Response,
    rider_id: int,
    rating_data: RatingCreate,
    current_user: User = Depends(get_current_user_async),
    db: AsyncSession = Depends(get_async_db)
):
    """提交或更新车手评分
    
    功能：
    - 用户对车手进行 1-5 分评分并可附带评价
    - 每个用户对每个车手仅限评价一次（重复提交则更新）
    - 使用 MySQL UPSERT 原子操作更新 RiderStats 汇总表，解决高并发问题
    
    限流：每个 IP 每分钟最多 5 次请求
    """
    # 验证车手是否存在
    result = await db.execute(select(Rider).filter(Rider.rider_id == rider_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="车手不存在")
    
    # 查询该用户对该车手的历史评分
    result = await db.execute(
        select(Rating).filter(
            Rating.rider_id == rider_id,
            Rating.user_id == current_user.user_id
        )
    )
    existing_rating = result.scalar_one_or_none()
    
    if existing_rating:
        # ========== 更新已有评分 ==========
        old_score = existing_rating.score
        score_diff = rating_data.score - old_score
        
        existing_rating.score = rating_data.score
        existing_rating.comment = rating_data.comment
        existing_rating.updated_at = datetime.utcnow()
        
        # 使用 MySQL UPSERT 原子更新统计表
        # 如果 RiderStats 不存在则插入（score_diff 作为初始值），存在则更新
        await db.execute(
            text("""
                INSERT INTO rider_stats (rider_id, total_rating_count, total_score_sum, version, updated_at)
                VALUES (:rider_id, 1, :score_diff, 1, NOW())
                ON DUPLICATE KEY UPDATE
                    total_score_sum = total_score_sum + :score_diff,
                    version = version + 1,
                    updated_at = NOW()
            """),
            {"rider_id": rider_id, "score_diff": score_diff}
        )
        
        await db.commit()
        await db.refresh(existing_rating)
        existing_rating.user = current_user
        
        # 清除该车手的评分相关缓存，确保前端获取最新数据
        invalidate_cache(f"rider_rating_stats:{rider_id}:*")
        invalidate_cache(f"rider_detail_with_ratings:{rider_id}:*")
        
        return existing_rating.to_dict()
    else:
        # ========== 新增评分 ==========
        new_rating = Rating(
            rider_id=rider_id,
            user_id=current_user.user_id,
            score=rating_data.score,
            comment=rating_data.comment
        )
        db.add(new_rating)
        
        # 使用 MySQL UPSERT 原子更新统计表
        # 如果 RiderStats 不存在则插入，存在则累加
        await db.execute(
            text("""
                INSERT INTO rider_stats (rider_id, total_rating_count, total_score_sum, version, updated_at)
                VALUES (:rider_id, 1, :score, 1, NOW())
                ON DUPLICATE KEY UPDATE
                    total_rating_count = total_rating_count + 1,
                    total_score_sum = total_score_sum + :score,
                    version = version + 1,
                    updated_at = NOW()
            """),
            {"rider_id": rider_id, "score": rating_data.score}
        )
        
        await db.commit()
        await db.refresh(new_rating)
        new_rating.user = current_user
        
        # 清除该车手的评分相关缓存，确保前端获取最新数据
        invalidate_cache(f"rider_rating_stats:{rider_id}:*")
        invalidate_cache(f"rider_detail_with_ratings:{rider_id}:*")
        
        return new_rating.to_dict()


@app.get("/api/riders/{rider_id}/rating-stats", response_model=RiderRatingStatsResponse, tags=["Ratings"])
@cache_response("rider_rating_stats", expire=300)
async def get_rider_rating_stats(
    rider_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """获取车手评分统计（带缓存）
    
    功能：
    - 获取车手的平均分和总评价人数
    - 数据缓存 5 分钟，提高查询性能
    - 如果没有评价，返回 0 分
    """
    # 验证车手是否存在
    result = await db.execute(select(Rider).filter(Rider.rider_id == rider_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="车手不存在")
    
    # 获取统计数据
    result = await db.execute(
        select(RiderStats).filter(RiderStats.rider_id == rider_id)
    )
    rider_stats = result.scalar_one_or_none()
    
    if not rider_stats:
        # 尚无评分，返回默认统计
        return {
            "stat_id": 0,
            "rider_id": rider_id,
            "total_rating_count": 0,
            "average_score": 0,
            "updated_at": datetime.utcnow()
        }
    
    return rider_stats.to_dict()


@app.get("/api/riders/{rider_id}/ratings", response_model=PaginatedRatingsResponse, tags=["Ratings"])
async def get_rider_ratings(
    rider_id: int,
    page: int = 1,
    limit: int = 10,
    db: AsyncSession = Depends(get_async_db)
):
    """获取车手的评价列表（分页）
    
    功能：
    - 按最新时间降序展示所有评价
    - 支持分页查询
    - 每个评价显示评分、评论和评价者昵称
    """
    # 验证车手是否存在
    result = await db.execute(select(Rider).filter(Rider.rider_id == rider_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="车手不存在")
    
    # 计算总记录数
    count_result = await db.execute(
        select(func.count()).select_from(Rating).filter(Rating.rider_id == rider_id)
    )
    total = count_result.scalar() or 0
    
    # 计算分页参数
    total_pages = (total + limit - 1) // limit
    offset = (page - 1) * limit
    
    # 查询分页数据（按创建时间降序）
    result = await db.execute(
        select(Rating)
        .options(selectinload(Rating.user))
        .filter(Rating.rider_id == rider_id)
        .order_by(Rating.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    ratings = result.scalars().all()
    
    return {
        "data": [r.to_dict() for r in ratings],
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


@app.get("/api/riders/{rider_id}/my-rating", response_model=Optional[RatingResponse], tags=["Ratings"])
async def get_my_rating(
    rider_id: int,
    current_user: User = Depends(get_current_user_async),
    db: AsyncSession = Depends(get_async_db)
):
    """获取当前用户对该车手的评分
    
    功能：
    - 查询当前登录用户是否已评分该车手
    - 如果已评分，返回评分详情；否则返回 null
    """
    # 验证车手是否存在
    result = await db.execute(select(Rider).filter(Rider.rider_id == rider_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="车手不存在")
    
    # 查询用户的评分
    result = await db.execute(
        select(Rating).filter(
            Rating.rider_id == rider_id,
            Rating.user_id == current_user.user_id
        )
    )
    rating = result.scalar_one_or_none()
    
    if rating:
        return rating.to_dict()
    else:
        return None


@app.delete("/api/riders/{rider_id}/ratings", response_model=MessageResponse, tags=["Ratings"])
@limiter.limit("10/minute")
async def delete_rating(
    request: Request,
    response: Response,
    rider_id: int,
    current_user: User = Depends(get_current_user_async),
    db: AsyncSession = Depends(get_async_db)
):
    """删除车手评分
    
    功能：
    - 用户删除自己对某车手的评分
    - 使用 MySQL 原子操作更新 RiderStats 汇总表（减少计数和总分）
    - 清除相关缓存确保数据一致性
    
    限流：每个 IP 每分钟最多 10 次请求
    """
    # 验证车手是否存在
    result = await db.execute(select(Rider).filter(Rider.rider_id == rider_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="车手不存在")
    
    # 查询该用户对该车手的评分
    result = await db.execute(
        select(Rating).filter(
            Rating.rider_id == rider_id,
            Rating.user_id == current_user.user_id
        )
    )
    existing_rating = result.scalar_one_or_none()
    
    if not existing_rating:
        raise HTTPException(status_code=404, detail="您尚未对该车手进行评分")
    
    # 保存评分信息（用于更新统计）
    deleted_score = existing_rating.score
    
    # 删除评分记录
    await db.delete(existing_rating)
    
    # 使用 MySQL 原子操作更新 RiderStats
    # 减少评分计数和总分
    await db.execute(
        text("""
            UPDATE rider_stats
            SET total_rating_count = GREATEST(0, total_rating_count - 1),
                total_score_sum = GREATEST(0, total_score_sum - :score),
                version = version + 1,
                updated_at = NOW()
            WHERE rider_id = :rider_id
        """),
        {"rider_id": rider_id, "score": deleted_score}
    )
    
    await db.commit()
    
    # 清除该车手的评分相关缓存
    invalidate_cache(f"rider_rating_stats:{rider_id}:*")
    invalidate_cache(f"rider_detail_with_ratings:{rider_id}:*")
    
    return MessageResponse(message="评分已删除", success=True)


@app.get("/api/riders/{rider_id}/detail-with-ratings", response_model=RiderDetailWithRatingsResponse, tags=["Ratings"])
@cache_response("rider_detail_with_ratings", expire=300)
async def get_rider_detail_with_ratings(
    rider_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user_async),
    db: AsyncSession = Depends(get_async_db)
):
    """获取车手详细信息（包含评分汇总和最近评价）
    
    功能：
    - 综合展示车手基本信息、评分统计、当前用户的评分、最近 5 条评价
    - 前端在车手详情页可直接调用本端点
    - 需要登录才能看到当前用户的评分
    """
    # 查询车手基本信息
    result = await db.execute(select(Rider).filter(Rider.rider_id == rider_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="车手不存在")
    
    # 获取评分统计
    result = await db.execute(
        select(RiderStats).filter(RiderStats.rider_id == rider_id)
    )
    rider_stats = result.scalar_one_or_none()
    stats_dict = rider_stats.to_dict() if rider_stats else None
    
    # 获取当前用户的评分（如果已登录）
    user_rating = None
    if current_user:
        result = await db.execute(
            select(Rating).filter(
                Rating.rider_id == rider_id,
                Rating.user_id == current_user.user_id
            )
        )
        user_rating_obj = result.scalar_one_or_none()
        if user_rating_obj:
            user_rating = user_rating_obj.to_dict()
    
    # 获取最近 5 条评价
    result = await db.execute(
        select(Rating)
        .options(selectinload(Rating.user))
        .filter(Rating.rider_id == rider_id)
        .order_by(Rating.created_at.desc())
        .limit(5)
    )
    recent_ratings = result.scalars().all()
    
    return {
        "rider_id": rider.rider_id,
        "rider_name": rider.rider_name,
        "stats": stats_dict,
        "user_rating": user_rating,
        "recent_ratings": [r.to_dict() for r in recent_ratings]
    }


@app.get("/api/auth/my-ratings", response_model=PaginatedRatingsResponse, tags=["Authentication"])
async def get_my_all_ratings(
    page: int = 1,
    limit: int = 10,
    current_user: User = Depends(get_current_user_async),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取当前用户的所有评价
    
    参数:
    - page: 页码，从 1 开始
    - limit: 每页记录数，默认 10
    """
    # 计算总记录数
    count_result = await db.execute(
        select(func.count())
        .select_from(Rating)
        .filter(Rating.user_id == current_user.user_id)
    )
    total = count_result.scalar() or 0
    
    # 计算分页参数
    total_pages = (total + limit - 1) // limit
    offset = (page - 1) * limit
    
    # 查询评价数据（预加载车手信息）
    result = await db.execute(
        select(Rating)
        .options(selectinload(Rating.rider))
        .filter(Rating.user_id == current_user.user_id)
        .order_by(Rating.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    ratings = result.scalars().all()
    
    # 构建响应数据
    ratings_data = []
    for rating in ratings:
        rating_dict = rating.to_dict()
        rating_dict['rider_name'] = rating.rider.rider_name if rating.rider else None
        ratings_data.append(rating_dict)
    
    return {
        "data": ratings_data,
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


# ============ 受保护的论坛端点（示例）============


@app.get("/api/forum/posts", tags=["Forum"])
def get_forum_posts(current_user: User = Depends(get_current_user)):
    """
    获取论坛帖子列表（需要登录）
    这是一个示例端点，用于测试 JWT 认证功能
    """
    return {
        "message": f"欢迎 {current_user.nickname}！这是论坛帖子列表。",
        "user": current_user.to_dict(),
        "posts": [
            {"id": 1, "title": "环法自行车赛观后感", "author": "车迷小王", "content": "今年的环法真精彩！"},
            {"id": 2, "title": "讨论：谁是最伟大的车手？", "author": "骑行爱好者", "content": "我觉得是..."},
            {"id": 3, "title": "2025赛季展望", "author": "资深车迷", "content": "期待新赛季的比赛！"}
        ]
    }

"""
@app.get("/api/stages/{stage_id}/results", response_model=PaginatedStageResultsResponse, tags=["Stages"])
@cache_response("stage_results", expire=3600)
def get_stage_results(stage_id: int, page: int = 1, limit: int = 20, db: Session = Depends(get_db)):
    #获取某一赛段的完整成绩单 (按排名)
    stage = db.query(Stage).filter(Stage.stage_id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    # 计算总记录数
    total = db.query(func.count()).select_from(StageResult).filter(StageResult.stage_id == stage.stage_id).scalar() or 0
    
    # 计算分页参数
    total_pages = (total + limit - 1) // limit
    offset = (page - 1) * limit
    
    # 查询分页数据
    results = db.query(StageResult).filter(StageResult.stage_id == stage.stage_id).order_by(StageResult.rank).offset(offset).limit(limit).all()
    
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
    
    return {
        "stage_info": stage.to_dict(),
        "data": results_with_relations,
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }

@app.get("/api/riders/{rider_id}", response_model=RiderStatsResponse, tags=["Riders"])
@cache_response("rider_detail", expire=600)
def get_rider_detail(rider_id: int, db: Session = Depends(get_db)):
    # 获取单个车手的详细统计信息
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

@app.get("/api/races", response_model=List[RaceBase], tags=["Races"])
@cache_response("races", expire=600)
def get_races(db: Session = Depends(get_db)):
    # 获取所有赛事 (例如: 环法, 环意) - 同步版本
    races = db.query(Race).order_by(Race.race_id).all()
    return [race.to_dict() for race in races]

@app.get("/api/races/{race_id}/editions", response_model=EditionsResponse, tags=["Races"])
@cache_response("race_editions", expire=600)
def get_editions(race_id: int, db: Session = Depends(get_db)):
    # 获取某一赛事的所有届数 (年份)
    race = db.query(Race).filter(Race.race_id == race_id).first()
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")
    
    editions = db.query(Edition).filter(Edition.race_id == race.race_id).order_by(Edition.year.desc()).all()
    return {"race": race.race_name, "editions": [e.to_dict() for e in editions]}


@app.get("/api/editions/{edition_id}/stages", response_model=StagesResponse, tags=["Editions"])
@cache_response("edition_stages", expire=1800)
def get_stages(edition_id: int, db: Session = Depends(get_db)):
    # 获取某一届赛事的所有赛段
    edition = db.query(Edition).filter(Edition.edition_id == edition_id).first()
    if not edition:
        raise HTTPException(status_code=404, detail="Edition not found")
    
    stages = db.query(Stage).filter(Stage.edition_id == edition.edition_id).order_by(Stage.stage_number).all()
    return {
        "edition_year": edition.year,
        "race_name": edition.race.race_name,
        "stages": [s.to_dict() for s in stages]
    }




@app.get("/api/riders", response_model=PaginatedRidersResponse, tags=["Riders"])
@cache_response("riders", expire=300)
def get_riders(page: int = 1, limit: int = 16, db: Session = Depends(get_db)):
    # 获取所有车手列表
    # 计算总记录数
    total = db.query(func.count()).select_from(Rider).scalar() or 0
    
    # 计算分页参数
    total_pages = (total + limit - 1) // limit
    offset = (page - 1) * limit
    
    # 查询分页数据
    riders = db.query(Rider).order_by(Rider.rider_name).offset(offset).limit(limit).all()
    
    return {
        "data": [rider.to_dict() for rider in riders],
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


 


@app.get("/api/riders/{rider_id}/races", response_model=RiderRacesResponse, tags=["Riders"])
@cache_response("rider_races", expire=1800)
def get_rider_races(rider_id: int, db: Session = Depends(get_db)):
    # 获取车手的所有参赛记录
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
    # 获取车手的所有赛段冠军记录
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


@app.post("/api/auth/register", response_model=RegisterResponse, tags=["Authentication"])
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    #用户注册 - 注册后需要验证邮箱
    # 验证邮箱格式（Pydantic 的 EmailStr 已经做了基本验证）
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, user_data.email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    
    # 检查邮箱是否已存在
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        # 如果用户已存在但未验证且token已过期，删除该用户允许重新注册
        if not existing_user.is_verified and is_token_expired(existing_user.verification_token_expires_at):
            db.delete(existing_user)
            db.commit()
        else:
            raise HTTPException(status_code=400, detail="该邮箱已被注册")
    
    # 检查昵称是否已存在（排除未验证且过期的用户）
    existing_nickname = db.query(User).filter(User.nickname == user_data.nickname).first()
    if existing_nickname:
        if not existing_nickname.is_verified and is_token_expired(existing_nickname.verification_token_expires_at):
            db.delete(existing_nickname)
            db.commit()
        else:
            raise HTTPException(status_code=400, detail="该昵称已被使用")
    
    # 生成验证令牌
    verification_token = generate_verification_token()
    verification_expires = get_verification_token_expiry()
    
    # 创建新用户（未验证状态）
    new_user = User(
        email=user_data.email,
        nickname=user_data.nickname,
        hashed_password=get_password_hash(user_data.password),
        avatar=user_data.avatar or "default",
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires_at=verification_expires
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # 发送验证邮件
    email_sent = send_verification_email(
        to_email=new_user.email,
        nickname=new_user.nickname,
        token=verification_token
    )
    
    if not email_sent:
        # 邮件发送失败，删除刚创建的用户
        db.delete(new_user)
        db.commit()
        raise HTTPException(status_code=500, detail="发送验证邮件失败，请稍后重试")
    
    return RegisterResponse(
        message="注册成功！请查收邮件并点击链接验证您的邮箱。",
        email=new_user.email,
        requires_verification=True
    )


@app.post("/api/auth/verify-email", response_model=MessageResponse, tags=["Authentication"])
def verify_email(verify_data: VerifyEmailRequest, db: Session = Depends(get_db)):
    # 验证邮箱
    # 查找具有该验证令牌的用户
    user = db.query(User).filter(User.verification_token == verify_data.token).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="无效的验证链接")
    
    if user.is_verified:
        return MessageResponse(message="邮箱已验证，无需重复验证", success=True)
    
    # 检查令牌是否过期
    if is_token_expired(user.verification_token_expires_at):
        raise HTTPException(status_code=400, detail="验证链接已过期，请重新发送验证邮件")
    
    # 验证成功
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    db.commit()
    
    return MessageResponse(message="邮箱验证成功！现在可以登录了。", success=True)


@app.post("/api/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login_user(login_data: UserLogin, db: Session = Depends(get_db)):
    # 用户登录
    # 查找用户
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    
    # 检查邮箱是否已验证
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="请先验证您的邮箱后再登录")
    
    # 验证密码
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    
    # 生成 Token（sub 必须是字符串）
    access_token = create_access_token(data={"sub": str(user.user_id)})
    refresh_token = create_refresh_token(data={"sub": str(user.user_id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }

@app.post("/api/auth/resend-verification", response_model=MessageResponse, tags=["Authentication"])
@limiter.limit("3/hour")
def resend_verification_email(request: Request, response: Response, email_data: EmailVerificationRequest, db: Session = Depends(get_db)):
    # 重新发送验证邮件
    # 限流：每个 IP 每小时最多 3 次请求
    
    user = db.query(User).filter(User.email == email_data.email).first()
    
    if not user:
        # 为了安全，不透露邮箱是否存在
        return MessageResponse(message="如果该邮箱已注册，验证邮件将发送到该地址。", success=True)
    
    if user.is_verified:
        raise HTTPException(status_code=400, detail="该邮箱已验证，无需重复验证")
    
    # 生成新的验证令牌
    verification_token = generate_verification_token()
    verification_expires = get_verification_token_expiry()
    
    user.verification_token = verification_token
    user.verification_token_expires_at = verification_expires
    db.commit()
    
    # 发送验证邮件
    email_sent = send_verification_email(
        to_email=user.email,
        nickname=user.nickname,
        token=verification_token
    )
    
    if not email_sent:
        raise HTTPException(status_code=500, detail="发送验证邮件失败，请稍后重试")
    
    return MessageResponse(message="验证邮件已发送，请查收。", success=True)


@app.post("/api/auth/forgot-password", response_model=MessageResponse, tags=["Authentication"])
@limiter.limit("10/hour")
def forgot_password(request: Request, response: Response, forgot_data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    # 发送密码重置邮件
    # 限流：每个 IP 每小时最多 10 次请求

    user = db.query(User).filter(User.email == forgot_data.email).first()
    
    # 为了安全，无论邮箱是否存在都返回相同的消息
    if not user or not user.is_verified:
        return MessageResponse(message="如果该邮箱已注册并验证，密码重置邮件将发送到该地址。", success=True)
    
    # 生成密码重置令牌
    reset_token = generate_reset_password_token()
    reset_expires = get_reset_password_token_expiry()
    
    user.reset_password_token = reset_token
    user.reset_password_token_expires_at = reset_expires
    db.commit()
    
    # 发送密码重置邮件
    email_sent = send_password_reset_email(
        to_email=user.email,
        nickname=user.nickname,
        token=reset_token
    )
    
    if not email_sent:
        raise HTTPException(status_code=500, detail="发送邮件失败，请稍后重试")
    
    return MessageResponse(message="如果该邮箱已注册并验证，密码重置邮件将发送到该地址。", success=True)


@app.post("/api/auth/refresh", response_model=TokenResponse, tags=["Authentication"])
def refresh_access_token(refresh_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    # 使用 Refresh Token 刷新 Access Token
    user_id = verify_refresh_token(refresh_data.refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的 Refresh Token")
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    # 生成新的 Token（sub 必须是字符串）
    access_token = create_access_token(data={"sub": str(user.user_id)})
    refresh_token = create_refresh_token(data={"sub": str(user.user_id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }
"""