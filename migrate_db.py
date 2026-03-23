"""
数据库迁移脚本
用于添加新字段而不丢失现有数据
"""

import os
import sys
import asyncio
import sqlite3
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

import yaml

CONFIG_PATH = os.getenv("RAG_CONFIG", "./config/config.yaml")


def migrate_database():
    """迁移数据库，添加新字段"""
    
    # 加载配置
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    db_url = config.get('database', {}).get('url', 'sqlite+aiosqlite:///./data/suni.db')
    
    # 从 URL 提取数据库文件路径
    if db_url.startswith('sqlite+aiosqlite:///'):
        db_path = db_url.replace('sqlite+aiosqlite:///', '')
    elif db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
    else:
        print(f"❌ 不支持的数据库类型: {db_url}")
        return False
    
    db_path = Path(db_path)
    
    if not db_path.exists():
        print(f"📁 数据库不存在，将在首次启动时自动创建: {db_path}")
        return True
    
    print(f"🔄 正在迁移数据库: {db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 检查 users 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("📁 users 表不存在，将在首次启动时自动创建")
            conn.close()
            return True
        
        # 获取现有字段
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        # 需要添加的新字段
        new_columns = {
            'chat_count': 'INTEGER DEFAULT 0',
            'max_chats': 'INTEGER DEFAULT 10',
            'doc_count': 'INTEGER DEFAULT 0',
            'max_docs': 'INTEGER DEFAULT 10'
        }
        
        added = []
        for col_name, col_type in new_columns.items():
            if col_name not in existing_columns:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                added.append(col_name)
                print(f"  ✓ 添加字段: {col_name}")
        
        conn.commit()
        conn.close()
        
        if added:
            print(f"✅ 迁移完成！已添加 {len(added)} 个新字段")
        else:
            print("✅ 数据库已是最新版本，无需迁移")
        
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("🔄 Suni AI 数据库迁移工具")
    print("=" * 50)
    
    success = migrate_database()
    
    if success:
        print("\n✅ 可以安全启动应用了")
    else:
        print("\n❌ 请检查错误后重试")
        sys.exit(1)
