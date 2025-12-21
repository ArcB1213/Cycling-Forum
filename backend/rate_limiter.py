"""
API 请求限流器配置
使用 slowapi 实现基于 IP 地址的请求频率限制
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
from cache import REDIS_HOST, REDIS_PORT, REDIS_DB


def get_client_ip(request: Request) -> str:
    """
    获取客户端真实 IP 地址
    优先从 X-Forwarded-For 或 X-Real-IP 头获取（适配反向代理场景）
    """
    # 尝试从代理头获取真实 IP
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For 可能包含多个 IP，取第一个
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # 回退到直连 IP
    return get_remote_address(request)


# 创建限流器实例
limiter = Limiter(
    key_func=get_client_ip,
    storage_uri=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
    default_limits=["1000/hour"],  # 全局默认限制（非敏感端点）
    headers_enabled=True  # 在响应头中返回限流信息
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    自定义限流异常处理器
    返回 JSON 格式的友好错误信息
    """
    return JSONResponse(
        status_code=429,
        content={
            "detail": "请求过于频繁，请稍后再试",
            "error": "rate_limit_exceeded",
            "retry_after": getattr(exc, "retry_after", "60秒后")
        },
        headers={
            "Retry-After": str(getattr(exc, "retry_after", 60))
        }
    )
