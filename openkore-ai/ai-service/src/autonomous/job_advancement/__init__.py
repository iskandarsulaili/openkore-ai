"""
Job Advancement System (CONSCIOUS Layer)
Autonomous job change detection and execution
"""

from .detector import JobAdvancementDetector
from .executor import JobAdvancementExecutor

__all__ = ["JobAdvancementDetector", "JobAdvancementExecutor"]
