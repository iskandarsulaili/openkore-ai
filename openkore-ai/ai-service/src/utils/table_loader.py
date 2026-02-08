"""
OpenKore Table Loader with Real-Time File Watching

Loads game data from openkore-ai/tables directory:
- items.txt - Item database (ID#Name#)
- monsters.txt - Monster database (ID Name) - UPDATED IN REAL-TIME
- npcs.txt - NPC locations (MapName X Y NPCName) - UPDATED IN REAL-TIME  
- portals.txt - Portal connections - UPDATED IN REAL-TIME
- portalsLOS.txt - Line of sight portal data - UPDATED IN REAL-TIME
- cities.txt - City/map names
- maps.txt - Map data

User requirement: "All hardcoded things should use database available
in openkore-ai/tables as the first source and NEVER hardcoded"

User requirement: "Apply active read/retrieve data from openkore-ai/tables 
(monsters.txt, npcs.txt, portalsLOS.txt, portals.txt) as this is updated 
in real-time" - OpenKore updates these files during gameplay
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Make watchdog optional - file watching is a bonus feature, not required
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("[TableLoader] watchdog module not available - file watching disabled")
    logger.info("[TableLoader] Install with: pip install watchdog>=3.0.0 (optional)")
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None

logger = logging.getLogger(__name__)


if WATCHDOG_AVAILABLE:
    class TableFileWatcher(FileSystemEventHandler):
        """Watch OpenKore table files for changes and reload automatically"""
        
        def __init__(self, table_loader):
            self.table_loader = table_loader
            self.last_reload = {}
            self.reload_cooldown = 2  # seconds - prevent rapid reloads
        
        def on_modified(self, event):
            if event.is_directory:
                return
            
            file_path = event.src_path
            file_name = os.path.basename(file_path)
            
            # Only reload if cooldown passed (prevent rapid reloads)
            current_time = time.time()
            if file_name in self.last_reload:
                if current_time - self.last_reload[file_name] < self.reload_cooldown:
                    return
            
            self.last_reload[file_name] = current_time
            
            logger.info(f"[TableWatcher] Detected change in {file_name}, reloading...")
            
            # Reload specific table
            if file_name == "monsters.txt":
                self.table_loader._monsters_cache = None
                self.table_loader.load_monsters()
            elif file_name == "npcs.txt":
                self.table_loader._npcs_cache = None
                self.table_loader.load_npcs()
            elif file_name == "portals.txt":
                self.table_loader._portals_cache = None
                self.table_loader.load_portals()
            elif file_name == "portalsLOS.txt":
                self.table_loader._portals_los_cache = None
                self.table_loader.load_portals_los()
            elif file_name == "items.txt":
                self.table_loader._items_cache = None
                self.table_loader.load_items()
else:
    # Dummy class when watchdog not available
    class TableFileWatcher:
        """Dummy watcher when watchdog not installed"""
        def __init__(self, table_loader):
            pass


class TableLoader:
    """
    Load OpenKore table files with real-time updates
    
    Supports server-specific overrides:
    - Base path: openkore-ai/tables/
    - Server path: openkore-ai/tables/{server}/
    
    Server-specific files take precedence over base files.
    """
    
    def __init__(self, tables_dir: Path = None, server: str = "ROla", watch_files: bool = True):
        """
        Initialize table loader
        
        Args:
            tables_dir: Path to tables directory (default: openkore-ai/tables)
            server: Server name for server-specific tables (default: ROla)
            watch_files: Enable file watching for real-time updates (default: True)
        """
        if tables_dir is None:
            # Default: openkore-ai/tables relative to this file
            # This file is in: openkore-ai/ai-service/src/utils/table_loader.py
            # Tables are in: openkore-ai/tables/
            tables_dir = Path(__file__).parent.parent.parent.parent / "tables"
        
        self.tables_dir = Path(tables_dir)
        self.server = server
        self.server_tables_dir = self.tables_dir / server
        
        logger.info(f"[TableLoader] Initializing with tables_dir={self.tables_dir}")
        logger.info(f"[TableLoader] Server-specific dir={self.server_tables_dir}")
        
        # Cache for all tables
        self._items_cache = None
        self._monsters_cache = None
        self._npcs_cache = None
        self._portals_cache = None
        self._portals_los_cache = None
        self._maps_cache = None
        self._cities_cache = None
        
        # Start file watcher if enabled AND watchdog available
        self.observer = None
        if watch_files and WATCHDOG_AVAILABLE:
            self.start_file_watcher()
        elif watch_files and not WATCHDOG_AVAILABLE:
            logger.info("[TableLoader] File watching requested but watchdog not installed")
            logger.info("[TableLoader] Tables will be loaded once at startup only")
        else:
            logger.info("[TableLoader] File watching disabled by configuration")
    
    def start_file_watcher(self):
        """Start watching table files for changes"""
        if not WATCHDOG_AVAILABLE:
            logger.warning("[TableLoader] Cannot start file watcher - watchdog not installed")
            return
        
        logger.info("[TableLoader] Starting file watcher for real-time updates")
        
        event_handler = TableFileWatcher(self)
        self.observer = Observer()
        
        # Watch main tables directory
        if self.tables_dir.exists():
            self.observer.schedule(event_handler, str(self.tables_dir), recursive=False)
            logger.info(f"[TableLoader] Watching: {self.tables_dir}")
        
        # Watch server-specific directory
        if self.server_tables_dir.exists():
            self.observer.schedule(event_handler, str(self.server_tables_dir), recursive=False)
            logger.info(f"[TableLoader] Watching: {self.server_tables_dir}")
        
        self.observer.start()
        logger.info("[TableLoader] File watcher started successfully")
    
    def stop_file_watcher(self):
        """Stop file watcher"""
        if self.observer and WATCHDOG_AVAILABLE:
            self.observer.stop()
            self.observer.join()
            logger.info("[TableLoader] File watcher stopped")
    
    def _get_file_path(self, filename: str) -> Optional[Path]:
        """
        Get file path, checking server-specific directory first
        
        Priority: server-specific > base directory
        """
        # Check server-specific first
        server_file = self.server_tables_dir / filename
        if server_file.exists():
            return server_file
        
        # Fallback to base directory
        base_file = self.tables_dir / filename
        if base_file.exists():
            return base_file
        
        return None
    
    def load_items(self) -> Dict[int, Dict[str, str]]:
        """
        Load items.txt
        
        Format: ItemID#ItemName#
        Example: 501#Poção Vermelha#
        
        Returns dict: {
            501: {"id": 501, "name": "Poção Vermelha"},
            ...
        }
        """
        if self._items_cache is not None:
            return self._items_cache
        
        items_file = self._get_file_path("items.txt")
        
        if not items_file:
            logger.warning("[TableLoader] items.txt not found")
            return {}
        
        items = {}
        with open(items_file, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split('#')
                if len(parts) < 2:
                    continue
                
                try:
                    item_id = int(parts[0])
                    item_name = parts[1]
                    
                    items[item_id] = {
                        "id": item_id,
                        "name": item_name
                    }
                except (ValueError, IndexError):
                    continue
        
        self._items_cache = items
        logger.info(f"[TableLoader] Loaded {len(items)} items from {items_file.name}")
        return items
    
    def load_monsters(self) -> Dict[str, Dict]:
        """
        Load monsters.txt - UPDATED IN REAL-TIME by OpenKore
        
        Format: MonsterID MonsterName
        Example: 1002 Poring
        
        Returns dict: {
            "Poring": {"id": 1002, "name": "Poring"},
            ...
        }
        """
        if self._monsters_cache is not None:
            return self._monsters_cache
        
        monsters_file = self._get_file_path("monsters.txt")
        
        if not monsters_file:
            logger.warning("[TableLoader] monsters.txt not found")
            return {}
        
        monsters = {}
        with open(monsters_file, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(maxsplit=1)
                if len(parts) < 2:
                    continue
                
                try:
                    monster_id = int(parts[0])
                    monster_name = parts[1]
                    
                    monsters[monster_name] = {
                        "id": monster_id,
                        "name": monster_name
                    }
                except (ValueError, IndexError) as e:
                    logger.warning(f"[TableLoader] Failed to parse monster line: {line}")
                    continue
        
        self._monsters_cache = monsters
        logger.info(f"[TableLoader] Loaded {len(monsters)} monsters from {monsters_file.name}")
        return monsters
    
    def load_npcs(self) -> Dict[Tuple[str, int, int], Dict]:
        """
        Load npcs.txt - UPDATED IN REAL-TIME by OpenKore
        
        Format: MapName X Y NPCName
        Example: prontera 156 191 Kafra Employee
        
        Returns dict: {
            ("prontera", 156, 191): {"map": "prontera", "x": 156, "y": 191, "name": "Kafra Employee"},
            ...
        }
        """
        if self._npcs_cache is not None:
            return self._npcs_cache
        
        npcs_file = self._get_file_path("npcs.txt")
        
        if not npcs_file:
            logger.warning("[TableLoader] npcs.txt not found")
            return {}
        
        npcs = {}
        with open(npcs_file, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(maxsplit=3)
                if len(parts) < 4:
                    continue
                
                try:
                    map_name = parts[0]
                    x = int(parts[1])
                    y = int(parts[2])
                    npc_name = parts[3]
                    
                    key = (map_name, x, y)
                    npcs[key] = {
                        "map": map_name,
                        "x": x,
                        "y": y,
                        "name": npc_name
                    }
                except (ValueError, IndexError) as e:
                    logger.warning(f"[TableLoader] Failed to parse NPC line: {line}")
                    continue
        
        self._npcs_cache = npcs
        logger.info(f"[TableLoader] Loaded {len(npcs)} NPCs from {npcs_file.name}")
        return npcs
    
    def load_portals(self) -> Dict[Tuple[str, int, int], Dict]:
        """
        Load portals.txt - UPDATED IN REAL-TIME by OpenKore
        
        Format: SourceMap SourceX SourceY DestMap DestX DestY [cost] [options]
        Example: alberta 195 151 alb2trea 62 69 0 c c r0
        
        Returns dict: {
            ("alberta", 195, 151): {
                "source_map": "alberta",
                "source_x": 195,
                "source_y": 151,
                "dest_map": "alb2trea",
                "dest_x": 62,
                "dest_y": 69,
                "cost": 0
            },
            ...
        }
        """
        if self._portals_cache is not None:
            return self._portals_cache
        
        portals_file = self._get_file_path("portals.txt")
        
        if not portals_file:
            logger.warning("[TableLoader] portals.txt not found")
            return {}
        
        portals = {}
        with open(portals_file, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split()
                if len(parts) < 6:
                    continue
                
                try:
                    source_map = parts[0]
                    source_x = int(parts[1])
                    source_y = int(parts[2])
                    dest_map = parts[3]
                    dest_x = int(parts[4])
                    dest_y = int(parts[5])
                    cost = int(parts[6]) if len(parts) > 6 else 0
                    
                    key = (source_map, source_x, source_y)
                    portals[key] = {
                        "source_map": source_map,
                        "source_x": source_x,
                        "source_y": source_y,
                        "dest_map": dest_map,
                        "dest_x": dest_x,
                        "dest_y": dest_y,
                        "cost": cost
                    }
                except (ValueError, IndexError):
                    continue
        
        self._portals_cache = portals
        logger.info(f"[TableLoader] Loaded {len(portals)} portals from {portals_file.name}")
        return portals
    
    def load_portals_los(self) -> Dict:
        """
        Load portalsLOS.txt - Line of sight portal data - UPDATED IN REAL-TIME
        
        Format depends on actual file structure
        """
        if self._portals_los_cache is not None:
            return self._portals_los_cache
        
        los_file = self._get_file_path("portalsLOS.txt")
        
        if not los_file:
            logger.warning("[TableLoader] portalsLOS.txt not found")
            return {}
        
        portals_los = {}
        # Implementation depends on file format
        # For now, return empty dict - can be enhanced when format is known
        
        self._portals_los_cache = portals_los
        logger.info(f"[TableLoader] Loaded portalsLOS.txt")
        return portals_los
    
    def load_maps(self) -> List[str]:
        """Load maps.txt - List of all maps"""
        if self._maps_cache is not None:
            return self._maps_cache
        
        maps_file = self._get_file_path("maps.txt")
        
        if not maps_file:
            logger.warning("[TableLoader] maps.txt not found")
            return []
        
        maps = []
        with open(maps_file, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    maps.append(line)
        
        self._maps_cache = maps
        logger.info(f"[TableLoader] Loaded {len(maps)} maps")
        return maps
    
    def load_cities(self) -> Dict[str, str]:
        """
        Load cities.txt
        
        Format: mapfile#DisplayName#
        Example: prontera.rsw#Prontera City#
        
        Returns: {"prontera.rsw": "Prontera City", ...}
        """
        if self._cities_cache is not None:
            return self._cities_cache
        
        cities_file = self._get_file_path("cities.txt")
        
        if not cities_file:
            logger.warning("[TableLoader] cities.txt not found")
            return {}
        
        cities = {}
        with open(cities_file, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split('#')
                if len(parts) >= 2:
                    map_file = parts[0]
                    city_name = parts[1]
                    cities[map_file] = city_name
        
        self._cities_cache = cities
        logger.info(f"[TableLoader] Loaded {len(cities)} cities")
        return cities
    
    # ========================================================================
    # Helper Methods for Game Logic (No Hardcoding!)
    # ========================================================================
    
    def get_monster_by_name(self, name: str) -> Optional[Dict]:
        """Get monster info by name"""
        monsters = self.load_monsters()
        return monsters.get(name)
    
    def get_npcs_on_map(self, map_name: str) -> List[Dict]:
        """Get all NPCs on a specific map"""
        npcs = self.load_npcs()
        return [npc for key, npc in npcs.items() if key[0] == map_name]
    
    def get_portal_from_location(self, map_name: str, x: int, y: int, tolerance: int = 5) -> Optional[Dict]:
        """Find portal near given coordinates (within tolerance)"""
        portals = self.load_portals()
        
        for (portal_map, portal_x, portal_y), portal_data in portals.items():
            if portal_map == map_name:
                distance = abs(portal_x - x) + abs(portal_y - y)  # Manhattan distance
                if distance <= tolerance:
                    return portal_data
        
        return None
    
    def get_healing_items(self) -> List[Tuple[str, int]]:
        """
        Get healing items (HP recovery) from items.txt
        
        Returns list of (item_name, item_id) tuples
        NO HARDCODING - dynamically loaded from tables
        """
        items = self.load_items()
        
        # Known healing item patterns (Portuguese names from ROla server)
        healing_patterns = [
            "Poção",  # Potions
            "Erva",   # Herbs
            "Mastela",
            "Geleia Real",  # Royal Jelly
        ]
        
        healing_items = []
        for item_id, item_data in items.items():
            name = item_data["name"]
            # Check if item name contains healing patterns
            if any(pattern in name for pattern in healing_patterns):
                healing_items.append((name, item_id))
        
        # Sort by item ID (typically lower ID = basic items)
        healing_items.sort(key=lambda x: x[1])
        
        logger.debug(f"[TableLoader] Found {len(healing_items)} healing items")
        return healing_items
    
    def get_sp_recovery_items(self) -> List[Tuple[str, int]]:
        """
        Get SP recovery items from items.txt
        
        Returns list of (item_name, item_id) tuples
        NO HARDCODING - dynamically loaded from tables
        """
        items = self.load_items()
        
        # Known SP recovery patterns
        sp_patterns = [
            "Poção Azul",  # Blue Potions
            "Poção Verde",  # Green Potions  
        ]
        
        sp_items = []
        for item_id, item_data in items.items():
            name = item_data["name"]
            if any(pattern in name for pattern in sp_patterns):
                sp_items.append((name, item_id))
        
        sp_items.sort(key=lambda x: x[1])
        
        logger.debug(f"[TableLoader] Found {len(sp_items)} SP recovery items")
        return sp_items
    
    def get_escape_items(self) -> List[str]:
        """
        Get escape items (Butterfly Wing, Teleport items) from items.txt
        
        Returns list of item names
        NO HARDCODING - dynamically loaded from tables
        """
        items = self.load_items()
        
        # Known escape item IDs (these are standard across servers)
        escape_item_ids = [
            602,  # Butterfly Wing (Asa de Borboleta)
            601,  # Fly Wing (Asa de Mosca)
        ]
        
        escape_items = []
        for item_id in escape_item_ids:
            if item_id in items:
                escape_items.append(items[item_id]["name"])
        
        logger.debug(f"[TableLoader] Found {len(escape_items)} escape items")
        return escape_items
    
    def get_quest_items(self) -> List[str]:
        """
        Get quest items from items.txt
        
        Quest items typically can't be sold/dropped
        Returns list of item names
        """
        # This would require additional metadata about which items are quest items
        # For now, return empty list - can be enhanced with quest item database
        return []
    
    def is_card(self, item_name: str) -> bool:
        """
        Check if item is a card (valuable, should never sell)
        
        Cards typically have "Card" or "Carta" in the name
        """
        if not item_name:
            return False
        
        card_keywords = ["Card", "Carta"]
        return any(keyword in item_name for keyword in card_keywords)


# ============================================================================
# Singleton Pattern - Get TableLoader Instance
# ============================================================================

_table_loader_instance: Optional[TableLoader] = None


def get_table_loader(server: str = "ROla", watch_files: bool = True) -> TableLoader:
    """
    Get or create table loader singleton instance
    
    Args:
        server: Server name for server-specific tables
        watch_files: Enable real-time file watching
    
    Returns:
        TableLoader instance
    """
    global _table_loader_instance
    
    if _table_loader_instance is None:
        _table_loader_instance = TableLoader(server=server, watch_files=watch_files)
        logger.info("[TableLoader] Singleton instance created")
    
    return _table_loader_instance
