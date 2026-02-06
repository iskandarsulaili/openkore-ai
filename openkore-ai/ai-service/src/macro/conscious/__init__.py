"""
CrewAI Conscious Layer
Strategic reasoning and macro generation using multi-agent system
"""

from .strategist import MacroStrategist, StrategicDecision
from .generator import MacroGenerator, GeneratedMacro
from .optimizer import MacroOptimizer, OptimizationSuggestion
from .analyst import PerformanceAnalyst, PerformanceReport
from .reference_loader import MacroReferenceLoader

__all__ = [
    'MacroStrategist',
    'StrategicDecision',
    'MacroGenerator',
    'GeneratedMacro',
    'MacroOptimizer',
    'OptimizationSuggestion',
    'PerformanceAnalyst',
    'PerformanceReport',
    'MacroReferenceLoader'
]
