"""
数据库会话管理模块
用于 FastAPI 的依赖注入
支持同步和异步两种模式
"""
import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool, AsyncAdaptedQueuePool
from typing import Generator, AsyncGenerator
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取数据库配置
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'cycling_stats')

# 连接池配置（提高高并发性能）
DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '20'))          # 增加基础连接池大小（原10）
DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '40'))    # 增加溢出连接数（原20）
DB_POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '3600'))  # 连接回收时间（秒）
DB_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))    # 获取连接的超时时间

# URL 编码密码（处理特殊字符如 @, /, ? 等）
encoded_password = quote_plus(MYSQL_PASSWORD)

# ==================== 同步数据库配置（保留向后兼容）====================
# MySQL 连接 URL
DATABASE_URL = (
    f'mysql+pymysql://{MYSQL_USER}:{encoded_password}'
    f'@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}'
    f'?charset=utf8mb4'
)

# 创建同步引擎
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    pool_timeout=DB_POOL_TIMEOUT,  # 添加超时配置
    pool_pre_ping=True,
    echo=False  # 设为 True 可查看 SQL 日志
)

# MySQL 连接优化
@event.listens_for(engine, "connect")
def set_mysql_pragma(dbapi_conn, connection_record):
    """设置 MySQL 连接参数"""
    cursor = dbapi_conn.cursor()
    cursor.execute("SET SESSION sql_mode='STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'")
    cursor.execute("SET SESSION time_zone='+00:00'")
    cursor.close()

# 创建同步会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """
    同步依赖注入函数，为每个请求创建独立的数据库会话
    使用 yield 确保请求结束后自动关闭会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== 异步数据库配置 ====================
# 异步 MySQL 连接 URL (使用 aiomysql 驱动)
ASYNC_DATABASE_URL = (
    f'mysql+aiomysql://{MYSQL_USER}:{encoded_password}'
    f'@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}'
    f'?charset=utf8mb4'
)

# 创建异步引擎
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    pool_timeout=DB_POOL_TIMEOUT,  # 添加超时配置
    pool_pre_ping=True,
    echo=False  # 设为 True 可查看 SQL 日志
)

# 异步 MySQL 连接优化
@event.listens_for(async_engine.sync_engine, "connect")
def set_async_mysql_pragma(dbapi_conn, connection_record):
    """设置异步 MySQL 连接参数"""
    cursor = dbapi_conn.cursor()
    cursor.execute("SET SESSION sql_mode='STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'")
    cursor.execute("SET SESSION time_zone='+00:00'")
    cursor.close()

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    异步依赖注入函数，为每个请求创建独立的异步数据库会话
    使用 yield 确保请求结束后自动关闭会话
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def close_db_connections():
    """
    关闭数据库连接池（引擎）
    应该在 FastAPI 应用关闭 (Shutdown) 时调用
    """
    print("[MySQL] 正在关闭连接池...")
    try:
        # 1. 关闭异步引擎 (最重要，解决 Event Loop closed 报错)
        await async_engine.dispose()
        
        # 2. 关闭同步引擎 (虽然同步引擎通常不依赖 Event Loop，但显式关闭是好习惯)
        engine.dispose()
        
        print("[MySQL] 连接池已关闭 ✓")
    except Exception as e:
        print(f"[MySQL] 关闭连接池时发生错误: {e}")