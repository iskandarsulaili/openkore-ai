"""
Job Advancement Executor
Executes job change process dynamically
Server-agnostic with pattern-based NPC interaction
"""

import asyncio
from pathlib import Path
from typing import Dict, Optional, Any
from loguru import logger
import json
import threading


class JobAdvancementExecutor:
    """
    Executes job advancement process
    Handles navigation, NPC interaction, and verification
    """
    
    def __init__(self, data_dir: Path, openkore_client):
        """
        Initialize job advancement executor
        
        Args:
            data_dir: Directory containing job change location data
            openkore_client: OpenKore HTTP client (REST API) for commands
        """
        self.data_dir = data_dir
        self.openkore = openkore_client
        self.job_locations: Dict[str, Dict] = {}
        self._lock = threading.RLock()
        self._load_job_locations()
        
        logger.info("JobAdvancementExecutor initialized")
    
    def _load_job_locations(self):
        """Load job change NPC locations from configuration"""
        try:
            location_file = self.data_dir / "job_change_locations.json"
            
            if location_file.exists():
                with open(location_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.job_locations = data.get('locations', {})
                logger.success(f"Loaded locations for {len(self.job_locations)} jobs")
            else:
                logger.warning("Job location file not found, using fallback")
                self._create_default_locations()
                
        except Exception as e:
            logger.error(f"Failed to load job locations: {e}")
            self._create_default_locations()
    
    def _create_default_locations(self):
        """Create default job change locations"""
        self.job_locations = {
            "Swordman": {
                "map": "izlude_in",
                "x": 74,
                "y": 172,
                "npc_pattern": "Swordman.*Guild"
            },
            "Mage": {
                "map": "geffen_in",
                "x": 163,
                "y": 98,
                "npc_pattern": "Mage.*Guild"
            },
            "Archer": {
                "map": "payon_in02",
                "x": 64,
                "y": 71,
                "npc_pattern": "Archer.*Guild"
            },
            "Acolyte": {
                "map": "prt_church",
                "x": 184,
                "y": 41,
                "npc_pattern": "Priest|Acolyte.*Guild"
            },
            "Merchant": {
                "map": "alberta_in",
                "x": 53,
                "y": 43,
                "npc_pattern": "Merchant.*Guild"
            },
            "Thief": {
                "map": "moc_prydb1",
                "x": 42,
                "y": 133,
                "npc_pattern": "Thief.*Guild"
            }
        }
    
    async def execute_job_change(
        self,
        current_job: str,
        target_job: str,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute complete job change process
        
        Args:
            current_job: Current job class
            target_job: Target job class
            game_state: Current game state
            
        Returns:
            Dictionary with execution result
        """
        with self._lock:
            logger.info(f"Starting job change: {current_job} → {target_job}")
            
            try:
                # Get location info for target job
                location = self.job_locations.get(target_job)
                
                if not location:
                    logger.error(f"No location data for job: {target_job}")
                    return {
                        'success': False,
                        'error': f"Unknown job location: {target_job}"
                    }
                
                # Step 1: Navigate to job change location
                logger.info(f"Step 1: Navigating to {location['map']} ({location['x']}, {location['y']})")
                nav_success = await self._navigate_to_location(location)
                
                if not nav_success:
                    return {
                        'success': False,
                        'error': "Navigation failed",
                        'step': 'navigation'
                    }
                
                # Step 2: Find and interact with NPC
                logger.info(f"Step 2: Looking for NPC matching: {location.get('npc_pattern', 'Job Change')}")
                npc_success = await self._interact_with_job_npc(location)
                
                if not npc_success:
                    return {
                        'success': False,
                        'error': "NPC interaction failed",
                        'step': 'npc_interaction'
                    }
                
                # Step 3: Complete job change quest/dialogue
                logger.info("Step 3: Completing job change dialogue")
                quest_success = await self._complete_job_change_dialogue(target_job)
                
                if not quest_success:
                    return {
                        'success': False,
                        'error': "Job change dialogue failed",
                        'step': 'dialogue'
                    }
                
                # Step 4: Verify job change success
                await asyncio.sleep(3)  # Wait for job change to process
                verify_success = await self._verify_job_change(target_job)
                
                if verify_success:
                    logger.success(f"Job change successful: {current_job} → {target_job}")
                    return {
                        'success': True,
                        'old_job': current_job,
                        'new_job': target_job,
                        'location': location['map']
                    }
                else:
                    logger.warning("Job change verification failed")
                    return {
                        'success': False,
                        'error': "Job change verification failed",
                        'step': 'verification'
                    }
                
            except Exception as e:
                logger.error(f"Job change execution error: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'step': 'exception'
                }
    
    async def _navigate_to_location(self, location: Dict) -> bool:
        """
        Navigate to job change location
        
        Args:
            location: Location dictionary with map and coordinates
            
        Returns:
            True if navigation successful
        """
        try:
            map_name = location['map']
            x = location['x']
            y = location['y']
            
            # Send move command to OpenKore
            command = f"move {map_name} {x} {y}"
            await self.openkore.send_command(command)
            
            # Wait for arrival (with timeout)
            for i in range(30):  # 30 second timeout
                await asyncio.sleep(1)
                
                # Check if arrived
                current_state = await self.openkore.get_game_state()
                if current_state:
                    current_map = current_state.get('character', {}).get('map', '')
                    current_x = current_state.get('character', {}).get('pos_x', 0)
                    current_y = current_state.get('character', {}).get('pos_y', 0)
                    
                    # Check if close enough (within 5 cells)
                    if current_map == map_name:
                        distance = abs(current_x - x) + abs(current_y - y)
                        if distance <= 5:
                            logger.success(f"Arrived at {map_name} ({current_x}, {current_y})")
                            return True
            
            logger.error(f"Navigation timeout to {map_name}")
            return False
            
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            return False
    
    async def _interact_with_job_npc(self, location: Dict) -> bool:
        """
        Find and interact with job change NPC
        
        Args:
            location: Location with NPC pattern
            
        Returns:
            True if interaction successful
        """
        try:
            # Use pattern to find NPC
            npc_pattern = location.get('npc_pattern', '')
            
            # Send talk command (OpenKore will find matching NPC)
            command = f"talk /.*{npc_pattern}.*/"
            await self.openkore.send_command(command)
            
            # Wait for dialogue to open
            await asyncio.sleep(2)
            
            return True
            
        except Exception as e:
            logger.error(f"NPC interaction error: {e}")
            return False
    
    async def _complete_job_change_dialogue(self, target_job: str) -> bool:
        """
        Complete job change NPC dialogue
        
        Args:
            target_job: Target job class
            
        Returns:
            True if dialogue completed
        """
        try:
            # Most job change dialogues follow pattern:
            # 1. Initial greeting → select "I want to change job"
            # 2. Confirmation → select "Yes"
            # 3. Job selection (if multiple) → select target job
            
            # Send dialogue responses
            responses = [
                "talk resp 0",  # First option (usually job change request)
                "talk resp 0",  # Confirmation
                "talk resp 0"   # Final confirmation
            ]
            
            for response in responses:
                await self.openkore.send_command(response)
                await asyncio.sleep(1.5)
            
            logger.info("Job change dialogue sequence completed")
            return True
            
        except Exception as e:
            logger.error(f"Dialogue completion error: {e}")
            return False
    
    async def _verify_job_change(self, expected_job: str) -> bool:
        """
        Verify job change was successful
        
        Args:
            expected_job: Expected new job class
            
        Returns:
            True if job changed successfully
        """
        try:
            current_state = await self.openkore.get_game_state()
            
            if current_state:
                current_job = current_state.get('character', {}).get('job_class', '')
                
                if current_job == expected_job:
                    logger.success(f"Job verification successful: {current_job}")
                    return True
                else:
                    logger.warning(f"Job mismatch: expected {expected_job}, got {current_job}")
                    return False
            
            logger.error("Failed to get game state for verification")
            return False
            
        except Exception as e:
            logger.error(f"Verification error: {e}")
            return False
    
    def get_estimated_duration(self, target_job: str) -> int:
        """
        Estimate job change duration in seconds
        
        Args:
            target_job: Target job class
            
        Returns:
            Estimated duration in seconds
        """
        # Base duration: 60 seconds
        # Add distance factor based on map
        location = self.job_locations.get(target_job, {})
        base_duration = 60
        
        # Remote locations add time
        remote_maps = ['hu_in01', 'monk_in', 'ein_in01']
        if location.get('map', '') in remote_maps:
            base_duration += 120
        
        return base_duration
