#!/usr/bin/env python3
"""检查 OpenClaw Gateway 配置"""
import os
import sys

sys.path.insert(0, 'src')
os.chdir('/root/claw_with_rag' if os.path.exists('/root/claw_with_rag') else '.')

# 检查环境变量
print("=" * 50)
print("环境变量:")
print("=" * 50)
print(f"  OPENCLAW_GATEWAY_URL = {os.environ.get('OPENCLAW_GATEWAY_URL', '未设置')}")
print(f"  OPENCLAW_GATEWAY_TOKEN = {'已设置' if os.environ.get('OPENCLAW_GATEWAY_TOKEN') else '未设置'}")

# 尝试导入并检查配置
try:
    from web_api import OPENCLAW_GATEWAY_URL, OPENCLAW_GATEWAY_TOKEN
    print(f"\n  web_api中读取的值:")
    print(f"    OPENCLAW_GATEWAY_URL = {OPENCLAW_GATEWAY_URL}")
    print(f"    OPENCLAW_GATEWAY_TOKEN = {'已设置' if OPENCLAW_GATEWAY_TOKEN else '未设置'}")
except Exception as e:
    print(f"\n  导入失败: {e}")

# 检查OpenClaw Gateway状态
print("\n" + "=" * 50)
print("测试 Gateway 连接:")
print("=" * 50)

import urllib.request
import json

gateway_url = os.environ.get('OPENCLAW_GATEWAY_URL', 'http://localhost:8080')

# 尝试几个常见的端点
endpoints = [
    '/health',
    '/status',
    '/v1/models',
    '/api/status',
]

for endpoint in endpoints:
    url = gateway_url.rstrip('/') + endpoint
    try:
        req = urllib.request.Request(url, method='GET')
        req.add_header('Accept', 'application/json')
        with urllib.request.urlopen(req, timeout=5) as response:
            print(f"  {endpoint}: {response.status} OK")
            if response.status == 200:
                try:
                    data = json.loads(response.read().decode())
                    print(f"    响应: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}")
                except:
                    pass
    except Exception as e:
        print(f"  {endpoint}: 失败 - {type(e).__name__}")
