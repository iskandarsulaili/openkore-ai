"""Safe execution with backup and rollback"""

from pathlib import Path
import shutil
from datetime import datetime
from typing import Dict, Any, List


class SafeExecutor:
    """Safely executes fixes with backup/rollback capability"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.backup_dir = Path(config['backup']['directory'])
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def execute_fix(self, file_path: str, changes: List[Dict]) -> Dict[str, Any]:
        """Execute fix with automatic backup"""
        
        file_path = Path(file_path)
        backup_path = self._create_backup(file_path)
        
        try:
            # Apply changes
            self._apply_changes(file_path, changes)
            
            return {
                'success': True,
                'backup': str(backup_path)
            }
        except Exception as e:
            # Rollback
            shutil.copy2(backup_path, file_path)
            return {
                'success': False,
                'error': str(e),
                'rollback': True
            }
    
    def _create_backup(self, file_path: Path) -> Path:
        """Create timestamped backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / backup_name
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def _apply_changes(self, file_path: Path, changes: List[Dict]):
        """Apply list of changes to file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for change in changes:
            if change['type'] == 'replace':
                content = re.sub(change['pattern'], change['replacement'], content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
