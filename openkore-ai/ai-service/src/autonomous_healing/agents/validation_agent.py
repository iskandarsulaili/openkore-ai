"""
Validation Agent - Syntax and Logic Checking
Validates proposed fixes before execution
"""

from crewai import Agent
from crewai_tools import BaseTool
from typing import Dict, List, Any
import re


class ConfigSyntaxValidatorTool(BaseTool):
    """Tool for validating OpenKore config syntax"""
    
    name: str = "syntax_validator"
    description: str = "Validate OpenKore configuration syntax before applying changes"
    
    def _run(self, proposed_changes: List[Dict], target_file: str) -> Dict[str, Any]:
        """Validate syntax of proposed changes"""
        try:
            errors = []
            warnings = []
            
            for change in proposed_changes:
                if change['type'] == 'replace':
                    # Validate regex pattern
                    try:
                        re.compile(change['pattern'])
                    except re.error as e:
                        errors.append({
                            'change': change,
                            'error': f"Invalid regex pattern: {e}"
                        })
                    
                    # Check replacement makes sense
                    replacement = change['replacement']
                    
                    # Validate common config patterns
                    if 'lockMap' in replacement:
                        if not re.match(r'lockMap\s+\w+', replacement):
                            warnings.append({
                                'change': change,
                                'warning': 'lockMap format may be invalid'
                            })
                    
                    if 'npc' in replacement:
                        if not re.match(r'npc\s+\w+\s+\d+\s+\d+', replacement):
                            warnings.append({
                                'change': change,
                                'warning': 'NPC coordinate format may be invalid'
                            })
            
            is_valid = len(errors) == 0
            
            return {
                'success': True,
                'is_valid': is_valid,
                'errors_count': len(errors),
                'errors': errors,
                'warnings_count': len(warnings),
                'warnings': warnings
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class LogicValidatorTool(BaseTool):
    """Tool for validating logical correctness of fixes"""
    
    name: str = "logic_validator"
    description: str = "Validate that proposed fixes make logical sense for the detected issue"
    
    def _run(self, issue: Dict, solution: Dict) -> Dict[str, Any]:
        """Validate logical correctness of solution"""
        try:
            validation_result = {'valid': True, 'reasons': []}
            
            issue_type = issue.get('type')
            action = solution.get('action')
            
            # Validate action matches issue
            valid_mappings = {
                'npc_not_found': ['disable_buyAuto', 'fix_npc_coords'],
                'lockMap_empty': ['set_lockMap'],
                'packet_unknown': ['suppress_packet_warning'],
                'death': ['improve_survival', 'adjust_healing'],
                'ai_stuck_loop': ['fix_routing', 'disable_blocking_task']
            }
            
            if issue_type in valid_mappings:
                if action not in valid_mappings[issue_type]:
                    validation_result['valid'] = False
                    validation_result['reasons'].append(
                        f"Action '{action}' doesn't match issue type '{issue_type}'"
                    )
            
            # Validate confidence threshold
            if solution.get('confidence', 0) < 0.6:
                validation_result['valid'] = False
                validation_result['reasons'].append(
                    f"Confidence too low: {solution['confidence']}"
                )
            
            return {
                'success': True,
                'is_valid': validation_result['valid'],
                'validation_reasons': validation_result['reasons']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class ValidationAgent:
    """Wrapper for Validation Agent"""
    pass


def create_validation_agent(config: Dict) -> Agent:
    """Create the Validation Agent"""
    
    tools = [
        ConfigSyntaxValidatorTool(),
        LogicValidatorTool()
    ]
    
    agent = Agent(
        role=config['role'],
        goal=config['goal'],
        backstory=config['backstory'],
        tools=tools,
        verbose=config.get('verbose', True),
        allow_delegation=False,
        max_iter=10,
        memory=True
    )
    
    return agent
