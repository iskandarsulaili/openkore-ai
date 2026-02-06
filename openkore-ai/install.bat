@echo off
setlocal enabledelayedexpansion
:: ============================================================================
:: OpenKore Advanced AI System - Installation Script
:: ============================================================================

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "LOG_FILE=%SCRIPT_DIR%\install.log"
set "VENV_DIR=%SCRIPT_DIR%\venv"
set "REQUIREMENTS_FILE=%SCRIPT_DIR%\ai-service\requirements.txt"

echo. > "%LOG_FILE%"

cls
echo.
echo ========================================================================
echo    OpenKore AI - Advanced AI System
echo    Installation Script
echo ========================================================================
echo.

echo [INFO] Starting installation...
echo [INFO] Starting installation... >> "%LOG_FILE%"

:: ============================================================================
:: DETECT PYTHON
:: ============================================================================

echo [INFO] Checking for Python...
echo [INFO] Checking for Python... >> "%LOG_FILE%"

set "PYTHON_CMD="

python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_CMD=python"
) else (
    python3 --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_CMD=python3"
    ) else (
        py --version >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_CMD=py"
        ) else (
            echo [ERROR] Python not found. Please install Python 3.11+
            echo [ERROR] Python not found >> "%LOG_FILE%"
            pause
            exit /b 1
        )
    )
)

echo [SUCCESS] Found Python: !PYTHON_CMD!
echo [SUCCESS] Found Python: !PYTHON_CMD! >> "%LOG_FILE%"

:: ============================================================================
:: DETECT GPU
:: ============================================================================

echo [INFO] Detecting GPU capabilities...
echo [INFO] Detecting GPU capabilities... >> "%LOG_FILE%"

set "HAS_GPU=0"
nvidia-smi >nul 2>&1
if !errorlevel! equ 0 (
    set "HAS_GPU=1"
    echo [SUCCESS] NVIDIA GPU detected
    echo [SUCCESS] NVIDIA GPU detected >> "%LOG_FILE%"
) else (
    echo [INFO] No NVIDIA GPU detected - will install CPU version
    echo [INFO] No NVIDIA GPU detected - will install CPU version >> "%LOG_FILE%"
)

:: ============================================================================
:: VIRTUAL ENVIRONMENT
:: ============================================================================

if exist "%VENV_DIR%\Scripts\python.exe" (
    echo [INFO] Virtual environment already exists
    echo [INFO] Virtual environment already exists >> "%LOG_FILE%"
) else (
    echo [INFO] Creating virtual environment...
    echo [INFO] Creating virtual environment... >> "%LOG_FILE%"
    !PYTHON_CMD! -m venv "%VENV_DIR%" >> "%LOG_FILE%" 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment
        echo [ERROR] Failed to create virtual environment >> "%LOG_FILE%"
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created
    echo [SUCCESS] Virtual environment created >> "%LOG_FILE%"
)

:: Use venv Python
set "PYTHON_CMD=%VENV_DIR%\Scripts\python.exe"

:: ============================================================================
:: UPGRADE PIP
:: ============================================================================

echo [INFO] Updating pip...
echo [INFO] Updating pip... >> "%LOG_FILE%"
"%PYTHON_CMD%" -m pip install --upgrade pip >> "%LOG_FILE%" 2>&1

:: ============================================================================
:: INSTALL PYTORCH
:: ============================================================================

if !HAS_GPU! equ 1 (
    echo [INFO] Installing PyTorch with CUDA support...
    echo [INFO] Installing PyTorch with CUDA support... >> "%LOG_FILE%"
    "%PYTHON_CMD%" -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 >> "%LOG_FILE%" 2>&1
) else (
    echo [INFO] Installing PyTorch CPU version...
    echo [INFO] Installing PyTorch CPU version... >> "%LOG_FILE%"
    "%PYTHON_CMD%" -m pip install torch torchvision torchaudio >> "%LOG_FILE%" 2>&1
)

if !errorlevel! neq 0 (
    echo [ERROR] Failed to install PyTorch
    echo [ERROR] Failed to install PyTorch >> "%LOG_FILE%"
    pause
    exit /b 1
)
echo [SUCCESS] PyTorch installed
echo [SUCCESS] PyTorch installed >> "%LOG_FILE%"

:: ============================================================================
:: INSTALL REQUIREMENTS
:: ============================================================================

if exist "%REQUIREMENTS_FILE%" (
    echo [INFO] Installing requirements...
    echo [INFO] Installing requirements... >> "%LOG_FILE%"
    "%PYTHON_CMD%" -m pip install -r "%REQUIREMENTS_FILE%" >> "%LOG_FILE%" 2>&1
    if !errorlevel! neq 0 (
        echo [WARNING] Some requirements may have failed
        echo [WARNING] Some requirements may have failed >> "%LOG_FILE%"
    ) else (
        echo [SUCCESS] Requirements installed
        echo [SUCCESS] Requirements installed >> "%LOG_FILE%"
    )
) else (
    echo [WARNING] requirements.txt not found
    echo [WARNING] requirements.txt not found >> "%LOG_FILE%"
)

:: ============================================================================
:: VERIFY
:: ============================================================================

echo [INFO] Verifying installation...
echo [INFO] Verifying installation... >> "%LOG_FILE%"

"%PYTHON_CMD%" -c "import torch; print('PyTorch OK'); print('CUDA available:', torch.cuda.is_available())" >> "%LOG_FILE%" 2>&1
if !errorlevel! neq 0 (
    echo [WARNING] PyTorch import check failed
    echo [WARNING] PyTorch import check failed >> "%LOG_FILE%"
) else (
    echo [SUCCESS] PyTorch verified
    echo [SUCCESS] PyTorch verified >> "%LOG_FILE%"
)

:: ============================================================================
:: COMPLETE
:: ============================================================================

echo.
echo ========================================================================
echo   Installation Complete!
echo ========================================================================
echo.
echo [SUCCESS] Installation completed successfully
echo [SUCCESS] Installation completed successfully >> "%LOG_FILE%"
echo.
echo Log file: %LOG_FILE%
echo.

pause
exit /b 0
