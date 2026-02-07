"""Root Cause Analysis - Correlate errors with configuration"""

from typing import Dict, List, Any
from pathlib import Path
import re


class RootCauseAnalyzer:
    """Analyzes issues to determine root causes"""
    
    def __init__(self):
        self.correlation_rules = []
    
    def analyze(self, issue: Dict, config_content: str, context: Dict) -> Dict[str, Any]:
        """Perform root cause analysis"""
        
        root_causes = []
        
        issue_type = issue.get('type')
        
        # NPC-related issues
        if issue_type in ['npc_not_found', 'npc_no_response']:
            # Check if buyAuto is configured
            buyauto_match = re.search(r'buyAuto.*?\{([^}]+)\}', config_content, re.DOTALL)
            if buyauto_match:
                block_content = buyauto_match.group(1)
                
                # Check if NPC is defined
                if re.search(r'npc\s*$', block_content, re.MULTILINE):
                    root_causes.append({
                        'cause': 'buyAuto_undefined_npc',
                        'confidence': 0.95,
                        'evidence': 'buyAuto block has no NPC coordinates defined'
                    })
                
                # Check if disabled
                if 'disabled 0' in block_content or 'disabled' not in block_content:
                    root_causes.append({
                        'cause': 'buyAuto_enabled_without_valid_npc',
                        'confidence': 0.90,
                        'evidence': 'buyAuto is enabled but may have invalid NPC'
                    })
        
        # Route/AI stuck issues  
        elif issue_type in ['ai_stuck_loop', 'route_stuck']:
            # Check lockMap configuration
            if re.search(r'lockMap\s*$', config_content, re.MULTILINE):
                root_causes.append({
                    'cause': 'lockMap_empty',
                    'confidence': 0.95,
                    'evidence': 'lockMap is not configured - bot has no farming area'
                })
        
        # Death analysis
        elif issue_type == 'death':
            # Check healing thresholds
            teleport_hp = re.search(r'teleportAuto_hp\s+(\d+)', config_content)
            sit_hp = re.search(r'sitAuto_hp_lower\s+(\d+)', config_content)
            
            if teleport_hp and int(teleport_hp.group(1)) < 20:
                root_causes.append({
                    'cause': 'teleport_threshold_too_low',
                    'confidence': 0.80,
                    'evidence': f'teleportAuto_hp is {teleport_hp.group(1)} - too risky'
                })
            
            if sit_hp and int(sit_hp.group(1)) < 80:
                root_causes.append({
                    'cause': 'healing_threshold_too_low',
                    'confidence': 0.75,
                    'evidence': f'sitAuto_hp_lower is {sit_hp.group(1)} - insufficient safety margin'
                })
        
        return {
            'root_causes': root_causes,
            'primary_cause': root_causes[0] if root_causes else None
        }
