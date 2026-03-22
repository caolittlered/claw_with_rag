"""
数据库模型 - 用户系统
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
import yaml
import os

# 加载配置
CONFIG_PATH = os.getenv("RAG_CONFIG", "./config/config.yaml")
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 数据库引擎
DATABASE_URL = config.get('database', {}).get('url', 'sqlite+aiosqlite:///./data/suni.db')
engine = create_async_engine(DATABASE_URL, echo=False)

# Session 工厂
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 基类
Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # 用户信息
    company = Column(String(255), nullable=True)
    
    # 状态
    is_active = Column(Boolean, default=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


class UserKnowledge(Base):
    """用户知识库文档表"""
    __tablename__ = "user_knowledge"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    
    # 文档信息
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    
    # 索引状态
    is_indexed = Column(Boolean, default=False)
    chunk_count = Column(Integer, default=0)
    
    # 时间戳
    uploaded_at = Column(DateTime, default=datetime.utcnow)


async def init_db():
    """初始化数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[DB] 用户数据库初始化完成")


async def get_db():
    """获取数据库 session"""
    async with async_session() as session:
        yield session