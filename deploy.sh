#!/bin/bash
# Suni AI 部署脚本
# 用于在 Ubuntu/Debian 服务器上一键部署
# 用法: sudo bash deploy.sh

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量（可根据需要修改）
DOMAIN="www.suniai.site"
EMAIL="your-email@example.com"  # 用于 SSL 证书
APP_NAME="suniai"
APP_DIR="/opt/claw_with_rag"
APP_PORT=3000
PYTHON_VERSION="3.11"

# 打印带颜色的信息
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

# 检查 root 权限
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "请使用 sudo 运行此脚本"
        exit 1
    fi
}

# 检查系统
check_system() {
    print_info "检查系统环境..."
    
    if ! command -v apt &> /dev/null; then
        print_error "此脚本仅支持 Ubuntu/Debian 系统"
        exit 1
    fi
    
    print_success "系统检查通过"
}

# 安装系统依赖
install_dependencies() {
    print_info "安装系统依赖..."
    
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
        supervisor \
        sqlite3 \
        libsqlite3-dev
    
    print_success "系统依赖安装完成"
}

# 配置项目目录（原地工作模式，不复制项目）
setup_project() {
    print_info "检查项目目录..."
    
    # 检查项目目录是否存在且包含必要文件
    if [[ ! -d "$APP_DIR" ]]; then
        print_error "项目目录 $APP_DIR 不存在！"
        print_info "请先上传项目文件到 $APP_DIR"
        print_info "使用方法: scp -r /本地项目路径/* root@服务器IP:$APP_DIR/"
        exit 1
    fi
    
    # 检查关键文件是否存在
    if [[ ! -f "$APP_DIR/run.py" ]]; then
        print_error "未找到 $APP_DIR/run.py，请确认项目文件已正确上传"
        exit 1
    fi
    
    # 只备份配置文件（如果有更新的话）
    SOURCE_CONFIG="/root/claw_with_rag/config.yaml"
    if [[ -f "$SOURCE_CONFIG" ]]; then
        print_info "更新配置文件..."
        mkdir -p $APP_DIR/config
        cp "$SOURCE_CONFIG" $APP_DIR/config/config.yaml
        print_success "配置文件已更新"
    fi
    
    # 确保数据目录存在
    mkdir -p $APP_DIR/data/user_docs
    chmod -R 777 $APP_DIR/data
    
    # 设置权限
    chmod -R 755 $APP_DIR
    
    print_success "项目目录检查完成（原地工作模式，不复制文件）"
}

# 创建 Python 虚拟环境
setup_venv() {
    print_info "配置 Python 虚拟环境..."
    
    cd $APP_DIR
    
    # 如果虚拟环境已存在，询问是否重建
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
    
    # 创建虚拟环境（如果不存在）
    if [[ ! -d "venv" ]]; then
        print_info "创建新的虚拟环境..."
        python3 -m venv venv
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级 pip
    pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
    
    # 安装依赖
    if [[ -f "requirements.txt" ]]; then
        print_info "安装 Python 依赖（使用清华镜像）..."
        pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    else
        print_error "未找到 requirements.txt"
        exit 1
    fi
    
    print_success "虚拟环境配置完成"
}

# 配置应用
setup_config() {
    print_info "配置应用..."
    
    cd $APP_DIR
    
    # 生成随机 JWT 密钥
    JWT_SECRET=$(openssl rand -hex 32)
    
    # 更新配置文件
    if [[ -f "config/config.yaml" ]]; then
        # 备份原配置
        cp config/config.yaml config/config.yaml.bak
        
        # 使用 sed 更新配置
        sed -i "s/secret: \".*\"/secret: \"$JWT_SECRET\"/" config/config.yaml
        sed -i "s|url: \"sqlite+aiosqlite:///.*\"|url: \"sqlite+aiosqlite:///$APP_DIR/data/suni.db\"|" config/config.yaml
        sed -i "s|upload_dir: \".*\"|upload_dir: \"$APP_DIR/data/user_docs\"|" config/config.yaml
        
        print_success "配置文件已更新"
    else
        print_warning "未找到 config/config.yaml，请手动配置"
    fi
}

# 配置 Nginx
setup_nginx() {
    print_info "配置 Nginx..."
    
    # 创建 Nginx 配置
    cat > /etc/nginx/sites-available/$APP_NAME << 'EOF'
server {
    listen 80;
    server_name www.suniai.site suniai.site;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    location /static {
        alias /opt/claw_with_rag/web/static;
        expires 30d;
    }
}
EOF

    # 启用站点
    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/$APP_NAME
    
    # 测试配置
    nginx -t
    
    # 重启 Nginx
    systemctl restart nginx
    systemctl enable nginx
    
    print_success "Nginx 配置完成"
}

# 申请 SSL 证书
setup_ssl() {
    print_info "申请 SSL 证书..."
    
    read -p "请输入邮箱地址（用于 SSL 证书通知）: " EMAIL
    
    if [[ -z "$EMAIL" ]]; then
        print_warning "未提供邮箱，跳过 SSL 配置"
        return
    fi
    
    # 申请证书
    certbot --nginx -d $DOMAIN -d suniai.site --non-interactive --agree-tos -m $EMAIL
    
    # 设置自动续期
    systemctl enable certbot.timer
    systemctl start certbot.timer
    
    print_success "SSL 证书配置完成"
}

# 创建 Systemd 服务
setup_systemd() {
    print_info "创建 Systemd 服务..."
    
    cat > /etc/systemd/system/$APP_NAME.service << EOF
[Unit]
Description=Suni AI Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
Environment="PYTHONPATH=$APP_DIR"
Environment="PYTHONUNBUFFERED=1"
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/run.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # 重新加载配置
    systemctl daemon-reload
    systemctl enable $APP_NAME
    
    print_success "Systemd 服务创建完成"
}

# 配置防火墙
setup_firewall() {
    print_info "配置防火墙..."
    
    # 安装 ufw（如果未安装）
    apt install -y ufw
    
    # 允许必要端口
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp    # SSH
    ufw allow 80/tcp    # HTTP
    ufw allow 443/tcp   # HTTPS
    
    # 启用防火墙
    ufw --force enable
    
    print_success "防火墙配置完成"
}

# 启动服务
start_service() {
    print_info "启动 Suni AI 服务..."
    
    systemctl start $APP_NAME
    sleep 3
    
    # 检查服务状态
    if systemctl is-active --quiet $APP_NAME; then
        print_success "服务启动成功！"
    else
        print_error "服务启动失败，查看日志: journalctl -u $APP_NAME -n 50"
        exit 1
    fi
}

# 打印完成信息
print_finish() {
    echo ""
    echo "=========================================="
    print_success "Suni AI 部署完成！"
    echo "=========================================="
    echo ""
    echo -e "访问地址: ${GREEN}https://$DOMAIN${NC}"
    echo -e "本地测试: ${GREEN}curl http://localhost:$APP_PORT${NC}"
    echo ""
    echo "常用命令:"
    echo -e "  查看状态: ${BLUE}systemctl status $APP_NAME${NC}"
    echo -e "  查看日志: ${BLUE}journalctl -u $APP_NAME -f${NC}"
    echo -e "  重启服务: ${BLUE}systemctl restart $APP_NAME${NC}"
    echo -e "  停止服务: ${BLUE}systemctl stop $APP_NAME${NC}"
    echo ""
    echo "配置文件位置:"
    echo -e "  应用配置: ${BLUE}$APP_DIR/config/config.yaml${NC}"
    echo -e "  Nginx 配置: ${BLUE}/etc/nginx/sites-available/$APP_NAME${NC}"
    echo -e "  服务配置: ${BLUE}/etc/systemd/system/$APP_NAME.service${NC}"
    echo ""
}

# 主函数
main() {
    echo "=========================================="
    echo "  Suni AI 一键部署脚本"
    echo "=========================================="
    echo ""
    
    check_root
    check_system
    
    read -p "开始部署? (y/n): " confirm
    if [[ $confirm != "y" && $confirm != "Y" ]]; then
        print_info "已取消部署"
        exit 0
    fi
    
    install_dependencies
    setup_project
    setup_venv
    setup_config
    setup_nginx
    setup_systemd
    setup_firewall
    
    read -p "是否申请 SSL 证书? (y/n): " ssl_confirm
    if [[ $ssl_confirm == "y" || $ssl_confirm == "Y" ]]; then
        setup_ssl
    fi
    
    start_service
    print_finish
}

# 运行主函数
main "$@"
