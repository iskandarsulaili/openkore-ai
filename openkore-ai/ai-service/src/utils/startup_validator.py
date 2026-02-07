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


def safe_print(message):
    """Print message, falling back to ASCII if encoding fails"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Replace emojis with ASCII equivalents
        ascii_message = (message
            .replace('🚨', '[!!]')
            .replace('❌', '[X]')
            .replace('⚠️', '[!]')
            .replace('✅', '[OK]')
            .replace('🧠', '[AI]')
            .replace('💓', '[SYS]')
            .replace('🔮', '[ML]')
            .replace('⚡', '[FAST]')
            .replace('📖', '[INFO]')
            .replace('🔧', '[CONFIG]')
        )
        print(ascii_message.encode('ascii', errors='replace').decode('ascii'))


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
        logger.warning("⚠️ No healing configured! Applying emergency defaults...")
        safe_print("\n" + "="*70)
        safe_print("  🚨 EMERGENCY AUTO-CONFIGURATION")
        safe_print("="*70)
        safe_print("  No healing items detected in config.txt!")
        safe_print("  Applying emergency survival configuration automatically...")
        safe_print("="*70 + "\n")
        
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
        
        if result.returncode == 0:
            logger.info("✅ Emergency configuration applied successfully")
            safe_print("\n✅ Emergency configuration applied successfully!\n")
            return True
        else:
            logger.error(f"❌ Emergency configuration failed: {result.stderr}")
            safe_print(f"\n❌ Emergency configuration failed: {result.stderr}\n")
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
                        "✅ AUTO-FIXED: No healing was configured, but emergency defaults were applied!\n"
                        "   Your bot now has:\n"
                        "   • Red Potion healing at 60-70% HP\n"
                        "   • Fly Wing emergency teleport at 30% HP\n"
                        "   • Auto-purchasing for Red Potions and Fly Wings\n\n"
                        "   ⚠️  You need ~20,000 zeny for bot to auto-buy items.\n"
                        "   If you don't have enough, bot will still work but without items initially."
                    )
                else:
                    errors.append(
                        "❌ CRITICAL: No healing items configured in config.txt!\n"
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
                        "✅ AUTO-FIXED: Empty template blocks replaced with working configuration!\n"
                        "   Your bot now has proper healing and item purchasing configured."
                    )
            
            # Check teleport threshold
            if 'teleportAuto_hp 10' in config_content:
                warnings.append(
                    "⚠️  teleportAuto_hp is 10% (VERY LOW - bot may die often)\n"
                    "   Recommended: 40% for safer farming\n\n"
                    "   SOLUTION: Run install.bat to apply optimal settings."
                )
            
            # Check for Fly Wing configuration (teleport item)
            has_flywing = 'useSelf_item Fly Wing' in config_content or 'useSelf_item 601' in config_content
            if not has_flywing:
                warnings.append(
                    "⚠️  No Fly Wing configured for emergency teleport\n"
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
        safe_print("\n" + "="*70)
        safe_print("  ❌ STARTUP VALIDATION ERRORS")
        safe_print("="*70)
        for i, error in enumerate(errors, 1):
            safe_print(f"\n{i}. {error}")
        safe_print("\n" + "="*70)
        safe_print("  System cannot start with these errors. Please fix them first.")
        safe_print("="*70 + "\n")
        
    if warnings:
        safe_print("\n" + "="*70)
        safe_print("  ⚠️  STARTUP VALIDATION WARNINGS")
        safe_print("="*70)
        for i, warning in enumerate(warnings, 1):
            safe_print(f"\n{i}. {warning}")
        safe_print("\n" + "="*70)
        safe_print("  System will start, but bot survival is NOT guaranteed!")
        safe_print("="*70 + "\n")
    
    if not warnings and not errors:
        logger.info("✅ Startup validation passed - all checks OK")
        safe_print("✅ Startup validation passed - bot properly configured\n")


def validate_and_report():
    """
    Run validation and report results.
    Raises RuntimeError if there are critical errors.
    """
    
    warnings, errors = validate_startup()
    
    # Log to logger
    if warnings:
        logger.warning("⚠️ Startup Validation Warnings:")
        for w in warnings:
            logger.warning(f"  - {w}")
    
    if errors:
        logger.error("❌ Startup Validation Errors:")
        for e in errors:
            logger.error(f"  - {e}")
    
    # Print to console
    print_validation_results(warnings, errors)
    
    # Raise error if critical errors found
    if errors:
        raise RuntimeError(
            "Startup validation failed with critical errors. "
            "Please fix the issues listed above before starting the system."
        )
