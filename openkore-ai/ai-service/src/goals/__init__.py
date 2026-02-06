"""
Temporal Goals System

A sophisticated goal planning and execution system with comprehensive contingency planning
that reasons about past, present, and future to achieve zero-failure operation.
"""

from .goal_model import (
    GoalStatus,
    GoalPriority,
    ContingencyPlan,
    TemporalGoal
)
from .past_analyzer import PastAnalyzer
from .present_evaluator import PresentEvaluator
from .future_predictor import FuturePredictor
from .contingency_manager import ContingencyManager
from .coordinator import TemporalGoalsCoordinator

# Intelligence layers
from .conscious_planner import ConsciousGoalPlanner
from .subconscious_predictor import SubconsciousGoalPredictor
from .reflex_trigger import ReflexGoalTrigger
from .muscle_memory import MuscleMemoryExecutor

__all__ = [
    # Data models
    'GoalStatus',
    'GoalPriority',
    'ContingencyPlan',
    'TemporalGoal',
    
    # Temporal reasoning components
    'PastAnalyzer',
    'PresentEvaluator',
    'FuturePredictor',
    'ContingencyManager',
    
    # Main coordinator
    'TemporalGoalsCoordinator',
    
    # Intelligence layers
    'ConsciousGoalPlanner',
    'SubconsciousGoalPredictor',
    'ReflexGoalTrigger',
    'MuscleMemoryExecutor',
]

__version__ = '1.0.0'
