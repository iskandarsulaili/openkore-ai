"""
Trigger Executor
Executes trigger actions with error handling, timeout protection, and async support
"""

import asyncio
import threading
import time
import importlib
from typing import Dict, Callable, Optional, Any
from loguru import logger

from .models import Trigger, TriggerExecutionResult


class TriggerExecutor:
    """
    Executes trigger actions with comprehensive error handling
    Supports both sync and async execution with timeout protection
    """
    
    def __init__(self, handler_registry: Optional[Dict[str, Callable]] = None):
        """
        Initialize executor with handler registry
        
        Args:
            handler_registry: Dict mapping handler paths to callable functions
        """
        self.handlers = handler_registry or {}
        self.execution_lock = threading.RLock()
        self._execution_count = 0
        self._total_execution_time_ms = 0
    
    def register_handler(self, handler_path: str, handler_func: Callable):
        """
        Register a handler function
        
        Args:
            handler_path: Module path string (e.g., 'autonomous.emergency.heal')
            handler_func: Callable handler function
        """
        with self.execution_lock:
            self.handlers[handler_path] = handler_func
            logger.info(f"Registered trigger handler: {handler_path}")
    
    async def execute_action(self, trigger: Trigger, game_state: Dict) -> TriggerExecutionResult:
        """
        Execute trigger action with timeout and error handling
        
        Args:
            trigger: Trigger containing action to execute
            game_state: Current game state for context
            
        Returns:
            TriggerExecutionResult with success status and result/error
        """
        start_time = time.time()
        
        try:
            # Get handler function
            handler = self._get_handler(trigger.action.handler)
            if handler is None:
                error_msg = f"Handler not found: {trigger.action.handler}"
                logger.error(error_msg)
                return TriggerExecutionResult(
                    success=False,
                    error=error_msg,
                    execution_time_ms=0
                )
            
            # Prepare handler parameters
            params = {**trigger.action.params, 'game_state': game_state}
            
            # Execute based on async flag
            if trigger.action.async_execution:
                result = await self._execute_async(
                    handler, 
                    params, 
                    trigger.action.timeout
                )
            else:
                result = await self._execute_sync(
                    handler,
                    params,
                    trigger.action.timeout
                )
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Update statistics
            with self.execution_lock:
                self._execution_count += 1
                self._total_execution_time_ms += execution_time_ms
            
            logger.info(
                f"Trigger '{trigger.name}' executed successfully in {execution_time_ms:.2f}ms"
            )
            
            return TriggerExecutionResult(
                success=True,
                result=result,
                execution_time_ms=execution_time_ms
            )
            
        except asyncio.TimeoutError:
            execution_time_ms = (time.time() - start_time) * 1000
            error_msg = f"Trigger '{trigger.name}' timed out after {trigger.action.timeout}s"
            logger.error(error_msg)
            
            return TriggerExecutionResult(
                success=False,
                error="timeout",
                execution_time_ms=execution_time_ms
            )
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            error_msg = f"Trigger '{trigger.name}' execution failed: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            
            return TriggerExecutionResult(
                success=False,
                error=str(e),
                execution_time_ms=execution_time_ms
            )
    
    async def _execute_async(self, handler: Callable, params: Dict, timeout: Optional[float]) -> Any:
        """
        Execute async handler with timeout
        
        Args:
            handler: Async callable to execute
            params: Parameters to pass to handler
            timeout: Timeout in seconds (None = no timeout)
            
        Returns:
            Handler result
        """
        if timeout:
            return await asyncio.wait_for(
                handler(**params),
                timeout=timeout
            )
        else:
            return await handler(**params)
    
    async def _execute_sync(self, handler: Callable, params: Dict, timeout: Optional[float]) -> Any:
        """
        Execute synchronous handler in thread pool with timeout
        
        Args:
            handler: Sync callable to execute
            params: Parameters to pass to handler
            timeout: Timeout in seconds (None = no timeout)
            
        Returns:
            Handler result
        """
        loop = asyncio.get_event_loop()
        
        if timeout:
            return await asyncio.wait_for(
                loop.run_in_executor(None, lambda: handler(**params)),
                timeout=timeout
            )
        else:
            return await loop.run_in_executor(None, lambda: handler(**params))
    
    def _get_handler(self, handler_path: str) -> Optional[Callable]:
        """
        Get handler function from registry or dynamically import
        
        Args:
            handler_path: Module path to handler (e.g., 'autonomous.emergency.heal')
            
        Returns:
            Callable handler or None if not found
        """
        # First check registry
        if handler_path in self.handlers:
            return self.handlers[handler_path]
        
        # Try dynamic import
        try:
            parts = handler_path.split('.')
            if len(parts) < 2:
                logger.error(f"Invalid handler path format: {handler_path}")
                return None
            
            # Module path is all but last part
            module_path = '.'.join(parts[:-1])
            function_name = parts[-1]
            
            # Import module
            module = importlib.import_module(module_path)
            handler = getattr(module, function_name, None)
            
            if handler is None:
                logger.error(f"Function '{function_name}' not found in module '{module_path}'")
                return None
            
            # Cache in registry for future use
            with self.execution_lock:
                self.handlers[handler_path] = handler
            
            logger.info(f"Dynamically imported handler: {handler_path}")
            return handler
            
        except ImportError as e:
            logger.error(f"Failed to import handler module '{handler_path}': {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading handler '{handler_path}': {e}")
            return None
    
    def get_statistics(self) -> Dict:
        """Get executor statistics"""
        with self.execution_lock:
            avg_time = (
                self._total_execution_time_ms / self._execution_count 
                if self._execution_count > 0 
                else 0
            )
            
            return {
                "total_executions": self._execution_count,
                "total_execution_time_ms": self._total_execution_time_ms,
                "average_execution_time_ms": avg_time,
                "registered_handlers": len(self.handlers)
            }


# ============================================================================
# BUILT-IN ACTION HANDLERS
# ============================================================================

def handler_emergency_heal(game_state: Dict, method: str = 'fastest_available', **kwargs) -> Dict:
    """
    Emergency healing handler - finds fastest healing method
    
    PHASE 13 FIX: Properly check inventory list structure for healing items
    
    Args:
        game_state: Current game state
        method: Healing method preference
        
    Returns:
        Action dictionary for execution
    """
    logger.info(f"[TRIGGER] Emergency heal triggered with method: {method}")
    
    character = game_state.get('character', {})
    # PHASE 13 CRITICAL FIX: Access the 'items' dict from inventory structure
    # main.py transforms inventory to: {"items": {name: amount}, "item_count": N, ...}
    inventory = game_state.get('inventory', {}).get('items', {})
    
    # Priority order for healing
    # 1. Healing items (fastest)
    # 2. Healing skills
    # 3. Emergency warp/flee
    
    if method == 'fastest_available':
        # PHASE 13 FIX: Check for healing items with proper item_id mapping
        # Priority order: Most effective healing first
        healing_items_priority = [
            ('Red Herb', 507),          # PHASE 13 FIX: Added Red Herb (most common early game)
            ('White Potion', 504),      # 325-405 HP
            ('Yellow Potion', 503),     # 175-235 HP
            ('Red Potion', 501),        # 45-65 HP
            ('Orange Potion', 502),     # 105-145 HP
            ('White Slim Potion', 11518), # Alternative white potion
            ('Apple', 512),             # Basic food healing
            ('Meat', 517),              # Basic food healing
        ]
        
        # PHASE 13 CRITICAL FIX: Iterate through dict of {item_name: amount}
        logger.debug(f"[EMERGENCY-HEAL] Checking inventory for healing items (inventory has {len(inventory)} items)")
        for item_name, item_id in healing_items_priority:
            # Iterate through actual inventory items dict
            for inv_item_name, inv_amount in inventory.items():
                inv_item_name_lower = inv_item_name.lower()
                item_name_lower = item_name.lower()
                
                # Match by name (case-insensitive) and check amount
                if item_name_lower in inv_item_name_lower and inv_amount > 0:
                    logger.info(f"[EMERGENCY-HEAL] Found {inv_item_name} x{inv_amount} - using for emergency healing")
                    return {
                        "action": "use_item",
                        "params": {
                            "item_name": inv_item_name,
                            "item_id": item_id,
                            "amount": 1
                        },
                        "reason": "Emergency HP critical - using fastest healing item"
                    }
        
        # No healing items found - log what we DO have
        logger.warning(f"[EMERGENCY-HEAL] No healing items found in inventory!")
        inv_items = [f"{name} x{amount}" for name, amount in inventory.items()]
        logger.debug(f"[EMERGENCY-HEAL] Inventory contents: {inv_items}")
        
        # Check for healing skill
        skills = character.get('skills', [])
        has_heal_skill = False
        
        if isinstance(skills, list):
            for skill in skills:
                if isinstance(skill, dict):
                    skill_name = skill.get('name', '')
                    if skill_name in ['AL_HEAL', 'Heal'] and skill.get('level', 0) > 0:
                        has_heal_skill = True
                        break
        elif isinstance(skills, dict):
            has_heal_skill = skills.get('AL_HEAL', {}).get('learned', False)
        
        if has_heal_skill:
            logger.info("[EMERGENCY-HEAL] Using Heal skill")
            return {
                "action": "use_skill",
                "params": {"skill_id": "AL_HEAL", "skill_name": "Heal", "target": "self"},
                "reason": "Emergency HP critical - using heal skill"
            }
        
        # Emergency flee - no healing available
        logger.error("[EMERGENCY-HEAL] NO HEALING OPTIONS AVAILABLE - emergency flee")
        return {
            "action": "emergency_flee",
            "params": {"direction": "safe_zone"},
            "reason": "Emergency HP critical - no healing available, fleeing"
        }
    
    return {
        "action": "none",
        "params": {},
        "reason": "No emergency healing action available"
    }


def handler_job_advancement(game_state: Dict, **kwargs) -> Dict:
    """
    Job advancement handler - initiates job change quest/process
    
    Args:
        game_state: Current game state
        
    Returns:
        Action dictionary for job change
    """
    logger.info("Job advancement handler triggered")
    
    character = game_state.get('character', {})
    job_class = character.get('job_class', 'Novice')
    
    if job_class == 'Novice':
        return {
            "action": "start_job_change_quest",
            "params": {
                "from_job": "Novice",
                "destination": "job_change_npc",
                "quest_type": "first_job"
            },
            "reason": "Character ready for first job advancement"
        }
    
    return {
        "action": "none",
        "params": {},
        "reason": "Job advancement not applicable"
    }


def handler_auto_storage(game_state: Dict, trigger_type: str = 'inventory_full', **kwargs) -> Dict:
    """
    Auto storage handler - moves items to storage
    
    Args:
        game_state: Current game state
        trigger_type: What triggered storage (inventory_full, weight_heavy)
        
    Returns:
        Action dictionary for storage
    """
    logger.info(f"Auto storage triggered: {trigger_type}")
    
    return {
        "action": "go_to_storage",
        "params": {
            "reason": trigger_type,
            "store_items": True,
            "item_filter": "non_essential"
        },
        "reason": f"Storage needed: {trigger_type}"
    }


def handler_auto_sell(game_state: Dict, **kwargs) -> Dict:
    """
    Auto sell handler - sells items to NPCs
    
    Args:
        game_state: Current game state
        
    Returns:
        Action dictionary for selling
    """
    logger.info("Auto sell handler triggered")
    
    return {
        "action": "go_to_npc_vendor",
        "params": {
            "action_type": "sell",
            "item_filter": "sellable_junk"
        },
        "reason": "Inventory cleanup needed"
    }


def handler_skill_training(game_state: Dict, skill_id: str = None, **kwargs) -> Dict:
    """
    Skill training handler - uses skill repeatedly for training
    
    Args:
        game_state: Current game state
        skill_id: Skill to train
        
    Returns:
        Action dictionary for skill training
    """
    logger.info(f"Skill training handler triggered for skill: {skill_id}")
    
    return {
        "action": "train_skill",
        "params": {
            "skill_id": skill_id,
            "repetitions": 10,
            "sp_threshold": 20
        },
        "reason": f"Automated skill training: {skill_id}"
    }


def handler_combat_retreat(game_state: Dict, **kwargs) -> Dict:
    """
    Combat retreat handler - tactical retreat from dangerous situation
    
    Args:
        game_state: Current game state
        
    Returns:
        Action dictionary for retreat
    """
    logger.info("Combat retreat triggered")
    
    combat = game_state.get('combat', {})
    hp_percent = game_state.get('character', {}).get('hp_percent', 100)
    
    return {
        "action": "tactical_retreat",
        "params": {
            "distance": 10,
            "heal_after": True,
            "hp_percent": hp_percent
        },
        "reason": "Tactical retreat from dangerous combat situation"
    }
