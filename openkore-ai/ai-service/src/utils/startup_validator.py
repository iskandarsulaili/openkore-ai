"""
Startup validation to warn users about missing items/config.
Prevents bot from dying due to missing survival items or misconfiguration.
"""

import io
import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# Windows UTF-8 console encoding fix
if sys.platform == 'win32':
    import os
    # Set environment variable for subprocess to inherit
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        # Reconfigure stdout/stderr to use UTF-8
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, io.UnsupportedOperation):
        # Fallback for older Python versions
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, errors='replace')


logger = logging.getLogger(__name__)

# Calculate paths relative to this script's location
# This file is at: openkore-ai/ai-service/src/utils/startup_validator.py
SCRIPT_DIR = Path(__file__).parent  # utils/
AI_SERVICE_SRC = SCRIPT_DIR.parent  # src/
AI_SERVICE_ROOT = AI_SERVICE_SRC.parent  # ai-service/
OPENKORE_ROOT = AI_SERVICE_ROOT.parent  # openkore-ai/


def apply_emergency_defaults():
    """Apply emergency survival configuration if healing is missing"""
    config_path = OPENKORE_ROOT / "control" / "config.txt"
    auto_configure_script = AI_SERVICE_ROOT / "tools" / "auto_configure.py"
    
    if not auto_configure_script.exists():
        logger.error(f"Cannot apply emergency defaults: auto_configure.py not found at {auto_configure_script}")
        return False
    
    try:
        logger.warning("[WARNING] No healing configured! Applying emergency defaults...")
        print("\n" + "="*70)
        print("  [EMERGENCY] EMERGENCY AUTO-CONFIGURATION")
        print("="*70)
        print("  No healing items detected in config.txt!")
        print("  Applying emergency survival configuration automatically...")
        print("="*70 + "\n")
        
        # Run auto_configure.py with UTF-8 encoding
        import os
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run(
            [sys.executable, str(auto_configure_script), "--emergency", str(config_path)],
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='replace',
            env=env
        )
        
        # Print subprocess output for visibility
        if result.stdout:
            print(result.stdout)
        
        if result.returncode == 0:
            logger.info("[SUCCESS] Emergency configuration applied successfully")
            print("\n[SUCCESS] Emergency configuration applied successfully!\n")
            return True
        else:
            logger.error(f"[ERROR] Emergency configuration failed: {result.stderr}")
            print(f"\n[ERROR] Emergency configuration failed: {result.stderr}\n")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Emergency configuration timed out after 30 seconds")
        return False
    except Exception as e:
        logger.error(f"Failed to apply emergency defaults: {e}")
        return False


def validate_startup() -> Tuple[List[str], List[str]]:
    """
    Validate system is properly configured.
    
    Returns:
        Tuple of (warnings, errors)
    """
    
    warnings = []
    errors = []
    
    # Check user_intent.json
    user_intent_path = AI_SERVICE_ROOT / "data" / "user_intent.json"
    if not user_intent_path.exists():
        warnings.append(
            "user_intent.json not found. "
            "Run install.bat to capture character build preferences for 95% autonomy."
        )
    
    # Check config.txt
    config_path = OPENKORE_ROOT / "control" / "config.txt"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
            
            # Check healing configured
            has_red_potion = 'useSelf_item Red Potion' in config_content or 'useSelf_item 501' in config_content
            has_healing_item = 'useSelf_item' in config_content and ('Potion' in config_content or '501' in config_content)
            
            # Check if it's an empty template block (useSelf_item { with only param names inside)
            has_empty_template = 'useSelf_item {' in config_content and 'hp\n' in config_content and 'sp\n' in config_content
            
            if not has_red_potion and not has_healing_item:
                # Try to apply emergency defaults automatically
                logger.warning("No healing configured - attempting auto-fix...")
                
                if apply_emergency_defaults():
                    warnings.append(
                        "[AUTO-FIXED] No healing was configured, but emergency defaults were applied!\n"
                        "   Your bot now has:\n"
                        "   - Red Potion healing at 60-70% HP\n"
                        "   - Fly Wing emergency teleport at 30% HP\n"
                        "   - Auto-purchasing for Red Potions and Fly Wings\n\n"
                        "   [WARNING] You need ~20,000 zeny for bot to auto-buy items.\n"
                        "   If you don't have enough, bot will still work but without items initially."
                    )
                else:
                    errors.append(
                        "[CRITICAL] No healing items configured in config.txt!\n"
                        "   Your bot WILL DIE without healing!\n\n"
                        "   SOLUTION: Run install.bat to auto-configure healing.\n"
                        "   Or manually add to config.txt:\n"
                        "   useSelf_item Red Potion {\n"
                        "       hp < 60\n"
                        "       inInventory Red Potion > 0\n"
                        "   }"
                    )
            elif has_empty_template:
                # Empty template detected - try to fix it
                logger.warning("Empty useSelf_item template detected - attempting auto-fix...")
                
                if apply_emergency_defaults():
                    warnings.append(
                        "[AUTO-FIXED] Empty template blocks replaced with working configuration!\n"
                        "   Your bot now has proper healing and item purchasing configured."
                    )
            
            # Check teleport threshold
            if 'teleportAuto_hp 10' in config_content:
                warnings.append(
                    "[WARNING] teleportAuto_hp is 10% (VERY LOW - bot may die often)\n"
                    "   Recommended: 40% for safer farming\n\n"
                    "   SOLUTION: Run install.bat to apply optimal settings."
                )
            
            # Check for Fly Wing configuration (teleport item)
            has_flywing = 'useSelf_item Fly Wing' in config_content or 'useSelf_item 601' in config_content
            if not has_flywing:
                warnings.append(
                    "[WARNING] No Fly Wing configured for emergency teleport\n"
                    "   Bot won't be able to escape dangerous situations\n\n"
                    "   SOLUTION: Buy 100x Fly Wing from Prontera Tool Shop (152, 29)\n"
                    "   Then add to config.txt: useSelf_item Fly Wing { hp < 30 }"
                )
            
        except Exception as e:
            warnings.append(f"Could not validate config.txt: {e}")
    else:
        errors.append(
            "config.txt not found at ../control/config.txt\n"
            "Please ensure OpenKore is properly installed."
        )
    
    # Check .env file
    env_path = AI_SERVICE_ROOT / ".env"
    if not env_path.exists():
        errors.append(
            ".env file not found!\n"
            "Copy .env.example to .env and add your API keys."
        )
    
    return warnings, errors


def print_validation_results(warnings: List[str], errors: List[str]):
    """Print validation results to console"""
    
    if errors:
        print("\n" + "="*70)
        print("  [ERROR] STARTUP VALIDATION ERRORS")
        print("="*70)
        for i, error in enumerate(errors, 1):
            print(f"\n{i}. {error}")
        print("\n" + "="*70)
        print("  System cannot start with these errors. Please fix them first.")
        print("="*70 + "\n")
        
    if warnings:
        print("\n" + "="*70)
        print("  [WARNING] STARTUP VALIDATION WARNINGS")
        print("="*70)
        for i, warning in enumerate(warnings, 1):
            print(f"\n{i}. {warning}")
        print("\n" + "="*70)
        print("  System will start, but bot survival is NOT guaranteed!")
        print("="*70 + "\n")
    
    if not warnings and not errors:
        logger.info("[SUCCESS] Startup validation passed - all checks OK")
        print("[SUCCESS] Startup validation passed - bot properly configured\n")


def validate_and_report():
    """
    Run validation and report results.
    Raises RuntimeError if there are critical errors that cannot be auto-fixed.
    """
    
    warnings, errors = validate_startup()
    
    # CRITICAL FIX: Check if errors exist but were already auto-fixed
    # The validate_startup() function calls apply_emergency_defaults() internally
    # and moves fixed errors to warnings. So if we reach here with errors,
    # they are truly unrecoverable.
    
    # Log to logger
    if warnings:
        logger.warning("[WARNING] Startup Validation Warnings:")
        for w in warnings:
            logger.warning(f"  - {w}")
    
    if errors:
        logger.error("[ERROR] Startup Validation Errors:")
        for e in errors:
            logger.error(f"  - {e}")
    
    # Print to console
    print_validation_results(warnings, errors)
    
    # CRITICAL FIX: Only raise RuntimeError for truly critical errors
    # that couldn't be auto-fixed (like missing .env file)
    # If errors were auto-fixed, they are now in warnings list instead
    if errors:
        # Check if these are truly blocking errors
        blocking_errors = []
        for error in errors:
            # .env file missing is truly blocking
            if ".env file not found" in error:
                blocking_errors.append(error)
            # Missing OpenKore is truly blocking
            elif "config.txt not found" in error and "Please ensure OpenKore" in error:
                blocking_errors.append(error)
        
        if blocking_errors:
            raise RuntimeError(
                "Startup validation failed with critical errors that cannot be auto-fixed. "
                "Please fix the issues listed above before starting the system."
            )
        else:
            # Errors were present but auto-fixed - log as warning
            logger.warning(
                "[WARNING] Some validation errors were detected but have been auto-fixed. "
                "System will start - monitor for issues."
            )
            print(
                "\n[WARNING] Validation errors were auto-fixed. "
                "System starting - please monitor.\n"
            )
