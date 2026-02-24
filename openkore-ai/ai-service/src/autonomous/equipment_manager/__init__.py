"""
Equipment Manager System (TACTICAL Layer)
Autonomous equipment optimization and combat swapping
"""

from .auto_equip import AutoEquipManager
from .combat_swapper import CombatEquipmentSwapper
from .optimizer import EquipmentOptimizer

__all__ = ["AutoEquipManager", "CombatEquipmentSwapper", "EquipmentOptimizer"]
