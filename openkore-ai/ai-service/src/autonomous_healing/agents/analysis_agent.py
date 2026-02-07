"""
Analysis Agent - Root Cause Identification
Correlates errors with configuration files to identify true causes
"""

from crewai import Agent
from crewai_tools import BaseTool, FileReadTool
from typing import Dict, List, Any, Optional
from pathlib import Path
import re


class ConfigurationAnalysisTool(BaseTool):
    """Tool for analyzing OpenKore configuration files"""
    
    name: str = "config_analyzer"
    description: str = "Analyze OpenKore config.txt for issues like empty lockMap, invalid NPCs, wrong coordinates"
    
    def __init__(self, analysis_config: Dict):
        super().__init__()
        self.config = analysis_config
    
    def _run(self, config_path: str, issue_context: Dict) -> Dict[str, Any]:
        """Analyze configuration file for issues related to the detected problem"""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                return {'success': False, 'error': 'Config file not found'}
            
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            findings = []
            
            # Check for empty lockMap
            if issue_context.get('type') in ['ai_stuck_loop', 'route_stuck']:
                lockmap_match = re.search(r'lockMap\s*$', content, re.MULTILINE)
                if lockmap_match:
                    findings.append({
                        'issue': 'empty_lockMap',
                        'severity': 'CRITICAL',
                        'description': 'lockMap is empty - bot has no farming area',
                        'line_number': content[:lockmap_match.start()].count('\n') + 1
                    })
            
            # Check for buyAuto with no NPC
            if issue_context.get('type') in ['npc_not_found', 'npc_no_response']:
                buyauto_match = re.search(r'buyAuto.*?\{[^}]*npc\s*$[^}]*\}', content, re.MULTILINE | re.DOTALL)
                if buyauto_match:
                    # Check if disabled
                    if 'disabled 0' in buyauto_match.group(0) or 'disabled' not in buyauto_match.group(0):
                        findings.append({
                            'issue': 'buyAuto_no_npc',
                            'severity': 'HIGH',
                            'description': 'buyAuto enabled but NPC not defined',
                            'block_content': buyauto_match.group(0)
                        })
            
            # Check for spawn position vs lockMap boundaries
            lockmap_x = re.search(r'lockMap_x\s+(\d+)\s+(\d+)', content)
            lockmap_y = re.search(r'lockMap_y\s+(\d+)\s+(\d+)', content)
            
            if lockmap_x and lockmap_y and issue_context.get('spawn_position'):
                spawn_x, spawn_y = issue_context['spawn_position']
                min_x, max_x = map(int, lockmap_x.groups())
                min_y, max_y = map(int, lockmap_y.groups())
                
                if not (min_x <= spawn_x <= max_x and min_y <= spawn_y <= max_y):
                    findings.append({
                        'issue': 'spawn_outside_lockMap',
                        'severity': 'HIGH',
                        'description': f'Spawn ({spawn_x},{spawn_y}) outside lockMap_x {min_x}-{max_x}, lockMap_y {min_y}-{max_y}',
                        'spawn': (spawn_x, spawn_y),
                        'boundaries': {'x': (min_x, max_x), 'y': (min_y, max_y)}
                    })
            
            return {
                'success': True,
                'findings_count': len(findings),
                'findings': findings,
                'config_content': content[:500]  # Preview
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class NPCDatabaseValidationTool(BaseTool):
    """Tool for validating NPC coordinates against database"""
    
    name: str = "npc_validator"
    description: str = "Validate NPC coordinates in config against actual NPC database (npcs.txt)"
    
    def _run(self, npc_coords: str, npcs_db_path: str) -> Dict[str, Any]:
        """Check if NPC exists in database"""
        try:
            # Parse coordinate from config (e.g., "prontera 146 204")
            match = re.match(r'(\w+)\s+(\d+)\s+(\d+)', npc_coords)
            if not match:
                return {'success': False, 'error': 'Invalid NPC coordinate format'}
            
            map_name, x, y = match.groups()
            x, y = int(x), int(y)
            
            # Load NPC database
            npcs_file = Path(npcs_db_path)
            if not npcs_file.exists():
                return {'success': False, 'error': 'NPCs database not found'}
            
            with open(npcs_file, 'r', encoding='utf-8') as f:
                npcs = f.readlines()
            
            # Check if NPC exists at coordinates
            npc_exists = False
            nearby_npcs = []
            
            for line in npcs:
                npc_match = re.match(r'(\\w+)\\s+(\\d+)\\s+(\\d+)\\s+(.+)', line.strip())
                if npc_match:
                    npc_map, npc_x, npc_y, npc_name = npc_match.groups()
                    npc_x, npc_y = int(npc_x), int(npc_y)
                    
                    if npc_map == map_name:
                        distance = abs(npc_x - x) + abs(npc_y - y)
                        
                        if npc_x == x and npc_y == y:
                            npc_exists = True
                            break
                        elif distance < 20:  # Within 20 cells
                            nearby_npcs.append({
                                'name': npc_name,
                                'coords': (npc_x, npc_y),
                                'distance': distance
                            })
            
            return {
                'success': True,
                'npc_exists': npc_exists,
                'requested_coords': f'{map_name} {x} {y}',
                'nearby_npcs': sorted(nearby_npcs, key=lambda n: n['distance'])[:5]
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class AnalysisAgent:
    """Wrapper for Analysis Agent"""
    pass


def create_analysis_agent(config: Dict, analysis_config: Dict) -> Agent:
    """
    Create the Analysis Agent for root cause identification
    
    Args:
        config: Agent configuration
        analysis_config: Analysis-specific configuration
        
    Returns:
        Configured CrewAI Agent
    """
    
    # Create tools
    tools = [
        ConfigurationAnalysisTool(analysis_config=analysis_config),
        NPCDatabaseValidationTool(),
        FileReadTool()  # Generic file reading
    ]
    
    # Create agent
    agent = Agent(
        role=config['role'],
        goal=config['goal'],
        backstory=config['backstory'],
        tools=tools,
        verbose=config.get('verbose', True),
        allow_delegation=True,  # Can delegate to other agents
        max_iter=20,
        memory=True
    )
    
    return agent
