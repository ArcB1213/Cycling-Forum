"""
数据库会话管理模块
用于 FastAPI 的依赖注入
"""
import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取数据库配置
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'cycling_stats')
DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '10'))
DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '20'))
DB_POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '3600'))

# URL 编码密码（处理特殊字符如 @, /, ? 等）
encoded_password = quote_plus(MYSQL_PASSWORD)

# MySQL 连接 URL
DATABASE_URL = (
    f'mysql+pymysql://{MYSQL_USER}:{encoded_password}'
    f'@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}'
    f'?charset=utf8mb4'
)

# SQLite 备用（用于开发/测试）
# basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# DATABASE_URL = 'sqlite:///' + os.path.join(basedir, 'cycling_stats.db')

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
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

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """
    依赖注入函数，为每个请求创建独立的数据库会话
    使用 yield 确保请求结束后自动关闭会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
