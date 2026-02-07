"""
Solution Agent - Intelligent Fix Generation
Generates context-aware solutions based on character state, game version, and activity
"""

from crewai import Agent
from crewai_tools import BaseTool
from typing import Dict, List, Any
from pathlib import Path
import re


class AdaptiveSolutionGeneratorTool(BaseTool):
    """Tool for generating adaptive solutions based on context"""
    
    name: str = "solution_generator"
    description: str = "Generate intelligent fixes adapted to character level, class, map, and detected issue"
    
    def __init__(self, knowledge_base, solution_config: Dict):
        super().__init__()
        self.kb = knowledge_base
        self.config = solution_config
    
    def _run(self, issue: Dict, analysis: Dict, character_context: Dict) -> Dict[str, Any]:
        """Generate adaptive solution based on issue and context"""
        try:
            issue_type = issue.get('type')
            solutions = []
            
            # Get similar past solutions from knowledge base
            past_solutions = self.kb.get_similar_solutions(issue_type)
            base_confidence = past_solutions[0]['confidence'] if past_solutions else 0.5
            
            # Generate solution based on issue type
            if issue_type == 'npc_not_found' or issue_type == 'npc_interaction_failure':
                # Solution: Disable buyAuto
                solutions.append({
                    'action': 'disable_buyAuto',
                    'file': 'control/config.txt',
                    'changes': [
                        {
                            'type': 'replace',
                            'pattern': r'(buyAuto\s*\{[^}]*?)disabled\s+0',
                            'replacement': r'\1disabled 1',
                            'reason': 'NPC not found - disabling buyAuto to allow farming'
                        }
                    ],
                    'confidence': base_confidence + 0.2,
                    'requires_approval': False
                })
            
            elif issue_type == 'lockMap_empty':
                # Solution: Set lockMap based on character level
                char_level = character_context.get('level', 1)
                char_class = character_context.get('class', 'Novice')
                
                # Adaptive map selection
                if char_level <= 10 and char_class == 'Novice':
                    farming_map = 'prt_fild08'
                    coords_x = '100 250'
                    coords_y = '100 250'
                elif char_level <= 30:
                    farming_map = 'prt_fild05'
                    coords_x = '100 300'
                    coords_y = '100 300'
                else:
                    farming_map = 'prt_fild08'  # Default
                    coords_x = '50 300'
                    coords_y = '50 300'
                
                solutions.append({
                    'action': 'set_lockMap',
                    'file': 'control/config.txt',
                    'changes': [
                        {
                            'type': 'replace',
                            'pattern': r'lockMap\s*$',
                            'replacement': f'lockMap {farming_map}',
                            'reason': f'Setting farming map for level {char_level} {char_class}'
                        },
                        {
                            'type': 'replace',
                            'pattern': r'lockMap_x\s*$',
                            'replacement': f'lockMap_x {coords_x}',
                            'reason': 'Setting X boundary for farming area'
                        },
                        {
                            'type': 'replace',
                            'pattern': r'lockMap_y\s*$',
                            'replacement': f'lockMap_y {coords_y}',
                            'reason': 'Setting Y boundary for farming area'
                        }
                    ],
                    'confidence': base_confidence + 0.25,
                    'requires_approval': True  # Critical change
                })
            
            elif issue_type == 'packet_unknown':
                # Solution: Add to debugPacket_exclude
                packet_id = issue.get('packet_id', '')
                solutions.append({
                    'action': 'suppress_packet_warning',
                    'file': 'control/config.txt',
                    'changes': [
                        {
                            'type': 'append_or_update',
                            'key': 'debugPacket_exclude',
                            'value': packet_id,
                            'reason': f'Suppressing warning for unknown packet {packet_id}'
                        }
                    ],
                    'confidence': base_confidence + 0.15,
                    'requires_approval': False
                })
            
            elif issue_type == 'death':
                # Solution: Adjust healing and teleport settings
                death_hp = analysis.get('death_hp_percent', 0)
                
                solutions.append({
                    'action': 'improve_survival',
                    'file': 'control/config.txt',
                    'changes': [
                        {
                            'type': 'replace',
                            'pattern': r'teleportAuto_hp\s+\d+',
                            'replacement': 'teleportAuto_hp 30',  # Teleport earlier
                            'reason': 'Increasing teleport threshold for safety'
                        },
                        {
                            'type': 'replace',
                            'pattern': r'sitAuto_hp_lower\s+\d+',
                            'replacement': 'sitAuto_hp_lower 90',  # Sit earlier
                            'reason': 'Increasing healing threshold to prevent death'
                        }
                    ],
                    'confidence': base_confidence + 0.1,
                    'requires_approval': False
                })
            
            return {
                'success': True,
                'solutions_count': len(solutions),
                'solutions': solutions,
                'base_confidence': base_confidence
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class SolutionAgent:
    """Wrapper for Solution Agent"""
    pass


def create_solution_agent(config: Dict, knowledge_base, solution_config: Dict) -> Agent:
    """Create the Solution Agent for intelligent fix generation"""
    
    tools = [
        AdaptiveSolutionGeneratorTool(
            knowledge_base=knowledge_base,
            solution_config=solution_config
        )
    ]
    
    agent = Agent(
        role=config['role'],
        goal=config['goal'],
        backstory=config['backstory'],
        tools=tools,
        verbose=config.get('verbose', True),
        allow_delegation=True,
        max_iter=20,
        memory=True
    )
    
    return agent
