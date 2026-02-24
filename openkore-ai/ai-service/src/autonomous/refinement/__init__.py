"""
Refinement System (SYSTEM Layer) - DISABLED BY DEFAULT
Autonomous equipment refinement and card slotting with safety nets
REQUIRES USER CONFIRMATION FOR VALUABLE ITEMS
"""

from .refiner import AutoRefiner
from .card_slotter import CardSlotter
from .safety_net import RefinementSafetyNet

__all__ = ["AutoRefiner", "CardSlotter", "RefinementSafetyNet"]

# CRITICAL: This module is DISABLED by default to prevent accidental loss
# Enable in autonomous_config.json with extreme caution
ENABLED_BY_DEFAULT = False
REQUIRES_USER_CONFIRMATION = True
VALUE_THRESHOLD_FOR_CONFIRMATION = 100000  # 100k zeny
