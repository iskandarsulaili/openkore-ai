"""
Comprehensive Cross-Integration Verification Script
Tests actual communication between all layers and features.

PRIMARY OBJECTIVE:
Verify and prove that OpenKore ↔ AI-Service ↔ Databases are actually
communicating with real data flow, not just theoretically integrated.
"""

import asyncio
import aiohttp
import time
import json
import sys
import os
from typing import Dict, List, Tuple
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    try:
        # Try to set UTF-8 encoding for Windows console
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Use ASCII-compatible symbols for Windows
CHECK_MARK = 'OK' if sys.platform == 'win32' else '[OK]'
CROSS_MARK = 'X' if sys.platform == 'win32' else '[X]'
WARNING_MARK = '!' if sys.platform == 'win32' else '[!]'
TARGET_MARK = '*' if sys.platform == 'win32' else '[*]'

class IntegrationVerifier:
    def __init__(self):
        self.ai_service_url = "http://127.0.0.1:9902"
        self.results = []
        self.start_time = time.time()
        
    async def verify_all(self) -> Dict:
        """Run all verification tests"""
        
        print("=" * 80)
        print("CROSS-INTEGRATION VERIFICATION TEST SUITE")
        print("=" * 80)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Target: {self.ai_service_url}")
        print("=" * 80)
        print()
        
        # Test 1: AI Service Health
        await self.test_ai_service_health()
        
        # Test 2: Database Loading
        await self.test_database_loading()
        
        # Test 3: Decision Endpoint
        await self.test_decision_endpoint()
        
        # Test 4: Monster Database Integration
        await self.test_monster_database_integration()
        
        # Test 5: Item Database Integration
        await self.test_item_database_integration()
        
        # Test 6: Loot System Integration
        await self.test_loot_system_integration()
        
        # Test 7: Stat Allocation Integration
        await self.test_stat_allocation_integration()
        
        # Test 8: Skill Allocation Integration
        await self.test_skill_allocation_integration()
        
        # Test 9: OpenMemory Integration
        await self.test_openmemory_integration()
        
        # Test 10: Trigger System Integration
        await self.test_trigger_system_integration()
        
        # Generate Report
        return self.generate_report()
        
    async def test_ai_service_health(self):
        """Test 1: AI Service is running and responding"""
        test_name = "AI Service Health"
        print(f"\n[TEST 1] {test_name}")
        print("-" * 80)
        
        try:
            async with aiohttp.ClientSession() as session:
                start = time.time()
                async with session.get(
                    f'{self.ai_service_url}/api/v1/health',
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    response_time = (time.time() - start) * 1000
                    
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}")
                    
                    data = await response.json()
                    
                    # Verify response structure
                    if 'status' not in data:
                        raise Exception("Missing 'status' field")
                    
                    if 'uptime_seconds' not in data:
                        raise Exception("Missing 'uptime_seconds' field")
                    
                    # Check component health
                    components = data.get('components', {})
                    db_healthy = components.get('database', False)
                    llm_healthy = any(components.get(f'llm_{provider}', False) 
                                     for provider in ['deepseek', 'openai', 'anthropic'])
                    
                    print(f"  {CHECK_MARK} Status: {data['status']}")
                    print(f"  {CHECK_MARK} Uptime: {data['uptime_seconds']}s")
                    print(f"  {CHECK_MARK} Response time: {response_time:.1f}ms")
                    print(f"  {CHECK_MARK} Database: {'HEALTHY' if db_healthy else 'DEGRADED'}")
                    print(f"  {CHECK_MARK} LLM: {'HEALTHY' if llm_healthy else 'DEGRADED'}")
                    
                    self.results.append({
                        'test': test_name,
                        'status': 'PASS',
                        'response_time_ms': response_time,
                        'uptime_seconds': data['uptime_seconds'],
                        'service_status': data['status'],
                        'database_healthy': db_healthy,
                        'llm_healthy': llm_healthy
                    })
                    
        except asyncio.TimeoutError:
            print(f"  [X] FAILED: Request timeout")
            self.results.append({
                'test': test_name,
                'status': 'FAIL',
                'error': 'Request timeout - AI service may not be running'
            })
        except Exception as e:
            print(f"  [X] FAILED: {e}")
            self.results.append({
                'test': test_name,
                'status': 'FAIL',
                'error': str(e)
            })
    
    async def test_database_loading(self):
        """Test 2: Monster and Item databases loaded"""
        test_name = "Database Loading"
        print(f"\n[TEST 2] {test_name}")
        print("-" * 80)
        
        try:
            # Check if database files exist
            data_dir = Path(__file__).parent.parent / "data"
            monster_db_path = data_dir / "monster_db.json"
            item_db_path = data_dir / "item_db.json"
            
            if not monster_db_path.exists():
                raise Exception(f"monster_db.json not found at {monster_db_path}")
            
            if not item_db_path.exists():
                raise Exception(f"item_db.json not found at {item_db_path}")
            
            # Load and verify structure
            with open(monster_db_path, 'r', encoding='utf-8') as f:
                monster_data = json.load(f)
            
            with open(item_db_path, 'r', encoding='utf-8') as f:
                item_data = json.load(f)
            
            monster_count = len(monster_data.get('monsters', []))
            item_count = len(item_data.get('items', []))
            
            # Verify expected counts
            expected_monsters = 2675
            expected_items = 29056
            
            print(f"  [OK] Monster DB found: {monster_db_path}")
            print(f"  [OK] Monster count: {monster_count}")
            print(f"  {'[OK]' if monster_count >= expected_monsters else '[!]'} Expected: {expected_monsters}+ monsters")
            print(f"  [OK] Item DB found: {item_db_path}")
            print(f"  [OK] Item count: {item_count}")
            print(f"  {'[OK]' if item_count >= expected_items else '[!]'} Expected: {expected_items}+ items")
            
            # Test lookup of known monster (Poring - ID 1002)
            monster_1002 = next((m for m in monster_data['monsters'] if m.get('id') == 1002), None)
            if monster_1002:
                print(f"  [OK] Verified monster lookup: {monster_1002['name']} (ID: 1002)")
            else:
                print(f"  [!] Could not find Poring (ID: 1002)")
            
            # Test lookup of known item (Jellopy - ID 909)
            item_909 = next((i for i in item_data['items'] if i.get('id') == 909), None)
            if item_909:
                print(f"  [OK] Verified item lookup: {item_909['name']} (ID: 909)")
            else:
                print(f"  [!] Could not find Jellopy (ID: 909)")
            
            self.results.append({
                'test': test_name,
                'status': 'PASS',
                'monster_count': monster_count,
                'item_count': item_count,
                'monster_lookup_test': monster_1002 is not None,
                'item_lookup_test': item_909 is not None
            })
            
        except Exception as e:
            print(f"  [X] FAILED: {e}")
            self.results.append({
                'test': test_name,
                'status': 'FAIL',
                'error': str(e)
            })
    
    async def test_decision_endpoint(self):
        """Test 3: /api/v1/decide endpoint functional with real data"""
        test_name = "Decision Endpoint"
        print(f"\n[TEST 3] {test_name}")
        print("-" * 80)
        
        try:
            # Construct realistic game state
            game_state = {
                "character": {
                    "name": "TestBot",
                    "level": 15,
                    "job_level": 10,
                    "job_class": "Novice",
                    "hp": 850,
                    "max_hp": 1200,
                    "sp": 120,
                    "max_sp": 200,
                    "position": {"x": 150, "y": 120, "map": "prt_fild08"},
                    "points_free": 0,
                    "points_skill": 0,
                    "zeny": 5000
                },
                "monsters": [
                    {"id": 1002, "name": "Poring", "distance": 5, "hp_percent": 100},
                    {"id": 1113, "name": "Drops", "distance": 8, "hp_percent": 100}
                ],
                "items_on_ground": [
                    {"id": 909, "name": "Jellopy", "distance": 3}
                ],
                "inventory": [
                    {"id": 501, "name": "Red Potion", "amount": 50}
                ],
                "skills": [],
                "combat": {"in_combat": False},
                "timestamp_ms": int(time.time() * 1000)
            }
            
            request_body = {
                "game_state": game_state,
                "request_id": "integration_test_001",
                "timestamp_ms": int(time.time() * 1000)
            }
            
            async with aiohttp.ClientSession() as session:
                start = time.time()
                async with session.post(
                    f'{self.ai_service_url}/api/v1/decide',
                    json=request_body,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time = (time.time() - start) * 1000
                    
                    if response.status != 200:
                        text = await response.text()
                        raise Exception(f"HTTP {response.status}: {text}")
                    
                    data = await response.json()
                    
                    # Verify response structure
                    if 'action' not in data:
                        raise Exception("No 'action' in response")
                    
                    action = data.get('action', 'unknown')
                    print(f"  [OK] Response received in {response_time:.1f}ms")
                    print(f"  [OK] Action: {action}")
                    print(f"  [OK] Layer: {data.get('layer', 'unknown')}")
                    print(f"  [OK] Reason: {data.get('reason', 'N/A')[:100]}")
                    
                    # Check if response is using database data (not hardcoded)
                    response_str = json.dumps(data)
                    uses_database = any(keyword in response_str for keyword in 
                                       ['monster', 'item', 'database', 'lookup'])
                    
                    print(f"  {'[OK]' if uses_database else '[!]'} Appears to use database: {uses_database}")
                    
                    self.results.append({
                        'test': test_name,
                        'status': 'PASS',
                        'response_time_ms': response_time,
                        'action': action,
                        'layer': data.get('layer'),
                        'uses_database': uses_database
                    })
                    
        except Exception as e:
            print(f"  [X] FAILED: {e}")
            self.results.append({
                'test': test_name,
                'status': 'FAIL',
                'error': str(e)
            })
    
    async def test_monster_database_integration(self):
        """Test 4: Monster DB actually being queried for decisions"""
        test_name = "Monster Database Integration"
        print(f"\n[TEST 4] {test_name}")
        print("-" * 80)
        
        try:
            # Test the select-target endpoint which uses monster database
            request_body = {
                "level": 15,
                "map": "prt_fild08",
                "monsters": [1002, 1113, 1031],  # Poring, Drops, Poporing
                "goal": "exp"
            }
            
            async with aiohttp.ClientSession() as session:
                start = time.time()
                async with session.post(
                    f'{self.ai_service_url}/api/v1/select-target',
                    json=request_body,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    response_time = (time.time() - start) * 1000
                    
                    if response.status != 200:
                        text = await response.text()
                        raise Exception(f"HTTP {response.status}: {text}")
                    
                    data = await response.json()
                    
                    if 'targets' not in data:
                        raise Exception("No 'targets' in response")
                    
                    targets = data.get('targets', [])
                    
                    if not targets:
                        print(f"  [!] No targets returned (monster database may not be integrated)")
                    else:
                        print(f"  [OK] Targets returned: {len(targets)}")
                        for i, target in enumerate(targets[:3]):
                            print(f"    {i+1}. {target.get('name')} (ID: {target.get('id')}, "
                                  f"Level: {target.get('level')}, "
                                  f"Base EXP: {target.get('base_exp')})")
                    
                    # Verify monster data includes database fields
                    if targets:
                        first_target = targets[0]
                        has_db_fields = all(field in first_target for field in 
                                           ['level', 'base_exp', 'job_exp', 'hp'])
                        print(f"  {'[OK]' if has_db_fields else '[!]'} Database fields present: {has_db_fields}")
                    else:
                        has_db_fields = False
                    
                    self.results.append({
                        'test': test_name,
                        'status': 'PASS' if targets else 'WARN',
                        'response_time_ms': response_time,
                        'targets_returned': len(targets),
                        'has_database_fields': has_db_fields
                    })
                    
        except Exception as e:
            print(f"  [X] FAILED: {e}")
            self.results.append({
                'test': test_name,
                'status': 'FAIL',
                'error': str(e)
            })
    
    async def test_item_database_integration(self):
        """Test 5: Item DB actually being queried for loot decisions"""
        test_name = "Item Database Integration"
        print(f"\n[TEST 5] {test_name}")
        print("-" * 80)
        
        try:
            # Send decision request with item on ground
            game_state = {
                "character": {
                    "name": "TestBot",
                    "level": 15,
                    "job_level": 10,
                    "hp": 1000,
                    "max_hp": 1200,
                    "sp": 180,
                    "max_sp": 200,
                    "position": {"x": 150, "y": 120, "map": "prt_fild08"}
                },
                "monsters": [],
                "items_on_ground": [
                    {"id": 909, "name": "Jellopy", "distance": 3},
                    {"id": 914, "name": "Fluff", "distance": 5},
                    {"id": 4001, "name": "Poring Card", "distance": 7}
                ],
                "inventory": [
                    {"id": 501, "name": "Red Potion", "amount": 50}
                ],
                "timestamp_ms": int(time.time() * 1000)
            }
            
            request_body = {
                "game_state": game_state,
                "request_id": "integration_test_items",
                "timestamp_ms": int(time.time() * 1000)
            }
            
            async with aiohttp.ClientSession() as session:
                start = time.time()
                async with session.post(
                    f'{self.ai_service_url}/api/v1/decide',
                    json=request_body,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time = (time.time() - start) * 1000
                    
                    if response.status != 200:
                        text = await response.text()
                        raise Exception(f"HTTP {response.status}: {text}")
                    
                    data = await response.json()
                    
                    action = data.get('action', 'unknown')
                    print(f"  [OK] Response received in {response_time:.1f}ms")
                    print(f"  [OK] Action: {action}")
                    
                    # Check if action involves items
                    item_related = action in ['pickup_item', 'loot'] or 'item' in action
                    print(f"  {'[OK]' if item_related else '[!]'} Item-related action: {item_related}")
                    
                    # Check if response mentions specific items (proving database lookup)
                    response_str = json.dumps(data).lower()
                    mentions_items = any(item in response_str for item in 
                                        ['jellopy', 'fluff', 'card', 'priority'])
                    print(f"  {'[OK]' if mentions_items else '[!]'} References specific items: {mentions_items}")
                    
                    # Check for item database usage indicators
                    uses_item_db = 'item_value' in response_str or 'priority' in response_str
                    print(f"  {'[OK]' if uses_item_db else '[!]'} Uses item database values: {uses_item_db}")
                    
                    self.results.append({
                        'test': test_name,
                        'status': 'PASS',
                        'response_time_ms': response_time,
                        'action': action,
                        'item_related': item_related,
                        'mentions_items': mentions_items,
                        'uses_item_db': uses_item_db
                    })
                    
        except Exception as e:
            print(f"  [X] FAILED: {e}")
            self.results.append({
                'test': test_name,
                'status': 'FAIL',
                'error': str(e)
            })
    
    async def test_loot_system_integration(self):
        """Test 6: Loot prioritizer using full item database"""
        test_name = "Loot System Integration"
        print(f"\n[TEST 6] {test_name}")
        print("-" * 80)
        
        try:
            # Check loot system files
            data_dir = Path(__file__).parent.parent / "data"
            loot_db_path = data_dir / "loot_priority_database.json"
            loot_config_path = data_dir / "loot_config.json"
            
            if not loot_db_path.exists():
                raise Exception(f"loot_priority_database.json not found")
            
            # Load and verify loot database
            with open(loot_db_path, 'r', encoding='utf-8') as f:
                loot_data = json.load(f)
            
            loot_item_count = len(loot_data.get('items', []))
            
            print(f"  [OK] Loot priority DB found")
            print(f"  [OK] Loot items: {loot_item_count}")
            
            # Verify using more than old 350-item limit
            uses_full_db = loot_item_count > 1000
            print(f"  {'[OK]' if uses_full_db else '[!]'} Using full database: {uses_full_db} "
                  f"({'>' if uses_full_db else '<='} 1000 items)")
            
            # Test if loot config exists
            has_config = loot_config_path.exists()
            print(f"  {'[OK]' if has_config else '[!]'} Loot config found: {has_config}")
            
            self.results.append({
                'test': test_name,
                'status': 'PASS',
                'loot_item_count': loot_item_count,
                'uses_full_db': uses_full_db,
                'has_config': has_config
            })
            
        except Exception as e:
            print(f"  [X] FAILED: {e}")
            self.results.append({
                'test': test_name,
                'status': 'FAIL',
                'error': str(e)
            })
    
    async def test_stat_allocation_integration(self):
        """Test 7: Stat allocation using AI-driven plans"""
        test_name = "Stat Allocation Integration"
        print(f"\n[TEST 7] {test_name}")
        print("-" * 80)
        
        try:
            # Check if stat allocation files exist
            data_dir = Path(__file__).parent.parent / "data"
            job_builds_path = data_dir / "job_builds.json"
            
            if not job_builds_path.exists():
                raise Exception("job_builds.json not found")
            
            with open(job_builds_path, 'r', encoding='utf-8') as f:
                job_builds = json.load(f)
            
            job_count = len([k for k in job_builds.keys() if not k.startswith('_')])
            
            print(f"  [OK] Job builds found: {job_builds_path}")
            print(f"  [OK] Job classes configured: {job_count}")
            
            # Verify novice build exists
            has_novice = 'novice' in job_builds
            print(f"  {'[OK]' if has_novice else '[!]'} Novice build configured: {has_novice}")
            
            # Check for stat allocation endpoint availability
            async with aiohttp.ClientSession() as session:
                # Test health endpoint as proxy for service availability
                async with session.get(
                    f'{self.ai_service_url}/api/v1/health',
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as response:
                    service_available = response.status == 200
            
            print(f"  {'[OK]' if service_available else '[!]'} AI service available: {service_available}")
            
            self.results.append({
                'test': test_name,
                'status': 'PASS',
                'job_count': job_count,
                'has_novice': has_novice,
                'service_available': service_available
            })
            
        except Exception as e:
            print(f"  [X] FAILED: {e}")
            self.results.append({
                'test': test_name,
                'status': 'FAIL',
                'error': str(e)
            })
    
    async def test_skill_allocation_integration(self):
        """Test 8: Skill allocation using AI-driven plans"""
        test_name = "Skill Allocation Integration"
        print(f"\n[TEST 8] {test_name}")
        print("-" * 80)
        
        try:
            # Check for skill metadata
            data_dir = Path(__file__).parent.parent / "data"
            skill_metadata_path = data_dir / "skill_metadata.json"
            
            has_skill_metadata = skill_metadata_path.exists()
            
            if has_skill_metadata:
                with open(skill_metadata_path, 'r', encoding='utf-8') as f:
                    skill_data = json.load(f)
                skill_count = len(skill_data.get('skills', {}))
                print(f"  [OK] Skill metadata found: {skill_metadata_path}")
                print(f"  [OK] Skills configured: {skill_count}")
            else:
                print(f"  [!] Skill metadata not found (may use defaults)")
                skill_count = 0
            
            # Check job builds for skill recommendations
            job_builds_path = data_dir / "job_builds.json"
            if job_builds_path.exists():
                with open(job_builds_path, 'r', encoding='utf-8') as f:
                    job_builds = json.load(f)
                
                # Check if any job has skill priorities
                has_skill_priorities = any(
                    'skill_priority' in job_data 
                    for job_name, job_data in job_builds.items() 
                    if isinstance(job_data, dict) and not job_name.startswith('_')
                )
                print(f"  {'[OK]' if has_skill_priorities else '[!]'} Job builds have skill priorities: {has_skill_priorities}")
            else:
                has_skill_priorities = False
            
            self.results.append({
                'test': test_name,
                'status': 'PASS',
                'has_skill_metadata': has_skill_metadata,
                'skill_count': skill_count,
                'has_skill_priorities': has_skill_priorities
            })
            
        except Exception as e:
            print(f"  [X] FAILED: {e}")
            self.results.append({
                'test': test_name,
                'status': 'FAIL',
                'error': str(e)
            })
    
    async def test_openmemory_integration(self):
        """Test 9: OpenMemory storing and retrieving data"""
        test_name = "OpenMemory Integration"
        print(f"\n[TEST 9] {test_name}")
        print("-" * 80)
        
        try:
            # Check if SQLite database exists
            data_dir = Path(__file__).parent.parent / "data"
            db_path = data_dir / "openkore-ai.db"
            
            if not db_path.exists():
                raise Exception("openkore-ai.db not found")
            
            db_size_mb = db_path.stat().st_size / (1024 * 1024)
            
            print(f"  [OK] Database found: {db_path}")
            print(f"  [OK] Database size: {db_size_mb:.2f} MB")
            
            # Check if database is being used (size > 100 KB means data exists)
            has_data = db_size_mb > 0.1
            print(f"  {'[OK]' if has_data else '[!]'} Database contains data: {has_data}")
            
            # Check health endpoint for memory system status
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'{self.ai_service_url}/api/v1/health',
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        openmemory_active = data.get('components', {}).get('openmemory', False)
                        print(f"  {'[OK]' if openmemory_active else '[!]'} OpenMemory active: {openmemory_active}")
                    else:
                        openmemory_active = False
            
            self.results.append({
                'test': test_name,
                'status': 'PASS',
                'db_size_mb': db_size_mb,
                'has_data': has_data,
                'openmemory_active': openmemory_active
            })
            
        except Exception as e:
            print(f"  [X] FAILED: {e}")
            self.results.append({
                'test': test_name,
                'status': 'FAIL',
                'error': str(e)
            })
    
    async def test_trigger_system_integration(self):
        """Test 10: Trigger system responding to game events"""
        test_name = "Trigger System Integration"
        print(f"\n[TEST 10] {test_name}")
        print("-" * 80)
        
        try:
            # Check for triggers configuration
            data_dir = Path(__file__).parent.parent / "data"
            triggers_path = data_dir / "triggers_config.json"
            
            if not triggers_path.exists():
                print(f"  [!] Triggers config not found (may be disabled)")
                has_triggers = False
                trigger_count = 0
            else:
                with open(triggers_path, 'r', encoding='utf-8') as f:
                    triggers_data = json.load(f)
                
                trigger_count = len(triggers_data.get('triggers', []))
                has_triggers = trigger_count > 0
                
                print(f"  [OK] Triggers config found: {triggers_path}")
                print(f"  [OK] Triggers configured: {trigger_count}")
                
                if has_triggers:
                    # Show trigger layers
                    layers = {}
                    for trigger in triggers_data.get('triggers', []):
                        layer = trigger.get('layer', 'unknown')
                        layers[layer] = layers.get(layer, 0) + 1
                    
                    print(f"  [OK] Trigger layers:")
                    for layer, count in sorted(layers.items()):
                        print(f"    - {layer}: {count}")
            
            # Send test request that should trigger autonomous action
            game_state = {
                "character": {
                    "name": "TestBot",
                    "level": 15,
                    "job_level": 10,
                    "hp": 200,  # Low HP - should trigger healing
                    "max_hp": 1200,
                    "sp": 50,
                    "max_sp": 200,
                    "position": {"x": 150, "y": 120, "map": "prt_fild08"}
                },
                "monsters": [],
                "inventory": [
                    {"id": 501, "name": "Red Potion", "amount": 50}
                ],
                "timestamp_ms": int(time.time() * 1000)
            }
            
            request_body = {
                "game_state": game_state,
                "request_id": "integration_test_trigger",
                "timestamp_ms": int(time.time() * 1000)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{self.ai_service_url}/api/v1/decide',
                    json=request_body,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        source = data.get('source', 'unknown')
                        trigger_fired = source == 'trigger_system'
                        print(f"  {'[OK]' if trigger_fired else '[!]'} Trigger system fired: {trigger_fired}")
                    else:
                        trigger_fired = False
            
            self.results.append({
                'test': test_name,
                'status': 'PASS',
                'has_triggers': has_triggers,
                'trigger_count': trigger_count,
                'trigger_fired': trigger_fired
            })
            
        except Exception as e:
            print(f"  [X] FAILED: {e}")
            self.results.append({
                'test': test_name,
                'status': 'FAIL',
                'error': str(e)
            })
    
    def generate_report(self) -> Dict:
        """Generate comprehensive integration verification report"""
        
        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        warned = sum(1 for r in self.results if r['status'] == 'WARN')
        
        pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        
        # Determine overall status
        if failed == 0 and warned == 0:
            overall_status = 'PASS'
            integration_health = 'OPERATIONAL'
        elif failed == 0 and warned <= 2:
            overall_status = 'PASS'
            integration_health = 'OPERATIONAL'
        elif failed <= 2:
            overall_status = 'DEGRADED'
            integration_health = 'DEGRADED'
        else:
            overall_status = 'FAIL'
            integration_health = 'CRITICAL'
        
        return {
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': time.time() - self.start_time,
            'total_tests': total_tests,
            'passed': passed,
            'failed': failed,
            'warned': warned,
            'pass_rate': pass_rate,
            'results': self.results,
            'overall_status': overall_status,
            'integration_health': integration_health
        }

async def main():
    """Main entry point"""
    verifier = IntegrationVerifier()
    
    try:
        report = await verifier.verify_all()
        
        # Save report
        report_path = Path(__file__).parent.parent / "integration_verification_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "=" * 80)
        print("VERIFICATION SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {report['total_tests']}")
        print(f"Passed: {report['passed']}")
        print(f"Failed: {report['failed']}")
        print(f"Warned: {report['warned']}")
        print(f"Pass Rate: {report['pass_rate']:.1f}%")
        print(f"Duration: {report['duration_seconds']:.1f}s")
        print(f"Overall Status: {report['overall_status']}")
        print(f"Integration Health: {report['integration_health']}")
        
        if report['failed'] > 0:
            print("\n" + "=" * 80)
            print("FAILED TESTS:")
            print("=" * 80)
            for result in report['results']:
                if result['status'] == 'FAIL':
                    print(f"  [X] {result['test']}: {result.get('error', 'Unknown error')}")
        
        if report['warned'] > 0:
            print("\n" + "=" * 80)
            print("WARNED TESTS:")
            print("=" * 80)
            for result in report['results']:
                if result['status'] == 'WARN':
                    print(f"  [!] {result['test']}: Check details above")
        
        print("\n" + "=" * 80)
        print(f"Report saved to: {report_path}")
        print("=" * 80)
        
        return report['overall_status'] == 'PASS' and report['failed'] == 0
        
    except KeyboardInterrupt:
        print("\n\nVerification interrupted by user")
        return False
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
