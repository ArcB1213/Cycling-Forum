"""
论坛浏览量 Write-Back 定时任务
定期将 Redis 中的浏览量增量批量回写到 MySQL
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
from models.database import get_async_db
from models.models import ForumPost
from cache import get_async_redis

# 配置
WRITE_BACK_INTERVAL = 300  # 5 分钟执行一次
BATCH_SIZE = 100  # 每次处理 100 个帖子

logger = logging.getLogger(__name__)

# Redis 键
POST_VIEW_KEY = "forum:post:view:{post_id}"
POST_VIEW_BATCH_KEY = "forum:post:view:batch"


async def write_back_view_counts():
    """
    将 Redis 中的浏览量批量回写到 MySQL
    """
    redis = await get_async_redis()

    try:
        # 从待回写集合获取所有帖子 ID
        post_ids = await redis.smembers(POST_VIEW_BATCH_KEY)

        if not post_ids:
            return

        logger.info(f"[Write-Back] 开始回写 {len(post_ids)} 个帖子的浏览量")

        async for db in get_async_db():
            try:
                # 转换为整数列表
                post_id_list = [int(pid) for pid in post_ids]

                # 分批处理
                for i in range(0, len(post_id_list), BATCH_SIZE):
                    batch = post_id_list[i:i + BATCH_SIZE]

                    # 获取当前数据库中的浏览量
                    posts_result = await db.execute(
                        select(ForumPost.post_id, ForumPost.view_count)
                        .filter(ForumPost.post_id.in_(batch))
                    )
                    current_view_counts = {row[0]: row[1] for row in posts_result.all()}

                    # 批量获取 Redis 中的增量
                    pipeline = redis.pipeline()
                    redis_keys = []
                    for post_id in batch:
                        key = POST_VIEW_KEY.format(post_id=post_id)
                        redis_keys.append(key)
                        pipeline.hget(key, "count")

                    redis_counts = await pipeline.execute()

                    # 构建批量更新
                    update_cases = []
                    update_params = {}
                    posts_to_update = []

                    for idx, post_id in enumerate(batch):
                        redis_count = redis_counts[idx]
                        if not redis_count:
                            continue

                        increment = int(redis_count)
                        db_count = current_view_counts.get(post_id, 0)
                        new_count = db_count + increment

                        update_cases.append(f"WHEN {post_id} THEN :count_{post_id}")
                        update_params[f"count_{post_id}"] = new_count
                        posts_to_update.append(post_id)

                    if update_cases:
                        # 执行批量更新（使用 CASE WHEN）
                        case_statement = " ".join(update_cases)
                        query = text(f"""
                            UPDATE forum_posts
                            SET view_count = CASE post_id {case_statement} ELSE view_count END
                            WHERE post_id IN :post_ids
                        """)

                        await db.execute(query, {**update_params, "post_ids": tuple(posts_to_update)})
                        await db.commit()

                        # 清除 Redis 数据
                        for post_id in posts_to_update:
                            key = POST_VIEW_KEY.format(post_id=post_id)
                            await redis.delete(key)

                        # 从待回写集合移除已处理的帖子
                        await redis.srem(POST_VIEW_BATCH_KEY, *posts_to_update)

                        logger.info(f"[Write-Back] 已回写 {len(posts_to_update)} 个帖子的浏览量")

            except Exception as e:
                logger.error(f"[Write-Back] 数据库操作失败: {e}")
                await db.rollback()
            break

    except Exception as e:
        logger.error(f"[Write-Back] 任务执行失败: {e}")


async def write_back_scheduler(stop_event: asyncio.Event):
    """
    定时任务调度器

    Args:
        stop_event: 停止事件
    """
    logger.info("[Write-Back] 定时任务调度器已启动")

    while not stop_event.is_set():
        try:
            await write_back_view_counts()
        except Exception as e:
            logger.error(f"[Write-Back] 定时任务执行失败: {e}")

        # 等待下一次执行或停止信号
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=WRITE_BACK_INTERVAL)
        except asyncio.TimeoutError:
            # 超时继续下一次循环
            pass

    logger.info("[Write-Back] 定时任务调度器已停止")


# 全局停止事件
_write_back_stop_event: Optional[asyncio.Event] = None
_write_back_task: Optional[asyncio.Task] = None


async def start_write_back_task():
    """启动 Write-Back 后台任务"""
    global _write_back_stop_event, _write_back_task

    if _write_back_task is not None:
        logger.warning("[Write-Back] 任务已在运行")
        return

    _write_back_stop_event = asyncio.Event()
    _write_back_task = asyncio.create_task(write_back_scheduler(_write_back_stop_event))

    logger.info("[Write-Back] 后台任务已启动")


async def stop_write_back_task():
    """停止 Write-Back 后台任务"""
    global _write_back_stop_event, _write_back_task

    if _write_back_stop_event:
        _write_back_stop_event.set()

    if _write_back_task:
        try:
            await asyncio.wait_for(_write_back_task, timeout=5.0)
        except asyncio.TimeoutError:
            _write_back_task.cancel()
        except Exception as e:
            logger.error(f"[Write-Back] 停止任务时出错: {e}")

        _write_back_task = None
        _write_back_stop_event = None

    logger.info("[Write-Back] 后台任务已停止")


@asynccontextmanager
async def lifespan_with_write_back(app):
    """
    FastAPI 生命周期管理（集成定时任务）
    在 app.py 的 lifespan 函数中调用

    使用示例:
    ```python
    from forum_write_back_task import lifespan_with_write_back

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # ... 其他启动逻辑
        async with lifespan_with_write_back(app):
            yield
        # ... 其他清理逻辑
    ```
    """
    # 启动时创建后台任务
    await start_write_back_task()
    yield
    # 关闭时停止任务
    await stop_write_back_task()
