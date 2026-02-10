"""
Trigger System - Multi-Layered Autonomous Trigger System
Provides intelligent, priority-based trigger evaluation and execution across layers
"""

from .models import (
    Trigger,
    TriggerCondition,
    TriggerAction,
    TriggerExecutionResult,
    LayerPriority
)

from .trigger_registry import TriggerRegistry
from .trigger_evaluator import TriggerEvaluator
from .trigger_executor import TriggerExecutor
from .trigger_coordinator import TriggerCoordinator
from .state_manager import StateManager, StateContext

__all__ = [
    # Models
    'Trigger',
    'TriggerCondition',
    'TriggerAction',
    'TriggerExecutionResult',
    'LayerPriority',
    
    # Core Components
    'TriggerRegistry',
    'TriggerEvaluator',
    'TriggerExecutor',
    'TriggerCoordinator',
    'StateManager',
    'StateContext'
]

__version__ = '1.0.0'
