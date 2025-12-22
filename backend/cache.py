"""
Redis 缓存管理 - 支持一键开关用于压力测试
"""
import redis
import redis.asyncio as aioredis
import json
from functools import wraps
from typing import Optional, Any, TypeVar, cast
import asyncio

# ==================== 压力测试开关 ====================
# 设为 True 开启缓存，设为 False 则完全绕过 Redis 进行压测
ENABLE_CACHE = True 
# ======================================================

ResponseT = TypeVar('ResponseT')

REDIS_HOST = "127.0.0.1" 
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_DECODE_RESPONSES = True

# 同步客户端
redis_client = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
    decode_responses=REDIS_DECODE_RESPONSES,
    socket_connect_timeout=10
)

async_redis_client: Optional[aioredis.Redis] = None
_init_lock = asyncio.Lock()

async def get_async_redis() -> aioredis.Redis:
    global async_redis_client
    if async_redis_client is None:
        async with _init_lock:
            if async_redis_client is None:
                async_redis_client = aioredis.Redis(
                    host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
                    decode_responses=REDIS_DECODE_RESPONSES,
                    socket_connect_timeout=10,
                    socket_timeout=10,
                    retry_on_timeout=True
                )
    return async_redis_client

async def close_async_redis():
    global async_redis_client
    if async_redis_client:
        await async_redis_client.close()
        async_redis_client = None

def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    key_parts = [prefix]
    for arg in args: key_parts.append(str(arg))
    for k in sorted(kwargs.keys()): key_parts.append(f"{k}:{kwargs[k]}")
    return ":".join(key_parts)

async def _async_set_cache(cache_key: str, result: Any, expire: int) -> None:
    if not ENABLE_CACHE: return # 开关检查
    try:
        redis = await get_async_redis()
        await redis.setex(cache_key, expire, json.dumps(result, ensure_ascii=False, default=str))
    except Exception: pass

def _sync_set_cache_in_thread(cache_key: str, result: Any, expire: int) -> None:
    if not ENABLE_CACHE: return # 开关检查
    try:
        redis_client.setex(cache_key, expire, json.dumps(result, ensure_ascii=False, default=str))
    except Exception: pass

def cache_response(prefix: str, expire: int = 300):
    """
    缓存装饰器 - 增加 ENABLE_CACHE 全局开关逻辑
    """
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # 如果关闭了缓存，直接执行原函数并返回
                if not ENABLE_CACHE:
                    return await func(*args, **kwargs)
                
                path_params = {k: v for k, v in kwargs.items() if k not in ['db', 'session']}
                cache_key = generate_cache_key(prefix, **path_params)
                
                try:
                    redis = await get_async_redis()
                    async with asyncio.timeout(2):
                        cached_data = await redis.get(cache_key)
                        if cached_data:
                            return json.loads(cached_data)
                except Exception as e:
                    print(f"[Cache] 异步读取异常: {e}")
                
                result = await func(*args, **kwargs)
                asyncio.create_task(_async_set_cache(cache_key, result, expire))
                return result
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # 如果关闭了缓存，直接执行原函数并返回
                if not ENABLE_CACHE:
                    return func(*args, **kwargs)
                
                path_params = {k: v for k, v in kwargs.items() if k not in ['db', 'session']}
                cache_key = generate_cache_key(prefix, **path_params)
                
                try:
                    cached_data = redis_client.get(cache_key)
                    if cached_data:
                        return json.loads(cached_data)
                except Exception as e:
                    print(f"[Cache] 同步读取异常: {e}")
                
                result = func(*args, **kwargs)
                import threading
                threading.Thread(target=_sync_set_cache_in_thread, args=(cache_key, result, expire), daemon=True).start()
                return result
            return sync_wrapper
    return decorator

# 其余功能保持不变...
def invalidate_cache(pattern: str) -> int:
    """同步缓存失效（用于同步代码）"""
    if not ENABLE_CACHE: return 0
    try:
        keys = cast(list[Any], redis_client.keys(pattern))
        if keys:
            redis_client.delete(*keys)
            return len(keys)
        return 0
    except Exception: return 0


async def invalidate_cache_async(pattern: str) -> int:
    """异步缓存失效（用于异步代码，避免阻塞事件循环）"""
    if not ENABLE_CACHE:
        return 0
    try:
        redis = await get_async_redis()
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
            return len(keys)
        return 0
    except Exception as e:
        print(f"[Cache] 异步失效缓存异常: {e}")
        return 0


def get_cache_stats() -> dict[str, Any]:
    """获取缓存统计信息"""
    try:
        info = cast(dict[str, Any], redis_client.info())
        hits: int = info.get("keyspace_hits", 0) # type: ignore
        misses: int = info.get("keyspace_misses", 0) # type: ignore
        return {
            "connected": True,
            "used_memory_human": info.get("used_memory_human"),
            "total_keys": redis_client.dbsize(),
            "hits": hits,
            "misses": misses,
            "hit_rate": round(hits / max(hits + misses, 1) * 100, 2)
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}