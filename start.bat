@echo off
echo ================================================
echo Suni AI - 企业知识智能体平台
echo ================================================
echo.

cd /d %~dp0

REM 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [警告] 未找到虚拟环境，使用系统 Python
)

REM 检查配置文件
if not exist "config\config.yaml" (
    echo [错误] 配置文件不存在: config\config.yaml
    pause
    exit /b 1
)

REM 启动服务
echo [信息] 启动 Suni AI 服务...
python run.py