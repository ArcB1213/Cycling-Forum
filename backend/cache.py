"""
Redis 缓存管理
"""
import redis
import json
from functools import wraps
from typing import Optional, Callable, Any, TypeVar, cast

ResponseT = TypeVar('ResponseT')

# Redis 连接配置
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_DECODE_RESPONSES = True

# 创建 Redis 连接池
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=REDIS_DECODE_RESPONSES,
    socket_connect_timeout=5
)


def get_redis() -> redis.Redis:
    """获取 Redis 客户端实例"""
    return redis_client


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    生成缓存键
    :param prefix: 键前缀（如 'rider', 'race'）
    :param args: 位置参数
    :param kwargs: 关键字参数
    """
    key_parts = [prefix]
    
    # 添加位置参数
    for arg in args:
        key_parts.append(str(arg))
    
    # 添加关键字参数（按字母排序保证一致性）
    for k in sorted(kwargs.keys()):
        key_parts.append(f"{k}:{kwargs[k]}")
    
    return ":".join(key_parts)


def cache_response(prefix: str, expire: int = 300) -> Callable[[Callable[..., ResponseT]], Callable[..., ResponseT]]:
    """
    缓存装饰器 - 用于 FastAPI 路由函数
    
    :param prefix: 缓存键前缀
    :param expire: 过期时间（秒），默认 5 分钟
    
    使用示例：
    @cache_response("riders", expire=600)
    def get_riders(db: Session = Depends(get_db)):
        ...
    """
    def decorator(func: Callable[..., ResponseT]) -> Callable[..., ResponseT]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> ResponseT:
            # 提取路径参数生成缓存键
            # 过滤掉 Session 对象，只使用路径参数
            path_params: dict[str, Any] = {k: v for k, v in kwargs.items() if not k == 'db'}
            cache_key = generate_cache_key(prefix, **path_params)
            
            try:
                # 尝试从缓存获取
                cached_data = cast(Optional[str], redis_client.get(cache_key))
                if cached_data:
                    print(f"[Cache HIT] {cache_key}")
                    return json.loads(cached_data)  # type: ignore[return-value]
                else:
                    print(f"[Cache MISS] {cache_key}")
            except Exception as e:
                print(f"[Cache] 读取失败: {e}")
            
            # 缓存未命中，执行原函数
            result: ResponseT = func(*args, **kwargs)
            
            try:
                # 将结果存入缓存
                redis_client.setex(
                    cache_key,
                    expire,
                    json.dumps(result, ensure_ascii=False, default=str)
                )
                print(f"[Cache SET] {cache_key} (expire: {expire}s)")
            except Exception as e:
                print(f"[Cache] 写入失败: {e}")
            
            return result
        
        return wrapper  # type: ignore[return-value]
    return decorator


def invalidate_cache(pattern: str) -> int:
    """
    清除匹配模式的缓存
    
    :param pattern: Redis 键模式（如 'rider:*'）
    """
    try:
        keys = cast(list[Any], redis_client.keys(pattern))
        if keys:
            redis_client.delete(*keys)
            num_deleted = len(keys)
            print(f"[Cache] 已清除 {num_deleted} 个缓存键")
            return num_deleted
        return 0
    except Exception as e:
        print(f"[Cache] 清除失败: {e}")
        return 0


def get_cache_stats() -> dict[str, Any]:
    """获取缓存统计信息"""
    try:
        info = cast(dict[str, Any], redis_client.info())
        hits: int = info.get("keyspace_hits", 0)  # type: ignore[assignment]
        misses: int = info.get("keyspace_misses", 0)  # type: ignore[assignment]
        return {
            "connected": True,
            "used_memory_human": info.get("used_memory_human"),
            "total_keys": redis_client.dbsize(),
            "hits": hits,
            "misses": misses,
            "hit_rate": round(
                hits / max(hits + misses, 1) * 100,
                2
            )
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}
