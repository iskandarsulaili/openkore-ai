"""
ML Module for OpenKore AI
Provides machine learning capabilities with cold-start strategy
"""

from .cold_start import cold_start_manager, ColdStartPhase
from .data_collector import data_collector, FeatureExtractor
from .model_trainer import model_trainer
from .online_learner import online_learner

__all__ = [
    'cold_start_manager',
    'ColdStartPhase',
    'data_collector',
    'FeatureExtractor',
    'model_trainer',
    'online_learner'
]
