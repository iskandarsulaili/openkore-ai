"""
Goal Persistence Manager - State Management Component

Saves and loads goal state across sessions for continuity and resume capabilities.

Features:
- Atomic file operations (no corruption)
- JSON serialization with schema validation
- Resume in-progress goals
- Abandon expired goals
- Backup/restore capabilities
"""

from typing import List, Optional, Dict, Any
import logging
import json
import os
from datetime import datetime
from pathlib import Path
import shutil

from .goal_model import TemporalGoal, GoalStatus
from pydantic import ValidationError


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

logger = logging.getLogger(__name__)


class GoalPersistenceManager:
    """
    Save/load goal state across sessions
    
    Key capabilities:
    - Persist all active goals to disk
    - Restore goals from previous session
    - Resume in-progress goals
    - Abandon expired goals
    - Maintain backup history
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize Persistence Manager
        
        Args:
            data_dir: Directory for storing goal state files
        """
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Goal Persistence Manager initialized (data_dir: {self.data_dir})")
    
    def save_goals(
        self,
        goals: List[TemporalGoal],
        filepath: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Persist all active goals to disk
        
        Uses atomic write (temp file → rename) to prevent corruption.
        
        Args:
            goals: List of goals to save
            filepath: Optional custom filepath (default: data/goals_state.json)
        
        Returns:
            Save operation result
        """
        
        if filepath is None:
            filepath = str(self.data_dir / "goals_state.json")
        
        logger.info(f"Saving {len(goals)} goals to {filepath}")
        
        try:
            # Prepare data for serialization
            goals_data = []
            for goal in goals:
                # Convert to dict using Pydantic
                goal_dict = goal.dict()
                
                # Add save metadata
                goal_dict['_saved_at'] = datetime.now().isoformat()
                goal_dict['_save_version'] = '1.0'
                
                goals_data.append(goal_dict)
            
            # Create save package
            save_package = {
                'saved_at': datetime.now().isoformat(),
                'version': '1.0',
                'goal_count': len(goals),
                'goals': goals_data
            }
            
            # Write to temporary file first (atomic operation)
            temp_filepath = f"{filepath}.tmp"
            
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(save_package, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
            
            # Backup existing file if it exists
            if os.path.exists(filepath):
                self._create_backup(filepath)
            
            # Atomic rename (replace old file)
            os.replace(temp_filepath, filepath)
            
            logger.info(f"✅ Successfully saved {len(goals)} goals")
            
            # Update last_saved_at for each goal
            for goal in goals:
                goal.last_saved_at = datetime.now()
            
            return {
                'success': True,
                'filepath': filepath,
                'goals_saved': len(goals),
                'file_size_bytes': os.path.getsize(filepath),
                'saved_at': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to save goals: {str(e)}")
            
            # Clean up temp file if it exists
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def load_goals(
        self,
        filepath: Optional[str] = None
    ) -> List[TemporalGoal]:
        """
        Restore goals from previous session
        
        Validates schema and handles expired goals.
        
        Args:
            filepath: Optional custom filepath (default: data/goals_state.json)
        
        Returns:
            List of restored goals
        """
        
        if filepath is None:
            filepath = str(self.data_dir / "goals_state.json")
        
        logger.info(f"Loading goals from {filepath}")
        
        if not os.path.exists(filepath):
            logger.warning(f"No saved goals file found at {filepath}")
            return []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                save_package = json.load(f)
            
            logger.info(f"Loaded save package from {save_package.get('saved_at', 'unknown time')}")
            
            goals_data = save_package.get('goals', [])
            restored_goals = []
            
            for goal_data in goals_data:
                try:
                    # Remove save metadata
                    goal_data.pop('_saved_at', None)
                    goal_data.pop('_save_version', None)
                    
                    # Restore goal using Pydantic
                    goal = TemporalGoal(**goal_data)
                    
                    # Check if goal is still valid
                    if self._should_resume(goal):
                        restored_goals.append(goal)
                        logger.info(f"Restored goal: {goal.name} (status: {goal.status})")
                    else:
                        logger.info(f"Abandoned expired goal: {goal.name}")
                
                except ValidationError as e:
                    logger.error(f"Failed to restore goal: {e}")
                    continue
            
            logger.info(f"✅ Successfully restored {len(restored_goals)} goals")
            
            return restored_goals
        
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted save file: {e}")
            
            # Try to restore from backup
            logger.info("Attempting to restore from backup...")
            return self._restore_from_backup(filepath)
        
        except Exception as e:
            logger.error(f"Failed to load goals: {str(e)}")
            return []
    
    def clear_saved_goals(self, filepath: Optional[str] = None) -> bool:
        """
        Clear saved goals file
        
        Args:
            filepath: Optional custom filepath
        
        Returns:
            True if successful
        """
        
        if filepath is None:
            filepath = str(self.data_dir / "goals_state.json")
        
        try:
            if os.path.exists(filepath):
                # Create backup first
                self._create_backup(filepath)
                
                os.remove(filepath)
                logger.info(f"Cleared saved goals at {filepath}")
                return True
            else:
                logger.info("No saved goals file to clear")
                return True
        
        except Exception as e:
            logger.error(f"Failed to clear saved goals: {str(e)}")
            return False
    
    def get_save_info(self, filepath: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get information about saved goals file
        
        Args:
            filepath: Optional custom filepath
        
        Returns:
            Save file information or None if doesn't exist
        """
        
        if filepath is None:
            filepath = str(self.data_dir / "goals_state.json")
        
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                save_package = json.load(f)
            
            file_stats = os.stat(filepath)
            
            return {
                'filepath': filepath,
                'exists': True,
                'saved_at': save_package.get('saved_at'),
                'version': save_package.get('version'),
                'goal_count': save_package.get('goal_count'),
                'file_size_bytes': file_stats.st_size,
                'modified_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to get save info: {str(e)}")
            return None
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all backup files
        
        Returns:
            List of backup file information
        """
        
        backups = []
        
        try:
            for backup_file in self.backup_dir.glob("goals_state_backup_*.json"):
                stats = os.stat(backup_file)
                
                backups.append({
                    'filepath': str(backup_file),
                    'filename': backup_file.name,
                    'created_at': datetime.fromtimestamp(stats.st_ctime).isoformat(),
                    'size_bytes': stats.st_size
                })
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x['created_at'], reverse=True)
        
        except Exception as e:
            logger.error(f"Failed to list backups: {str(e)}")
        
        return backups
    
    # ===== Private Helper Methods =====
    
    def _should_resume(self, goal: TemporalGoal) -> bool:
        """
        Determine if goal should be resumed or abandoned
        
        Resume if:
        - Status is IN_PROGRESS
        - Not expired (deadline not passed)
        
        Abandon if:
        - Status is COMPLETED, FAILED, or ABANDONED
        - Deadline passed
        """
        
        # Don't resume completed/failed goals
        if goal.status in [GoalStatus.COMPLETED, GoalStatus.FAILED, GoalStatus.ABANDONED]:
            return False
        
        # Check if expired
        if goal.is_overdue():
            logger.info(f"Goal {goal.name} is overdue, abandoning")
            goal.status = GoalStatus.ABANDONED
            return False
        
        return True
    
    def _create_backup(self, filepath: str) -> None:
        """Create backup of existing save file"""
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"goals_state_backup_{timestamp}.json"
            backup_path = self.backup_dir / backup_filename
            
            shutil.copy2(filepath, backup_path)
            
            logger.info(f"Created backup: {backup_filename}")
            
            # Clean up old backups (keep last 10)
            self._cleanup_old_backups(keep=10)
        
        except Exception as e:
            logger.warning(f"Failed to create backup: {str(e)}")
    
    def _cleanup_old_backups(self, keep: int = 10) -> None:
        """Clean up old backup files, keeping only the most recent"""
        
        try:
            backups = self.list_backups()
            
            if len(backups) > keep:
                # Delete oldest backups
                for backup in backups[keep:]:
                    os.remove(backup['filepath'])
                    logger.debug(f"Deleted old backup: {backup['filename']}")
        
        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {str(e)}")
    
    def _restore_from_backup(self, filepath: str) -> List[TemporalGoal]:
        """Attempt to restore from most recent backup"""
        
        backups = self.list_backups()
        
        if not backups:
            logger.error("No backups available for restoration")
            return []
        
        # Try most recent backup
        latest_backup = backups[0]
        
        logger.info(f"Restoring from backup: {latest_backup['filename']}")
        
        try:
            return self.load_goals(latest_backup['filepath'])
        except Exception as e:
            logger.error(f"Failed to restore from backup: {str(e)}")
            return []
