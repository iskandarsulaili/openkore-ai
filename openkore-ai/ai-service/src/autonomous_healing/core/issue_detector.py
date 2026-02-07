"""
Issue detection from log patterns
"""

import re
from typing import List, Dict, Any
from collections import Counter


class IssueDetector:
    """
    Detects specific issue patterns in OpenKore logs
    Uses regex patterns and heuristics to identify problems
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.patterns = config['patterns']
        self.thresholds = config['thresholds']
        
        # Track issue frequency for threshold-based detection
        self.issue_counts = Counter()
    
    def scan_log_file(self, log_path: str) -> List[Dict]:
        """Scan entire log file for issues"""
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        return self.scan_lines(lines)
    
    def scan_lines(self, lines: List[str]) -> List[Dict]:
        """Scan list of log lines for issues"""
        detected_issues = []
        
        for line_num, line in enumerate(lines, 1):
            # Check each pattern
            for issue_name, pattern in self.patterns.items():
                match = re.search(pattern, line)
                if match:
                    issue = {
                        'type': issue_name,
                        'line_number': line_num,
                        'line_content': line.strip(),
                        'matched_groups': match.groups() if match.groups() else None,
                        'severity': self._determine_severity(issue_name)
                    }
                    
                    # Add specific context based on issue type
                    if issue_name == 'packet_unknown':
                        issue['packet_id'] = match.group(1)
                    
                    elif issue_name == 'position_desync':
                        issue['current_pos'] = (int(match.group(1)), int(match.group(2)))
                        issue['target_pos'] = (int(match.group(3)), int(match.group(4)))
                    
                    detected_issues.append(issue)
                    self.issue_counts[issue_name] += 1
        
        # Check for threshold-based issues
        threshold_issues = self._check_thresholds()
        detected_issues.extend(threshold_issues)
        
        return detected_issues
    
    def _determine_severity(self, issue_type: str) -> str:
        """Determine severity level of issue"""
        high_severity = [
            'death',
            'npc_interaction_failure',
            'ai_stuck_loop'
        ]
        
        if issue_type in high_severity:
            return 'HIGH'
        elif issue_type.startswith('packet_'):
            return 'LOW'
        else:
            return 'MEDIUM'
    
    def _check_thresholds(self) -> List[Dict]:
        """Check if any issue counts exceed thresholds"""
        threshold_issues = []
        
        for issue_name, threshold in self.thresholds.items():
            count_key = issue_name.replace('_max', '')
            if self.issue_counts[count_key] >= threshold:
                threshold_issues.append({
                    'type': f'{count_key}_threshold_exceeded',
                    'count': self.issue_counts[count_key],
                    'threshold': threshold,
                    'severity': 'HIGH'
                })
        
        return threshold_issues
    
    def reset_counts(self):
        """Reset issue counters"""
        self.issue_counts.clear()
