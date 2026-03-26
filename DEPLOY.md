# 部署指南

## 环境变量配置

部署前请务必设置以下环境变量：

```bash
# 必需：OpenClaw Gateway 地址（流式输出功能依赖）
export OPENCLAW_GATEWAY_URL=http://localhost:8080

# 可选：OpenClaw Token
export OPENCLAW_GATEWAY_TOKEN=your_token_here

# 可选：自定义配置路径
export RAG_CONFIG=/opt/claw_with_rag/config/config.yaml
```

**systemd 服务配置方式：**

编辑 `/etc/systemd/system/suniai.service`：

```ini
[Service]
Environment="OPENCLAW_GATEWAY_URL=http://localhost:8080"
Environment="OPENCLAW_GATEWAY_TOKEN=your_token_here"
```

然后重载并重启：
```bash
sudo systemctl daemon-reload
sudo systemctl restart suniai
```

---

## 快速部署

### 1. 上传项目到服务器

```bash
# 在你的 Windows 上执行（使用 PowerShell）
scp -r D:\openclaw\code\claw_with_rag root@你的服务器IP:/tmp/
```

### 2. SSH 登录服务器并执行部署

```bash
ssh root@你的服务器IP

# 移动项目到 /opt
cp -r /tmp/claw_with_rag /opt/
cd /opt/claw_with_rag

# 执行部署脚本
sudo bash deploy.sh
```

### 3. 按提示操作

- 输入邮箱地址申请 SSL 证书
- 等待部署完成

### 4. 访问

打开浏览器访问: `https://www.suniai.site`

---

## 手动部署步骤

如果自动脚本遇到问题，可以按以下步骤手动部署：

### 安装依赖

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx
```

### 配置项目

```bash
cd /opt/claw_with_rag
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 启动服务

```bash
python run.py
```

---

## 常用命令

```bash
# 查看服务状态
sudo systemctl status suniai

# 查看实时日志
sudo journalctl -u suniai -f

# 重启服务
sudo systemctl restart suniai

# 停止服务
sudo systemctl stop suniai

# 更新代码后重启
sudo bash /opt/claw_with_rag/update.sh
```

---

## 故障排查

### 服务启动失败

```bash
# 查看详细日志
sudo journalctl -u suniai -n 100 --no-pager

# 手动运行查看错误
source /opt/claw_with_rag/venv/bin/activate
cd /opt/claw_with_rag
python run.py
```

### 端口被占用

```bash
# 查看占用 3000 端口的进程
sudo lsof -i :3000

# 杀掉进程
sudo kill -9 <PID>
```

### Nginx 配置错误

```bash
# 测试配置
sudo nginx -t

# 重新加载
sudo systemctl reload nginx
```

### SSL 证书问题

```bash
# 重新申请证书
sudo certbot --nginx -d www.suniai.site

# 强制续期
sudo certbot renew --force-renewal
```

---

## 文件说明

| 文件 | 用途 |
|------|------|
| `deploy.sh` | 一键部署脚本 |
| `update.sh` | 更新脚本 |
| `DEPLOY.md` | 本文件 |
