"""Solution Generation - Context-aware fix creation"""

from typing import Dict, List, Any


class SolutionGenerator:
    """Generates intelligent solutions based on root causes"""
    
    def __init__(self, knowledge_base):
        self.kb = knowledge_base
    
    def generate(self, root_cause: Dict, context: Dict) -> List[Dict]:
        """Generate solutions for identified root cause"""
        
        solutions = []
        cause_type = root_cause.get('cause')
        confidence = root_cause.get('confidence', 0.5)
        
        # Get past successful solutions
        past_solutions = self.kb.get_similar_solutions(cause_type)
        
        # Generate adaptive solution
        if cause_type == 'buyAuto_enabled_without_valid_npc':
            solutions.append({
                'action': 'disable_buyAuto',
                'changes': [{
                    'type': 'replace',
                    'pattern': r'(buyAuto\s*\{[^}]*?)disabled\s+0',
                    'replacement': r'\1disabled 1',
                    'reason': 'Disabling buyAuto due to invalid NPC configuration'
                }],
                'confidence': confidence,
                'requires_approval': False
            })
        
        elif cause_type == 'lockMap_empty':
            # Use character context to determine best map
            char_level = context.get('character_level', 1)
            farming_map = 'prt_fild08' if char_level < 20 else 'prt_fild05'
            
            solutions.append({
                'action': 'configure_lockMap',
                'changes': [
                    {'type': 'replace', 'pattern': r'lockMap\s*$', 
                     'replacement': f'lockMap {farming_map}',
                     'reason': f'Setting farming map for level {char_level}'},
                    {'type': 'replace', 'pattern': r'lockMap_x\s*$',
                     'replacement': 'lockMap_x 100 250',
                     'reason': 'Setting X boundaries'},
                    {'type': 'replace', 'pattern': r'lockMap_y\s*$',
                     'replacement': 'lockMap_y 100 250',
                     'reason': 'Setting Y boundaries'}
                ],
                'confidence': confidence + 0.1,
                'requires_approval': True
            })
        
        return solutions
