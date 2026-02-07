"""
Auto-configure config.txt based on user_intent.json.
Fixes the disconnect between wizard and actual bot configuration.

This tool reads the user's preferences from user_intent.json (captured during install.bat)
and applies them to OpenKore's config.txt to ensure the bot is properly configured for survival.
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional
import sys
import io

# Windows UTF-8 console encoding fix
if sys.platform == 'win32':
    import os
    # Set environment variable for subprocess to inherit
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
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
            .replace('ℹ️', '[i]')
        )
        print(ascii_message.encode('ascii', errors='replace').decode('ascii'))


def load_user_intent(intent_path: str) -> Optional[Dict]:
    """Load user intent from JSON file"""
    try:
        # Try UTF-8 with BOM first
        with open(intent_path, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except FileNotFoundError:
        safe_print(f"❌ user_intent.json not found at: {intent_path}")
        return None
    except json.JSONDecodeError as e:
        safe_print(f"❌ Invalid JSON in user_intent.json: {e}")
        return None


def apply_user_intent(config_path: str, user_intent_path: str) -> bool:
    """Apply user intent to config.txt"""
    
    try:
        # Convert to absolute paths
        config_path = Path(config_path).resolve()
        user_intent_path = Path(user_intent_path).resolve()
        
        safe_print("\n" + "="*60)
        safe_print("  Auto-Configuring OpenKore Bot")
        safe_print("="*60 + "\n")
        
        safe_print(f"[DEBUG] Config path: {config_path}")
        safe_print(f"[DEBUG] Intent path: {user_intent_path}")
        
        if not user_intent_path.exists():
            safe_print(f"❌ User intent file not found: {user_intent_path}")
            return False
        
        if not config_path.exists():
            safe_print(f"❌ Config file not found: {config_path}")
            return False
        
        # Load user intent
        safe_print(f"\n📖 Loading user preferences from: {user_intent_path}")
        user_intent = load_user_intent(str(user_intent_path))
        
        if not user_intent:
            safe_print("❌ Failed to load user intent. Cannot auto-configure.")
            return False
        
        safe_print(f"[DEBUG] Loaded user intent: {user_intent.get('build', 'unknown')}")
    except Exception as e:
        safe_print(f"❌ Error initializing configuration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    playstyle = user_intent.get('playstyle_config', {})
    build_name = user_intent.get('build_name', 'Unknown')
    playstyle_name = user_intent.get('playstyle', 'balanced')
    
    safe_print(f"✅ Loaded configuration for: {build_name}")
    safe_print(f"   Playstyle: {playstyle_name}")
    
    # Read current config
    safe_print(f"\n📖 Reading config from: {config_path}")
    try:
        with open(str(config_path), 'r', encoding='utf-8') as f:
            config_lines = f.readlines()
    except FileNotFoundError:
        safe_print(f"❌ config.txt not found at: {config_path}")
        return False
    except Exception as e:
        safe_print(f"❌ Error reading config.txt: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    safe_print(f"✅ Read {len(config_lines)} lines from config.txt")
    
    # Apply fixes
    safe_print("\n🔧 Applying configuration changes...\n")
    
    new_lines = []
    in_useself_block = False
    in_buyauto_block = False
    skip_empty_block = False
    useself_block_name = ""
    heal_configured = False
    buyauto_configured = False
    teleport_configured = False
    teleport_maxdmg_configured = False
    changes_made = []
    
    i = 0
    while i < len(config_lines):
        line = config_lines[i]
        
        # Fix teleportAuto_hp threshold
        if line.startswith('teleportAuto_hp'):
            old_value = line.strip()
            threshold = int(playstyle.get('teleport_hp_threshold', 0.40) * 100)
            new_line = f'teleportAuto_hp {threshold}\n'
            new_lines.append(new_line)
            
            if old_value != new_line.strip():
                changes_made.append(f"✓ Updated teleportAuto_hp: {old_value} → teleportAuto_hp {threshold}")
                teleport_configured = True
            i += 1
            continue
        
        # Fix teleportAuto_maxDmg (lower it for better survival)
        if line.startswith('teleportAuto_maxDmg'):
            old_value = line.strip()
            new_line = f'teleportAuto_maxDmg 300\n'
            new_lines.append(new_line)
            
            if old_value != new_line.strip():
                changes_made.append(f"✓ Updated teleportAuto_maxDmg: {old_value} → teleportAuto_maxDmg 300")
                teleport_maxdmg_configured = True
            i += 1
            continue
        
        # Detect EMPTY useSelf_item template block and replace it
        if line.strip().startswith('useSelf_item {'):
            # This is the empty template block - skip it entirely
            safe_print("[DEBUG] Found empty useSelf_item template block, replacing with real configuration...")
            
            # Skip until we find the closing brace
            j = i + 1
            while j < len(config_lines) and '}' not in config_lines[j]:
                j += 1
            
            # Skip the closing brace too
            if j < len(config_lines):
                j += 1
            
            # Replace with real healing configuration
            heal_threshold = int(playstyle.get('heal_threshold', 0.60) * 100)
            healing_block = [
                f"\n# Auto-configured healing (from user_intent.json)\n",
                f"useSelf_item Red Potion {{\n",
                f"    hp < {heal_threshold}\n",
                f"    inInventory Red Potion > 0\n",
                f"    notWhileSitting 1\n",
                f"}}\n\n",
                f"# Emergency teleport with Fly Wing\n",
                f"useSelf_item Fly Wing {{\n",
                f"    hp < 30\n",
                f"    inInventory Fly Wing > 0\n",
                f"    notWhileSitting 1\n",
                f"}}\n\n"
            ]
            
            new_lines.extend(healing_block)
            changes_made.append(f"✓ Replaced empty useSelf_item template with Red Potion healing at {heal_threshold}% HP")
            changes_made.append(f"✓ Added Fly Wing emergency teleport at 30% HP")
            heal_configured = True
            
            i = j  # Skip past the entire empty block
            continue
        
        # Detect EMPTY buyAuto template block and replace it
        if line.strip().startswith('buyAuto {'):
            # This is the empty template block - skip it entirely
            safe_print("[DEBUG] Found empty buyAuto template block, replacing with real configuration...")
            
            # Skip until we find the closing brace
            j = i + 1
            while j < len(config_lines) and '}' not in config_lines[j]:
                j += 1
            
            # Skip the closing brace too
            if j < len(config_lines):
                j += 1
            
            # Replace with real buyAuto configuration
            buyauto_block = [
                f"\n# Auto-configured autonomous item purchasing\n",
                f"# Bot will automatically buy items when running low\n",
                f"buyAuto Red Potion {{\n",
                f"    npc prontera 152 29\n",
                f"    minAmount 30\n",
                f"    maxAmount 100\n",
                f"}}\n\n",
                f"buyAuto Fly Wing {{\n",
                f"    npc prontera 152 29\n",
                f"    minAmount 10\n",
                f"    maxAmount 50\n",
                f"}}\n\n"
            ]
            
            new_lines.extend(buyauto_block)
            changes_made.append(f"✓ Replaced empty buyAuto template with Red Potion purchasing (min:30, max:100)")
            changes_made.append(f"✓ Added Fly Wing purchasing (min:10, max:50)")
            buyauto_configured = True
            
            i = j  # Skip past the entire empty block
            continue
        
        # Detect regular useSelf_item blocks (non-empty)
        if line.strip().startswith('useSelf_item') and '{' in line and 'useSelf_item {' not in line:
            in_useself_block = True
            # Extract item name from "useSelf_item ItemName {"
            match = re.match(r'useSelf_item\s+(.+?)\s*\{', line.strip())
            if match:
                useself_block_name = match.group(1)
                if 'Red Potion' in useself_block_name or 'Fly Wing' in useself_block_name:
                    heal_configured = True
        
        # Check if block is closing
        if in_useself_block and '}' in line:
            in_useself_block = False
            useself_block_name = ""
        
        # Detect regular buyAuto blocks
        if line.strip().startswith('buyAuto') and '{' in line and 'buyAuto {' not in line:
            in_buyauto_block = True
            if 'Red Potion' in line or 'Fly Wing' in line:
                buyauto_configured = True
        
        if in_buyauto_block and '}' in line:
            in_buyauto_block = False
        
        new_lines.append(line)
        i += 1
    
    # Add healing and buyAuto if still not configured (fallback for configs without template blocks)
    if not heal_configured or not buyauto_configured:
        heal_threshold = int(playstyle.get('heal_threshold', 0.60) * 100)
        
        # Find a good insertion point (after lockMap or other early settings)
        insert_index = 0
        for idx, line in enumerate(new_lines):
            if line.strip().startswith('lockMap') or line.strip().startswith('route_randomWalk'):
                insert_index = idx + 1
                break
        
        if insert_index == 0:
            # Default to inserting after first 10 lines
            insert_index = min(10, len(new_lines))
        
        fallback_blocks = []
        
        if not heal_configured:
            fallback_blocks.extend([
                f"\n# Auto-configured healing (from user_intent.json)\n",
                f"useSelf_item Red Potion {{\n",
                f"    hp < {heal_threshold}\n",
                f"    inInventory Red Potion > 0\n",
                f"    notWhileSitting 1\n",
                f"}}\n\n",
                f"# Emergency teleport with Fly Wing\n",
                f"useSelf_item Fly Wing {{\n",
                f"    hp < 30\n",
                f"    inInventory Fly Wing > 0\n",
                f"    notWhileSitting 1\n",
                f"}}\n\n"
            ])
            changes_made.append(f"✓ Added Red Potion healing at {heal_threshold}% HP")
            changes_made.append(f"✓ Added Fly Wing emergency teleport at 30% HP")
        
        if not buyauto_configured:
            fallback_blocks.extend([
                f"# Auto-configured autonomous item purchasing\n",
                f"# Bot will automatically buy items when running low\n",
                f"buyAuto Red Potion {{\n",
                f"    npc prontera 152 29\n",
                f"    minAmount 30\n",
                f"    maxAmount 100\n",
                f"}}\n\n",
                f"buyAuto Fly Wing {{\n",
                f"    npc prontera 152 29\n",
                f"    minAmount 10\n",
                f"    maxAmount 50\n",
                f"}}\n\n"
            ])
            changes_made.append(f"✓ Added buyAuto for Red Potion (min:30, max:100)")
            changes_made.append(f"✓ Added buyAuto for Fly Wing (min:10, max:50)")
        
        if fallback_blocks:
            new_lines[insert_index:insert_index] = fallback_blocks
    
    # Write back
    try:
        with open(str(config_path), 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        safe_print(f"✅ Config.txt updated successfully\n")
    except Exception as e:
        safe_print(f"❌ Error writing config.txt: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    safe_print("="*60)
    safe_print("  Configuration Changes Applied")
    safe_print("="*60)
    if changes_made:
        for change in changes_made:
            safe_print(f"  {change}")
    else:
        safe_print("  ℹ️  No changes needed (config already optimal)")
    safe_print("="*60 + "\n")
    
    # Add informational note about initial zeny
    safe_print("⚠️  IMPORTANT INFORMATION:")
    safe_print("="*60)
    safe_print("Your character needs ~20,000 zeny for initial item purchases.")
    safe_print("If you don't have enough zeny:")
    safe_print("  1. Farm some zeny first (bot can still work without items, just less safe)")
    safe_print("  2. Or manually give your character some zeny")
    safe_print("")
    safe_print("The bot will AUTOMATICALLY buy Red Potions and Fly Wings when it has")
    safe_print("enough zeny. You don't need to buy items manually!")
    safe_print("="*60 + "\n")
    
    safe_print("[SUCCESS] Configuration applied successfully")
    return True


def get_emergency_intent() -> Dict:
    """Return emergency default configuration when user_intent.json is missing"""
    return {
        "build": "balanced",
        "playstyle": "conservative",
        "build_name": "Conservative Auto-Bot",
        "playstyle_config": {
            "heal_threshold": 0.70,  # Heal at 70% HP (safe)
            "teleport_hp_threshold": 0.40,  # Teleport at 40% HP
            "risk_tolerance": "conservative"
        }
    }


def main():
    """Main entry point"""
    
    # Handle --emergency flag
    if "--emergency" in sys.argv:
        safe_print("\n🚨 EMERGENCY MODE: Applying conservative default configuration\n")
        
        # Get paths from environment or use defaults
        if len(sys.argv) >= 3:
            config_path = sys.argv[1]
        else:
            # Use default paths relative to this script
            script_dir = Path(__file__).parent
            ai_service_root = script_dir.parent
            openkore_root = ai_service_root.parent
            config_path = str(openkore_root / "control" / "config.txt")
        
        # Create emergency user_intent
        emergency_intent_path = Path(__file__).parent.parent / "data" / "user_intent_emergency.json"
        emergency_intent = get_emergency_intent()
        
        with open(emergency_intent_path, 'w', encoding='utf-8') as f:
            json.dump(emergency_intent, f, indent=4)
        
        success = apply_user_intent(config_path, str(emergency_intent_path))
        sys.exit(0 if success else 1)
    
    elif len(sys.argv) >= 3:
        config_path = sys.argv[1]
        user_intent_path = sys.argv[2]
        
        success = apply_user_intent(config_path, user_intent_path)
        sys.exit(0 if success else 1)
    else:
        safe_print("Usage: python auto_configure.py <config.txt> <user_intent.json>")
        safe_print("   or: python auto_configure.py --emergency [config.txt]")
        safe_print("\nExample:")
        safe_print("  python auto_configure.py ../control/config.txt data/user_intent.json")
        safe_print("  python auto_configure.py --emergency")
        sys.exit(1)


if __name__ == "__main__":
    main()
