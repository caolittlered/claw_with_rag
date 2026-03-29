#!/bin/bash
# Suni AI 一键部署脚本
# 用于在 Ubuntu/Debian 服务器上一键部署
# 用法: sudo bash deploy.sh

set -e  # 遇到错误立即退出

# ============================================
# 配置变量（根据你的实际情况修改）
# ============================================
DOMAIN="www.suniai.site"           # 你的域名
EMAIL=""                           # SSL 证书邮箱（空则跳过 SSL）
APP_NAME="suniai"                  # 应用名称
APP_DIR="/root/claw_with_rag/claw_with_rag"  # 项目路径
APP_PORT=3000                      # 应用端口
PYTHON_VERSION="3.10"              # Python 版本

# ============================================
# 颜色定义
# ============================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================
# 日志函数
# ============================================
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "\n${CYAN}▶ $1${NC}"
}

# ============================================
# 检查函数
# ============================================
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "请使用 sudo 运行此脚本"
        exit 1
    fi
}

check_system() {
    print_step "检查系统环境"
    
    if ! command -v apt &> /dev/null; then
        print_error "此脚本仅支持 Ubuntu/Debian 系统"
        exit 1
    fi
    
    # 检查 Python 版本
    PYTHON_VER=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
    print_info "Python 版本: $PYTHON_VER"
    
    print_success "系统检查通过"
}

check_project() {
    print_step "检查项目结构"
    
    if [[ ! -d "$APP_DIR" ]]; then
        print_error "项目目录不存在: $APP_DIR"
        exit 1
    fi
    
    if [[ ! -f "$APP_DIR/run.py" ]]; then
        print_error "未找到 run.py，请确认项目路径正确"
        exit 1
    fi
    
    if [[ ! -f "$APP_DIR/requirements.txt" ]]; then
        print_error "未找到 requirements.txt"
        exit 1
    fi
    
    if [[ ! -f "$APP_DIR/config/config.yaml" ]]; then
        print_error "未找到 config/config.yaml"
        exit 1
    fi
    
    print_success "项目结构检查通过"
}

# ============================================
# 安装依赖
# ============================================
install_dependencies() {
    print_step "安装系统依赖"
    
    apt update
    apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        nginx \
        git \
        curl \
        wget \
        build-essential \
        certbot \
        python3-certbot-nginx \
        sqlite3 \
        libsqlite3-dev \
        ufw
    
    print_success "系统依赖安装完成"
}

# ============================================
# 配置项目
# ============================================
setup_project() {
    print_step "配置项目目录"
    
    # 创建数据目录
    mkdir -p $APP_DIR/data/user_docs
    mkdir -p $APP_DIR/data/chroma
    chmod -R 755 $APP_DIR/data
    
    # 设置项目权限
    chmod -R 755 $APP_DIR
    
    print_success "项目目录配置完成"
}

# ============================================
# 配置 Python 虚拟环境
# ============================================
setup_venv() {
    print_step "配置 Python 虚拟环境"
    
    cd $APP_DIR
    
    # 检查是否需要重建虚拟环境
    if [[ -d "venv" ]]; then
        print_warning "检测到已存在虚拟环境"
        read -p "是否重建虚拟环境? (y/n, 默认n): " rebuild_venv
        if [[ $rebuild_venv == "y" || $rebuild_venv == "Y" ]]; then
            print_info "删除旧虚拟环境..."
            rm -rf venv
        else
            print_info "使用现有虚拟环境"
        fi
    fi
    
    # 创建虚拟环境
    if [[ ! -d "venv" ]]; then
        print_info "创建新的虚拟环境..."
        python3 -m venv venv
    fi
    
    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    
    print_info "升级 pip..."
    pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
    
    print_info "安装 Python 依赖（使用清华镜像）..."
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    
    print_success "虚拟环境配置完成"
}

# ============================================
# 配置应用
# ============================================
setup_config() {
    print_step "配置应用"
    
    cd $APP_DIR
    
    # 生成随机 JWT 密钥（如果还是默认的）
    JWT_SECRET=$(openssl rand -hex 32)
    
    # 备份原配置
    if [[ -f "config/config.yaml" ]]; then
        cp config/config.yaml config/config.yaml.bak.$(date +%Y%m%d_%H%M%S)
        print_info "已备份原配置文件"
        
        # 更新关键配置
        sed -i "s|url: \"sqlite+aiosqlite://.*\"|url: \"sqlite+aiosqlite:///$APP_DIR/data/suni.db\"|" config/config.yaml
        sed -i "s|upload_dir: \".*\"|upload_dir: \"$APP_DIR/data/user_docs\"|" config/config.yaml
        sed -i "s|persist_directory: \"./data/chroma\"|persist_directory: \"$APP_DIR/data/chroma\"|" config/config.yaml
        
        print_success "配置文件已更新"
    fi
}

# ============================================
# 配置 Nginx
# ============================================
setup_nginx() {
    print_step "配置 Nginx"
    
    # 创建 Nginx 配置
    cat > /etc/nginx/sites-available/$APP_NAME << EOF
server {
    listen 80;
    server_name $DOMAIN ${DOMAIN#www.};

    client_max_body_size 50M;

    # 静态文件缓存
    location /static {
        alias $APP_DIR/web/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 反向代理到应用
    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
        proxy_connect_timeout 60;
        proxy_send_timeout 60;
    }

    # 健康检查端点（可选）
    location /health {
        proxy_pass http://127.0.0.1:$APP_PORT/health;
        access_log off;
    }
}
EOF

    # 启用站点
    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/$APP_NAME
    
    # 测试配置
    nginx -t || {
        print_error "Nginx 配置测试失败"
        exit 1
    }
    
    # 重启 Nginx
    systemctl restart nginx
    systemctl enable nginx
    
    print_success "Nginx 配置完成"
}

# ============================================
# 配置 SSL
# ============================================
setup_ssl() {
    print_step "配置 SSL 证书"
    
    if [[ -z "$EMAIL" ]]; then
        print_warning "未配置邮箱，跳过 SSL 设置"
        read -p "是否现在输入邮箱申请 SSL? (y/n): " ssl_now
        if [[ $ssl_now == "y" || $ssl_now == "Y" ]]; then
            read -p "请输入邮箱地址: " EMAIL
        else
            return
        fi
    fi
    
    if [[ -z "$EMAIL" ]]; then
        print_warning "仍未提供邮箱，跳过 SSL 配置"
        return
    fi
    
    # 申请证书
    print_info "正在申请 SSL 证书..."
    certbot --nginx -d $DOMAIN -d ${DOMAIN#www.} --non-interactive --agree-tos -m $EMAIL || {
        print_warning "SSL 证书申请失败，请检查域名解析是否正确"
        return
    }
    
    # 设置自动续期
    systemctl enable certbot.timer
    systemctl start certbot.timer
    
    print_success "SSL 证书配置完成"
}

# ============================================
# 创建 Systemd 服务
# ============================================
setup_systemd() {
    print_step "创建 Systemd 服务"
    
    # 创建服务文件
    cat > /etc/systemd/system/$APP_NAME.service << EOF
[Unit]
Description=Suni AI Web Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
Environment="PYTHONPATH=$APP_DIR"
Environment="PYTHONUNBUFFERED=1"
Environment="RAG_CONFIG=$APP_DIR/config/config.yaml"
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/run.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# 安全限制
NoNewPrivileges=false
ProtectSystem=false
ProtectHome=false

[Install]
WantedBy=multi-user.target
EOF

    # 重新加载配置
    systemctl daemon-reload
    systemctl enable $APP_NAME
    
    print_success "Systemd 服务创建完成"
}

# ============================================
# 配置防火墙
# ============================================
setup_firewall() {
    print_step "配置防火墙"
    
    # 允许必要端口
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp comment 'SSH'
    ufw allow 80/tcp comment 'HTTP'
    ufw allow 443/tcp comment 'HTTPS'
    
    # 启用防火墙
    ufw --force enable
    
    print_success "防火墙配置完成"
    ufw status numbered
}

# ============================================
# 启动服务
# ============================================
start_service() {
    print_step "启动 Suni AI 服务"
    
    # 停止旧服务（如果存在）
    systemctl stop $APP_NAME 2>/dev/null || true
    
    # 启动服务
    systemctl start $APP_NAME
    
    # 等待服务启动
    print_info "等待服务启动..."
    sleep 5
    
    # 检查服务状态
    if systemctl is-active --quiet $APP_NAME; then
        print_success "Suni AI 服务启动成功 (端口 $APP_PORT)"
    else
        print_error "服务启动失败"
        print_info "查看日志: journalctl -u $APP_NAME -n 50 --no-pager"
        exit 1
    fi
}

# ============================================
# 健康检查
# ============================================
health_check() {
    print_step "健康检查"
    
    # 检查本地端口
    if curl -s http://localhost:$APP_PORT > /dev/null; then
        print_success "本地服务正常 (端口 $APP_PORT)"
    else
        print_error "本地服务无响应"
        return 1
    fi
    
    # 检查 Nginx
    if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|302"; then
        print_success "Nginx 反向代理正常"
    else
        print_warning "Nginx 检查未通过"
    fi
    
    print_success "健康检查完成"
}

# ============================================
# 创建管理脚本
# ============================================
create_manage_script() {
    print_step "创建管理脚本"
    
    cat > $APP_DIR/manage.sh << 'EOF'
#!/bin/bash
# Suni AI 管理脚本

APP_NAME="suniai"
APP_DIR="/root/claw_with_rag/claw_with_rag"

show_help() {
    echo "Suni AI 管理脚本"
    echo ""
    echo "用法: bash manage.sh [命令]"
    echo ""
    echo "命令:"
    echo "  start       启动服务"
    echo "  stop        停止服务"
    echo "  restart     重启服务"
    echo "  status      查看服务状态"
    echo "  logs        查看实时日志"
    echo "  update      更新代码并重启"
    echo "  backup      备份数据"
    echo "  help        显示帮助"
}

case "$1" in
    start)
        systemctl start $APP_NAME
        echo "服务已启动"
        ;;
    stop)
        systemctl stop $APP_NAME
        echo "服务已停止"
        ;;
    restart)
        systemctl restart $APP_NAME
        echo "服务已重启"
        ;;
    status)
        systemctl status $APP_NAME --no-pager
        ;;
    logs)
        journalctl -u $APP_NAME -f
        ;;
    update)
        cd $APP_DIR
        git pull
        systemctl restart $APP_NAME
        echo "更新完成并已重启"
        ;;
    backup)
        BACKUP_DIR="$APP_DIR/backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p $BACKUP_DIR
        cp $APP_DIR/data/suni.db $BACKUP_DIR/ 2>/dev/null || true
        cp -r $APP_DIR/data/chroma $BACKUP_DIR/ 2>/dev/null || true
        cp $APP_DIR/config/config.yaml $BACKUP_DIR/ 2>/dev/null || true
        echo "备份完成: $BACKUP_DIR"
        ;;
    help|*)
        show_help
        ;;
esac
EOF

    chmod +x $APP_DIR/manage.sh
    
    # 创建软链到 /usr/local/bin
    ln -sf $APP_DIR/manage.sh /usr/local/bin/suniai
    
    print_success "管理脚本已创建"
    print_info "使用方式: suniai [start|stop|restart|status|logs|update|backup]"
}

# ============================================
# 完成信息
# ============================================
print_finish() {
    echo ""
    echo "=========================================="
    echo -e "  ${GREEN}🎉 Suni AI 部署完成！${NC}"
    echo "=========================================="
    echo ""
    echo -e "🌐 访问地址:"
    echo -e "   HTTP:  ${CYAN}http://$DOMAIN${NC}"
    if [[ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]]; then
        echo -e "   HTTPS: ${CYAN}https://$DOMAIN${NC}"
    fi
    echo ""
    echo -e "📁 项目路径: ${CYAN}$APP_DIR${NC}"
    echo ""
    echo -e "🔧 常用命令:"
    echo -e "   查看状态:  ${BLUE}suniai status${NC}"
    echo -e "   查看日志:  ${BLUE}suniai logs${NC}"
    echo -e "   重启服务:  ${BLUE}suniai restart${NC}"
    echo -e "   备份数据:  ${BLUE}suniai backup${NC}"
    echo ""
    echo -e "📋 配置文件:"
    echo -e "   应用配置: ${CYAN}$APP_DIR/config/config.yaml${NC}"
    echo -e "   Nginx:    ${CYAN}/etc/nginx/sites-available/$APP_NAME${NC}"
    echo -e "   Systemd:  ${CYAN}/etc/systemd/system/$APP_NAME.service${NC}"
    echo ""
    echo -e "⚠️  注意事项:"
    echo -e "   1. 首次启动可能需要几分钟加载模型"
    echo -e "   2. 确保域名 $DOMAIN 已解析到本服务器"
    echo -e "   3. 如需修改配置，编辑后执行: ${BLUE}suniai restart${NC}"
    echo ""
}

# ============================================
# 主函数
# ============================================
main() {
    echo "=========================================="
    echo -e "  ${CYAN}Suni AI 一键部署脚本${NC}"
    echo "=========================================="
    echo ""
    
    # 前置检查
    check_root
    check_system
    check_project
    
    # 确认部署
    echo "部署配置:"
    echo "  域名: $DOMAIN"
    echo "  路径: $APP_DIR"
    echo "  端口: $APP_PORT"
    echo ""
    read -p "开始部署? (y/n): " confirm
    if [[ $confirm != "y" && $confirm != "Y" ]]; then
        print_info "已取消部署"
        exit 0
    fi
    
    # 执行部署步骤
    install_dependencies
    setup_project
    setup_venv
    setup_config
    setup_nginx
    setup_systemd
    setup_firewall
    
    # SSL（可选）
    read -p "是否申请 SSL 证书? (y/n): " ssl_confirm
    if [[ $ssl_confirm == "y" || $ssl_confirm == "Y" ]]; then
        setup_ssl
    fi
    
    # 启动服务
    start_service
    
    # 健康检查
    health_check
    
    # 创建管理脚本
    create_manage_script
    
    # 完成信息
    print_finish
}

# 运行主函数
main "$@"
