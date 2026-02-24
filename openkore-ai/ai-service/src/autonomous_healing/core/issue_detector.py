"""
Issue detection from log patterns
"""

import re
import logging
from typing import List, Dict, Any, Optional
from collections import Counter
from pathlib import Path


class IssueDetector:
    """
    Detects specific issue patterns in OpenKore logs
    Uses regex patterns and heuristics to identify problems
    Enhanced for Phase 31 OpenKore critical issues
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.patterns = config['patterns']
        self.thresholds = config['thresholds']
        
        # Track issue frequency for threshold-based detection
        self.issue_counts = Counter()
        
        # Setup logging
        self.logger = logging.getLogger('autonomous_healing.issue_detector')
        
        # Track context for multi-pattern detection
        self.context = {
            'recent_deaths': [],
            'healing_items': {},
            'stat_points': 0,
            'hp_at_death': 0,
            'teleport_errors': 0,
            'config_values': {}
        }
    
    def scan_log_file(self, log_path: str) -> List[Dict]:
        """Scan entire log file for issues"""
        self.logger.info(f"Scanning log file: {log_path}")
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            issues = self.scan_lines(lines)
            self.logger.info(f"Detected {len(issues)} issues in {log_path}")
            return issues
        except Exception as e:
            self.logger.error(f"Failed to scan log file: {e}")
            return []
    
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
                    
                    # Phase 31: OpenKore critical issue context
                    elif issue_name == 'teleport_no_skill':
                        self.context['teleport_errors'] += 1
                        issue['context'] = 'teleportAuto enabled without Teleport skill/Fly Wings'
                        self.logger.warning(f"Teleport spam detected: {self.context['teleport_errors']} occurrences")
                    
                    elif issue_name == 'healing_item_in_inventory':
                        item_name = match.group(1)
                        item_count = int(match.group(2))
                        if 'Apple' in item_name or 'Potion' in item_name:
                            self.context['healing_items'][item_name] = item_count
                            issue['context'] = f'Healing item available: {item_name} x{item_count}'
                    
                    elif issue_name == 'stat_points_available':
                        points = int(match.group(1))
                        self.context['stat_points'] = points
                        issue['context'] = f'{points} unspent stat points'
                    
                    elif issue_name == 'hp_percent_status':
                        current_hp = int(match.group(1))
                        max_hp = int(match.group(2))
                        hp_percent = int(match.group(3))
                        issue['hp_info'] = {'current': current_hp, 'max': max_hp, 'percent': hp_percent}
                        
                        # Check if death occurred near this line
                        if self._check_death_near(lines, line_num):
                            self.context['hp_at_death'] = hp_percent
                            issue['context'] = f'Death occurred at {hp_percent}% HP'
                    
                    elif issue_name == 'death':
                        self.context['recent_deaths'].append(line_num)
                        # Check for healing items in context
                        if self.context['healing_items']:
                            issue['critical'] = True
                            issue['context'] = f"Death with unused healing items: {list(self.context['healing_items'].keys())}"
                            self.logger.critical(f"Bot died with healing items in inventory!")
                    
                    detected_issues.append(issue)
                    self.issue_counts[issue_name] += 1
        
        # Check for threshold-based issues
        threshold_issues = self._check_thresholds()
        detected_issues.extend(threshold_issues)
        
        # Analyze for complex multi-pattern issues
        complex_issues = self._detect_complex_issues()
        detected_issues.extend(complex_issues)
        
        return detected_issues
    
    def _determine_severity(self, issue_type: str) -> str:
        """Determine severity level of issue"""
        # Critical severity (Phase 31 issues)
        critical_severity = [
            'teleport_no_skill',
            'death'
        ]
        
        high_severity = [
            'npc_interaction_failure',
            'ai_stuck_loop',
            'healing_item_in_inventory',
            'stat_points_available'
        ]
        
        if issue_type in critical_severity:
            return 'CRITICAL'
        elif issue_type in high_severity:
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
    
    def _check_death_near(self, lines: List[str], current_line: int, window: int = 5) -> bool:
        """Check if death occurred near the current line"""
        death_pattern = self.patterns.get('death', r'\[DEAD\]')
        for i in range(max(0, current_line - window), min(len(lines), current_line + window)):
            if re.search(death_pattern, lines[i]):
                return True
        return False
    
    def _detect_complex_issues(self) -> List[Dict]:
        """Detect complex issues requiring multiple pattern correlations"""
        complex_issues = []
        
        # Issue 1: Missing auto-heal (death with healing items)
        if self.context['recent_deaths'] and self.context['healing_items']:
            complex_issues.append({
                'type': 'missing_auto_heal',
                'severity': 'CRITICAL',
                'description': 'Bot died with healing items in inventory - useSelf_item not configured',
                'healing_items': list(self.context['healing_items'].keys()),
                'death_count': len(self.context['recent_deaths']),
                'confidence': 0.95
            })
            self.logger.critical("CRITICAL: Missing auto-heal configuration detected!")
        
        # Issue 2: Teleport spam
        if self.context['teleport_errors'] >= self.thresholds.get('teleport_spam_max', 5):
            complex_issues.append({
                'type': 'teleport_spam',
                'severity': 'CRITICAL',
                'description': 'teleportAuto configured but no Teleport skill/Fly Wings available',
                'error_count': self.context['teleport_errors'],
                'confidence': 0.98
            })
            self.logger.critical("CRITICAL: Teleport spam detected - bot lacks teleport capability!")
        
        # Issue 3: Unspent stat points
        if self.context['stat_points'] > 0:
            complex_issues.append({
                'type': 'unspent_stat_points',
                'severity': 'HIGH',
                'description': f"{self.context['stat_points']} stat points not allocated - statsAddAuto likely disabled",
                'stat_points': self.context['stat_points'],
                'confidence': 0.90
            })
            self.logger.warning(f"Unspent stat points detected: {self.context['stat_points']}")
        
        return complex_issues
    
    def scan_config_file(self, config_path: str) -> List[Dict]:
        """Scan config.txt for configuration issues"""
        self.logger.info(f"Scanning config file: {config_path}")
        config_issues = []
        
        try:
            with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # CRITICAL: Check for empty/missing lockMap (most common cause of idle bot)
            lockmap_match = re.search(r'^lockMap\s*$', content, re.MULTILINE)
            lockmap_with_value = re.search(r'^lockMap\s+(\S+)', content, re.MULTILINE)
            lockmap_x = re.search(r'^lockMap_x\s*$', content, re.MULTILINE)
            lockmap_y = re.search(r'^lockMap_y\s*$', content, re.MULTILINE)
            lockmap_x_with_value = re.search(r'^lockMap_x\s+\d+\s+\d+', content, re.MULTILINE)
            lockmap_y_with_value = re.search(r'^lockMap_y\s+\d+\s+\d+', content, re.MULTILINE)
            
            # Check multiple failure scenarios:
            # 1. lockMap line exists but is empty
            # 2. lockMap_x or lockMap_y exist but are empty
            # 3. lockMap has value but coordinates are missing
            has_lockmap_issues = False
            lockmap_issue_reason = ""
            
            if lockmap_match:
                has_lockmap_issues = True
                lockmap_issue_reason = "lockMap is empty"
            elif lockmap_x and lockmap_y:
                has_lockmap_issues = True
                lockmap_issue_reason = "lockMap coordinates (lockMap_x, lockMap_y) are empty"
            elif lockmap_with_value and (not lockmap_x_with_value or not lockmap_y_with_value):
                has_lockmap_issues = True
                lockmap_issue_reason = f"lockMap is set to '{lockmap_with_value.group(1)}' but coordinates are missing"
            
            if has_lockmap_issues:
                config_issues.append({
                    'type': 'lockMap_empty',
                    'severity': 'CRITICAL',
                    'description': f'lockMap is not fully configured - {lockmap_issue_reason} - bot has no farming area and will remain idle',
                    'confidence': 0.99,
                    'fix_required': 'Set lockMap to appropriate map for character level',
                    'recommended_fix': 'lockMap prt_fild08'
                })
                self.logger.critical(f"CRITICAL: lockMap configuration incomplete - {lockmap_issue_reason} - bot cannot farm!")
            
            # Issue 3: Inappropriate sitAuto threshold
            sitauto_match = re.search(r'sitAuto_hp_lower\s+(\d+)', content)
            if sitauto_match:
                threshold = int(sitauto_match.group(1))
                if threshold > 70:  # Too cautious for low-level bot
                    config_issues.append({
                        'type': 'inappropriate_sitAuto_threshold',
                        'severity': 'MEDIUM',
                        'description': f'sitAuto_hp_lower {threshold} is too high (cautious) for efficient farming',
                        'current_value': threshold,
                        'recommended_value': 50,
                        'confidence': 0.85
                    })
                    self.logger.warning(f"Inappropriate sitAuto threshold: {threshold}")
            
            # Issue 4: Inefficient lockMap range (only check if lockMap has values)
            lockmap_x_vals = re.search(r'lockMap_x\s+(\d+)\s+(\d+)', content)
            lockmap_y_vals = re.search(r'lockMap_y\s+(\d+)\s+(\d+)', content)
            if lockmap_x_vals and lockmap_y_vals:
                x_range = int(lockmap_x_vals.group(2)) - int(lockmap_x_vals.group(1))
                y_range = int(lockmap_y_vals.group(2)) - int(lockmap_y_vals.group(1))
                total_area = x_range * y_range
                
                if total_area > 15000:  # Too large (e.g., 150*150 = 22500)
                    config_issues.append({
                        'type': 'inefficient_lockMap',
                        'severity': 'MEDIUM',
                        'description': f'lockMap area {total_area} sq units is too large for efficient farming',
                        'current_area': total_area,
                        'x_range': x_range,
                        'y_range': y_range,
                        'recommended_max': 10000,
                        'confidence': 0.80
                    })
                    self.logger.warning(f"Inefficient lockMap size: {total_area} sq units")
            
            # PHASE 11 ENHANCEMENT: Check attackAuto disabled (bot won't farm)
            attackauto_match = re.search(r'attackAuto\s+(\d+)', content)
            if attackauto_match:
                attack_value = int(attackauto_match.group(1))
                if attack_value == 0:
                    config_issues.append({
                        'type': 'attackAuto_disabled',
                        'severity': 'CRITICAL',
                        'description': 'Combat is disabled (attackAuto: 0) - bot will NOT attack monsters or farm',
                        'current_value': 0,
                        'recommended_value': 2,
                        'confidence': 0.99,
                        'fix_required': 'Set attackAuto 2 for aggressive auto-attack',
                        'recommended_fix': 'attackAuto 2',
                        'impact': 'Bot cannot attack monsters - 0 farming capability'
                    })
                    self.logger.critical("[SELF-HEAL] CRITICAL: Combat disabled (attackAuto: 0) - Recommending fix: attackAuto 2")
            
            # PHASE 11 ENHANCEMENT: Check route_randomWalk disabled (bot won't seek monsters)
            randomwalk_match = re.search(r'route_randomWalk\s+(\d+)', content)
            if randomwalk_match:
                walk_value = int(randomwalk_match.group(1))
                if walk_value == 0:
                    config_issues.append({
                        'type': 'route_randomWalk_disabled',
                        'severity': 'HIGH',
                        'description': 'Random walk disabled (route_randomWalk: 0) - bot will NOT actively seek monsters',
                        'current_value': 0,
                        'recommended_value': 1,
                        'confidence': 0.95,
                        'fix_required': 'Set route_randomWalk 1 to enable active monster seeking',
                        'recommended_fix': 'route_randomWalk 1',
                        'impact': 'Bot won\'t explore map to find monsters'
                    })
                    self.logger.warning("[SELF-HEAL] HIGH: Exploration disabled (route_randomWalk: 0) - Recommending fix: route_randomWalk 1")
            
            # Issue 5: statsAddAuto disabled
            statsadd_match = re.search(r'statsAddAuto\s+(\d+)', content)
            if statsadd_match and int(statsadd_match.group(1)) == 0:
                config_issues.append({
                    'type': 'statsAddAuto_disabled',
                    'severity': 'HIGH',
                    'description': 'statsAddAuto is disabled (0) - stat points will not be allocated',
                    'current_value': 0,
                    'recommended_value': 1,
                    'confidence': 0.90
                })
                self.logger.warning("statsAddAuto is disabled")
            
            # Issue 2: teleportAuto with low HP
            teleport_hp = re.search(r'teleportAuto_hp\s+(\d+)', content)
            if teleport_hp:
                hp_threshold = int(teleport_hp.group(1))
                if hp_threshold <= 15 and self.context['teleport_errors'] > 0:
                    config_issues.append({
                        'type': 'teleportAuto_misconfigured',
                        'severity': 'CRITICAL',
                        'description': f'teleportAuto_hp {hp_threshold} enabled but bot has no teleport capability',
                        'current_value': hp_threshold,
                        'teleport_errors': self.context['teleport_errors'],
                        'confidence': 0.95
                    })
                    self.logger.critical(f"teleportAuto misconfigured: hp={hp_threshold}, errors={self.context['teleport_errors']}")
            
            # Issue 1: Check for missing useSelf_item blocks
            healing_items_in_config = re.findall(r'useSelf_item\s+([^\s]+)', content)
            if not healing_items_in_config and self.context['healing_items']:
                config_issues.append({
                    'type': 'missing_useSelf_item',
                    'severity': 'CRITICAL',
                    'description': 'No useSelf_item configuration found but healing items in inventory',
                    'available_items': list(self.context['healing_items'].keys()),
                    'confidence': 0.95
                })
                self.logger.critical("Missing useSelf_item configuration!")
            
            self.logger.info(f"Detected {len(config_issues)} configuration issues")
            return config_issues
            
        except Exception as e:
            self.logger.error(f"Failed to scan config file: {e}")
            return []
    
    def reset_counts(self):
        """Reset issue counters and context"""
        self.issue_counts.clear()
        self.context = {
            'recent_deaths': [],
            'healing_items': {},
            'stat_points': 0,
            'hp_at_death': 0,
            'teleport_errors': 0,
            'config_values': {}
        }
        self.logger.debug("Issue detector context reset")
