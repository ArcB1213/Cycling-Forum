"""
数据库会话管理模块
用于 FastAPI 的依赖注入
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# 获取数据库路径
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATABASE_URL = 'sqlite:///' + os.path.join(basedir, 'cycling_stats.db')

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 需要此配置
    echo=False  # 设为 True 可查看 SQL 日志
)

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
