"""
Execution Agent - Safe Fix Application
Applies fixes with backup, rollback, and hot-reload capabilities
"""

from crewai import Agent
from crewai_tools import BaseTool
from typing import Dict, List, Any
from pathlib import Path
import shutil
from datetime import datetime
import re


class SafeFileModifierTool(BaseTool):
    """Tool for safely modifying configuration files"""
    
    name: str = "safe_file_modifier"
    description: str = "Safely modify OpenKore config files with automatic backup and rollback"
    
    def __init__(self, execution_config: Dict):
        super().__init__()
        self.config = execution_config
        self.backup_dir = Path(execution_config['backup']['directory'])
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def _create_backup(self, file_path: Path) -> Path:
        """Create timestamped backup of file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def _apply_changes(self, file_path: Path, changes: List[Dict]) -> bool:
        """Apply list of changes to file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            modified_content = content
            
            for change in changes:
                change_type = change['type']
                
                if change_type == 'replace':
                    pattern = change['pattern']
                    replacement = change['replacement']
                    modified_content = re.sub(pattern, replacement, modified_content)
                
                elif change_type == 'append_or_update':
                    key = change['key']
                    value = change['value']
                    
                    # Check if key exists
                    key_pattern = f"^{re.escape(key)}\\s+.*$"
                    if re.search(key_pattern, modified_content, re.MULTILINE):
                        # Update existing
                        modified_content = re.sub(
                            key_pattern,
                            f"{key} {value}",
                            modified_content,
                            flags=re.MULTILINE
                        )
                    else:
                        # Append new
                        modified_content += f"\n{key} {value}\n"
            
            # Write modified content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to apply changes: {e}")
    
    def _run(self, file_path: str, changes: List[Dict], require_approval: bool = False) -> Dict[str, Any]:
        """Safely modify file with backup"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return {'success': False, 'error': 'File not found'}
            
            # Create backup
            backup_path = self._create_backup(file_path)
            
            try:
                # Apply changes
                self._apply_changes(file_path, changes)
                
                return {
                    'success': True,
                    'file_modified': str(file_path),
                    'backup_created': str(backup_path),
                    'changes_applied': len(changes)
                }
                
            except Exception as e:
                # Restore from backup on failure
                shutil.copy2(backup_path, file_path)
                return {
                    'success': False,
                    'error': str(e),
                    'rollback_performed': True
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class HotReloadTriggerTool(BaseTool):
    """Tool for triggering OpenKore config hot-reload"""
    
    name: str = "hot_reload"
    description: str = "Trigger OpenKore to reload configuration without restarting"
    
    def _run(self, files_modified: List[str]) -> Dict[str, Any]:
        """Trigger hot-reload mechanism"""
        try:
            # For OpenKore, some configs reload automatically
            # Others may need explicit reload command
            
            # Check which files were modified
            needs_restart = []
            auto_reloads = []
            
            for file in files_modified:
                if 'config.txt' in file:
                    # Most config.txt changes reload automatically
                    auto_reloads.append(file)
                elif 'recvpackets.txt' in file:
                    # Packet definitions need restart
                    needs_restart.append(file)
            
            return {
                'success': True,
                'auto_reloaded': auto_reloads,
                'needs_restart': needs_restart,
                'restart_required': len(needs_restart) > 0
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class ExecutionAgent:
    """Wrapper for Execution Agent"""
    pass


def create_execution_agent(config: Dict, execution_config: Dict) -> Agent:
    """Create the Execution Agent for safe fix application"""
    
    tools = [
        SafeFileModifierTool(execution_config=execution_config),
        HotReloadTriggerTool()
    ]
    
    agent = Agent(
        role=config['role'],
        goal=config['goal'],
        backstory=config['backstory'],
        tools=tools,
        verbose=config.get('verbose', True),
        allow_delegation=False,  # Executor doesn't delegate
        max_iter=10,
        memory=True
    )
    
    return agent
