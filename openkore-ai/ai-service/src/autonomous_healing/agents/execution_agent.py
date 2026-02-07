"""
Execution Agent - Safe Fix Application
Applies fixes with backup, rollback, and hot-reload capabilities
Enhanced for Phase 31 OpenKore critical issues
"""

from crewai import Agent
from crewai.tools import BaseTool
from typing import Dict, List, Any
from pathlib import Path
import shutil
from datetime import datetime
import re
import logging
from pydantic import ConfigDict


class SafeFileModifierTool(BaseTool):
    """Tool for safely modifying configuration files"""
    
    model_config = ConfigDict(
        extra='allow',
        arbitrary_types_allowed=True
    )
    
    name: str = "safe_file_modifier"
    description: str = "Safely modify OpenKore config files with automatic backup and rollback"
    
    def __init__(self, execution_config: Dict):
        super().__init__()
        self.config = execution_config
        self.backup_dir = Path(execution_config['backup']['directory'])
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger('autonomous_healing.execution_agent')
    
    def _create_backup(self, file_path: Path) -> Path:
        """Create timestamped backup of file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(file_path, backup_path)
        self.logger.info(f"Created backup: {backup_path}")
        return backup_path
    
    def _apply_changes(self, file_path: Path, changes: List[Dict]) -> bool:
        """Apply list of changes to file with enhanced change types"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            modified_content = content
            changes_applied = 0
            
            for idx, change in enumerate(changes, 1):
                change_type = change['type']
                reason = change.get('reason', 'No reason provided')
                
                self.logger.debug(f"Applying change {idx}/{len(changes)}: {change_type} - {reason}")
                
                if change_type == 'replace':
                    pattern = change['pattern']
                    replacement = change['replacement']
                    
                    # Check if pattern exists before replacing
                    if re.search(pattern, modified_content):
                        modified_content = re.sub(pattern, replacement, modified_content)
                        changes_applied += 1
                        self.logger.info(f"Applied replace: {pattern[:50]}... -> {replacement[:50]}...")
                    else:
                        self.logger.warning(f"Pattern not found for replace: {pattern[:50]}...")
                
                elif change_type == 'append':
                    # Simple append to end of file
                    append_content = change.get('content', '')
                    if append_content:
                        modified_content += append_content
                        changes_applied += 1
                        self.logger.info(f"Appended content: {append_content[:50]}...")
                    else:
                        self.logger.warning("No content provided for append")
                
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
                        changes_applied += 1
                        self.logger.info(f"Updated existing key: {key}")
                    else:
                        # Append new
                        modified_content += f"\n{key} {value}\n"
                        changes_applied += 1
                        self.logger.info(f"Appended new key: {key}")
                
                elif change_type == 'append_if_missing':
                    key = change.get('key', '')
                    content_to_add = change.get('content', '')
                    
                    # Check if key already exists
                    if key and not re.search(f"^{re.escape(key)}", modified_content, re.MULTILINE):
                        modified_content += content_to_add
                        changes_applied += 1
                        self.logger.info(f"Appended missing key: {key}")
                    else:
                        self.logger.debug(f"Key already exists, skipping: {key}")
                
                elif change_type == 'comment':
                    # Add comment before a pattern
                    pattern = change.get('pattern', '')
                    comment = change.get('comment', '')
                    
                    if pattern and comment:
                        # Find the pattern and add comment before it
                        lines = modified_content.split('\n')
                        new_lines = []
                        for line in lines:
                            if re.search(pattern, line) and comment not in modified_content:
                                new_lines.append(comment)
                                changes_applied += 1
                                self.logger.info(f"Added comment: {comment}")
                            new_lines.append(line)
                        modified_content = '\n'.join(new_lines)
                
                else:
                    self.logger.warning(f"Unknown change type: {change_type}")
            
            # Write modified content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            self.logger.info(f"Successfully applied {changes_applied}/{len(changes)} changes to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to apply changes: {e}", exc_info=True)
            raise Exception(f"Failed to apply changes: {e}")
    
    def _run(self, file_path: str, changes: List[Dict], require_approval: bool = False) -> Dict[str, Any]:
        """Safely modify file with backup and validation"""
        try:
            # Convert to absolute path if relative
            if not Path(file_path).is_absolute():
                # Assume relative to openkore-ai directory
                file_path = str(Path('openkore-ai') / file_path) if 'openkore-ai' not in file_path else file_path
            
            file_path = Path(file_path)
            
            self.logger.info(f"Starting safe file modification: {file_path}")
            self.logger.info(f"Number of changes to apply: {len(changes)}")
            
            if not file_path.exists():
                self.logger.error(f"File not found: {file_path}")
                return {'success': False, 'error': f'File not found: {file_path}'}
            
            # Create backup
            backup_path = self._create_backup(file_path)
            
            try:
                # Apply changes
                self._apply_changes(file_path, changes)
                
                self.logger.info(f"Successfully modified {file_path}")
                
                # Validate the modified file (basic syntax check)
                validation_result = self._validate_config_file(file_path)
                
                if not validation_result['valid']:
                    self.logger.error(f"Validation failed: {validation_result['error']}")
                    # Restore from backup
                    shutil.copy2(backup_path, file_path)
                    self.logger.warning("Rolled back changes due to validation failure")
                    return {
                        'success': False,
                        'error': f"Validation failed: {validation_result['error']}",
                        'rollback_performed': True
                    }
                
                return {
                    'success': True,
                    'file_modified': str(file_path),
                    'backup_created': str(backup_path),
                    'changes_applied': len(changes),
                    'validation': 'passed'
                }
                
            except Exception as e:
                # Restore from backup on failure
                self.logger.error(f"Error applying changes: {e}", exc_info=True)
                shutil.copy2(backup_path, file_path)
                self.logger.warning("Rolled back changes due to error")
                return {
                    'success': False,
                    'error': str(e),
                    'rollback_performed': True
                }
        
        except Exception as e:
            self.logger.error(f"Critical error in safe file modifier: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _validate_config_file(self, file_path: Path) -> Dict[str, Any]:
        """Basic validation of OpenKore config.txt syntax"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for common syntax errors
            errors = []
            
            # Check for unmatched braces
            open_braces = content.count('{')
            close_braces = content.count('}')
            if open_braces != close_braces:
                errors.append(f"Unmatched braces: {open_braces} open, {close_braces} close")
            
            # Check for lines that might be malformed
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                stripped = line.strip()
                # Skip empty lines and comments
                if not stripped or stripped.startswith('#'):
                    continue
                
                # Check for lines with only a key and no value (except blocks)
                if not stripped.endswith('{') and not stripped.endswith('}'):
                    parts = stripped.split(None, 1)
                    if len(parts) == 1 and parts[0] not in ['saveMap', 'lockMap']:
                        # This might be intentional for some settings, so just log warning
                        self.logger.debug(f"Line {line_num}: Key without value: {parts[0]}")
            
            if errors:
                return {'valid': False, 'error': '; '.join(errors)}
            
            return {'valid': True}
            
        except Exception as e:
            return {'valid': False, 'error': f'Validation error: {e}'}


class HotReloadTriggerTool(BaseTool):
    """Tool for triggering OpenKore config hot-reload"""
    
    model_config = ConfigDict(
        extra='allow',
        arbitrary_types_allowed=True
    )
    
    name: str = "hot_reload"
    description: str = "Trigger OpenKore to reload configuration without restarting"
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('autonomous_healing.hot_reload')
    
    def _run(self, files_modified: List[str]) -> Dict[str, Any]:
        """Trigger hot-reload mechanism"""
        try:
            self.logger.info(f"Checking hot-reload requirements for {len(files_modified)} files")
            
            # For OpenKore, some configs reload automatically
            # Others may need explicit reload command
            
            # Check which files were modified
            needs_restart = []
            auto_reloads = []
            
            for file in files_modified:
                if 'config.txt' in file:
                    # Most config.txt changes reload automatically
                    auto_reloads.append(file)
                    self.logger.info(f"Auto-reload: {file}")
                elif 'recvpackets.txt' in file:
                    # Packet definitions need restart
                    needs_restart.append(file)
                    self.logger.warning(f"Restart required: {file}")
            
            result = {
                'success': True,
                'auto_reloaded': auto_reloads,
                'needs_restart': needs_restart,
                'restart_required': len(needs_restart) > 0
            }
            
            if result['restart_required']:
                self.logger.warning("Manual restart required for some changes to take effect")
            else:
                self.logger.info("All changes will auto-reload")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Hot-reload check failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }


class ExecutionAgent:
    """Wrapper for Execution Agent"""
    pass


def create_execution_agent(config: Dict, execution_config: Dict, llm) -> Agent:
    """
    Create the Execution Agent for safe fix application
    
    Args:
        config: Agent configuration
        execution_config: Execution-specific configuration
        llm: LLM instance (DeepSeek via provider chain)
        
    Returns:
        Configured CrewAI Agent
    """
    
    tools = [
        SafeFileModifierTool(execution_config=execution_config),
        HotReloadTriggerTool()
    ]
    
    # Create agent with DeepSeek LLM
    agent = Agent(
        role=config['role'],
        goal=config['goal'],
        backstory=config['backstory'],
        tools=tools,
        verbose=config.get('verbose', True),
        allow_delegation=False,  # Executor doesn't delegate
        max_iter=10,
        memory=True,
        llm=llm  # Use DeepSeek LLM
    )
    
    return agent
