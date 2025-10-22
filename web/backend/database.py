"""
数据库连接配置 - 支持同步和异步
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 数据库文件路径
DATABASE_DIR = "data"
os.makedirs(DATABASE_DIR, exist_ok=True)

# 同步数据库配置（用于初始化）
SYNC_DATABASE_URL = f"sqlite:///./{DATABASE_DIR}/quiz_history.db"
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# 异步数据库配置（用于API）
ASYNC_DATABASE_URL = f"sqlite+aiosqlite:///./{DATABASE_DIR}/quiz_history.db"
async_engine = create_async_engine(ASYNC_DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# 创建基类
Base = declarative_base()

# 同步依赖注入（用于初始化）
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 异步依赖注入（用于API）
async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# 为了兼容性，保持原有的engine引用
engine = sync_engine
