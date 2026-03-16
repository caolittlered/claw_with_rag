# Windows PowerShell 安装脚本

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "    企业知识库 RAG Agent 安装脚本" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# 检查 Python
Write-Host "`n[1/5] 检查 Python 环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "错误: 未找到 Python，请先安装 Python 3.9+" -ForegroundColor Red
    exit 1
}

# 检查 pip
Write-Host "`n[2/5] 检查 pip..." -ForegroundColor Yellow
try {
    pip --version | Out-Null
    Write-Host "✓ pip 已安装" -ForegroundColor Green
} catch {
    Write-Host "安装 pip..." -ForegroundColor Yellow
    python -m ensurepip --upgrade
}

# 询问是否创建虚拟环境
$createVenv = Read-Host "是否创建 Python 虚拟环境？(推荐) [Y/n]"
if ([string]::IsNullOrWhiteSpace($createVenv) -or $createVenv -eq "Y" -or $createVenv -eq "y") {
    Write-Host "`n创建虚拟环境..." -ForegroundColor Yellow
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    Write-Host "✓ 虚拟环境已创建并激活" -ForegroundColor Green
} else {
    Write-Host "跳过虚拟环境创建" -ForegroundColor Yellow
}

# 安装 Python 依赖
Write-Host "`n[3/5] 安装 Python 依赖..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install -r requirements.txt
Write-Host "✓ Python 依赖安装完成" -ForegroundColor Green

# 检查 Node.js 和 OpenClaw
Write-Host "`n[4/5] 检查 OpenClaw..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "✓ Node.js: $nodeVersion" -ForegroundColor Green
    
    $openclawVersion = openclaw --version 2>&1
    Write-Host "✓ OpenClaw: $openclawVersion" -ForegroundColor Green
} catch {
    Write-Host "OpenClaw 未安装" -ForegroundColor Yellow
    $installOpenclaw = Read-Host "是否安装 OpenClaw？[Y/n]"
    if ([string]::IsNullOrWhiteSpace($installOpenclaw) -or $installOpenclaw -eq "Y" -or $installOpenclaw -eq "y") {
        npm install -g openclaw
        Write-Host "✓ OpenClaw 安装完成" -ForegroundColor Green
    }
}

# 创建必要目录
Write-Host "`n[5/5] 初始化项目结构..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path docs, data\chroma, logs | Out-Null
Write-Host "✓ 目录创建完成" -ForegroundColor Green

# 复制环境变量模板
if (-not (Test-Path config\.env)) {
    Copy-Item config\.env.example config\.env
    Write-Host "✓ 已创建 config\.env 配置文件" -ForegroundColor Green
}

# 完成
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "    安装完成！" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "下一步："
Write-Host "  1. 编辑 config\.env 填入你的 API 密钥"
Write-Host "  2. 下载模型: python scripts\download_models.py --mirror"
Write-Host "  3. 将知识文档放入 docs\ 目录"
Write-Host "  4. 运行: python src\main.py index  # 索引文档"
Write-Host "  5. 运行: python src\main.py search `"查询内容`"  # 搜索"
Write-Host ""