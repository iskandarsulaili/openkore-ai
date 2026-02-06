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
:: DEPENDENCY INSTALLATION CONFIGURATION
:: ============================================================================

:: Python configuration
set "PYTHON_INSTALL_PATH=C:\Python311"
set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"

:: Perl configuration
set "PERL_INSTALL_PATH=C:\Strawberry"
set "PERL_URL=https://strawberryperl.com/download/5.36.3.1/strawberry-perl-5.36.3.1-64bit.msi"

:: ============================================================================
:: CHECK AND INSTALL PYTHON
:: ============================================================================

echo [INFO] Checking for Python...
echo [INFO] Checking for Python... >> "%LOG_FILE%"

set "PYTHON_CMD="

:: Try to find Python in PATH
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
            :: Check if Python exists in default installation path
            if exist "%PYTHON_INSTALL_PATH%\python.exe" (
                echo [INFO] Found Python in %PYTHON_INSTALL_PATH%
                echo [INFO] Found Python in %PYTHON_INSTALL_PATH% >> "%LOG_FILE%"
                set "PYTHON_CMD=%PYTHON_INSTALL_PATH%\python.exe"
                set "PATH=%PYTHON_INSTALL_PATH%;%PYTHON_INSTALL_PATH%\Scripts;%PATH%"
            ) else (
                :: Python not found - install it
                echo [INFO] Python not found. Installing Python 3.11...
                echo [INFO] Python not found. Installing Python 3.11... >> "%LOG_FILE%"
                
                echo [INFO] Downloading Python installer...
                echo [INFO] Downloading Python installer... >> "%LOG_FILE%"
                
                powershell -NoProfile -Command ^
                    "$ProgressPreference = 'SilentlyContinue'; " ^
                    "try { " ^
                    "    Write-Host '[INFO] Downloading from %PYTHON_URL%'; " ^
                    "    Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%TEMP%\python-installer.exe' -UseBasicParsing -TimeoutSec 300; " ^
                    "    Write-Host '[SUCCESS] Download complete'; " ^
                    "    exit 0; " ^
                    "} catch { " ^
                    "    Write-Host '[ERROR] Download failed:' $_.Exception.Message; " ^
                    "    exit 1; " ^
                    "}" >> "%LOG_FILE%" 2>&1
                
                if !errorlevel! neq 0 (
                    echo [ERROR] Failed to download Python installer
                    echo [ERROR] Failed to download Python installer >> "%LOG_FILE%"
                    echo.
                    echo Please install Python 3.11+ manually from:
                    echo https://www.python.org/downloads/
                    pause
                    exit /b 1
                )
                
                echo [INFO] Installing Python to %PYTHON_INSTALL_PATH%...
                echo [INFO] Installing Python to %PYTHON_INSTALL_PATH%... >> "%LOG_FILE%"
                
                :: Silent installation with all required features
                start /wait "" "%TEMP%\python-installer.exe" /quiet InstallAllUsers=1 TargetDir=%PYTHON_INSTALL_PATH% PrependPath=1 Include_test=0 Include_pip=1
                
                if !errorlevel! neq 0 (
                    echo [ERROR] Python installation failed
                    echo [ERROR] Python installation failed >> "%LOG_FILE%"
                    del "%TEMP%\python-installer.exe" >nul 2>&1
                    pause
                    exit /b 1
                )
                
                :: Clean up installer
                del "%TEMP%\python-installer.exe" >nul 2>&1
                
                :: Add to PATH for this session
                set "PATH=%PYTHON_INSTALL_PATH%;%PYTHON_INSTALL_PATH%\Scripts;%PATH%"
                set "PYTHON_CMD=%PYTHON_INSTALL_PATH%\python.exe"
                
                :: Verify installation
                "%PYTHON_CMD%" --version >nul 2>&1
                if !errorlevel! neq 0 (
                    echo [ERROR] Python installation verification failed
                    echo [ERROR] Python installation verification failed >> "%LOG_FILE%"
                    pause
                    exit /b 1
                )
                
                echo [SUCCESS] Python installed successfully
                echo [SUCCESS] Python installed successfully >> "%LOG_FILE%"
            )
        )
    )
)

:: Validate Python version
for /f "tokens=2" %%v in ('"%PYTHON_CMD%" --version 2^>^&1') do set PYTHON_VERSION=%%v
echo [SUCCESS] Found Python: %PYTHON_VERSION%
echo [SUCCESS] Found Python: %PYTHON_VERSION% >> "%LOG_FILE%"

:: Extract and validate version (3.11+)
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)

if not defined PY_MAJOR set PY_MAJOR=0
if not defined PY_MINOR set PY_MINOR=0

if %PY_MAJOR% LSS 3 (
    echo [WARNING] Python 3.11+ recommended, found %PYTHON_VERSION%
    echo [WARNING] Python 3.11+ recommended, found %PYTHON_VERSION% >> "%LOG_FILE%"
) else if %PY_MAJOR% EQU 3 (
    if %PY_MINOR% LSS 11 (
        echo [WARNING] Python 3.11+ recommended, found %PYTHON_VERSION%
        echo [WARNING] Python 3.11+ recommended, found %PYTHON_VERSION% >> "%LOG_FILE%"
    )
)

:: ============================================================================
:: CHECK AND INSTALL PERL
:: ============================================================================

echo [INFO] Checking for Perl...
echo [INFO] Checking for Perl... >> "%LOG_FILE%"

perl --version >nul 2>&1
if !errorlevel! neq 0 (
    :: Check if Perl exists in default installation path
    if exist "%PERL_INSTALL_PATH%\perl\bin\perl.exe" (
        echo [INFO] Found Perl in %PERL_INSTALL_PATH%
        echo [INFO] Found Perl in %PERL_INSTALL_PATH% >> "%LOG_FILE%"
        set "PATH=%PERL_INSTALL_PATH%\perl\bin;%PERL_INSTALL_PATH%\perl\site\bin;%PATH%"
    ) else (
        :: Perl not found - install it
        echo [INFO] Perl not found. Installing Strawberry Perl...
        echo [INFO] Perl not found. Installing Strawberry Perl... >> "%LOG_FILE%"
        
        echo [INFO] Downloading Strawberry Perl installer...
        echo [INFO] Downloading Strawberry Perl installer... >> "%LOG_FILE%"
        
        powershell -NoProfile -Command ^
            "$ProgressPreference = 'SilentlyContinue'; " ^
            "try { " ^
            "    Write-Host '[INFO] Downloading from %PERL_URL%'; " ^
            "    Invoke-WebRequest -Uri '%PERL_URL%' -OutFile '%TEMP%\strawberry-perl.msi' -UseBasicParsing -TimeoutSec 300; " ^
            "    Write-Host '[SUCCESS] Download complete'; " ^
            "    exit 0; " ^
            "} catch { " ^
            "    Write-Host '[ERROR] Download failed:' $_.Exception.Message; " ^
            "    exit 1; " ^
            "}" >> "%LOG_FILE%" 2>&1
        
        if !errorlevel! neq 0 (
            echo [ERROR] Failed to download Strawberry Perl installer
            echo [ERROR] Failed to download Strawberry Perl installer >> "%LOG_FILE%"
            echo.
            echo Please install Strawberry Perl manually from:
            echo https://strawberryperl.com/
            pause
            exit /b 1
        )
        
        echo [INFO] Installing Strawberry Perl to %PERL_INSTALL_PATH%...
        echo [INFO] Installing Strawberry Perl to %PERL_INSTALL_PATH%... >> "%LOG_FILE%"
        
        :: Silent installation
        start /wait msiexec /i "%TEMP%\strawberry-perl.msi" /quiet /norestart INSTALLDIR="%PERL_INSTALL_PATH%" ADDLOCAL=ALL
        
        if !errorlevel! neq 0 (
            echo [WARNING] Silent installation may have had issues
            echo [WARNING] Silent installation may have had issues >> "%LOG_FILE%"
        )
        
        :: Clean up installer
        del "%TEMP%\strawberry-perl.msi" >nul 2>&1
        
        :: Wait for installation to complete
        timeout /t 3 /nobreak >nul
        
        :: Add to PATH for this session
        set "PATH=%PERL_INSTALL_PATH%\perl\bin;%PERL_INSTALL_PATH%\perl\site\bin;%PATH%"
        
        :: Verify installation
        "%PERL_INSTALL_PATH%\perl\bin\perl.exe" --version >nul 2>&1
        if !errorlevel! neq 0 (
            echo [WARNING] Perl installation verification failed
            echo [WARNING] Perl installation verification failed >> "%LOG_FILE%"
            echo.
            echo Please restart your computer and run this script again.
        ) else (
            echo [SUCCESS] Strawberry Perl installed successfully
            echo [SUCCESS] Strawberry Perl installed successfully >> "%LOG_FILE%"
        )
    )
) else (
    for /f "tokens=*" %%i in ('perl --version 2^>^&1 ^| findstr /i "perl"') do set PERL_VERSION=%%i
    echo [SUCCESS] Found Perl: %PERL_VERSION%
    echo [SUCCESS] Found Perl: %PERL_VERSION% >> "%LOG_FILE%"
)

:: Warn if not Strawberry Perl
perl --version 2>&1 | findstr /I "strawberry" >nul
if !errorlevel! neq 0 (
    echo [WARNING] Non-Strawberry Perl detected
    echo [WARNING] Non-Strawberry Perl detected >> "%LOG_FILE%"
    echo [WARNING] Strawberry Perl is recommended for best compatibility
)

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
    "%PYTHON_CMD%" -m venv "%VENV_DIR%" >> "%LOG_FILE%" 2>&1
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
:: PROMPT FOR API KEY
:: ============================================================================

echo.
echo ========================================================================
echo   API Key Configuration
echo ========================================================================
echo.
echo Please enter your OpenAI API key (or press Enter to skip):
set /p "API_KEY="

if not "!API_KEY!"=="" (
    echo [INFO] Configuring API key...
    echo [INFO] Configuring API key... >> "%LOG_FILE%"
    
    :: Save API key to config file
    if exist "%SCRIPT_DIR%\ai-service\config.py" (
        powershell -NoProfile -Command ^
            "$content = Get-Content '%SCRIPT_DIR%\ai-service\config.py' -Raw; " ^
            "$content = $content -replace 'OPENAI_API_KEY = .*', 'OPENAI_API_KEY = ''!API_KEY!'''; " ^
            "$content | Set-Content '%SCRIPT_DIR%\ai-service\config.py'"
        echo [SUCCESS] API key configured
    ) else (
        echo [WARNING] Config file not found, skipping API key configuration
    )
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
echo Installed components:
echo   - Python: %PYTHON_VERSION%
echo   - Perl: %PERL_VERSION%
echo   - PyTorch: GPU Support = !HAS_GPU!
echo.
echo Log file: %LOG_FILE%
echo.
echo Next steps:
echo   1. Configure your settings in ai-service\config.py
echo   2. Start OpenKore with your desired interface
echo   3. The AI service will start automatically
echo.

pause
exit /b 0
