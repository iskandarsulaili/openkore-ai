"""
Safety Module for Macro System

Provides anomaly detection and circuit breaker protection
for robust macro execution.
"""

from .anomaly_detector import MacroAnomalyDetector, AnomalyAlertSystem
from .circuit_breaker import (
    MacroCircuitBreaker,
    CircuitState,
    CircuitOpenError,
    circuit_breaker
)

__all__ = [
    'MacroAnomalyDetector',
    'AnomalyAlertSystem',
    'MacroCircuitBreaker',
    'CircuitState',
    'CircuitOpenError',
    'circuit_breaker'
]
