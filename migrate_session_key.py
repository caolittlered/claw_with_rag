#!/usr/bin/env python3
"""
数据库迁移脚本：为现有用户添加 session_key
运行此脚本以支持 OpenClaw Session 隔离
"""

import sys
import os
import uuid

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
from sqlalchemy import select, text
from models import engine, User, async_session, init_db


async def migrate():
    """迁移数据库，添加 session_key 字段"""
    
    print("=" * 50)
    print("数据库迁移：添加 session_key 支持")
    print("=" * 50)
    
    # 1. 检查 session_key 列是否存在
    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA table_info(users)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'session_key' not in columns:
            print("[Migration] 添加 session_key 列...")
            await conn.execute(text("ALTER TABLE users ADD COLUMN session_key VARCHAR(100)"))
            print("[Migration] session_key 列已添加")
        else:
            print("[Migration] session_key 列已存在")
    
    # 2. 为现有用户生成 session_key
    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        updated_count = 0
        for user in users:
            if not user.session_key:
                user.session_key = User.generate_session_key(user.id)
                updated_count += 1
                print(f"[Migration] 用户 {user.username} (id={user.id}) -> session_key={user.session_key}")
        
        if updated_count > 0:
            await session.commit()
            print(f"[Migration] 已为 {updated_count} 个用户生成 session_key")
        else:
            print("[Migration] 所有用户已有 session_key")
    
    # 3. 创建用户 workspace 目录
    base_path = "/root/claw_with_rag/claw_with_rag/data/user_docs"
    
    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        for user in users:
            workspace = os.path.join(base_path, str(user.id))
            if not os.path.exists(workspace):
                os.makedirs(workspace, exist_ok=True)
                print(f"[Migration] 创建 workspace: {workspace}")
    
    print("=" * 50)
    print("[Migration] 迁移完成！")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(migrate())