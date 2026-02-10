"""
Log Extraction Utility

Extracts relevant game events from OpenKore logs for AI decision-making:
- Character deaths
- Level ups
- Achievements
- Important events
"""

import re
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


class LogEvent:
    """Represents a parsed log event"""
    
    def __init__(self, timestamp: datetime, event_type: str, details: Dict[str, Any]):
        self.timestamp = timestamp
        self.event_type = event_type
        self.details = details
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'details': self.details
        }


class LogExtractor:
    """
    Extracts meaningful events from OpenKore logs
    
    Patterns detected:
    - Character death: "You have died"
    - Level up: "Level X"
    - EXP gain: "Gained X exp"
    - Skill learned: "Learned skill"
    - Item obtained: "Got item"
    - Status effects: "Status effect applied"
    """
    
    # Regular expression patterns for log parsing
    PATTERNS = {
        'death': re.compile(r'You have died|Your character has died', re.IGNORECASE),
        'level_up': re.compile(r'Level (\d+)', re.IGNORECASE),
        'base_level_up': re.compile(r'Base Level: (\d+)', re.IGNORECASE),
        'job_level_up': re.compile(r'Job Level: (\d+)', re.IGNORECASE),
        'exp_gained': re.compile(r'Gained (\d+) base exp', re.IGNORECASE),
        'job_exp_gained': re.compile(r'Gained (\d+) job exp', re.IGNORECASE),
        'skill_learned': re.compile(r'Learned skill (.+)', re.IGNORECASE),
        'item_obtained': re.compile(r'(?:Got item|Obtained|Picked up) (.+) \((\d+)\)', re.IGNORECASE),
        'zeny_gained': re.compile(r'Gained (\d+) zeny', re.IGNORECASE),
        'monster_killed': re.compile(r'(?:Killed|Defeated) (.+)', re.IGNORECASE),
        'quest_completed': re.compile(r'Quest (.+) (?:completed|finished)', re.IGNORECASE),
        'status_effect': re.compile(r'Status: (.+)', re.IGNORECASE),
        'teleported': re.compile(r'Teleported to (.+)', re.IGNORECASE),
        'map_change': re.compile(r'Map changed to (.+)', re.IGNORECASE)
    }
    
    def __init__(self, max_events: int = 100):
        """
        Initialize log extractor
        
        Args:
            max_events: Maximum number of events to keep in memory
        """
        self.max_events = max_events
        self.events: deque[LogEvent] = deque(maxlen=max_events)
    
    def parse_line(self, line: str, timestamp: Optional[datetime] = None) -> Optional[LogEvent]:
        """
        Parse a single log line and extract event if present
        
        Args:
            line: Log line to parse
            timestamp: Optional timestamp (extracted from log or current time)
            
        Returns:
            LogEvent if event found, None otherwise
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        line = line.strip()
        if not line:
            return None
        
        # Try to extract timestamp from log line if present
        # Common format: [2026-02-09 22:00:00] Message
        timestamp_match = re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
        if timestamp_match:
            try:
                timestamp = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                line = line[timestamp_match.end():].strip()
            except ValueError:
                pass
        
        # Check each pattern
        for event_type, pattern in self.PATTERNS.items():
            match = pattern.search(line)
            if match:
                details = self._extract_details(event_type, match, line)
                return LogEvent(timestamp, event_type, details)
        
        return None
    
    def _extract_details(self, event_type: str, match: re.Match, line: str) -> Dict[str, Any]:
        """Extract detailed information based on event type"""
        details = {'raw_message': line}
        
        if event_type == 'death':
            details['death_count'] = 1
            
        elif event_type in ['level_up', 'base_level_up']:
            details['new_level'] = int(match.group(1))
            
        elif event_type == 'job_level_up':
            details['new_job_level'] = int(match.group(1))
            
        elif event_type == 'exp_gained':
            details['exp_amount'] = int(match.group(1))
            
        elif event_type == 'job_exp_gained':
            details['job_exp_amount'] = int(match.group(1))
            
        elif event_type == 'skill_learned':
            details['skill_name'] = match.group(1).strip()
            
        elif event_type == 'item_obtained':
            details['item_name'] = match.group(1).strip()
            details['quantity'] = int(match.group(2)) if match.lastindex >= 2 else 1
            
        elif event_type == 'zeny_gained':
            details['zeny_amount'] = int(match.group(1))
            
        elif event_type == 'monster_killed':
            details['monster_name'] = match.group(1).strip()
            
        elif event_type == 'quest_completed':
            details['quest_name'] = match.group(1).strip()
            
        elif event_type == 'status_effect':
            details['status_name'] = match.group(1).strip()
            
        elif event_type in ['teleported', 'map_change']:
            details['destination'] = match.group(1).strip()
        
        return details
    
    def extract_from_file(
        self,
        log_file: Path,
        lookback_minutes: int = 60,
        max_lines: int = 1000
    ) -> List[LogEvent]:
        """
        Extract events from log file
        
        Args:
            log_file: Path to log file
            lookback_minutes: Only extract events from last N minutes
            max_lines: Maximum lines to read (from end of file)
            
        Returns:
            List of extracted events
        """
        if not log_file.exists():
            logger.warning(f"Log file not found: {log_file}")
            return []
        
        try:
            # Read last N lines efficiently
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                # Seek to end and read backwards
                lines = deque(maxlen=max_lines)
                for line in f:
                    lines.append(line)
            
            # Parse lines
            events = []
            cutoff_time = datetime.now() - timedelta(minutes=lookback_minutes)
            
            for line in lines:
                event = self.parse_line(line)
                if event and event.timestamp >= cutoff_time:
                    events.append(event)
                    self.events.append(event)
            
            logger.info(f"Extracted {len(events)} events from {log_file.name}")
            return events
            
        except Exception as e:
            logger.error(f"Error extracting from log file: {e}")
            return []
    
    def extract_from_directory(
        self,
        log_dir: Path,
        lookback_minutes: int = 60,
        file_pattern: str = "*.log"
    ) -> List[LogEvent]:
        """
        Extract events from all log files in directory
        
        Args:
            log_dir: Directory containing log files
            lookback_minutes: Only extract events from last N minutes
            file_pattern: Glob pattern for log files
            
        Returns:
            List of extracted events from all files
        """
        if not log_dir.exists():
            logger.warning(f"Log directory not found: {log_dir}")
            return []
        
        all_events = []
        for log_file in log_dir.glob(file_pattern):
            events = self.extract_from_file(log_file, lookback_minutes)
            all_events.extend(events)
        
        # Sort by timestamp
        all_events.sort(key=lambda e: e.timestamp)
        
        return all_events
    
    def get_recent_events(
        self,
        event_types: Optional[List[str]] = None,
        lookback_minutes: int = 60,
        limit: int = 50
    ) -> List[LogEvent]:
        """
        Get recent events from memory
        
        Args:
            event_types: Filter by event types (None = all types)
            lookback_minutes: Only return events from last N minutes
            limit: Maximum number of events to return
            
        Returns:
            List of recent events
        """
        cutoff_time = datetime.now() - timedelta(minutes=lookback_minutes)
        
        filtered = [
            event for event in self.events
            if event.timestamp >= cutoff_time
            and (event_types is None or event.event_type in event_types)
        ]
        
        # Return most recent first
        filtered.reverse()
        return filtered[:limit]
    
    def get_event_summary(self, lookback_minutes: int = 60) -> Dict[str, Any]:
        """
        Get summary statistics of recent events
        
        Args:
            lookback_minutes: Time window for summary
            
        Returns:
            Summary dictionary with event counts and important metrics
        """
        recent_events = self.get_recent_events(lookback_minutes=lookback_minutes)
        
        summary = {
            'total_events': len(recent_events),
            'event_counts': {},
            'deaths': 0,
            'level_ups': 0,
            'exp_gained': 0,
            'zeny_gained': 0,
            'items_obtained': 0,
            'skills_learned': [],
            'quests_completed': [],
            'recent_maps': []
        }
        
        for event in recent_events:
            # Count by type
            event_type = event.event_type
            summary['event_counts'][event_type] = summary['event_counts'].get(event_type, 0) + 1
            
            # Aggregate specific metrics
            if event_type == 'death':
                summary['deaths'] += 1
            
            elif event_type in ['level_up', 'base_level_up', 'job_level_up']:
                summary['level_ups'] += 1
            
            elif event_type == 'exp_gained':
                summary['exp_gained'] += event.details.get('exp_amount', 0)
            
            elif event_type == 'zeny_gained':
                summary['zeny_gained'] += event.details.get('zeny_amount', 0)
            
            elif event_type == 'item_obtained':
                summary['items_obtained'] += event.details.get('quantity', 1)
            
            elif event_type == 'skill_learned':
                skill = event.details.get('skill_name')
                if skill and skill not in summary['skills_learned']:
                    summary['skills_learned'].append(skill)
            
            elif event_type == 'quest_completed':
                quest = event.details.get('quest_name')
                if quest and quest not in summary['quests_completed']:
                    summary['quests_completed'].append(quest)
            
            elif event_type in ['teleported', 'map_change']:
                map_name = event.details.get('destination')
                if map_name and map_name not in summary['recent_maps']:
                    summary['recent_maps'].append(map_name)
        
        return summary
    
    def add_to_character_context(
        self,
        character_context: Dict[str, Any],
        lookback_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Enhance character context with recent log events
        
        Args:
            character_context: Existing character context dictionary
            lookback_minutes: How far back to look for events
            
        Returns:
            Enhanced character context with log-derived data
        """
        summary = self.get_event_summary(lookback_minutes)
        
        # Add event summary to context
        character_context['recent_events'] = {
            'lookback_minutes': lookback_minutes,
            'summary': summary,
            'last_updated': datetime.now().isoformat()
        }
        
        # Add specific alerts for critical events
        if summary['deaths'] > 0:
            character_context['recent_deaths'] = summary['deaths']
            character_context['high_risk_indicator'] = True
        
        if summary['level_ups'] > 0:
            character_context['recent_level_ups'] = summary['level_ups']
        
        # Add performance indicators
        character_context['recent_performance'] = {
            'exp_per_minute': summary['exp_gained'] / lookback_minutes if lookback_minutes > 0 else 0,
            'zeny_per_minute': summary['zeny_gained'] / lookback_minutes if lookback_minutes > 0 else 0,
            'death_rate': summary['deaths'] / (lookback_minutes / 60.0) if lookback_minutes > 0 else 0  # deaths per hour
        }
        
        return character_context


# Global instance
_log_extractor = LogExtractor()


def get_log_extractor() -> LogExtractor:
    """Get global log extractor instance"""
    return _log_extractor


def extract_recent_logs(
    log_path: Optional[Path] = None,
    lookback_minutes: int = 30
) -> List[LogEvent]:
    """
    Convenience function to extract recent log events
    
    Args:
        log_path: Path to log file or directory (defaults to ../logs)
        lookback_minutes: Time window for extraction
        
    Returns:
        List of recent events
    """
    extractor = get_log_extractor()
    
    if log_path is None:
        # Default to logs directory
        log_path = Path(__file__).parent.parent.parent / "logs"
    
    if log_path.is_dir():
        return extractor.extract_from_directory(log_path, lookback_minutes)
    elif log_path.is_file():
        return extractor.extract_from_file(log_path, lookback_minutes)
    else:
        logger.warning(f"Invalid log path: {log_path}")
        return []


if __name__ == "__main__":
    # Test log extraction
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Test parsing
    extractor = LogExtractor()
    
    test_lines = [
        "[2026-02-09 22:00:00] You have died",
        "[2026-02-09 22:05:00] Base Level: 50",
        "[2026-02-09 22:06:00] Gained 1500 base exp",
        "[2026-02-09 22:07:00] Got item Red Potion (10)",
        "[2026-02-09 22:08:00] Gained 500 zeny",
        "[2026-02-09 22:09:00] Killed Poring",
        "[2026-02-09 22:10:00] Quest Poring Hunt completed"
    ]
    
    print("\n=== Testing Log Parsing ===\n")
    for line in test_lines:
        event = extractor.parse_line(line)
        if event:
            print(f"Event: {event.event_type}")
            print(f"  Timestamp: {event.timestamp}")
            print(f"  Details: {event.details}")
            print()
    
    # Test summary
    print("\n=== Event Summary ===\n")
    summary = extractor.get_event_summary(lookback_minutes=60)
    print(f"Total events: {summary['total_events']}")
    print(f"Deaths: {summary['deaths']}")
    print(f"Level ups: {summary['level_ups']}")
    print(f"EXP gained: {summary['exp_gained']}")
    print(f"Zeny gained: {summary['zeny_gained']}")
    print(f"Items obtained: {summary['items_obtained']}")
    print(f"Quests completed: {summary['quests_completed']}")
