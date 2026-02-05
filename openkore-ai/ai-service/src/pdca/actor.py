"""
PDCA Act Phase: Hot-reload macros and apply improvements
"""

from typing import Dict, Any, List
from pathlib import Path
from loguru import logger
import shutil
import time

class PDCAActor:
    """Applies improvements through macro hot-reload"""
    
    def __init__(self, macro_directory: str = "../../../macros"):
        self.macro_dir = Path(macro_directory)
        self.backup_dir = self.macro_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        logger.info("PDCA Actor initialized")
        
    async def backup_current_macros(self) -> bool:
        """Backup current macros before updating"""
        try:
            timestamp = int(time.time())
            backup_subdir = self.backup_dir / f"backup_{timestamp}"
            backup_subdir.mkdir(parents=True, exist_ok=True)
            
            # Copy all current macros
            for macro_file in self.macro_dir.glob("*.txt"):
                if macro_file.parent == self.macro_dir:  # Skip backups folder
                    shutil.copy2(macro_file, backup_subdir / macro_file.name)
                    
            logger.info(f"Backed up macros to {backup_subdir}")
            return True
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False
            
    async def apply_new_macros(self, new_macros: List[tuple]) -> bool:
        """Apply new macros (atomic replacement)"""
        try:
            # Backup current macros first
            await self.backup_current_macros()
            
            # Write new macros atomically
            for filename, content in new_macros:
                macro_path = self.macro_dir / filename
                temp_path = macro_path.with_suffix('.tmp')
                
                # Write to temp file first
                temp_path.write_text(content, encoding='utf-8')
                
                # Atomic rename
                temp_path.replace(macro_path)
                logger.info(f"Hot-reloaded macro: {filename}")
                
            return True
        except Exception as e:
            logger.error(f"Hot-reload failed: {e}")
            return False
            
    async def notify_reload(self, session_id: str) -> Dict[str, Any]:
        """Notify system that macros have been reloaded"""
        from database.schema import db
        
        await db.add_memory(
            session_id,
            "reflective",
            f"Macros hot-reloaded based on PDCA cycle at {int(time.time())}",
            importance=0.8
        )
        
        return {
            "status": "macros_reloaded",
            "timestamp": int(time.time()),
            "message": "OpenKore will detect changes on next macro check"
        }
        
    async def rollback_to_backup(self, backup_timestamp: int) -> bool:
        """Rollback to a specific backup if new macros fail"""
        try:
            backup_subdir = self.backup_dir / f"backup_{backup_timestamp}"
            if not backup_subdir.exists():
                logger.error(f"Backup {backup_timestamp} not found")
                return False
                
            # Restore from backup
            for backup_file in backup_subdir.glob("*.txt"):
                target_path = self.macro_dir / backup_file.name
                shutil.copy2(backup_file, target_path)
                logger.info(f"Restored {backup_file.name} from backup")
                
            return True
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

actor = PDCAActor()
