"""
Data Management Package

Handles monster database, item database, and dynamic server adaptation.
"""

from .monster_database import MonsterDatabase
from .item_database import ItemDatabase
from .server_adapter import ServerContentAdapter

__all__ = [
    'MonsterDatabase',
    'ItemDatabase',
    'ServerContentAdapter'
]
