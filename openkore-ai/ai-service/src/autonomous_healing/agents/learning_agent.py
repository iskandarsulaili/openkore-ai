"""
Learning Agent - Knowledge Base Management
Maintains and improves knowledge from successful/failed fixes
"""

from crewai import Agent
from crewai_tools import BaseTool
from typing import Dict, List, Any
from datetime import datetime, timedelta


class PatternRecognitionTool(BaseTool):
    """Tool for recognizing recurring patterns in issues"""
    
    name: str = "pattern_recognizer"
    description: str = "Identify recurring patterns in bot failures to improve future fixes"
    
    def __init__(self, knowledge_base):
        super().__init__()
        self.kb = knowledge_base
    
    def _run(self, recent_issues: List[Dict], timeframe_hours: int = 24) -> Dict[str, Any]:
        """Analyze recent issues for patterns"""
        try:
            # Group issues by type
            issue_counts = {}
            issue_contexts = {}
            
            for issue in recent_issues:
                issue_type = issue.get('type', 'unknown')
                issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
                
                if issue_type not in issue_contexts:
                    issue_contexts[issue_type] = []
                issue_contexts[issue_type].append(issue)
            
            # Identify patterns
            patterns = []
            
            for issue_type, count in issue_counts.items():
                if count >= 3:  # Recurring issue
                    patterns.append({
                        'type': issue_type,
                        'frequency': count,
                        'severity': 'HIGH' if count > 5 else 'MEDIUM',
                        'contexts': issue_contexts[issue_type][:5]  # Sample
                    })
            
            return {
                'success': True,
                'patterns_found': len(patterns),
                'patterns': patterns,
                'total_issues_analyzed': len(recent_issues)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class KnowledgeUpdateTool(BaseTool):
    """Tool for updating knowledge base"""
    
    name: str = "knowledge_updater"
    description: str = "Update knowledge base with success/failure information to improve future solutions"
    
    def __init__(self, knowledge_base):
        super().__init__()
        self.kb = knowledge_base
    
    def _run(self, fix_result: Dict, confidence_adjustment: float = 0.1) -> Dict[str, Any]:
        """Update knowledge base based on fix result"""
        try:
            issue_type = fix_result.get('issue_type')
            solution = fix_result.get('solution')
            success = fix_result.get('success', False)
            
            # Update confidence for this solution pattern
            if success:
                new_confidence = min(1.0, fix_result.get('confidence', 0.5) + confidence_adjustment)
            else:
                new_confidence = max(0.0, fix_result.get('confidence', 0.5) - confidence_adjustment * 2)
            
            # Store in knowledge base
            self.kb.update_solution_confidence(
                issue_type=issue_type,
                solution_action=solution.get('action'),
                new_confidence=new_confidence,
                outcome=success
            )
            
            return {
                'success': True,
                'confidence_updated': True,
                'new_confidence': new_confidence
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class LearningAgent:
    """Wrapper for Learning Agent"""
    pass


def create_learning_agent(config: Dict, knowledge_base) -> Agent:
    """Create the Learning Agent"""
    
    tools = [
        PatternRecognitionTool(knowledge_base=knowledge_base),
        KnowledgeUpdateTool(knowledge_base=knowledge_base)
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
