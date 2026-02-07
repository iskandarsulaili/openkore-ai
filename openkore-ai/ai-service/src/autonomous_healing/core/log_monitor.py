"""
Real-time log monitoring with tail-f style watching
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import re
from datetime import datetime


class LogMonitor:
    """
    Monitors OpenKore log files in real-time for new entries
    Implements efficient tail-f style reading
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.log_dir = Path(config['log_directory'])
        self.poll_interval = config['poll_interval_seconds']
        self.watch_patterns = config['watch_patterns']
        
        # Track file positions for tail-f behavior
        self.file_positions = {}
        self.last_check = datetime.now()
    
    async def check_for_issues(self) -> List[Dict]:
        """Check all monitored logs for new issues"""
        all_issues = []
        
        # Find log files matching patterns
        log_files = self._find_log_files()
        
        for log_file in log_files:
            new_lines = await self._read_new_lines(log_file)
            
            if new_lines:
                # Return new lines for analysis
                all_issues.append({
                    'file': str(log_file),
                    'new_lines': new_lines,
                    'timestamp': datetime.now().isoformat()
                })
        
        return all_issues
    
    def _find_log_files(self) -> List[Path]:
        """Find all log files matching watch patterns"""
        log_files = []
        
        for pattern in self.watch_patterns:
            log_files.extend(self.log_dir.glob(pattern))
        
        return sorted(log_files, key=lambda f: f.stat().st_mtime, reverse=True)
    
    async def _read_new_lines(self, log_file: Path) -> List[str]:
        """Read only new lines from log file (tail -f behavior)"""
        try:
            file_key = str(log_file)
            
            # Get current file size
            current_size = log_file.stat().st_size
            
            # Initialize or get last position
            last_pos = self.file_positions.get(file_key, 0)
            
            # If file was truncated/rotated, reset position
            if current_size < last_pos:
                last_pos = 0
            
            # No new content
            if current_size == last_pos:
                return []
            
            # Read new content
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(last_pos)
                new_content = f.read()
                new_pos = f.tell()
            
            # Update position
            self.file_positions[file_key] = new_pos
            
            # Split into lines
            new_lines = new_content.strip().split('\n') if new_content.strip() else []
            
            return new_lines
            
        except Exception as e:
            print(f"Error reading {log_file}: {e}")
            return []
    
    def reset_position(self, log_file: Optional[Path] = None):
        """Reset file position tracking (useful for debugging)"""
        if log_file:
            self.file_positions.pop(str(log_file), None)
        else:
            self.file_positions.clear()
