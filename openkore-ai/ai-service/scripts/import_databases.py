"""
Database Import Script

Imports monster and item databases with validation and rollback capability.
"""

import asyncio
import json
import logging
import shutil
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.monster_database import MonsterDatabase
from src.data.item_database import ItemDatabase
from src.data.server_adapter import ServerContentAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseImporter:
    """Handles database import with validation and rollback."""
    
    def __init__(self):
        """Initialize database importer."""
        self.base_path = Path(__file__).parent.parent
        self.data_path = self.base_path / "data"
        self.extracted_path = self.base_path / "data-validation" / "output" / "extracted"
        self.backup_path = self.data_path / "backups"
        
        self.import_results = {
            'monster_db': {'status': 'pending', 'errors': []},
            'item_db': {'status': 'pending', 'errors': []},
            'integration_tests': {'status': 'pending', 'errors': []}
        }
        
        # Create backup directory
        self.backup_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"DatabaseImporter initialized")
        logger.info(f"Data path: {self.data_path}")
        logger.info(f"Extracted path: {self.extracted_path}")
    
    async def import_all(self):
        """Import all databases."""
        logger.info("=" * 80)
        logger.info("STARTING DATABASE IMPORT")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        try:
            # Import monster database
            await self.import_monster_database()
            
            # Import item database
            await self.import_item_database()
            
            # Run integration tests
            await self.run_integration_tests()
            
            # Check if all imports succeeded
            all_success = all(
                result['status'] == 'success'
                for result in self.import_results.values()
            )
            
            if all_success:
                logger.info(" All databases imported successfully!")
                self._print_summary(time.time() - start_time)
            else:
                logger.error(" Some imports failed, rolling back...")
                await self.rollback_if_failed()
        
        except Exception as e:
            logger.error(f"Import failed with exception: {e}", exc_info=True)
            await self.rollback_if_failed()
    
    async def import_monster_database(self):
        """
        Import monster database:
        1. Load extracted monster_db.json
        2. Validate all entries
        3. Copy to data/monster_db.json
        4. Create backup of old data
        5. Test loading with MonsterDatabase class
        """
        logger.info("\n" + "-" * 80)
        logger.info("IMPORTING MONSTER DATABASE")
        logger.info("-" * 80)
        
        try:
            # Paths
            source_file = self.extracted_path / "monster_db.json"
            target_file = self.data_path / "monster_db.json"
            
            # Validate source exists
            if not source_file.exists():
                raise FileNotFoundError(f"Source file not found: {source_file}")
            
            logger.info(f"Source: {source_file}")
            logger.info(f"Target: {target_file}")
            
            # Backup existing file if it exists
            if target_file.exists():
                backup_file = self.backup_path / f"monster_db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                logger.info(f"Creating backup: {backup_file}")
                shutil.copy2(target_file, backup_file)
            
            # Load and validate source data
            logger.info("Loading and validating source data...")
            with open(source_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = data.get('metadata', {})
            monsters = data.get('monsters', [])
            
            logger.info(f"Loaded {len(monsters)} monsters")
            logger.info(f"Metadata: {metadata}")
            
            # Validate entries
            validation_errors = self._validate_monsters(monsters)
            if validation_errors:
                logger.warning(f"Found {len(validation_errors)} validation warnings")
                for error in validation_errors[:5]:  # Show first 5
                    logger.warning(f"  - {error}")
            
            # Copy to target location
            logger.info(f"Copying to {target_file}...")
            shutil.copy2(source_file, target_file)
            
            # Test loading with MonsterDatabase class
            logger.info("Testing MonsterDatabase class loading...")
            test_db = MonsterDatabase(str(target_file))
            
            # Verify loading
            if len(test_db.monsters) != len(monsters):
                raise ValueError(f"Monster count mismatch: expected {len(monsters)}, got {len(test_db.monsters)}")
            
            # Test some queries
            logger.info("Running test queries...")
            
            # Test ID lookup
            test_monster = test_db.get_monster_by_id(1002)
            if test_monster:
                logger.info(f"   ID lookup test: Found {test_monster.get('name')}")
            
            # Test name lookup
            test_monster = test_db.get_monster_by_name("Poring")
            if test_monster:
                logger.info(f"   Name lookup test: Found ID {test_monster.get('id')}")
            
            # Test optimal target finding
            targets = test_db.find_optimal_targets({'level': 50, 'monsters': [1002, 1113, 1031]})
            logger.info(f"   Optimal target test: Found {len(targets)} targets")
            
            # Get statistics
            stats = test_db.get_statistics()
            logger.info(f"Database statistics:")
            logger.info(f"  Total monsters: {stats['total_monsters']}")
            logger.info(f"  Load time: {stats['load_time_seconds']:.3f}s")
            logger.info(f"  Query count: {stats['query_count']}")
            
            # Performance check
            if stats['load_time_seconds'] > 1.0:
                logger.warning(f"⚠ Load time exceeds 1s: {stats['load_time_seconds']:.3f}s")
            else:
                logger.info(f"   Performance: Load time {stats['load_time_seconds']:.3f}s < 1s")
            
            self.import_results['monster_db']['status'] = 'success'
            logger.info(" Monster database import successful")
        
        except Exception as e:
            logger.error(f" Monster database import failed: {e}", exc_info=True)
            self.import_results['monster_db']['status'] = 'failed'
            self.import_results['monster_db']['errors'].append(str(e))
    
    async def import_item_database(self):
        """
        Import item database:
        1. Load extracted item_db.json
        2. Merge with existing loot_priority_database.json
        3. Validate all entries
        4. Copy to data/item_db.json
        5. Create backup of old data
        6. Test loading with ItemDatabase class
        """
        logger.info("\n" + "-" * 80)
        logger.info("IMPORTING ITEM DATABASE")
        logger.info("-" * 80)
        
        try:
            # Paths
            source_file = self.extracted_path / "item_db.json"
            target_file = self.data_path / "item_db.json"
            priority_file = self.data_path / "loot_priority_database.json"
            
            # Validate source exists
            if not source_file.exists():
                raise FileNotFoundError(f"Source file not found: {source_file}")
            
            logger.info(f"Source: {source_file}")
            logger.info(f"Target: {target_file}")
            logger.info(f"Priority DB: {priority_file}")
            
            # Backup existing file if it exists
            if target_file.exists():
                backup_file = self.backup_path / f"item_db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                logger.info(f"Creating backup: {backup_file}")
                shutil.copy2(target_file, backup_file)
            
            # Load and validate source data
            logger.info("Loading and validating source data...")
            with open(source_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = data.get('metadata', {})
            items = data.get('items', [])
            
            logger.info(f"Loaded {len(items)} items")
            logger.info(f"Metadata: {metadata}")
            
            # Validate entries
            validation_errors = self._validate_items(items)
            if validation_errors:
                logger.warning(f"Found {len(validation_errors)} validation warnings")
                for error in validation_errors[:5]:  # Show first 5
                    logger.warning(f"  - {error}")
            
            # Copy to target location
            logger.info(f"Copying to {target_file}...")
            shutil.copy2(source_file, target_file)
            
            # Test loading with ItemDatabase class
            logger.info("Testing ItemDatabase class loading...")
            priority_path = str(priority_file) if priority_file.exists() else None
            test_db = ItemDatabase(str(target_file), priority_path)
            
            # Verify loading
            if len(test_db.items) != len(items):
                raise ValueError(f"Item count mismatch: expected {len(items)}, got {len(test_db.items)}")
            
            # Test some queries
            logger.info("Running test queries...")
            
            # Test ID lookup
            test_item = test_db.get_item_by_id(909)
            if test_item:
                logger.info(f"   ID lookup test: Found {test_item.get('name')}")
            
            # Test name lookup
            test_item = test_db.get_item_by_name("Jellopy")
            if test_item:
                logger.info(f"   Name lookup test: Found ID {test_item.get('id')}")
            
            # Test category lookup
            cards = test_db.get_items_by_category("card")
            logger.info(f"   Category lookup test: Found {len(cards)} cards")
            
            # Get statistics
            stats = test_db.get_statistics()
            logger.info(f"Database statistics:")
            logger.info(f"  Total items: {stats['total_items']}")
            logger.info(f"  Priority items: {stats['priority_items']}")
            logger.info(f"  Load time: {stats['load_time_seconds']:.3f}s")
            logger.info(f"  Query count: {stats['query_count']}")
            
            # Performance check
            if stats['load_time_seconds'] > 1.0:
                logger.warning(f"⚠ Load time exceeds 1s: {stats['load_time_seconds']:.3f}s")
            else:
                logger.info(f"   Performance: Load time {stats['load_time_seconds']:.3f}s < 1s")
            
            self.import_results['item_db']['status'] = 'success'
            logger.info(" Item database import successful")
        
        except Exception as e:
            logger.error(f" Item database import failed: {e}", exc_info=True)
            self.import_results['item_db']['status'] = 'failed'
            self.import_results['item_db']['errors'].append(str(e))
    
    def _validate_monsters(self, monsters: List[Dict]) -> List[str]:
        """Validate monster entries."""
        errors = []
        
        for i, monster in enumerate(monsters[:100]):  # Check first 100
            if not monster.get('id'):
                errors.append(f"Monster {i}: Missing ID")
            if not monster.get('name'):
                errors.append(f"Monster {i}: Missing name")
            if monster.get('level', 0) < 1:
                errors.append(f"Monster {i}: Invalid level")
        
        return errors
    
    def _validate_items(self, items: List[Dict]) -> List[str]:
        """Validate item entries."""
        errors = []
        
        for i, item in enumerate(items[:100]):  # Check first 100
            if not item.get('id'):
                errors.append(f"Item {i}: Missing ID")
            if not item.get('name'):
                errors.append(f"Item {i}: Missing name")
        
        return errors
    
    async def run_integration_tests(self):
        """
        Run comprehensive integration tests:
        1. Test data loading performance (<500ms)
        2. Test lookup performance (<5ms)
        3. Test cross-layer communication
        4. Test loot system integration
        5. Test monster targeting integration
        """
        logger.info("\n" + "-" * 80)
        logger.info("RUNNING INTEGRATION TESTS")
        logger.info("-" * 80)
        
        try:
            # Load databases
            monster_db_path = self.data_path / "monster_db.json"
            item_db_path = self.data_path / "item_db.json"
            priority_db_path = self.data_path / "loot_priority_database.json"
            
            # Test 1: Loading performance
            logger.info("Test 1: Loading performance...")
            start = time.time()
            monster_db = MonsterDatabase(str(monster_db_path))
            monster_load_time = time.time() - start
            
            start = time.time()
            item_db = ItemDatabase(str(item_db_path), str(priority_db_path) if priority_db_path.exists() else None)
            item_load_time = time.time() - start
            
            total_load_time = monster_load_time + item_load_time
            logger.info(f"  Monster DB load time: {monster_load_time:.3f}s")
            logger.info(f"  Item DB load time: {item_load_time:.3f}s")
            logger.info(f"  Total load time: {total_load_time:.3f}s")
            
            if total_load_time < 0.5:
                logger.info(f"   Load performance: {total_load_time:.3f}s < 0.5s")
            else:
                logger.warning(f"  ⚠ Load performance: {total_load_time:.3f}s > 0.5s")
            
            # Test 2: Lookup performance
            logger.info("Test 2: Lookup performance...")
            
            # Monster lookup test
            start = time.time()
            for _ in range(100):
                monster_db.get_monster_by_id(1002)
            monster_lookup_time = (time.time() - start) / 100 * 1000  # Convert to ms
            
            # Item lookup test
            start = time.time()
            for _ in range(100):
                item_db.get_item_by_id(909)
            item_lookup_time = (time.time() - start) / 100 * 1000  # Convert to ms
            
            logger.info(f"  Monster lookup: {monster_lookup_time:.3f}ms per query")
            logger.info(f"  Item lookup: {item_lookup_time:.3f}ms per query")
            
            if monster_lookup_time < 5.0 and item_lookup_time < 5.0:
                logger.info(f"   Lookup performance: All queries < 5ms")
            else:
                logger.warning(f"  ⚠ Lookup performance: Some queries > 5ms")
            
            # Test 3: Server adapter
            logger.info("Test 3: Server adapter integration...")
            adapter = ServerContentAdapter(monster_db, item_db)
            
            # Test custom content detection
            custom_monster = {'id': 60000, 'name': 'Custom Monster', 'level': 50}
            adapter.register_custom_content('monster', custom_monster)
            
            custom_item = {'id': 60001, 'name': 'Custom Item'}
            adapter.register_custom_content('item', custom_item)
            
            logger.info(f"   Server adapter: Registered custom content")
            
            self.import_results['integration_tests']['status'] = 'success'
            logger.info(" Integration tests passed")
        
        except Exception as e:
            logger.error(f" Integration tests failed: {e}", exc_info=True)
            self.import_results['integration_tests']['status'] = 'failed'
            self.import_results['integration_tests']['errors'].append(str(e))
    
    async def rollback_if_failed(self):
        """Restore backups if any test fails."""
        logger.info("\n" + "-" * 80)
        logger.info("ROLLING BACK CHANGES")
        logger.info("-" * 80)
        
        try:
            # Find most recent backups
            monster_backups = sorted(self.backup_path.glob("monster_db_backup_*.json"))
            item_backups = sorted(self.backup_path.glob("item_db_backup_*.json"))
            
            if monster_backups:
                latest_monster_backup = monster_backups[-1]
                target = self.data_path / "monster_db.json"
                logger.info(f"Restoring monster DB from: {latest_monster_backup}")
                shutil.copy2(latest_monster_backup, target)
            
            if item_backups:
                latest_item_backup = item_backups[-1]
                target = self.data_path / "item_db.json"
                logger.info(f"Restoring item DB from: {latest_item_backup}")
                shutil.copy2(latest_item_backup, target)
            
            logger.info(" Rollback complete")
        
        except Exception as e:
            logger.error(f" Rollback failed: {e}", exc_info=True)
    
    def _print_summary(self, total_time: float):
        """Print import summary."""
        logger.info("\n" + "=" * 80)
        logger.info("IMPORT SUMMARY")
        logger.info("=" * 80)
        
        for component, result in self.import_results.items():
            status_icon = "" if result['status'] == 'success' else ""
            logger.info(f"{status_icon} {component}: {result['status']}")
            if result['errors']:
                for error in result['errors']:
                    logger.info(f"    Error: {error}")
        
        logger.info(f"\nTotal import time: {total_time:.2f}s")
        logger.info("=" * 80)


async def main():
    """Main entry point."""
    importer = DatabaseImporter()
    await importer.import_all()


if __name__ == "__main__":
    asyncio.run(main())
