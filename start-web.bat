@echo off
chcp 65001 >nul
echo ========================================
echo   AI Voice Cloner - Web Interface
echo ========================================
echo.

cd /d "%~dp0"

:: 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo [错误] 未找到虚拟环境，请先运行: python -m venv venv
    pause
    exit /b 1
)

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 启动Web服务器
echo.
echo 🚀 正在启动Web服务器...
echo 📍 访问地址: http://127.0.0.1:5000
echo 💡 按 Ctrl+C 停止服务器
echo.
python app.py

pause
