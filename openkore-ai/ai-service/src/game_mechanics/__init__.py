"""
Game mechanics module extracted from rathena-AI-world.

This module provides game mechanics knowledge to OpenKore AI without
modifying any server-side code. It's purely for intelligent decision-making.
"""

from .status_effects import StatusChange, StatusEffectInfo, StatusEffectDatabase
from .status_handler import StatusEffectHandler
from .skill_tree import SkillInfo, SkillTreeDatabase

__all__ = [
    'StatusChange',
    'StatusEffectInfo', 
    'StatusEffectDatabase',
    'StatusEffectHandler',
    'SkillInfo',
    'SkillTreeDatabase'
]
