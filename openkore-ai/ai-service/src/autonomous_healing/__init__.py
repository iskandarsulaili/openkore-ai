"""
OpenKore Autonomous Self-Healing System
Multi-agent CrewAI framework for intelligent bot monitoring and repair
"""

__version__ = "1.0.0"
__author__ = "OpenKore AI Service Team"

from .main import AutonomousHealingSystem
from .agents import (
    MonitorAgent,
    AnalysisAgent,
    SolutionAgent,
    ValidationAgent,
    ExecutionAgent,
    LearningAgent
)
from .core import (
    LogMonitor,
    IssueDetector,
    RootCauseAnalyzer,
    SolutionGenerator,
    SafeExecutor,
    KnowledgeBase
)

__all__ = [
    'AutonomousHealingSystem',
    'MonitorAgent',
    'AnalysisAgent',
    'SolutionAgent',
    'ValidationAgent',
    'ExecutionAgent',
    'LearningAgent',
    'LogMonitor',
    'IssueDetector',
    'RootCauseAnalyzer',
    'SolutionGenerator',
    'SafeExecutor',
    'KnowledgeBase'
]
