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
echo Please enter your DeepSeek API key (or press Enter to skip):
echo (Get your key from: https://platform.deepseek.com/)
set /p "API_KEY=DeepSeek API Key: "

if not "!API_KEY!"=="" (
    echo [INFO] Configuring API key...
    echo [INFO] Configuring API key... >> "%LOG_FILE%"
    
    :: Create ai-service directory if it doesn't exist
    if not exist "%SCRIPT_DIR%\ai-service" mkdir "%SCRIPT_DIR%\ai-service"
    
    :: Save API key to .env file
    echo DEEPSEEK_API_KEY=!API_KEY!> "%SCRIPT_DIR%\ai-service\.env"
    if !errorlevel! equ 0 (
        echo [SUCCESS] API key configured in ai-service\.env
        echo [SUCCESS] API key configured in ai-service\.env >> "%LOG_FILE%"
    ) else (
        echo [WARNING] Failed to create .env file
        echo [WARNING] Failed to create .env file >> "%LOG_FILE%"
    )
)

:: ============================================================================
:: USER INTENT WIZARD - Character Build Configuration
:: ============================================================================

echo.
echo ========================================================================
echo   Character Build Configuration Wizard
echo ========================================================================
echo.
echo This wizard will configure your autonomous bot for optimal performance.
echo Your choices will enable 95%% autonomy with automatic stat allocation,
echo skill learning, and equipment management.
echo.
pause

:: JOB PATH SELECTION
:job_selection
cls
echo.
echo ========================================================================
echo   Step 1: Select Your Job Path
echo ========================================================================
echo.
echo Which job path do you want to follow?
echo.
echo   1. Swordsman ^> Knight ^> Lord Knight (Tank/Melee DPS)
echo   2. Mage ^> Wizard ^> High Wizard (Magic DPS)
echo   3. Archer ^> Hunter ^> Sniper (Ranged Physical DPS)
echo   4. Acolyte ^> Priest ^> High Priest (Support/Healer)
echo   5. Thief ^> Assassin ^> Assassin Cross (Burst DPS)
echo   6. Merchant ^> Blacksmith ^> Whitesmith (Tank/Utility)
echo.
set /p "JOB_CHOICE=Enter your choice (1-6): "

if "%JOB_CHOICE%"=="1" (
    set "JOB_PATH=Swordsman"
    set "JOB_PATH_FULL=Novice,Swordsman,Knight,Lord Knight"
    goto build_selection_swordsman
)
if "%JOB_CHOICE%"=="2" (
    set "JOB_PATH=Mage"
    set "JOB_PATH_FULL=Novice,Mage,Wizard,High Wizard"
    goto build_selection_mage
)
if "%JOB_CHOICE%"=="3" (
    set "JOB_PATH=Archer"
    set "JOB_PATH_FULL=Novice,Archer,Hunter,Sniper"
    goto build_selection_archer
)
if "%JOB_CHOICE%"=="4" (
    set "JOB_PATH=Acolyte"
    set "JOB_PATH_FULL=Novice,Acolyte,Priest,High Priest"
    goto build_selection_acolyte
)
if "%JOB_CHOICE%"=="5" (
    set "JOB_PATH=Thief"
    set "JOB_PATH_FULL=Novice,Thief,Assassin,Assassin Cross"
    goto build_selection_thief
)
if "%JOB_CHOICE%"=="6" (
    set "JOB_PATH=Merchant"
    set "JOB_PATH_FULL=Novice,Merchant,Blacksmith,Whitesmith"
    goto build_selection_merchant
)
echo [ERROR] Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto job_selection

:: BUILD SELECTION - SWORDSMAN
:build_selection_swordsman
cls
echo.
echo ========================================================================
echo   Step 2: Select Your Swordsman Build
echo ========================================================================
echo.
echo   1. AGI Knight (High ASPD, Dodge) - Fast attacks, evasion tank
echo   2. VIT Knight (Tank) - Maximum HP and defense, pure tanking
echo   3. STR Knight (Pure DPS) - Maximum damage output, glass cannon
echo.
set /p "BUILD_CHOICE=Enter your choice (1-3): "

if "%BUILD_CHOICE%"=="1" (
    set "BUILD_TYPE=agi_knight"
    set "BUILD_NAME=AGI Knight"
    set "STAT_PRIORITY=AGI,STR,VIT,DEX"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="2" (
    set "BUILD_TYPE=vit_knight"
    set "BUILD_NAME=VIT Knight"
    set "STAT_PRIORITY=VIT,STR,DEX,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="3" (
    set "BUILD_TYPE=str_knight"
    set "BUILD_NAME=STR Knight"
    set "STAT_PRIORITY=STR,DEX,AGI,VIT"
    goto playstyle_selection
)
echo [ERROR] Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto build_selection_swordsman

:: BUILD SELECTION - MAGE
:build_selection_mage
cls
echo.
echo ========================================================================
echo   Step 2: Select Your Mage Build
echo ========================================================================
echo.
echo   1. Magic DPS (High Wizard) - Pure magic damage, glass cannon
echo.
set /p "BUILD_CHOICE=Enter your choice (1): "

if "%BUILD_CHOICE%"=="1" (
    set "BUILD_TYPE=magic_dps"
    set "BUILD_NAME=High Wizard"
    set "STAT_PRIORITY=INT,DEX,VIT,AGI"
    goto playstyle_selection
)
echo [ERROR] Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto build_selection_mage

:: BUILD SELECTION - ARCHER
:build_selection_archer
cls
echo.
echo ========================================================================
echo   Step 2: Select Your Archer Build
echo ========================================================================
echo.
echo   1. DEX Hunter (Sniper) - High damage ranged physical DPS
echo.
set /p "BUILD_CHOICE=Enter your choice (1): "

if "%BUILD_CHOICE%"=="1" (
    set "BUILD_TYPE=dex_hunter"
    set "BUILD_NAME=Sniper"
    set "STAT_PRIORITY=DEX,AGI,STR,VIT"
    goto playstyle_selection
)
echo [ERROR] Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto build_selection_archer

:: BUILD SELECTION - ACOLYTE
:build_selection_acolyte
cls
echo.
echo ========================================================================
echo   Step 2: Select Your Acolyte Build
echo ========================================================================
echo.
echo   1. Support Priest (High Priest) - Party support and healing
echo.
set /p "BUILD_CHOICE=Enter your choice (1): "

if "%BUILD_CHOICE%"=="1" (
    set "BUILD_TYPE=support_priest"
    set "BUILD_NAME=High Priest"
    set "STAT_PRIORITY=INT,VIT,DEX,AGI"
    goto playstyle_selection
)
echo [ERROR] Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto build_selection_acolyte

:: BUILD SELECTION - THIEF
:build_selection_thief
cls
echo.
echo ========================================================================
echo   Step 2: Select Your Thief Build
echo ========================================================================
echo.
echo   1. Critical Assassin (Assassin Cross) - Crit specialist, burst DPS
echo.
set /p "BUILD_CHOICE=Enter your choice (1): "

if "%BUILD_CHOICE%"=="1" (
    set "BUILD_TYPE=crit_assassin"
    set "BUILD_NAME=Assassin Cross"
    set "STAT_PRIORITY=LUK,AGI,STR,DEX"
    goto playstyle_selection
)
echo [ERROR] Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto build_selection_thief

:: BUILD SELECTION - MERCHANT
:build_selection_merchant
cls
echo.
echo ========================================================================
echo   Step 2: Select Your Merchant Build
echo ========================================================================
echo.
echo   1. Tank Blacksmith (Whitesmith) - High HP, utility support
echo.
set /p "BUILD_CHOICE=Enter your choice (1): "

if "%BUILD_CHOICE%"=="1" (
    set "BUILD_TYPE=tank_blacksmith"
    set "BUILD_NAME=Whitesmith"
    set "STAT_PRIORITY=VIT,STR,DEX,AGI"
    goto playstyle_selection
)
echo [ERROR] Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto build_selection_merchant

:: PLAYSTYLE SELECTION
:playstyle_selection
cls
echo.
echo ========================================================================
echo   Step 3: Select Your Playstyle
echo ========================================================================
echo.
echo   1. Aggressive (Kill fast, risk death) - High damage, low defense
echo   2. Balanced (Medium risk, medium reward) - Recommended for most
echo   3. Safe (Never die, slower leveling) - Maximum survival focus
echo   4. Efficient (Optimal XP/hour) - Calculated risk management
echo.
set /p "PLAYSTYLE_CHOICE=Enter your choice (1-4): "

if "%PLAYSTYLE_CHOICE%"=="1" (
    set "PLAYSTYLE=aggressive"
    set "PLAYSTYLE_NAME=Aggressive"
    set "HP_THRESHOLD=20"
    set "HEAL_THRESHOLD=40"
    goto save_user_intent
)
if "%PLAYSTYLE_CHOICE%"=="2" (
    set "PLAYSTYLE=balanced"
    set "PLAYSTYLE_NAME=Balanced"
    set "HP_THRESHOLD=35"
    set "HEAL_THRESHOLD=50"
    goto save_user_intent
)
if "%PLAYSTYLE_CHOICE%"=="3" (
    set "PLAYSTYLE=safe"
    set "PLAYSTYLE_NAME=Safe"
    set "HP_THRESHOLD=50"
    set "HEAL_THRESHOLD=70"
    goto save_user_intent
)
if "%PLAYSTYLE_CHOICE%"=="4" (
    set "PLAYSTYLE=efficient"
    set "PLAYSTYLE_NAME=Efficient"
    set "HP_THRESHOLD=40"
    set "HEAL_THRESHOLD=60"
    goto save_user_intent
)
echo [ERROR] Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto playstyle_selection

:: SAVE USER INTENT
:save_user_intent
cls
echo.
echo ========================================================================
echo   Configuration Summary
echo ========================================================================
echo.
echo Job Path: %JOB_PATH_FULL%
echo Build: %BUILD_NAME%
echo Playstyle: %PLAYSTYLE_NAME%
echo.
echo [INFO] Saving configuration...
echo [INFO] Saving configuration... >> "%LOG_FILE%"

:: Create ai-service\data directory if it doesn't exist
if not exist "%SCRIPT_DIR%\ai-service\data" mkdir "%SCRIPT_DIR%\ai-service\data"

:: Generate user_intent.json using PowerShell
powershell -NoProfile -Command ^
    "$json = @{" ^
    "    job_path = @('%JOB_PATH_FULL%'.Split(','));" ^
    "    current_job = 'novice';" ^
    "    build = '%BUILD_TYPE%';" ^
    "    build_name = '%BUILD_NAME%';" ^
    "    stat_priority = '%STAT_PRIORITY%';" ^
    "    playstyle = '%PLAYSTYLE%';" ^
    "    playstyle_config = @{" ^
    "        teleport_hp_threshold = [decimal]0.%HP_THRESHOLD%;" ^
    "        heal_threshold = [decimal]0.%HEAL_THRESHOLD%;" ^
    "        aggressive_range = 5;" ^
    "        risk_tolerance = '%PLAYSTYLE%'" ^
    "    };" ^
    "    autonomy_level = 95;" ^
    "    features_enabled = @{" ^
    "        auto_stat_allocation = $true;" ^
    "        auto_skill_learning = $true;" ^
    "        adaptive_equipment = $true;" ^
    "        autonomous_healing = $true" ^
    "    }" ^
    "};" ^
    "$json | ConvertTo-Json -Depth 10 | Out-File -FilePath '%SCRIPT_DIR%\ai-service\data\user_intent.json' -Encoding UTF8"

if !errorlevel! equ 0 (
    echo [SUCCESS] Configuration saved to ai-service\data\user_intent.json
    echo [SUCCESS] Configuration saved >> "%LOG_FILE%"
) else (
    echo [WARNING] Failed to save configuration
    echo [WARNING] Failed to save configuration >> "%LOG_FILE%"
)

echo.
echo [SUCCESS] Character configuration saved!
echo.

:: ============================================================================
:: STEP 6: AUTO-CONFIGURE OPENKORE BOT
:: ============================================================================

echo.
echo ========================================================================
echo   STEP 6: Auto-Configuring OpenKore Bot
echo ========================================================================
echo.

echo [INFO] Applying configuration to OpenKore config.txt...
echo [INFO] Applying configuration to OpenKore config.txt... >> "%LOG_FILE%"

REM Set absolute paths to avoid context issues
set "OPENKORE_ROOT=%SCRIPT_DIR%"
set "AI_SERVICE_ROOT=%OPENKORE_ROOT%\ai-service"
set "TOOLS_PATH=%AI_SERVICE_ROOT%\tools"
set "CONFIG_PATH=%OPENKORE_ROOT%\control\config.txt"
set "INTENT_PATH=%AI_SERVICE_ROOT%\data\user_intent.json"

REM Activate venv and run auto-configure from correct directory
cd /d "%AI_SERVICE_ROOT%"
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    python "%TOOLS_PATH%\auto_configure.py" "%CONFIG_PATH%" "%INTENT_PATH%"
    set AUTO_CONFIG_RESULT=!errorlevel!
    deactivate
) else (
    "%PYTHON_CMD%" "%TOOLS_PATH%\auto_configure.py" "%CONFIG_PATH%" "%INTENT_PATH%"
    set AUTO_CONFIG_RESULT=!errorlevel!
)

cd /d "%OPENKORE_ROOT%"

if !AUTO_CONFIG_RESULT! neq 0 (
    echo [WARNING] Auto-configuration encountered issues
    echo [WARNING] Auto-configuration encountered issues >> "%LOG_FILE%"
    echo [WARNING] You may need to configure config.txt manually
    echo.
) else (
    echo [SUCCESS] Config.txt auto-configured successfully!
    echo [SUCCESS] Config.txt auto-configured successfully! >> "%LOG_FILE%"
)

:: ============================================================================
:: AUTONOMOUS ITEM PURCHASING CONFIGURED
:: ============================================================================

echo.
echo ========================================================================
echo   ✅ Autonomous Item Purchasing Enabled
echo ========================================================================
echo.
echo   Your bot is configured for FULL AUTONOMY:
echo.
echo   🤖 AUTOMATIC ITEM PURCHASING:
echo   • Bot will auto-buy Red Potions (healing)
echo   • Bot will auto-buy Fly Wings (emergency teleport)
echo   • No manual item purchasing needed!
echo.
echo   💰 Initial Zeny Requirement:
echo   • Your character needs ~20,000 zeny to start buying items
echo   • If you have less: Bot will farm first, then buy items automatically
echo   • If you have more: Bot starts buying items immediately
echo.
echo   📍 NPC Location: Prontera Tool Shop (152, 29)
echo   • Bot knows where to go automatically
echo   • Bot will walk there when items run low
echo.
echo   ✅ 95%% AUTONOMOUS OPERATION:
echo   1. Farm monsters for zeny and exp
echo   2. Auto-buy healing items when low
echo   3. Auto-heal when HP drops
echo   4. Emergency teleport when in danger
echo   5. Return to farming automatically
echo.
echo ========================================================================
echo.

:: ============================================================================
:: COMPLETE
:: ============================================================================

echo.
echo ========================================================================
echo   ✅ Installation Complete!
echo ========================================================================
echo.
echo [SUCCESS] Installation completed successfully
echo [SUCCESS] Installation completed successfully >> "%LOG_FILE%"
echo.
echo Installed components:
echo   - Python: %PYTHON_VERSION%
echo   - Perl: %PERL_VERSION%
echo   - PyTorch: GPU Support = !HAS_GPU!
echo   - Character Build: %BUILD_NAME% (%PLAYSTYLE_NAME%)
echo   - Bot Configuration: Auto-applied to config.txt
echo.
echo Log file: %LOG_FILE%
echo.
echo ========================================================================
echo   ⚡ NEXT STEPS (IN ORDER):
echo ========================================================================
echo.
echo   1. ✅ API Key: Configured automatically during installation
echo      • If you skipped API key entry, you can add it manually to ai-service\.env
echo      • Format: DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxx
echo.
echo   2. 💰 Optional - Give Character Zeny:
echo      • If your character has ^<20k zeny, consider giving some zeny
echo      • Bot can farm first, but 20k+ zeny allows immediate item buying
echo      • Bot will AUTO-BUY items - no manual purchasing needed!
echo.
echo   3. 🚀 Start the system:
echo      • Run: start.bat
echo      • AI Engine will start first (port 9901)
echo      • AI Service will start second (port 9902)
echo      • OpenKore will start last
echo.
echo ========================================================================
echo   ✅ FULL AUTONOMY ACHIEVED - Let the bot do its job!
echo ========================================================================
echo.

pause
exit /b 0
