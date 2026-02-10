"""
Report generation modules for validation results.
"""

from .coverage_reporter import CoverageReporter, generate_coverage_report
from .gap_analyzer import GapAnalyzer

__all__ = [
    'CoverageReporter',
    'generate_coverage_report',
    'GapAnalyzer',
]
