"""
论坛 Write-Back 策略工具函数
用于处理帖子浏览量的高并发读写
"""
import redis.asyncio as aioredis
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models.models import ForumPost
from cache import get_async_redis

# Redis 键前缀
POST_VIEW_KEY = "forum:post:view:{post_id}"  # Hash: {count: 增量值}
POST_VIEW_BATCH_KEY = "forum:post:view:batch"  # Set: 待回写的帖子 ID 集合

# Redis 过期时间（秒）
REDIS_EXPIRE_TIME = 604800  # 7 天


async def increment_view_count(post_id: int) -> int:
    """
    增加帖子浏览量（仅操作 Redis）

    Args:
        post_id: 帖子 ID

    Returns:
        当前的 Redis 增量值
    """
    redis = await get_async_redis()

    # 使用 Hash 存储浏览量，支持批量操作
    key = POST_VIEW_KEY.format(post_id=post_id)

    # Redis HINCRBY 原子操作
    new_view_count = await redis.hincrby(key, "count", 1)

    # 设置过期时间（7 天）
    await redis.expire(key, REDIS_EXPIRE_TIME)

    # 将帖子 ID 添加到待回写集合
    await redis.sadd(POST_VIEW_BATCH_KEY, post_id)

    return new_view_count


async def get_view_count_from_redis(post_id: int) -> int:
    """
    从 Redis 获取浏览量增量

    Args:
        post_id: 帖子 ID

    Returns:
        Redis 中的浏览量增量
    """
    redis = await get_async_redis()
    key = POST_VIEW_KEY.format(post_id=post_id)
    count = await redis.hget(key, "count")
    return int(count) if count else 0


async def get_total_view_count(db: AsyncSession, post_id: int) -> int:
    """
    获取总浏览量（MySQL + Redis）

    Args:
        db: 数据库会话
        post_id: 帖子 ID

    Returns:
        总浏览量（数据库基础值 + Redis 增量）
    """
    # 从 MySQL 获取基础浏览量
    result = await db.execute(
        select(ForumPost.view_count).filter(ForumPost.post_id == post_id)
    )
    db_view_count = result.scalar_one_or_none() or 0

    # 加上 Redis 中的增量
    redis_view_count = await get_view_count_from_redis(post_id)

    return db_view_count + redis_view_count


async def batch_get_view_counts(db: AsyncSession, post_ids: list[int]) -> dict[int, int]:
    """
    批量获取多个帖子的总浏览量

    Args:
        db: 数据库会话
        post_ids: 帖子 ID 列表

    Returns:
        {post_id: total_view_count} 字典
    """
    if not post_ids:
        return {}

    # 批量从 MySQL 获取基础浏览量
    result = await db.execute(
        select(ForumPost.post_id, ForumPost.view_count)
        .filter(ForumPost.post_id.in_(post_ids))
    )
    db_view_counts = {row[0]: row[1] for row in result.all()}

    # 从 Redis 获取所有增量
    redis = await get_async_redis()
    pipeline = redis.pipeline()

    for post_id in post_ids:
        key = POST_VIEW_KEY.format(post_id=post_id)
        pipeline.hget(key, "count")

    redis_counts = await pipeline.execute()

    # 合并结果
    result_dict = {}
    for i, post_id in enumerate(post_ids):
        db_count = db_view_counts.get(post_id, 0)
        redis_count = int(redis_counts[i]) if redis_counts[i] else 0
        result_dict[post_id] = db_count + redis_count

    return result_dict


async def invalidate_post_view_cache(post_id: int) -> None:
    """
    清除指定帖子的 Redis 浏览量缓存

    Args:
        post_id: 帖子 ID
    """
    redis = await get_async_redis()
    key = POST_VIEW_KEY.format(post_id=post_id)
    await redis.delete(key)


async def get_pending_write_back_count() -> int:
    """
    获取待回写的帖子数量

    Returns:
        待回写的帖子数量
    """
    redis = await get_async_redis()
    count = await redis.scard(POST_VIEW_BATCH_KEY)
    return count
