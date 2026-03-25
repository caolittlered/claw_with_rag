"""
认证模块 - JWT 用户认证
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import yaml
import os
import hashlib

from models import User, async_session

# 加载配置
CONFIG_PATH = os.getenv("RAG_CONFIG", "./config/config.yaml")
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# JWT 配置
jwt_config = config.get('jwt', {})
JWT_SECRET = os.getenv("JWT_SECRET", jwt_config.get('secret', 'change-me-in-production'))
JWT_ALGORITHM = jwt_config.get('algorithm', 'HS256')
JWT_EXPIRE_HOURS = jwt_config.get('expire_hours', 24)

# 密码哈希 - 使用 argon2 避免 bcrypt 兼容性问题
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Bearer 认证
security = HTTPBearer()


def _prehash_password(password: str) -> str:
    """
    预处理密码：使用 SHA256 哈希，解决 bcrypt 72 字节限制
    同时避免 passlib+bcrypt 版本兼容问题
    """
    # 将密码编码为 bytes 后 SHA256，得到固定 64 字符的十六进制字符串
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def hash_password(password: str) -> str:
    """哈希密码"""
    # 先预处理密码，确保长度固定且不超过限制
    prehashed = _prehash_password(password)
    return pwd_context.hash(prehashed)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    # 同样预处理后再验证
    prehashed = _prehash_password(plain_password)
    return pwd_context.verify(prehashed, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """获取当前用户（依赖注入）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # 查询用户
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise credentials_exception
        return user