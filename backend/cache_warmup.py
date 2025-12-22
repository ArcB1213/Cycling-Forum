"""
缓存预热模块
在应用启动时预加载热点数据到 Redis 缓存
"""
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models.models import Race, Edition, Stage, Rider
from cache import get_async_redis, generate_cache_key


async def preload_races(db: AsyncSession) -> int:
    """
    预加载所有赛事数据
    对应端点: GET /api/async/races
    """
    try:
        redis = await get_async_redis()
        cache_key = generate_cache_key("races_async")
        
        # 查询所有赛事
        result = await db.execute(select(Race).order_by(Race.race_id))
        races = result.scalars().all()
        races_data = [race.to_dict() for race in races]
        
        # 写入缓存（10 分钟）
        await redis.setex(
            cache_key,
            600,
            json.dumps(races_data, ensure_ascii=False, default=str)
        )
        
        print(f"  ✓ 预热赛事数据: {len(races_data)} 条")
        return len(races_data)
    except Exception as e:
        print(f"  ✗ 预热赛事数据失败: {e}")
        return 0


async def preload_popular_riders(db: AsyncSession, limit: int = 50) -> int:
    """
    预加载热门车手数据（前N页）
    对应端点: GET /api/async/riders?page=X&limit=16
    """
    try:
        redis = await get_async_redis()
        preloaded = 0
        
        # 预热前几页车手列表
        pages_to_preload = (limit + 15) // 16  # 计算需要预热的页数
        
        for page in range(1, pages_to_preload + 1):
            cache_key = generate_cache_key("riders_async", page=page, limit=16)
            
            # 查询车手数据
            offset = (page - 1) * 16
            result = await db.execute(
                select(Rider).order_by(Rider.rider_name).offset(offset).limit(16)
            )
            riders = result.scalars().all()
            
            # 计算总数和分页信息
            count_result = await db.execute(select(func.count()).select_from(Rider))
            total = count_result.scalar() or 0
            total_pages = (total + 16 - 1) // 16
            
            riders_data = {
                "data": [rider.to_dict() for rider in riders],
                "pagination": {
                    "total": total,
                    "page": page,
                    "limit": 16,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
            
            # 写入缓存（5 分钟）
            await redis.setex(
                cache_key,
                300,
                json.dumps(riders_data, ensure_ascii=False, default=str)
            )
            preloaded += 1
        
        print(f"  ✓ 预热车手列表: 前 {preloaded} 页")
        return preloaded
    except Exception as e:
        print(f"  ✗ 预热车手数据失败: {e}")
        return 0


async def preload_recent_editions(db: AsyncSession, limit: int = 5) -> int:
    """
    预加载最近几届赛事的届数信息
    对应端点: GET /api/async/races/{race_id}/editions
    """
    try:
        redis = await get_async_redis()
        preloaded = 0
        
        # 获取所有赛事ID
        result = await db.execute(select(Race.race_id))
        race_ids = [row[0] for row in result.all()]
        
        for race_id in race_ids:
            cache_key = generate_cache_key("race_editions_async", race_id=race_id)
            
            # 查询赛事
            race_result = await db.execute(select(Race).filter(Race.race_id == race_id))
            race = race_result.scalar_one_or_none()
            if not race:
                continue
            
            # 查询届数（只预热最近N届）
            editions_result = await db.execute(
                select(Edition)
                .filter(Edition.race_id == race_id)
                .order_by(Edition.year.desc())
                .limit(limit)
            )
            editions = editions_result.scalars().all()
            
            editions_data = {
                "race": race.race_name,
                "editions": [e.to_dict() for e in editions]
            }
            
            # 写入缓存（10 分钟）
            await redis.setex(
                cache_key,
                600,
                json.dumps(editions_data, ensure_ascii=False, default=str)
            )
            preloaded += 1
        
        print(f"  ✓ 预热赛事届数: {preloaded} 个赛事 (每个最近 {limit} 届)")
        return preloaded
    except Exception as e:
        print(f"  ✗ 预热赛事届数失败: {e}")
        return 0


async def preload_all_caches(db: AsyncSession) -> dict:
    """
    预热所有关键缓存
    
    返回预热统计信息
    """
    print("\n🔥 开始预热缓存...")
    stats = {
        "races": 0,
        "riders_pages": 0,
        "editions": 0,
    }
    
    # 预热赛事数据
    stats["races"] = await preload_races(db)
    
    # 预热车手列表（前50个，约3-4页）
    stats["riders_pages"] = await preload_popular_riders(db, limit=50)
    
    # 预热最近赛事届数（每个赛事最近5届）
    stats["editions"] = await preload_recent_editions(db, limit=5)
    
    print(f"\n✅ 缓存预热完成!")
    print(f"   - 赛事数据: {stats['races']} 条")
    print(f"   - 车手列表: {stats['riders_pages']} 页")
    print(f"   - 赛事届数: {stats['editions']} 个赛事")
    
    return stats


async def clear_all_caches() -> int:
    """
    清除所有缓存
    """
    try:
        redis = await get_async_redis()
        keys = await redis.keys("*")
        if keys:
            await redis.delete(*keys)
            print(f"🗑️  已清除 {len(keys)} 个缓存键")
            return len(keys)
        return 0
    except Exception as e:
        print(f"✗ 清除缓存失败: {e}")
        return 0
