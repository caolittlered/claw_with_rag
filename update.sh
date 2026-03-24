#!/bin/bash
# Suni AI 更新脚本
# 用于更新已部署的服务
# 用法: sudo bash update.sh

set -e

APP_NAME="suniai"
APP_DIR="/opt/claw_with_rag"

echo "=========================================="
echo "  Suni AI 更新脚本"
echo "=========================================="
echo ""

# 停止服务
echo "[1/5] 停止服务..."
systemctl stop $APP_NAME

# 备份数据
echo "[2/5] 备份数据..."
BACKUP_DIR="/tmp/suniai_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR
cp -r $APP_DIR/data $BACKUP_DIR/ 2>/dev/null || true
cp $APP_DIR/config/config.yaml $BACKUP_DIR/ 2>/dev/null || true
echo "备份已保存到: $BACKUP_DIR"

# 更新代码
echo "[3/5] 更新代码..."
cd $APP_DIR

# 如果有 git 仓库，拉取最新代码
if [[ -d ".git" ]]; then
    git pull
else
    echo "请手动更新代码文件到 $APP_DIR"
    read -p "按回车继续..."
fi

# 更新依赖
echo "[4/5] 更新依赖..."
source venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 重启服务
echo "[5/5] 重启服务..."
systemctl start $APP_NAME

sleep 2
if systemctl is-active --quiet $APP_NAME; then
    echo ""
    echo "✅ 更新成功！"
    echo ""
    echo "查看日志: journalctl -u $APP_NAME -f"
else
    echo ""
    echo "❌ 服务启动失败，请检查日志:"
    echo "journalctl -u $APP_NAME -n 50"
fi
