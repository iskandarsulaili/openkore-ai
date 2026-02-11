@echo off
setlocal enabledelayedexpansion
:: ============================================================================
:: OpenKore Advanced AI System - Startup Script
:: ============================================================================
:: This script starts the C++ AI Engine, Python AI Service, and OpenKore
:: with proper health checks and process management
:: ============================================================================

:: Script configuration
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "LOG_FILE=%SCRIPT_DIR%\startup.log"
set "VENV_DIR=%SCRIPT_DIR%\venv"
set "AI_SERVICE_DIR=%SCRIPT_DIR%\ai-service"
set "AI_ENGINE_DIR=%SCRIPT_DIR%\ai-engine"
set "CONFIG_DIR=%SCRIPT_DIR%\config"
set "DATA_DIR=%SCRIPT_DIR%\data"
set "LOGS_DIR=%SCRIPT_DIR%\logs"
set "SECRET_FILE=%SCRIPT_DIR%\..\secret.txt"

:: Process configuration
set "AI_ENGINE_EXE=%SCRIPT_DIR%\ai-engine.exe"
set "AI_SERVICE_MAIN=%AI_SERVICE_DIR%\src\main.py"

:: Port configuration
set "GODTIER_AI_SERVICE_PORT=9901"
set "AI_ENGINE_PORT=9901"
set "AI_SERVICE_PORT=9902"

:: Process IDs (will be populated)
set "AI_ENGINE_PID="
set "AI_SERVICE_PID="

:: Health check configuration
set "ENGINE_RETRY_COUNT=10"
set "SERVICE_RETRY_COUNT=15"
set "RETRY_DELAY=2"
set "ENGINE_START_DELAY=5"
set "SERVICE_START_DELAY=15"

:: Restart configuration
set "MAX_RESTARTS=3"
set "ENGINE_RESTART_COUNT=0"
set "SERVICE_RESTART_COUNT=0"

:: Clear previous log
echo. > "%LOG_FILE%"

:: ============================================================================
:: LOGGING FUNCTIONS
:: ============================================================================

goto :skip_functions

:log_info
echo [INFO] %*
echo [INFO] %* >> "%LOG_FILE%" 2>nul
goto :eof

:log_success
echo [SUCCESS] %*
echo [SUCCESS] %* >> "%LOG_FILE%" 2>nul
goto :eof

:log_warning
echo [WARNING] %*
echo [WARNING] %* >> "%LOG_FILE%" 2>nul
goto :eof

:log_error
echo [ERROR] %*
echo [ERROR] %* >> "%LOG_FILE%" 2>nul
goto :eof

:log_step
echo [STEP] %*
echo [STEP] %* >> "%LOG_FILE%" 2>nul
goto :eof

:skip_functions

:: ============================================================================
:: BANNER
:: ============================================================================

cls
echo.
echo ========================================================================
echo    OpenKore AI - Advanced AI System
echo    Startup Script
echo ========================================================================
echo.
echo               Starting Multi-Layer AI System
echo.

call :log_info "Starting OpenKore AI System..."
call :log_info "Script directory: %SCRIPT_DIR%"
call :log_info "Log file: %LOG_FILE%"
echo.

:: ============================================================================
:: PRE-FLIGHT CHECKS
:: ============================================================================

call :log_step "Running pre-flight checks..."
echo.

:: Check if install.bat was run
call :log_info "Checking Python installation..."

set "PYTHON_CMD="
set "PYTHON_FOUND=0"

:: Check if venv exists
if exist "%VENV_DIR%\Scripts\python.exe" (
    set "PYTHON_CMD=%VENV_DIR%\Scripts\python.exe"
    set "PYTHON_FOUND=1"
    call :log_success "Found Python in virtual environment"
) else (
    :: Check system Python
    python --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_CMD=python"
        set "PYTHON_FOUND=1"
        call :log_success "Found system Python"
    ) else (
        py --version >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_CMD=py"
            set "PYTHON_FOUND=1"
            call :log_success "Found Python via py launcher"
        )
    )
)

if !PYTHON_FOUND! equ 0 (
    call :log_error "Python not found. Please run install.bat first."
    goto :error_exit
)

:: Check required directories
call :log_info "Checking directory structure..."

if not exist "%DATA_DIR%" (
    call :log_error "Data directory not found: %DATA_DIR%"
    call :log_error "Please run install.bat first"
    goto :error_exit
)

if not exist "%LOGS_DIR%" (
    call :log_warning "Logs directory not found, creating: %LOGS_DIR%"
    mkdir "%LOGS_DIR%" 2>nul
)

if not exist "%CONFIG_DIR%" (
    call :log_error "Config directory not found: %CONFIG_DIR%"
    goto :error_exit
)

call :log_success "Directory structure OK"

:: Check configuration files
call :log_info "Checking configuration files..."

if not exist "%CONFIG_DIR%\ai-engine.yaml" (
    call :log_error "Missing: config/ai-engine.yaml"
    goto :error_exit
)

if not exist "%CONFIG_DIR%\ai-service.yaml" (
    call :log_error "Missing: config/ai-service.yaml"
    goto :error_exit
)

if not exist "%CONFIG_DIR%\plugin.yaml" (
    call :log_error "Missing: config/plugin.yaml"
    goto :error_exit
)

call :log_success "Configuration files OK"

:: Check secret.txt
if not exist "%SECRET_FILE%" (
    call :log_error "API key file not found: %SECRET_FILE%"
    call :log_error "Please create secret.txt with your DeepSeek API key"
    goto :error_exit
)

call :log_success "API key file found"

:: Check AI Engine executable
if not exist "%AI_ENGINE_EXE%" (
    call :log_error "AI Engine not found: %AI_ENGINE_EXE%"
    call :log_error "Please compile or download ai-engine.exe"
    goto :error_exit
)

call :log_success "AI Engine executable found"

:: Check AI Service main.py
if not exist "%AI_SERVICE_MAIN%" (
    call :log_error "AI Service not found: %AI_SERVICE_MAIN%"
    goto :error_exit
)

call :log_success "AI Service script found"

:: Check OpenKore openkore.pl
if not exist "%SCRIPT_DIR%\openkore.pl" (
    call :log_error "OpenKore script not found"
    goto :error_exit
)

call :log_success "OpenKore script found"

:: Check if ports are available (informational only)
call :log_info "Checking port availability..."

netstat -ano | findstr ":%AI_ENGINE_PORT%" >nul 2>&1
if !errorlevel! equ 0 (
    call :log_warning "Port %AI_ENGINE_PORT% is currently in use (will be cleaned up)"
) else (
    call :log_success "Port %AI_ENGINE_PORT% is available"
)

netstat -ano | findstr ":%AI_SERVICE_PORT%" >nul 2>&1
if !errorlevel! equ 0 (
    call :log_warning "Port %AI_SERVICE_PORT% is currently in use (will be cleaned up)"
) else (
    call :log_success "Port %AI_SERVICE_PORT% is available"
)

echo.
call :log_success "All pre-flight checks passed!"
echo.

:: ============================================================================
:: LOG CLEANUP
:: ============================================================================

call :log_step "Log Cleanup"
call :log_info "Cleaning old log files before starting services..."
echo.

:: Define log directories to clean
set "LOG_DIR_1=%SCRIPT_DIR%\logs"
set "LOG_DIR_2=%SCRIPT_DIR%\ai-service\logs"
set "LOG_DIR_3=%SCRIPT_DIR%\..\logs"

:: Create directories if they don't exist
if not exist "%LOG_DIR_1%" (
    call :log_info "Creating directory: %LOG_DIR_1%"
    mkdir "%LOG_DIR_1%" 2>nul
)

if not exist "%LOG_DIR_2%" (
    call :log_info "Creating directory: %LOG_DIR_2%"
    mkdir "%LOG_DIR_2%" 2>nul
)

if not exist "%LOG_DIR_3%" (
    call :log_info "Creating directory: %LOG_DIR_3%"
    mkdir "%LOG_DIR_3%" 2>nul
)

:: Clean log files in openkore-ai\logs
set "FILES_DELETED=0"
if exist "%LOG_DIR_1%\*.log" (
    call :log_info "Deleting *.log files in %LOG_DIR_1%"
    del /Q "%LOG_DIR_1%\*.log" 2>nul
    if !errorlevel! equ 0 set "FILES_DELETED=1"
)
if exist "%LOG_DIR_1%\*.txt" (
    call :log_info "Deleting *.txt files in %LOG_DIR_1%"
    del /Q "%LOG_DIR_1%\*.txt" 2>nul
    if !errorlevel! equ 0 set "FILES_DELETED=1"
)

:: Clean log files in openkore-ai\ai-service\logs
if exist "%LOG_DIR_2%\*.log" (
    call :log_info "Deleting *.log files in %LOG_DIR_2%"
    del /Q "%LOG_DIR_2%\*.log" 2>nul
    if !errorlevel! equ 0 set "FILES_DELETED=1"
)
if exist "%LOG_DIR_2%\*.txt" (
    call :log_info "Deleting *.txt files in %LOG_DIR_2%"
    del /Q "%LOG_DIR_2%\*.txt" 2>nul
    if !errorlevel! equ 0 set "FILES_DELETED=1"
)

:: Clean log files in parent logs directory
if exist "%LOG_DIR_3%\*.log" (
    call :log_info "Deleting *.log files in %LOG_DIR_3%"
    del /Q "%LOG_DIR_3%\*.log" 2>nul
    if !errorlevel! equ 0 set "FILES_DELETED=1"
)
if exist "%LOG_DIR_3%\*.txt" (
    call :log_info "Deleting *.txt files in %LOG_DIR_3%"
    del /Q "%LOG_DIR_3%\*.txt" 2>nul
    if !errorlevel! equ 0 set "FILES_DELETED=1"
)

if !FILES_DELETED! equ 1 (
    call :log_success "Old log files cleaned successfully"
) else (
    call :log_info "No old log files found to clean"
)
echo.

:: ============================================================================
:: SETUP CLEANUP HANDLER
:: ============================================================================

:: Setup Ctrl+C handler
if /i "%~1"=="child" goto :start_services

:: ============================================================================
:: CLEANUP: Terminate zombie processes from previous runs
:: ============================================================================

call :log_step "5" "Cleanup"
call :log_info "Terminating any existing AI processes..."
echo.

:: Kill all ai-engine.exe instances
taskkill /F /IM ai-engine.exe >nul 2>&1
if !errorlevel! equ 0 (
    call :log_warning "Terminated existing ai-engine.exe processes"
) else (
    call :log_info "No existing ai-engine.exe processes found"
)

:: Kill processes using port 9901
set "PORT_9901_KILLED=0"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":9901.*LISTENING" 2^>nul') do (
    call :log_warning "Killing process on port 9901 (PID: %%a)"
    taskkill /F /PID %%a >nul 2>&1
    set "PORT_9901_KILLED=1"
)
if !PORT_9901_KILLED! equ 0 (
    call :log_info "Port 9901 is not in use"
)

:: Kill processes using port 9902
set "PORT_9902_KILLED=0"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":9902.*LISTENING" 2^>nul') do (
    call :log_warning "Killing process on port 9902 (PID: %%a)"
    taskkill /F /PID %%a >nul 2>&1
    set "PORT_9902_KILLED=1"
)
if !PORT_9902_KILLED! equ 0 (
    call :log_info "Port 9902 is not in use"
)

:: Wait for ports to release
ping 127.0.0.1 -n 3 > nul 2>&1

call :log_success "Cleanup complete - all previous instances terminated"
echo.

:: ============================================================================
:: START SERVICES
:: ============================================================================

:start_services

call :log_step "6" "Starting AI Engine (Port %AI_ENGINE_PORT%)..."
echo.

:: Start C++ AI Engine in NEW WINDOW using verified executable path
call :log_info "Launching ai-engine.exe in separate window from %SCRIPT_DIR%..."
start "AI Engine (Port %AI_ENGINE_PORT%)" cmd /k "%AI_ENGINE_EXE%"

:: Get the PID of ai-engine.exe
ping 127.0.0.1 -n 3 > nul 2>&1
for /f "tokens=2" %%a in ('tasklist /fi "imagename eq ai-engine.exe" /fo list ^| findstr "PID:"') do (
    set "AI_ENGINE_PID=%%a"
)

if "!AI_ENGINE_PID!"=="" (
    call :log_error "Failed to start AI Engine"
    goto :cleanup_exit
)

call :log_success "AI Engine started in separate window (PID: !AI_ENGINE_PID!)"

:: Wait for engine to initialize
call :log_info "Waiting %ENGINE_START_DELAY% seconds for engine initialization..."
set /a PING_COUNT=%ENGINE_START_DELAY%+1
ping 127.0.0.1 -n %PING_COUNT% > nul 2>&1

:: Health check for AI Engine
call :log_info "Performing health check on AI Engine..."
call :health_check_engine
if !errorlevel! neq 0 (
    call :log_warning "AI Engine health check failed (may still be starting in separate window)"
    echo.
    echo Note: AI Engine is running in a separate window. Check that window for errors.
    echo Do you want to continue anyway? ^(Y/N^)
    set /p "CONTINUE=Continue? "
    if /i "!CONTINUE!" neq "Y" (
        goto :cleanup_exit
    )
    call :log_warning "Continuing despite failed health check..."
) else (
    call :log_success "AI Engine is healthy and responding"
)

echo.
call :log_step "7" "Starting AI Service (Port %AI_SERVICE_PORT%)..."
echo.

:: Start Python AI Service in NEW WINDOW
call :log_info "Launching main.py in separate window..."
if exist "%VENV_DIR%\Scripts\python.exe" (
    start "AI Service (Port %AI_SERVICE_PORT%)" /D "%SCRIPT_DIR%" cmd /k ""%VENV_DIR%\Scripts\python.exe" "%AI_SERVICE_MAIN%""
) else (
    start "AI Service (Port %AI_SERVICE_PORT%)" /D "%SCRIPT_DIR%" cmd /k "!PYTHON_CMD! "%AI_SERVICE_MAIN%""
)

:: Get the PID of python process
ping 127.0.0.1 -n 3 > nul 2>&1
for /f "tokens=2" %%a in ('tasklist /fi "imagename eq python.exe" /fo list ^| findstr "PID:"') do (
    set "AI_SERVICE_PID=%%a"
)

if "!AI_SERVICE_PID!"=="" (
    call :log_warning "Could not detect AI Service PID (multiple Python processes may be running)"
) else (
    call :log_success "AI Service started in separate window (PID: !AI_SERVICE_PID!)"
)

:: Wait for service to initialize
call :log_info "Waiting %SERVICE_START_DELAY% seconds for service initialization..."
set /a PING_COUNT=%SERVICE_START_DELAY%+1
ping 127.0.0.1 -n %PING_COUNT% > nul 2>&1

:: Health check for AI Service
call :log_info "Performing health check on AI Service..."
call :health_check_service
if !errorlevel! neq 0 (
    call :log_warning "AI Service health check failed (may still be starting in separate window)"
    echo.
    echo Note: AI Service is running in a separate window. Check that window for errors.
    echo Do you want to continue anyway? ^(Y/N^)
    set /p "CONTINUE=Continue? "
    if /i "!CONTINUE!" neq "Y" (
        goto :cleanup_exit
    )
    call :log_warning "Continuing despite failed health check..."
) else (
    call :log_success "AI Service is healthy and responding"
)

:: ============================================================================
:: SYSTEM READY
:: ============================================================================

echo.
echo ========================================================================
echo   AI System Ready!
echo ========================================================================
echo.
call :log_success "All AI services are running"
echo.
echo Service Status:
echo   [OK] AI Engine:  http://127.0.0.1:%AI_ENGINE_PORT% (PID: !AI_ENGINE_PID!)
echo   [OK] AI Service: http://127.0.0.1:%AI_SERVICE_PORT% (PID: !AI_SERVICE_PID!)
echo.
echo [36mAuto-launching OpenKore in 3 seconds...[0m
timeout /t 3 /nobreak >nul

:: ============================================================================
:: LAUNCH OPENKORE
:: ============================================================================

echo.
call :log_step "8" "Launching OpenKore..."
echo.

:: Check for Perl
perl -v >nul 2>&1
if !errorlevel! neq 0 (
    call :log_error "Perl not found. Please install Perl to run OpenKore."
    goto :cleanup_exit
)

call :log_info "Starting OpenKore in separate window..."
echo.
echo ========================================================================
echo   OpenKore is starting...
echo ========================================================================
echo.

:: Start OpenKore in NEW WINDOW
cd /d "%SCRIPT_DIR%"
start "OpenKore" /D "%SCRIPT_DIR%" cmd /k "perl openkore.pl"

call :log_success "OpenKore launched in separate window"
echo.
echo ========================================================================
echo   All Services Launched!
echo ========================================================================
echo.
echo Service Status:
echo   [OK] AI Engine:  http://127.0.0.1:%AI_ENGINE_PORT% (PID: !AI_ENGINE_PID!) - Separate window
echo   [OK] AI Service: http://127.0.0.1:%AI_SERVICE_PORT% (PID: !AI_SERVICE_PID!) - Separate window
echo   [OK] OpenKore: Running in separate window
echo.
echo This launcher window will remain open to monitor services.
echo Close this window or press Ctrl+C to stop all services.
echo.
echo Press any key to exit and stop all services...
pause >nul

:: User wants to exit, cleanup services
call :log_info "User requested shutdown"
goto :cleanup_exit

:: ============================================================================
:: HEALTH CHECK FUNCTIONS
:: ============================================================================

:health_check_engine
set "HEALTH_URL=http://127.0.0.1:%AI_ENGINE_PORT%/api/v1/health"
set "RETRY=0"

:engine_health_retry
set /a RETRY+=1

:: Try curl first (Windows 10+)
curl --version >nul 2>&1
if !errorlevel! equ 0 (
    curl -s -o nul -w "%%{http_code}" "%HEALTH_URL%" 2>nul | findstr "200" >nul
    if !errorlevel! equ 0 (
        exit /b 0
    )
) else (
    :: Fallback: check if port is listening
    netstat -ano | findstr ":%AI_ENGINE_PORT%" | findstr "LISTENING" >nul
    if !errorlevel! equ 0 (
        exit /b 0
    )
)

if !RETRY! lss %ENGINE_RETRY_COUNT% (
    call :log_warning "Health check attempt !RETRY!/%ENGINE_RETRY_COUNT% failed, retrying..."
    ping 127.0.0.1 -n %RETRY_DELAY% > nul 2>&1
    goto :engine_health_retry
)

exit /b 1

:health_check_service
set "HEALTH_URL=http://127.0.0.1:%AI_SERVICE_PORT%/api/v1/health"
set "RETRY=0"

:service_health_retry
set /a RETRY+=1

:: Try curl first (Windows 10+)
curl --version >nul 2>&1
if !errorlevel! equ 0 (
    curl -s -o nul -w "%%{http_code}" "%HEALTH_URL%" 2>nul | findstr "200" >nul
    if !errorlevel! equ 0 (
        exit /b 0
    )
) else (
    :: Fallback: check if port is listening
    netstat -ano | findstr ":%AI_SERVICE_PORT%" | findstr "LISTENING" >nul
    if !errorlevel! equ 0 (
        exit /b 0
    )
)

if !RETRY! lss %SERVICE_RETRY_COUNT% (
    call :log_warning "Health check attempt !RETRY!/%SERVICE_RETRY_COUNT% failed, retrying..."
    ping 127.0.0.1 -n %RETRY_DELAY% > nul 2>&1
    goto :service_health_retry
)

exit /b 1

:: ============================================================================
:: CLEANUP FUNCTION
:: ============================================================================

:cleanup_exit
echo.
call :log_step "Shutting down AI services..."
echo.

:: Kill AI Service
if not "!AI_SERVICE_PID!"=="" (
    call :log_info "Stopping AI Service (PID: !AI_SERVICE_PID!)..."
    taskkill /PID !AI_SERVICE_PID! /F >nul 2>&1
    if !errorlevel! equ 0 (
        call :log_success "AI Service stopped"
    ) else (
        call :log_warning "Could not stop AI Service gracefully"
    )
) else (
    :: Kill all python processes running main.py (fallback)
    call :log_info "Stopping AI Service processes..."
    for /f "tokens=2" %%a in ('tasklist /fi "imagename eq python.exe" /fo list ^| findstr "PID:"') do (
        taskkill /PID %%a /F >nul 2>&1
    )
)

:: Kill AI Engine
if not "!AI_ENGINE_PID!"=="" (
    call :log_info "Stopping AI Engine (PID: !AI_ENGINE_PID!)..."
    taskkill /PID !AI_ENGINE_PID! /F >nul 2>&1
    if !errorlevel! equ 0 (
        call :log_success "AI Engine stopped"
    ) else (
        call :log_warning "Could not stop AI Engine gracefully"
    )
) else (
    :: Kill all ai-engine.exe processes (fallback)
    call :log_info "Stopping AI Engine processes..."
    taskkill /IM ai-engine.exe /F >nul 2>&1
)

:: Save final logs
call :log_info "Saving final logs..."
if exist "%LOGS_DIR%\ai-engine.log" (
    echo ========== SESSION ENDED: %date% %time% ========== >> "%LOGS_DIR%\ai-engine.log"
)
if exist "%LOGS_DIR%\ai-service.log" (
    echo ========== SESSION ENDED: %date% %time% ========== >> "%LOGS_DIR%\ai-service.log"
)

echo.
echo ========================================================================
echo   Shutdown Complete
echo ========================================================================
echo.
call :log_success "All services stopped gracefully"
echo.
echo Logs saved to:
echo   - Startup: %LOG_FILE%
echo   - AI Engine: %LOGS_DIR%\ai-engine.log
echo   - AI Service: %LOGS_DIR%\ai-service.log
echo.

pause
endlocal
exit /b 0

:: ============================================================================
:: ERROR EXIT
:: ============================================================================

:error_exit
echo.
echo ========================================================================
echo   Startup Failed
echo ========================================================================
echo.
call :log_error "Failed to start OpenKore AI System"
echo.
echo For help, check:
echo   - Log file: %LOG_FILE%
echo   - Run install.bat to verify installation
echo   - Check configuration files in config/
echo.

:: Cleanup any started services
if not "!AI_ENGINE_PID!"=="" (
    taskkill /PID !AI_ENGINE_PID! /F >nul 2>&1
)
if not "!AI_SERVICE_PID!"=="" (
    taskkill /PID !AI_SERVICE_PID! /F >nul 2>&1
)

pause
endlocal
exit /b 1
