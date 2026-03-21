#!/bin/bash
# Linux/Mac 安装脚本

set -e

echo "================================================"
echo "    企业知识库 RAG Agent 安装脚本"
echo "================================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Python
echo -e "\n${YELLOW}[1/5] 检查 Python 环境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 Python3，请先安装 Python 3.9+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python 版本: $PYTHON_VERSION${NC}"

# 检查 pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 pip3${NC}"
    exit 1
fi

# 创建虚拟环境（可选）
read -p "是否创建 Python 虚拟环境？(推荐) [Y/n]: " create_venv
if [[ -z "$create_venv" || "$create_venv" =~ ^[Yy] ]]; then
    echo -e "\n${YELLOW}[2/5] 创建虚拟环境...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${GREEN}✓ 虚拟环境已创建并激活${NC}"
else
    echo -e "${YELLOW}跳过虚拟环境创建${NC}"
fi

# 安装 Python 依赖
echo -e "\n${YELLOW}[3/5] 安装 Python 依赖...${NC}"
pip3 install --upgrade pip
pip3 install -r requirements.txt
echo -e "${GREEN}✓ Python 依赖安装完成${NC}"

# 检查 OpenClaw
echo -e "\n${YELLOW}[4/5] 检查 OpenClaw...${NC}"
if ! command -v openclaw &> /dev/null; then
    echo -e "${YELLOW}OpenClaw 未安装，正在安装...${NC}"
    curl -fsSL https://openclaw.ai/install.sh | bash
else
    OPENCLAW_VERSION=$(openclaw --version 2>&1 | head -1)
    echo -e "${GREEN}✓ OpenClaw 已安装: $OPENCLAW_VERSION${NC}"
fi

# 创建必要目录
echo -e "\n${YELLOW}[5/5] 初始化项目结构...${NC}"
mkdir -p docs data/chroma logs
echo -e "${GREEN}✓ 目录创建完成${NC}"

# 复制环境变量模板
if [ ! -f config/.env ]; then
    cp config/.env.example config/.env
    echo -e "${GREEN}✓ 已创建 config/.env 配置文件${NC}"
fi

# 完成
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}    安装完成！${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "下一步："
echo "  1. 编辑 config/.env 填入你的 API 密钥"
echo "  2. 下载模型: python scripts/download_models.py --modelscope"
echo "  3. 将知识文档放入 docs/ 目录"
echo "  4. 运行: python src/main.py index  # 全量索引文档"
echo "  5. 运行: python src/main.py search \"查询内容\"  # 搜索"
echo ""
echo "增量索引："
echo "  python src/main.py inc-index docs_inc/inc_1/  # 索引指定目录"
echo ""