"""
Auto-generate teleToDest plugin configuration
User requirement: Never manually fix config - use autonomous self-healing

This module automatically generates teleToDest plugin configuration when the plugin
reports missing config keys. It adapts settings based on character level and class.
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TeleDestConfigGenerator:
    """Generates teleToDest plugin configuration based on character level/class"""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
    
    def generate_config(self, character_level: int, character_class: str) -> Dict[str, str]:
        """
        Generate teleToDest configuration
        
        Args:
            character_level: Character base level
            character_class: Character class (Novice, Swordman, etc.)
        
        Returns:
            Dict of config settings to append to config.txt
        """
        logger.info(f"[TeleDest] Generating config for Lv{character_level} {character_class}")
        
        # Basic teleToDest settings - required by the plugin
        # Based on teleToDest.pl validation requirements (lines 61-76):
        # - teleToDestOn: Enable/disable plugin (0 or 1)
        # - teleToDestMap: Target map name
        # - teleToDestXY: Target coordinates (format: x y)
        # - teleToDestDistance: Distance threshold
        # - teleToDestMethod: Teleport method (steps or radius)
        
        config = {
            # Enable the plugin (required)
            "teleToDestOn": "0",  # Start disabled, user can enable when ready
            
            # Default target map (required) - use prontera as safe default
            "teleToDestMap": "prontera",
            
            # Default coordinates (required) - prontera center
            "teleToDestXY": "156 191",
            
            # Distance threshold in cells (required)
            "teleToDestDistance": "10",
            
            # Teleport method (required): steps or radius
            "teleToDestMethod": "radius",
        }
        
        # Level-based adjustments for optimal teleporting behavior
        if character_level < 10:
            # Low level: Conservative settings
            config["teleToDestDistance"] = "8"  # Smaller search radius
        elif character_level >= 30:
            # Higher level: More aggressive settings
            config["teleToDestDistance"] = "15"  # Larger search radius
        
        logger.info(f"[TeleDest] Generated config with {len(config)} keys")
        return config
    
    def append_to_config(self, config_dict: Dict[str, str]) -> Dict[str, Any]:
        """
        Append teleToDest config to config.txt with hot reload support
        
        User requirement: Use hot reload to avoid disconnect
        
        Args:
            config_dict: Configuration key-value pairs to append
            
        Returns:
            Result dict with success status and keys added
        """
        logger.info(f"[TeleDest] Appending {len(config_dict)} config keys to config.txt")
        
        try:
            # Read current config
            with open(self.config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Check if teleToDest section already exists
            has_teledest_section = any("teleToDest" in line for line in lines)
            
            if has_teledest_section:
                logger.info("[TeleDest] Configuration section already exists, updating...")
                
                # Update existing keys
                updated_keys = []
                for i, line in enumerate(lines):
                    for key, value in config_dict.items():
                        if line.strip().startswith(key):
                            lines[i] = f"{key} {value}\n"
                            updated_keys.append(key)
                
                # Add missing keys
                missing_keys = [k for k in config_dict.keys() if k not in updated_keys]
                if missing_keys:
                    # Find the teleToDest section and add after it
                    insert_index = None
                    for i, line in enumerate(lines):
                        if "teleToDest" in line and "#" in line:
                            insert_index = i + 1
                            break
                    
                    if insert_index:
                        for key in missing_keys:
                            lines.insert(insert_index, f"{key} {config_dict[key]}\n")
                            insert_index += 1
                    else:
                        # Append at end if section not clearly defined
                        for key in missing_keys:
                            lines.append(f"{key} {config_dict[key]}\n")
                
                # Write back
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                logger.info(f"[TeleDest] Updated {len(updated_keys)} keys, added {len(missing_keys)} keys")
                return {
                    "success": True,
                    "keys_added": list(config_dict.keys()),
                    "updated": len(updated_keys),
                    "added": len(missing_keys)
                }
            else:
                # Add new section at the end
                lines.append("\n")
                lines.append("# ============================================\n")
                lines.append("# teleToDest Plugin Configuration\n")
                lines.append("# Auto-generated by AI autonomous self-healing\n")
                lines.append("# ============================================\n")
                
                for key, value in config_dict.items():
                    lines.append(f"{key} {value}\n")
                
                # Write back
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                logger.info(f"[TeleDest] Successfully added configuration section with {len(config_dict)} keys")
                logger.info("[TeleDest] OpenKore will hot-reload automatically (GodTierAI monitors config.txt)")
                
                return {
                    "success": True,
                    "keys_added": list(config_dict.keys()),
                    "section_created": True
                }
        
        except FileNotFoundError:
            logger.error(f"[TeleDest] Config file not found: {self.config_path}")
            return {
                "success": False,
                "error": f"Config file not found: {self.config_path}"
            }
        except Exception as e:
            logger.error(f"[TeleDest] Error writing config: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Convenience function for easy import
def generate_teledest_config(config_path: Path, character_level: int = 1, character_class: str = "Novice") -> Dict[str, Any]:
    """
    Generate and append teleToDest configuration
    
    Args:
        config_path: Path to config.txt
        character_level: Character base level
        character_class: Character class
        
    Returns:
        Result dict with success status
    """
    generator = TeleDestConfigGenerator(config_path)
    config_dict = generator.generate_config(character_level, character_class)
    result = generator.append_to_config(config_dict)
    return result
