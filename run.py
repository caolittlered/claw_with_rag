"""
Suni AI - 企业知识智能体平台
统一启动入口
"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

import uvicorn
import yaml

# 加载配置
CONFIG_PATH = os.getenv("RAG_CONFIG", "./config/config.yaml")
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

if __name__ == "__main__":
    server_config = config.get('server', {})
    
    print("=" * 50)
    print("🌟 Suni AI - 企业知识智能体平台")
    print("=" * 50)
    print(f"📡 服务地址: http://{server_config.get('host', '0.0.0.0')}:{server_config.get('port', 3000)}")
    print(f"📁 配置文件: {CONFIG_PATH}")
    print("=" * 50)
    
    uvicorn.run(
        "web_api:app",
        host=server_config.get('host', '0.0.0.0'),
        port=server_config.get('port', 3000),
        reload=server_config.get('debug', False),
        app_dir="src"
    )