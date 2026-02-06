"""
Three-Layer Adaptive Macro Management System

Layer 1 (Conscious): CrewAI multi-agent strategic reasoning
Layer 2 (Subconscious): ML pattern learning and prediction
Layer 3 (Reflex): Rule-based emergency responses
"""

from .deployment_service import (
    MacroDeploymentService,
    MacroDefinition,
    MacroValidator,
    quick_inject
)

__all__ = [
    'MacroDeploymentService',
    'MacroDefinition',
    'MacroValidator',
    'quick_inject'
]
