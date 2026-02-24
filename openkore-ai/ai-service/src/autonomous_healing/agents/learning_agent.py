"""
Learning Agent - Knowledge Base Management
Maintains and improves knowledge from successful/failed fixes
"""

from crewai import Agent
from crewai.tools import BaseTool
from typing import Dict, List, Any
from datetime import datetime, timedelta
from pydantic import ConfigDict


class PatternRecognitionTool(BaseTool):
    """Tool for recognizing recurring patterns in issues"""
    
    model_config = ConfigDict(
        extra='allow',
        arbitrary_types_allowed=True
    )
    
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
    
    model_config = ConfigDict(
        extra='allow',
        arbitrary_types_allowed=True
    )
    
    name: str = "knowledge_updater"
    description: str = "Update knowledge base with success/failure information to improve future solutions"
    
    def __init__(self, knowledge_base):
        super().__init__()
        self.kb = knowledge_base
    
    def _run(self, fix_result: Dict, confidence_adjustment: float = 0.1) -> Dict[str, Any]:
        """Update knowledge base based on fix result (handles both dict and CrewOutput)"""
        try:
            # PHASE 8 FIX #3: Handle both dict and CrewOutput from CrewAI
            issue_type = getattr(fix_result, 'issue_type', None) or (fix_result.get('issue_type') if isinstance(fix_result, dict) else None)
            solution = getattr(fix_result, 'solution', None) or (fix_result.get('solution') if isinstance(fix_result, dict) else None)
            success = getattr(fix_result, 'success', None)
            if success is None:
                success = fix_result.get('success', False) if isinstance(fix_result, dict) else False
            
            confidence = getattr(fix_result, 'confidence', None)
            if confidence is None:
                confidence = fix_result.get('confidence', 0.5) if isinstance(fix_result, dict) else 0.5
            
            # Update confidence for this solution pattern
            if success:
                new_confidence = min(1.0, confidence + confidence_adjustment)
            else:
                new_confidence = max(0.0, confidence - confidence_adjustment * 2)
            
            # Extract action from solution (handle both dict and object)
            solution_action = None
            if solution:
                solution_action = getattr(solution, 'action', None) or (solution.get('action') if isinstance(solution, dict) else None)
            
            # Store in knowledge base
            self.kb.update_solution_confidence(
                issue_type=issue_type,
                solution_action=solution_action,
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


def create_learning_agent(config: Dict, knowledge_base, llm) -> Agent:
    """
    Create the Learning Agent
    
    Args:
        config: Agent configuration
        knowledge_base: Knowledge base instance
        llm: LLM instance (DeepSeek via provider chain)
        
    Returns:
        Configured CrewAI Agent
    """
    
    tools = [
        PatternRecognitionTool(knowledge_base=knowledge_base),
        KnowledgeUpdateTool(knowledge_base=knowledge_base)
    ]
    
    # Create agent with DeepSeek LLM
    agent = Agent(
        role=config['role'],
        goal=config['goal'],
        backstory=config['backstory'],
        tools=tools,
        verbose=config.get('verbose', True),
        allow_delegation=False,
        max_iter=10,
        memory=True,
        llm=llm  # Use DeepSeek LLM
    )
    
    return agent
