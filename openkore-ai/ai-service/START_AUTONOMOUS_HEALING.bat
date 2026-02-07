@echo off
REM Start OpenKore Autonomous Self-Healing System
REM This script launches the CrewAI-powered monitoring and repair system

echo ============================================================
echo OpenKore Autonomous Self-Healing System
echo ============================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

echo Checking dependencies...
pip show crewai >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r src\autonomous_healing\requirements.txt
)

echo.
echo Starting autonomous healing system...
echo - Monitoring: openkore-ai/logs/
echo - Config: src/autonomous_healing/config.yaml
echo - Mode: Active (will apply fixes)
echo.
echo Press Ctrl+C to stop
echo.

REM Start the system
python src\autonomous_healing\quick_start.py

pause
