#!/usr/bin/env python3
"""检查 FastAPI 路由"""
import sys
import os

# 设置工作目录
os.chdir('/root/claw_with_rag')
sys.path.insert(0, 'src')

# 设置环境变量避免数据库问题
os.environ['RAG_CONFIG'] = './config/config.yaml'

from web_api import app

print("=" * 50)
print("注册的路由列表:")
print("=" * 50)

for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        methods = ','.join(route.methods - {'HEAD', 'OPTIONS'})
        print(f"  {methods:10} {route.path}")

print("=" * 50)

# 检查目标路由
target = '/api/chat/stream'
paths = [r.path for r in app.routes if hasattr(r, 'path')]
if target in paths:
    print(f"✅ {target} 已注册")
else:
    print(f"❌ {target} 未找到")
    print("\n相似路由:")
    for p in paths:
        if 'chat' in p or 'api' in p:
            print(f"  - {p}")
