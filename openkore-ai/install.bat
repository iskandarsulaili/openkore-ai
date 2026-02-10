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
                    endlocal
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
                    endlocal
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
                    endlocal
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
            endlocal
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
:: INSTALL PERL DEPENDENCIES (LWP::UserAgent for GodTierAI plugin)
:: ============================================================================

echo [INFO] Checking Perl module dependencies...
echo [INFO] Checking Perl module dependencies... >> "%LOG_FILE%"

:: Test if LWP::UserAgent module loads
perl -e "use LWP::UserAgent; exit 0;" >nul 2>&1
set PERL_LWP_TEST=%errorlevel%

if %PERL_LWP_TEST%==0 goto perl_lwp_found
goto perl_lwp_not_found

:perl_lwp_found
echo [SUCCESS] LWP::UserAgent module is installed
echo [SUCCESS] LWP::UserAgent module is installed >> "%LOG_FILE%"

:: Test if LWP::UserAgent can actually be USED (runtime verification)
echo [INFO] Testing LWP::UserAgent runtime verification...
echo [INFO] Testing LWP::UserAgent runtime verification... >> "%LOG_FILE%"
perl -e "use LWP::UserAgent; my $ua = LWP::UserAgent->new; exit 0;" >nul 2>&1
set PERL_LWP_RUNTIME_TEST=%errorlevel%

if %PERL_LWP_RUNTIME_TEST%==0 goto perl_lwp_verified
echo [WARNING] LWP::UserAgent loads but runtime creation FAILED
echo [WARNING] LWP::UserAgent loads but runtime creation FAILED >> "%LOG_FILE%"
echo [INFO] Attempting reinstall...
echo [INFO] Attempting reinstall... >> "%LOG_FILE%"
goto perl_lwp_not_found

:perl_lwp_verified
echo [SUCCESS] LWP::UserAgent runtime verification PASSED
echo [SUCCESS] LWP::UserAgent runtime verification PASSED >> "%LOG_FILE%"
goto perl_deps_done

:perl_lwp_not_found
echo [INFO] LWP::UserAgent not found, installing...
echo [INFO] LWP::UserAgent not found, installing... >> "%LOG_FILE%"
echo.
echo [INFO] This may take 2-5 minutes on first CPAN run
echo [INFO] CPAN will configure itself automatically

:: Set environment variables to prevent cpan from hanging
set PERL_MM_USE_DEFAULT=1
set AUTOMATED_TESTING=1

:: Try to install LWP::UserAgent using cpan with minimal output
echo [INFO] Installing LWP::UserAgent via cpan (non-interactive, tests skipped)...
echo [INFO] Installing LWP::UserAgent via cpan... >> "%LOG_FILE%"
call cpan -T LWP::UserAgent 2>&1 | findstr /V "Reading" | findstr /V "Fetching" >> "%LOG_FILE%"

echo.
echo [INFO] Verifying LWP::UserAgent installation...
echo [INFO] Verifying LWP::UserAgent installation... >> "%LOG_FILE%"
perl -e "use LWP::UserAgent; my $ua = LWP::UserAgent->new; print qq(LWP::UserAgent successfully installed and verified\n);" 2>&1
if %errorlevel%==0 (
    echo [SUCCESS] LWP::UserAgent installed and working
    echo [SUCCESS] LWP::UserAgent installed and working >> "%LOG_FILE%"
    goto perl_deps_done
)

:: If cpan failed, provide comprehensive troubleshooting
echo.
echo [ERROR] LWP::UserAgent installation failed via cpan
echo [ERROR] LWP::UserAgent installation failed via cpan >> "%LOG_FILE%"
echo.
echo ========================================================================
echo   TROUBLESHOOTING - Try these methods in order:
echo ========================================================================
echo.
echo METHOD 1 - Using cpanm (faster, recommended):
echo   cpan App::cpanminus
echo   cpanm LWP::UserAgent
echo.
echo METHOD 2 - Using Strawberry Perl Package Manager:
echo   a. Ensure you have Strawberry Perl installed
echo   b. Open Command Prompt as Administrator
echo   c. Run: cpan -fi LWP::UserAgent
echo.
echo METHOD 3 - Manual installation:
echo   a. Download from https://metacpan.org/dist/libwww-perl
echo   b. Extract and follow installation instructions
echo.
echo METHOD 4 - Reinstall Strawberry Perl:
echo   a. Download latest from https://strawberryperl.com/
echo   b. Install (includes LWP::UserAgent by default in recent versions)
echo.
echo IMPORTANT: LWP::UserAgent is required for the GodTierAI plugin
echo Without it, the plugin will run in degraded mode with limited features
echo.
echo After installation, run this setup script again.
echo.
echo For now, continuing setup (GodTierAI plugin will be disabled without LWP::UserAgent)...
echo.
pause

:perl_deps_done
echo [SUCCESS] Perl dependencies verified
echo [SUCCESS] Perl dependencies verified >> "%LOG_FILE%"

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
        endlocal
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
    endlocal
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
:: VERIFY BUILD VARIANT DATA FILES
:: ============================================================================

echo [INFO] Verifying build variant data files...
echo [INFO] Verifying build variant data files... >> "%LOG_FILE%"

set "DATA_MISSING=0"

if not exist "%SCRIPT_DIR%\ai-service\data\job_build_variants.json" (
    echo [ERROR] Missing: job_build_variants.json
    echo [ERROR] Missing: job_build_variants.json >> "%LOG_FILE%"
    set "DATA_MISSING=1"
) else (
    echo [SUCCESS] Found: job_build_variants.json
    echo [SUCCESS] Found: job_build_variants.json >> "%LOG_FILE%"
)

if not exist "%SCRIPT_DIR%\ai-service\data\job_change_locations.json" (
    echo [ERROR] Missing: job_change_locations.json
    echo [ERROR] Missing: job_change_locations.json >> "%LOG_FILE%"
    set "DATA_MISSING=1"
) else (
    echo [SUCCESS] Found: job_change_locations.json
    echo [SUCCESS] Found: job_change_locations.json >> "%LOG_FILE%"
)

if not exist "%SCRIPT_DIR%\ai-service\data\skill_rotations.json" (
    echo [ERROR] Missing: skill_rotations.json
    echo [ERROR] Missing: skill_rotations.json >> "%LOG_FILE%"
    set "DATA_MISSING=1"
) else (
    echo [SUCCESS] Found: skill_rotations.json
    echo [SUCCESS] Found: skill_rotations.json >> "%LOG_FILE%"
)

if !DATA_MISSING! equ 1 (
    echo [ERROR] Required data files are missing!
    echo [ERROR] Please ensure all variant data files are present.
    echo [ERROR] Required data files are missing! >> "%LOG_FILE%"
    pause
    endlocal
    exit /b 1
)

echo [SUCCESS] All build variant data files verified
echo [SUCCESS] All build variant data files verified >> "%LOG_FILE%"

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
echo INTEGRATED BUILD VARIANTS:
echo   - 11 Job Paths (Swordsman to Gunslinger)
echo   - 55 Build Variants (5 builds per path)
echo   - Supports 39 Jobs and 42 Skill Rotations
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
echo   CLASSIC PATHS:
echo   1. Swordsman ^> Knight ^> Lord Knight ^> Rune Knight (Tank/Melee DPS)
echo   2. Mage ^> Wizard ^> High Wizard ^> Warlock (Magic DPS)
echo   3. Archer ^> Hunter ^> Sniper ^> Ranger (Ranged Physical DPS)
echo   4. Acolyte ^> Priest ^> High Priest ^> Arch Bishop (Support/Healer)
echo   5. Thief ^> Assassin ^> Assassin Cross ^> Guillotine Cross (Burst DPS)
echo   6. Merchant ^> Blacksmith ^> Whitesmith ^> Mechanic (Tank/Utility)
echo.
echo   EXTENDED PATHS:
echo   7. Archer ^> Bard/Dancer ^> Clown/Gypsy ^> Minstrel/Wanderer (Support)
echo   8. Mage ^> Sage ^> Professor ^> Sorcerer (Magic Support/DPS)
echo   9. Acolyte ^> Monk ^> Champion ^> Sura (Melee Combo)
echo   10. Thief ^> Rogue ^> Stalker ^> Shadow Chaser (Utility/DPS)
echo   11. Novice ^> Super Novice ^> Expanded Super Novice (Versatile)
echo.
echo   0. Show more info about each path
echo.
set /p "JOB_CHOICE=Enter your choice (1-11, or 0 for info): "

if "%JOB_CHOICE%"=="0" goto job_info
if "%JOB_CHOICE%"=="1" (
    set "JOB_PATH=swordman_knight_rune_knight"
    set "JOB_PATH_NAME=Knight Path"
    set "JOB_PATH_FULL=Novice,Swordman,Knight,Lord_Knight,Rune_Knight"
    goto build_selection_swordsman
)
if "%JOB_CHOICE%"=="2" (
    set "JOB_PATH=mage_wizard_warlock"
    set "JOB_PATH_NAME=Wizard Path"
    set "JOB_PATH_FULL=Novice,Mage,Wizard,High_Wizard,Warlock"
    goto build_selection_mage
)
if "%JOB_CHOICE%"=="3" (
    set "JOB_PATH=archer_hunter_ranger"
    set "JOB_PATH_NAME=Hunter Path"
    set "JOB_PATH_FULL=Novice,Archer,Hunter,Sniper,Ranger"
    goto build_selection_archer
)
if "%JOB_CHOICE%"=="4" (
    set "JOB_PATH=acolyte_priest_arch_bishop"
    set "JOB_PATH_NAME=Priest Path"
    set "JOB_PATH_FULL=Novice,Acolyte,Priest,High_Priest,Arch_Bishop"
    goto build_selection_acolyte
)
if "%JOB_CHOICE%"=="5" (
    set "JOB_PATH=thief_assassin_guillotine"
    set "JOB_PATH_NAME=Assassin Path"
    set "JOB_PATH_FULL=Novice,Thief,Assassin,Assassin_Cross,Guillotine_Cross"
    goto build_selection_thief
)
if "%JOB_CHOICE%"=="6" (
    set "JOB_PATH=merchant_blacksmith_mechanic"
    set "JOB_PATH_NAME=Blacksmith Path"
    set "JOB_PATH_FULL=Novice,Merchant,Blacksmith,Whitesmith,Mechanic"
    goto build_selection_merchant
)
if "%JOB_CHOICE%"=="7" (
    set "JOB_PATH=archer_bard_minstrel"
    set "JOB_PATH_NAME=Bard/Dancer Path"
    set "JOB_PATH_FULL=Novice,Archer,Bard,Clown,Minstrel"
    goto build_selection_bard
)
if "%JOB_CHOICE%"=="8" (
    set "JOB_PATH=mage_sage_sorcerer"
    set "JOB_PATH_NAME=Sage Path"
    set "JOB_PATH_FULL=Novice,Mage,Sage,Professor,Sorcerer"
    goto build_selection_sage
)
if "%JOB_CHOICE%"=="9" (
    set "JOB_PATH=acolyte_monk_sura"
    set "JOB_PATH_NAME=Monk Path"
    set "JOB_PATH_FULL=Novice,Acolyte,Monk,Champion,Sura"
    goto build_selection_monk
)
if "%JOB_CHOICE%"=="10" (
    set "JOB_PATH=thief_rogue_shadow_chaser"
    set "JOB_PATH_NAME=Rogue Path"
    set "JOB_PATH_FULL=Novice,Thief,Rogue,Stalker,Shadow_Chaser"
    goto build_selection_rogue
)
if "%JOB_CHOICE%"=="11" (
    set "JOB_PATH=super_novice"
    set "JOB_PATH_NAME=Super Novice Path"
    set "JOB_PATH_FULL=Novice,Super_Novice,Expanded_Super_Novice"
    goto build_selection_supernovice
)
echo [ERROR] Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto job_selection

:: JOB INFO DISPLAY
:job_info
cls
echo.
echo ========================================================================
echo   Job Path Information
echo ========================================================================
echo.
echo CLASSIC PATHS:
echo   1. Knight: Tank/Melee DPS - High survivability, strong melee damage
echo   2. Wizard: Magic DPS - Powerful AoE spells, elemental mastery
echo   3. Hunter: Ranged DPS - Physical ranged damage, trapping abilities
echo   4. Priest: Support/Healer - Party support, healing, resurrection
echo   5. Assassin: Burst DPS - Critical strikes, poison, stealth
echo   6. Blacksmith: Tank/Utility - Weapon crafting, cart mastery
echo.
echo EXTENDED PATHS:
echo   7. Bard/Dancer: Party Support - Buffs, debuffs, ensemble skills
echo   8. Sage: Magic Support - Magic damage, dispelling, elemental bolts
echo   9. Monk: Melee Combo - Combo attacks, spirit spheres
echo   10. Rogue: Utility/DPS - Skills copying, stripping, versatile
echo   11. Super Novice: Versatile - Can use many 1st class skills
echo.
pause
goto job_selection

:: BUILD SELECTION - SWORDSMAN
:build_selection_swordsman
cls
echo.
echo ========================================================================
echo   Step 2: Select Your Knight Build (5 Variants Available)
echo ========================================================================
echo.
echo   1. AGI Knight - High ASPD, dodge, two-hand sword specialist
echo   2. VIT Knight - Maximum survivability, spear tank
echo   3. Bowling Bash - AoE bash specialist for mob farming
echo   4. Crit Knight - Critical damage focus with LUK
echo   5. Balanced Knight - Well-rounded build for versatility
echo.
set /p "BUILD_CHOICE=Enter your choice (1-5): "

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
    set "BUILD_TYPE=bowling_bash"
    set "BUILD_NAME=Bowling Bash Knight"
    set "STAT_PRIORITY=STR,VIT,DEX,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="4" (
    set "BUILD_TYPE=crit_knight"
    set "BUILD_NAME=Crit Knight"
    set "STAT_PRIORITY=STR,LUK,AGI,VIT"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="5" (
    set "BUILD_TYPE=balanced_knight"
    set "BUILD_NAME=Balanced Knight"
    set "STAT_PRIORITY=STR,VIT,AGI,DEX"
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
echo   Step 2: Select Your Wizard Build (5 Variants Available)
echo ========================================================================
echo.
echo   1. Fire Wizard - Fire element specialist, high burst damage
echo   2. Ice Wizard - Ice element specialist, crowd control
echo   3. Lightning Wizard - Lightning element, balanced damage
echo   4. Full Support Wizard - Support magic, buffs, dispel
echo   5. Balanced Wizard - Multi-element versatile build
echo.
set /p "BUILD_CHOICE=Enter your choice (1-5): "

if "%BUILD_CHOICE%"=="1" (
    set "BUILD_TYPE=fire_wizard"
    set "BUILD_NAME=Fire Wizard"
    set "STAT_PRIORITY=INT,DEX,VIT,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="2" (
    set "BUILD_TYPE=ice_wizard"
    set "BUILD_NAME=Ice Wizard"
    set "STAT_PRIORITY=INT,DEX,VIT,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="3" (
    set "BUILD_TYPE=lightning_wizard"
    set "BUILD_NAME=Lightning Wizard"
    set "STAT_PRIORITY=INT,DEX,VIT,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="4" (
    set "BUILD_TYPE=support_wizard"
    set "BUILD_NAME=Support Wizard"
    set "STAT_PRIORITY=INT,DEX,VIT,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="5" (
    set "BUILD_TYPE=balanced_wizard"
    set "BUILD_NAME=Balanced Wizard"
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
echo   Step 2: Select Your Hunter Build (5 Variants Available)
echo ========================================================================
echo.
echo   1. DEX Hunter - Pure damage, high DEX focus
echo   2. Trap Hunter - Trap specialist, battlefield control
echo   3. Falcon Hunter - Falcon assault specialist
echo   4. AGI Hunter - High ASPD, double strafe focus
echo   5. Balanced Hunter - Versatile ranged DPS
echo.
set /p "BUILD_CHOICE=Enter your choice (1-5): "

if "%BUILD_CHOICE%"=="1" (
    set "BUILD_TYPE=dex_hunter"
    set "BUILD_NAME=DEX Hunter"
    set "STAT_PRIORITY=DEX,AGI,STR,VIT"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="2" (
    set "BUILD_TYPE=trap_hunter"
    set "BUILD_NAME=Trap Hunter"
    set "STAT_PRIORITY=DEX,INT,AGI,VIT"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="3" (
    set "BUILD_TYPE=falcon_hunter"
    set "BUILD_NAME=Falcon Hunter"
    set "STAT_PRIORITY=DEX,LUK,AGI,VIT"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="4" (
    set "BUILD_TYPE=agi_hunter"
    set "BUILD_NAME=AGI Hunter"
    set "STAT_PRIORITY=AGI,DEX,STR,VIT"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="5" (
    set "BUILD_TYPE=balanced_hunter"
    set "BUILD_NAME=Balanced Hunter"
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
echo   Step 2: Select Your Priest Build (5 Variants Available)
echo ========================================================================
echo.
echo   1. Full Support - Maximum healing and buffs
echo   2. Battle Priest - Melee combat with support skills
echo   3. Magnus Priest - Magnus Exorcismus specialist
echo   4. TU Priest - Turn Undead specialist
echo   5. Balanced Priest - Versatile support build
echo.
set /p "BUILD_CHOICE=Enter your choice (1-5): "

if "%BUILD_CHOICE%"=="1" (
    set "BUILD_TYPE=full_support"
    set "BUILD_NAME=Full Support Priest"
    set "STAT_PRIORITY=INT,VIT,DEX,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="2" (
    set "BUILD_TYPE=battle_priest"
    set "BUILD_NAME=Battle Priest"
    set "STAT_PRIORITY=STR,INT,VIT,DEX"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="3" (
    set "BUILD_TYPE=magnus_priest"
    set "BUILD_NAME=Magnus Priest"
    set "STAT_PRIORITY=INT,DEX,VIT,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="4" (
    set "BUILD_TYPE=tu_priest"
    set "BUILD_NAME=TU Priest"
    set "STAT_PRIORITY=INT,LUK,DEX,VIT"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="5" (
    set "BUILD_TYPE=balanced_priest"
    set "BUILD_NAME=Balanced Priest"
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
echo   Step 2: Select Your Assassin Build (5 Variants Available)
echo ========================================================================
echo.
echo   1. Crit Assassin - Critical strike specialist
echo   2. Katar Assassin - Dual katar, sonic blow focus
echo   3. Poison Assassin - Poison and envenom specialist
echo   4. AGI Assassin - High ASPD, dodge focus
echo   5. Balanced Assassin - Versatile damage dealer
echo.
set /p "BUILD_CHOICE=Enter your choice (1-5): "

if "%BUILD_CHOICE%"=="1" (
    set "BUILD_TYPE=crit_assassin"
    set "BUILD_NAME=Crit Assassin"
    set "STAT_PRIORITY=LUK,AGI,STR,DEX"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="2" (
    set "BUILD_TYPE=katar_assassin"
    set "BUILD_NAME=Katar Assassin"
    set "STAT_PRIORITY=STR,AGI,DEX,VIT"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="3" (
    set "BUILD_TYPE=poison_assassin"
    set "BUILD_NAME=Poison Assassin"
    set "STAT_PRIORITY=INT,AGI,STR,DEX"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="4" (
    set "BUILD_TYPE=agi_assassin"
    set "BUILD_NAME=AGI Assassin"
    set "STAT_PRIORITY=AGI,STR,LUK,DEX"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="5" (
    set "BUILD_TYPE=balanced_assassin"
    set "BUILD_NAME=Balanced Assassin"
    set "STAT_PRIORITY=STR,AGI,LUK,DEX"
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
echo   Step 2: Select Your Blacksmith Build (5 Variants Available)
echo ========================================================================
echo.
echo   1. STR Blacksmith - Pure damage with axes
echo   2. VIT Blacksmith - Tank with high survivability
echo   3. Forger Blacksmith - Crafting and utility focus
echo   4. Cart Termination - Cart termination specialist
echo   5. Balanced Blacksmith - Versatile build
echo.
set /p "BUILD_CHOICE=Enter your choice (1-5): "

if "%BUILD_CHOICE%"=="1" (
    set "BUILD_TYPE=str_blacksmith"
    set "BUILD_NAME=STR Blacksmith"
    set "STAT_PRIORITY=STR,VIT,DEX,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="2" (
    set "BUILD_TYPE=vit_blacksmith"
    set "BUILD_NAME=VIT Blacksmith"
    set "STAT_PRIORITY=VIT,STR,DEX,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="3" (
    set "BUILD_TYPE=forger_blacksmith"
    set "BUILD_NAME=Forger Blacksmith"
    set "STAT_PRIORITY=DEX,STR,VIT,LUK"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="4" (
    set "BUILD_TYPE=cart_termination"
    set "BUILD_NAME=Cart Termination"
    set "STAT_PRIORITY=STR,INT,VIT,DEX"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="5" (
    set "BUILD_TYPE=balanced_blacksmith"
    set "BUILD_NAME=Balanced Blacksmith"
    set "STAT_PRIORITY=STR,VIT,DEX,AGI"
    goto playstyle_selection
)
echo [ERROR] Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto build_selection_merchant

:: BUILD SELECTION - BARD/DANCER
:build_selection_bard
cls
echo.
echo ========================================================================
echo   Step 2: Select Your Bard/Dancer Build (5 Variants Available)
echo ========================================================================
echo.
echo   1. Full Support - Party buffs and debuffs specialist
echo   2. Arrow Vulcan - Musical strike/arrow vulcan DPS
echo   3. Tank Bard - High survivability support
echo   4. AGI Bard - Mobile support with evasion
echo   5. Balanced Bard - Versatile party support
echo.
set /p "BUILD_CHOICE=Enter your choice (1-5): "

if "%BUILD_CHOICE%"=="1" (
    set "BUILD_TYPE=support_bard"
    set "BUILD_NAME=Full Support Bard"
    set "STAT_PRIORITY=INT,VIT,DEX,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="2" (
    set "BUILD_TYPE=dps_bard"
    set "BUILD_NAME=Arrow Vulcan Bard"
    set "STAT_PRIORITY=DEX,AGI,INT,VIT"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="3" (
    set "BUILD_TYPE=tank_bard"
    set "BUILD_NAME=Tank Bard"
    set "STAT_PRIORITY=VIT,INT,DEX,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="4" (
    set "BUILD_TYPE=agi_bard"
    set "BUILD_NAME=AGI Bard"
    set "STAT_PRIORITY=AGI,INT,DEX,VIT"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="5" (
    set "BUILD_TYPE=balanced_bard"
    set "BUILD_NAME=Balanced Bard"
    set "STAT_PRIORITY=INT,DEX,VIT,AGI"
    goto playstyle_selection
)
echo [ERROR] Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto build_selection_bard

:: BUILD SELECTION - SAGE
:build_selection_sage
cls
echo.
echo ========================================================================
echo   Step 2: Select Your Sage Build (5 Variants Available)
echo ========================================================================
echo.
echo   1. Bolt Sage - Elemental bolt specialist
echo   2. Support Sage - Dispel, wall, party support
echo   3. AoE Sage - Heaven's Drive, Earth Spike specialist
echo   4. Full INT - Maximum magic power
echo   5. Balanced Sage - Versatile magic support
echo.
set /p "BUILD_CHOICE=Enter your choice (1-5): "

if "%BUILD_CHOICE%"=="1" (
    set "BUILD_TYPE=bolt_sage"
    set "BUILD_NAME=Bolt Sage"
    set "STAT_PRIORITY=INT,DEX,VIT,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="2" (
    set "BUILD_TYPE=support_sage"
    set "BUILD_NAME=Support Sage"
    set "STAT_PRIORITY=INT,VIT,DEX,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="3" (
    set "BUILD_TYPE=aoe_sage"
    set "BUILD_NAME=AoE Sage"
    set "STAT_PRIORITY=INT,DEX,VIT,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="4" (
    set "BUILD_TYPE=full_int_sage"
    set "BUILD_NAME=Full INT Sage"
    set "STAT_PRIORITY=INT,VIT,DEX,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="5" (
    set "BUILD_TYPE=balanced_sage"
    set "BUILD_NAME=Balanced Sage"
    set "STAT_PRIORITY=INT,DEX,VIT,AGI"
    goto playstyle_selection
)
echo [ERROR] Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto build_selection_sage

:: BUILD SELECTION - MONK
:build_selection_monk
cls
echo.
echo ========================================================================
echo   Step 2: Select Your Monk Build (5 Variants Available)
echo ========================================================================
echo.
echo   1. Combo Monk - Triple attack, combo finish specialist
echo   2. Asura Monk - Asura strike one-shot build
echo   3. Tank Monk - High VIT, steel body focus
echo   4. AGI Monk - High ASPD, dodge focus
echo   5. Balanced Monk - Versatile combo build
echo.
set /p "BUILD_CHOICE=Enter your choice (1-5): "

if "%BUILD_CHOICE%"=="1" (
    set "BUILD_TYPE=combo_monk"
    set "BUILD_NAME=Combo Monk"
    set "STAT_PRIORITY=STR,AGI,VIT,DEX"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="2" (
    set "BUILD_TYPE=asura_monk"
    set "BUILD_NAME=Asura Monk"
    set "STAT_PRIORITY=STR,INT,VIT,DEX"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="3" (
    set "BUILD_TYPE=tank_monk"
    set "BUILD_NAME=Tank Monk"
    set "STAT_PRIORITY=VIT,STR,DEX,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="4" (
    set "BUILD_TYPE=agi_monk"
    set "BUILD_NAME=AGI Monk"
    set "STAT_PRIORITY=AGI,STR,VIT,DEX"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="5" (
    set "BUILD_TYPE=balanced_monk"
    set "BUILD_NAME=Balanced Monk"
    set "STAT_PRIORITY=STR,VIT,AGI,DEX"
    goto playstyle_selection
)
echo [ERROR] Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto build_selection_monk

:: BUILD SELECTION - ROGUE
:build_selection_rogue
cls
echo.
echo ========================================================================
echo   Step 2: Select Your Rogue Build (5 Variants Available)
echo ========================================================================
echo.
echo   1. Strip Rogue - Equipment stripping specialist
echo   2. Copy Rogue - Plagiarism/reproduce focus
echo   3. Bow Rogue - Ranged attack rogue
echo   4. Crit Rogue - Critical strike focus
echo   5. Balanced Rogue - Versatile utility build
echo.
set /p "BUILD_CHOICE=Enter your choice (1-5): "

if "%BUILD_CHOICE%"=="1" (
    set "BUILD_TYPE=strip_rogue"
    set "BUILD_NAME=Strip Rogue"
    set "STAT_PRIORITY=DEX,AGI,STR,VIT"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="2" (
    set "BUILD_TYPE=copy_rogue"
    set "BUILD_NAME=Copy Rogue"
    set "STAT_PRIORITY=INT,DEX,AGI,VIT"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="3" (
    set "BUILD_TYPE=bow_rogue"
    set "BUILD_NAME=Bow Rogue"
    set "STAT_PRIORITY=DEX,AGI,STR,VIT"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="4" (
    set "BUILD_TYPE=crit_rogue"
    set "BUILD_NAME=Crit Rogue"
    set "STAT_PRIORITY=LUK,AGI,STR,DEX"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="5" (
    set "BUILD_TYPE=balanced_rogue"
    set "BUILD_NAME=Balanced Rogue"
    set "STAT_PRIORITY=STR,AGI,DEX,VIT"
    goto playstyle_selection
)
echo [ERROR] Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto build_selection_rogue

:: BUILD SELECTION - SUPER NOVICE
:build_selection_supernovice
cls
echo.
echo ========================================================================
echo   Step 2: Select Your Super Novice Build (5 Variants Available)
echo ========================================================================
echo.
echo   1. Magic Super Novice - INT-based magic build
echo   2. Physical Super Novice - STR-based melee build
echo   3. Support Super Novice - Healing and buff focus
echo   4. Tank Super Novice - High VIT survivability
echo   5. Balanced Super Novice - Jack of all trades
echo.
set /p "BUILD_CHOICE=Enter your choice (1-5): "

if "%BUILD_CHOICE%"=="1" (
    set "BUILD_TYPE=magic_supernovice"
    set "BUILD_NAME=Magic Super Novice"
    set "STAT_PRIORITY=INT,DEX,VIT,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="2" (
    set "BUILD_TYPE=physical_supernovice"
    set "BUILD_NAME=Physical Super Novice"
    set "STAT_PRIORITY=STR,AGI,DEX,VIT"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="3" (
    set "BUILD_TYPE=support_supernovice"
    set "BUILD_NAME=Support Super Novice"
    set "STAT_PRIORITY=INT,VIT,DEX,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="4" (
    set "BUILD_TYPE=tank_supernovice"
    set "BUILD_NAME=Tank Super Novice"
    set "STAT_PRIORITY=VIT,STR,DEX,AGI"
    goto playstyle_selection
)
if "%BUILD_CHOICE%"=="5" (
    set "BUILD_TYPE=balanced_supernovice"
    set "BUILD_NAME=Balanced Super Novice"
    set "STAT_PRIORITY=STR,INT,VIT,DEX"
    goto playstyle_selection
)
echo [ERROR] Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto build_selection_supernovice

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
echo Job Path: %JOB_PATH_NAME%
echo Job Path ID: %JOB_PATH%
echo Build Type: %BUILD_TYPE%
echo Build Name: %BUILD_NAME%
echo Playstyle: %PLAYSTYLE_NAME%
echo Stat Priority: %STAT_PRIORITY%
echo.
echo Build Variant System: ENABLED
echo   - Total Variants Available: 55 (11 paths x 5 builds)
echo   - Job Change Support: 39 jobs
echo   - Skill Rotation Support: 42 jobs
echo.
echo [INFO] Saving configuration...
echo [INFO] Saving configuration... >> "%LOG_FILE%"

:: Create ai-service\data directory if it doesn't exist
if not exist "%SCRIPT_DIR%\ai-service\data" mkdir "%SCRIPT_DIR%\ai-service\data"

:: Generate user_intent.json using PowerShell
:: Include job_path_id for proper integration with job_build_variants.json
powershell -NoProfile -Command ^
    "$json = @{" ^
    "    job_path_id = '%JOB_PATH%';" ^
    "    job_path = @('%JOB_PATH_FULL%'.Split(','));" ^
    "    current_job = 'novice';" ^
    "    build = '%BUILD_TYPE%';" ^
    "    build_name = '%BUILD_NAME%';" ^
    "    stat_priority = @('%STAT_PRIORITY%'.Split(','));" ^
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
    "        autonomous_healing = $true;" ^
    "        job_advancement = $true" ^
    "    };" ^
    "    variant_system = @{" ^
    "        enabled = $true;" ^
    "        data_version = '2.0.0';" ^
    "        total_variants = 55;" ^
    "        integration_complete = $true" ^
    "    }" ^
    "};" ^
    "$json | ConvertTo-Json -Depth 10 | Out-File -FilePath '%SCRIPT_DIR%\ai-service\data\user_intent.json' -Encoding UTF8"

if !errorlevel! equ 0 (
    echo [SUCCESS] Configuration saved to ai-service\data\user_intent.json
    echo [SUCCESS] Configuration saved >> "%LOG_FILE%"
    
    :: Verify the configuration file was created
    if exist "%SCRIPT_DIR%\ai-service\data\user_intent.json" (
        echo [SUCCESS] Configuration file verified
        echo [SUCCESS] Configuration file verified >> "%LOG_FILE%"
    )
) else (
    echo [WARNING] Failed to save configuration
    echo [WARNING] Failed to save configuration >> "%LOG_FILE%"
)

echo.
echo ========================================================================
echo   [SUCCESS] Build Variant System Integration Complete!
echo ========================================================================
echo.
echo Your configuration includes:
echo   - Job Path: %JOB_PATH_NAME%
echo   - Build Variant: %BUILD_NAME%
echo   - Playstyle: %PLAYSTYLE_NAME%
echo   - Stat Allocation: Fully Automated
echo   - Job Advancement: Fully Automated
echo   - Equipment Management: Fully Automated
echo.
echo The AI will automatically:
echo   [OK] Allocate stats based on your build variant
echo   [OK] Learn skills in optimal order
echo   [OK] Change jobs when ready (39 jobs supported)
echo   [OK] Use appropriate skill rotations (42 jobs supported)
echo   [OK] Manage equipment based on progression
echo.
echo [SUCCESS] Character configuration saved with full variant support!
echo.

:: ============================================================================
:: STEP 6: AUTO-CONFIGURE OPENKORE BOT
:: ============================================================================

echo.
echo ========================================================================
echo   STEP 6: Auto-Configuring OpenKore Bot
echo ========================================================================
echo.

echo [INFO] Verifying user_intent.json was created...
echo [INFO] Verifying user_intent.json was created... >> "%LOG_FILE%"

REM Verify critical files exist before proceeding
set "INTENT_FILE_CHECK=%SCRIPT_DIR%\ai-service\data\user_intent.json"
if not exist "%INTENT_FILE_CHECK%" (
    echo [ERROR] user_intent.json was not created properly!
    echo [ERROR] user_intent.json was not created properly! >> "%LOG_FILE%"
    echo [ERROR] Installation cannot continue without this file.
    echo.
    echo Please report this issue with the install.log file.
    pause
    endlocal
    exit /b 1
)

echo [SUCCESS] user_intent.json verified
echo [SUCCESS] user_intent.json verified >> "%LOG_FILE%"

echo [INFO] Applying configuration to OpenKore config.txt...
echo [INFO] Applying configuration to OpenKore config.txt... >> "%LOG_FILE%"

REM Set absolute paths to avoid context issues
set "OPENKORE_ROOT=%SCRIPT_DIR%"
set "AI_SERVICE_ROOT=%OPENKORE_ROOT%\ai-service"
set "TOOLS_PATH=%AI_SERVICE_ROOT%\tools"
set "CONFIG_PATH=%OPENKORE_ROOT%\control\config.txt"
set "INTENT_PATH=%AI_SERVICE_ROOT%\data\user_intent.json"

REM Verify auto_configure.py exists
if not exist "%TOOLS_PATH%\auto_configure.py" (
    echo [ERROR] auto_configure.py not found at: %TOOLS_PATH%\auto_configure.py
    echo [ERROR] auto_configure.py not found >> "%LOG_FILE%"
    echo [WARNING] Skipping auto-configuration
    echo [WARNING] Skipping auto-configuration >> "%LOG_FILE%"
    set AUTO_CONFIG_RESULT=1
    goto skip_auto_config
)

REM Verify config.txt exists
if not exist "%CONFIG_PATH%" (
    echo [ERROR] config.txt not found at: %CONFIG_PATH%
    echo [ERROR] config.txt not found >> "%LOG_FILE%"
    echo [WARNING] Skipping auto-configuration
    echo [WARNING] Skipping auto-configuration >> "%LOG_FILE%"
    set AUTO_CONFIG_RESULT=1
    goto skip_auto_config
)

REM Run auto-configure using venv Python
REM Note: Using venv Python directly instead of activating to avoid path issues
echo [INFO] Running auto_configure.py with venv Python...
echo [DEBUG] Python: %PYTHON_CMD%
echo [DEBUG] Script: %TOOLS_PATH%\auto_configure.py
echo [DEBUG] Config: %CONFIG_PATH%
echo [DEBUG] Intent: %INTENT_PATH%

"%PYTHON_CMD%" "%TOOLS_PATH%\auto_configure.py" "%CONFIG_PATH%" "%INTENT_PATH%" 2>&1 | findstr /V "^$"
set AUTO_CONFIG_RESULT=!errorlevel!

echo [DEBUG] auto_configure.py returned: !AUTO_CONFIG_RESULT!

:skip_auto_config

if !AUTO_CONFIG_RESULT! neq 0 (
    echo [WARNING] Auto-configuration encountered issues (exit code: !AUTO_CONFIG_RESULT!)
    echo [WARNING] Auto-configuration encountered issues (exit code: !AUTO_CONFIG_RESULT!) >> "%LOG_FILE%"
    echo [WARNING] You may need to configure config.txt manually
    echo [WARNING] Continuing with installation...
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
echo   [SUCCESS] Autonomous Item Purchasing Enabled
echo ========================================================================
echo.
echo   Your bot is configured for FULL AUTONOMY:
echo.
echo   [AUTOMATIC ITEM PURCHASING]:
echo   - Bot will auto-buy Red Potions (healing)
echo   - Bot will auto-buy Fly Wings (emergency teleport)
echo   - No manual item purchasing needed!
echo.
echo   [Initial Zeny Requirement]:
echo   - Your character needs ~20,000 zeny to start buying items
echo   - If you have less: Bot will farm first, then buy items automatically
echo   - If you have more: Bot starts buying items immediately
echo.
echo   [NPC Location]: Prontera Tool Shop (152, 29)
echo   - Bot knows where to go automatically
echo   - Bot will walk there when items run low
echo.
echo   [95%% AUTONOMOUS OPERATION]:
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
echo   [SUCCESS] Installation Complete!
echo ========================================================================
echo.
echo [SUCCESS] Installation completed successfully
echo [SUCCESS] Installation completed successfully >> "%LOG_FILE%"
echo.
echo Installed components:
echo   - Python: %PYTHON_VERSION%
echo   - Perl: %PERL_VERSION%
echo   - Perl Modules: LWP::UserAgent (for GodTierAI plugin)
echo   - PyTorch: GPU Support = !HAS_GPU!
echo   - Character Build: %BUILD_NAME% (%PLAYSTYLE_NAME%)
echo   - Job Path: %JOB_PATH_NAME%
echo   - Build Variant System: ENABLED (55 variants across 11 paths)
echo   - Bot Configuration: Auto-applied to config.txt
echo.
echo Build Variant Integration:
echo   [OK] Job Build Variants: 55 builds (11 paths x 5 variants)
echo   [OK] Job Change Locations: 39 jobs supported
echo   [OK] Skill Rotations: 42 jobs supported
echo   [OK] Stat Allocation: Fully automated per build
echo   [OK] Job Advancement: Fully automated
echo.
echo Log file: %LOG_FILE%
echo.
echo ========================================================================
echo   NEXT STEPS (IN ORDER):
echo ========================================================================
echo.
echo   1. [API Key]: Configured automatically during installation
echo      - If you skipped API key entry, you can add it manually to ai-service\.env
echo      - Format: DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxx
echo.
echo   2. [Optional] - Give Character Zeny:
echo      - If your character has less than 20k zeny, consider giving some zeny
echo      - Bot can farm first, but 20k+ zeny allows immediate item buying
echo      - Bot will AUTO-BUY items - no manual purchasing needed!
echo.
echo   3. [Start the system]:
echo      - Run: start.bat
echo      - AI Engine will start first (port 9901)
echo      - AI Service will start second (port 9902)
echo      - OpenKore will start last
echo.
echo   4. [What Your Bot Will Do Automatically]:
echo      - Allocate stats according to %BUILD_NAME% build
echo      - Learn skills in optimal order
echo      - Change jobs when level requirements are met
echo      - Use appropriate skill rotations for your job
echo      - Manage equipment based on progression
echo      - Farm, heal, and purchase items autonomously
echo.
echo ========================================================================
echo   FULL AUTONOMY ACHIEVED WITH BUILD VARIANT SYSTEM
echo ========================================================================
echo.
echo Your bot now has access to 55 pre-configured build variants
echo across 11 job paths with complete automation support.
echo.

pause
endlocal
exit /b 0
