"""
Trigger Coordinator
Coordinates trigger execution across layers with priority management and interrupt handling
"""

import asyncio
import threading
from typing import Dict, Optional, List
from loguru import logger

from .models import Trigger, LayerPriority, TriggerExecutionResult
from .trigger_registry import TriggerRegistry
from .trigger_evaluator import TriggerEvaluator
from .trigger_executor import TriggerExecutor
from .state_manager import StateManager


class TriggerCoordinator:
    """
    Coordinates trigger execution across all layers
    Manages priority, interrupts, and layer transitions
    """
    
    def __init__(
        self,
        registry: TriggerRegistry,
        evaluator: TriggerEvaluator,
        executor: TriggerExecutor,
        state_manager: StateManager
    ):
        """
        Initialize coordinator with all required components
        
        Args:
            registry: Trigger registry instance
            evaluator: Condition evaluator instance
            executor: Action executor instance
            state_manager: State manager instance
        """
        self.registry = registry
        self.evaluator = evaluator
        self.executor = executor
        self.state = state_manager
        
        # Execution state
        self.active_layer: Optional[LayerPriority] = None
        self.interrupt_requested: bool = False
        self._coordination_lock = threading.RLock()
        
        # Statistics
        self._total_checks = 0
        self._total_triggers_fired = 0
        self._layer_execution_count = {layer: 0 for layer in LayerPriority}
        
        logger.info("TriggerCoordinator initialized")
    
    async def process_game_state(self, game_state: Dict) -> Optional[Dict]:
        """
        Process game state through all layers respecting priority
        
        This is the main entry point for the trigger system.
        Checks layers in priority order: REFLEX → TACTICAL → SUBCONSCIOUS → CONSCIOUS
        SYSTEM layer runs in parallel as background tasks
        
        Args:
            game_state: Current game state dictionary
            
        Returns:
            Action dictionary if a trigger fired, None otherwise
        """
        self._total_checks += 1
        
        try:
            # Store game state in state manager for cross-layer access
            self.state.set('last_game_state', game_state)
            self.state.set('last_check_timestamp', asyncio.get_event_loop().time())
            
            # Check layers in priority order (lower enum value = higher priority)
            priority_order = [
                LayerPriority.REFLEX,
                LayerPriority.TACTICAL,
                LayerPriority.SUBCONSCIOUS,
                LayerPriority.CONSCIOUS
            ]
            
            for layer in priority_order:
                # Check if higher priority layer needs interrupt
                if self._should_interrupt_for_higher_priority():
                    logger.warning("Interrupt requested for higher priority layer")
                    break
                
                # Process layer
                action = await self._check_layer(layer, game_state)
                
                if action:
                    logger.info(f"Layer {layer.name} produced action: {action.get('action', 'unknown')}")
                    return action
            
            # Process SYSTEM layer in background (don't wait for result)
            asyncio.create_task(
                self._check_layer_background(LayerPriority.SYSTEM, game_state)
            )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in trigger coordinator: {e}")
            logger.exception(e)
            return None
    
    async def _check_layer(self, layer: LayerPriority, game_state: Dict) -> Optional[Dict]:
        """
        Check all triggers in a specific layer
        
        Args:
            layer: Layer to check
            game_state: Current game state
            
        Returns:
            Action dictionary if trigger fired, None otherwise
        """
        with self._coordination_lock:
            self.active_layer = layer
        
        try:
            # Get all enabled triggers for this layer (sorted by priority)
            triggers = self.registry.get_triggers_for_layer(layer)
            
            if not triggers:
                logger.debug(f"No enabled triggers in layer {layer.name}")
                return None
            
            logger.debug(f"Checking {len(triggers)} triggers in layer {layer.name}")
            
            # Check each trigger in priority order
            for trigger in triggers:
                try:
                    # Check if trigger can execute (enabled + cooldown)
                    if not trigger.enabled:
                        continue
                    
                    if not self.evaluator.check_cooldown(trigger):
                        continue
                    
                    # Evaluate condition
                    condition_met = self.evaluator.evaluate_condition(
                        trigger.condition,
                        game_state
                    )
                    
                    if not condition_met:
                        continue
                    
                    # Condition met! Execute action
                    logger.info(
                        f"Trigger '{trigger.name}' condition met in layer {layer.name}, "
                        f"executing action..."
                    )
                    
                    result = await self.executor.execute_action(trigger, game_state)
                    
                    # Update trigger statistics
                    self.registry.update_trigger_stats(
                        trigger.trigger_id,
                        result.success,
                        result.execution_time_ms
                    )
                    
                    # Update layer statistics
                    with self._coordination_lock:
                        self._layer_execution_count[layer] += 1
                        if result.success:
                            self._total_triggers_fired += 1
                    
                    # Log execution to database
                    await self._log_trigger_execution(trigger, game_state, result)
                    
                    # Return result if successful
                    if result.success:
                        return result.result
                    else:
                        logger.warning(
                            f"Trigger '{trigger.name}' executed but failed: {result.error}"
                        )
                        # Continue to next trigger
                        continue
                    
                except Exception as e:
                    logger.error(f"Error checking trigger {trigger.trigger_id}: {e}")
                    continue
            
            return None
            
        finally:
            with self._coordination_lock:
                self.active_layer = None
    
    async def _check_layer_background(self, layer: LayerPriority, game_state: Dict):
        """
        Check layer in background without blocking
        Used for SYSTEM layer maintenance tasks
        
        Args:
            layer: Layer to check
            game_state: Current game state
        """
        try:
            await self._check_layer(layer, game_state)
        except Exception as e:
            logger.error(f"Error in background layer check for {layer.name}: {e}")
    
    async def _log_trigger_execution(
        self,
        trigger: Trigger,
        game_state: Dict,
        result: TriggerExecutionResult
    ):
        """
        Log trigger execution to database for analysis
        
        Args:
            trigger: Trigger that was executed
            game_state: Game state at time of execution
            result: Execution result
        """
        try:
            import json
            from database import db
            
            if db.conn:
                await db.conn.execute(
                    """
                    INSERT INTO trigger_executions 
                    (trigger_id, trigger_name, layer, game_state_json, action_taken, 
                     success, execution_time_ms, error_message, context_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trigger.trigger_id,
                        trigger.name,
                        trigger.layer.name,
                        json.dumps(game_state),
                        trigger.action.handler,
                        result.success,
                        result.execution_time_ms,
                        result.error,
                        json.dumps({
                            'priority': trigger.priority,
                            'cooldown': trigger.cooldown,
                            'execution_count': trigger.execution_count
                        })
                    )
                )
                await db.conn.commit()
        except Exception as e:
            logger.error(f"Failed to log trigger execution: {e}")
    
    def request_interrupt(self, higher_priority_layer: LayerPriority):
        """
        Request interrupt from higher priority layer
        
        Args:
            higher_priority_layer: Layer requesting interrupt
        """
        with self._coordination_lock:
            if self.active_layer and higher_priority_layer.value < self.active_layer.value:
                self.interrupt_requested = True
                logger.info(
                    f"Interrupt requested by {higher_priority_layer.name} "
                    f"(current: {self.active_layer.name})"
                )
    
    def _should_interrupt_for_higher_priority(self) -> bool:
        """Check if current execution should be interrupted"""
        with self._coordination_lock:
            if self.interrupt_requested:
                self.interrupt_requested = False
                return True
            return False
    
    def get_statistics(self) -> Dict:
        """Get coordinator statistics"""
        with self._coordination_lock:
            layer_stats = {
                layer.name: count 
                for layer, count in self._layer_execution_count.items()
            }
            
            return {
                "total_checks": self._total_checks,
                "total_triggers_fired": self._total_triggers_fired,
                "active_layer": self.active_layer.name if self.active_layer else None,
                "layer_execution_counts": layer_stats,
                "registry_stats": self.registry.get_statistics(),
                "evaluator_stats": self.evaluator.get_statistics(),
                "executor_stats": self.executor.get_statistics()
            }
    
    async def health_check(self) -> Dict:
        """
        Perform health check on trigger system
        
        Returns:
            Health status dictionary
        """
        try:
            stats = self.get_statistics()
            
            # Check if triggers are loaded
            triggers_loaded = stats['registry_stats']['total_triggers'] > 0
            
            # Check if system is responsive
            test_state = {'test': True}
            result = await self.process_game_state(test_state)
            
            return {
                "healthy": True,
                "triggers_loaded": triggers_loaded,
                "system_responsive": True,
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e)
            }
    
    def reset_statistics(self):
        """Reset coordinator statistics"""
        with self._coordination_lock:
            self._total_checks = 0
            self._total_triggers_fired = 0
            self._layer_execution_count = {layer: 0 for layer in LayerPriority}
            logger.info("Coordinator statistics reset")


# ============================================================================
# LAYER-SPECIFIC PROCESSING STRATEGIES
# ============================================================================

class LayerStrategy:
    """Base class for layer-specific processing strategies"""
    
    @staticmethod
    async def pre_check(game_state: Dict) -> bool:
        """
        Pre-check before evaluating layer triggers
        
        Args:
            game_state: Current game state
            
        Returns:
            bool: True if layer should be checked
        """
        return True
    
    @staticmethod
    async def post_execution(trigger: Trigger, result: TriggerExecutionResult, game_state: Dict):
        """
        Post-execution hook for layer-specific logic
        
        Args:
            trigger: Executed trigger
            result: Execution result
            game_state: Game state
        """
        pass


class ReflexLayerStrategy(LayerStrategy):
    """Strategy for REFLEX layer - emergency responses"""
    
    @staticmethod
    async def pre_check(game_state: Dict) -> bool:
        """Only check reflex layer if in potential danger"""
        character = game_state.get('character', {})
        hp_percent = character.get('hp_percent', 100)
        
        # Always check if HP is below 50%
        return hp_percent < 50


class TacticalLayerStrategy(LayerStrategy):
    """Strategy for TACTICAL layer - combat decisions"""
    
    @staticmethod
    async def pre_check(game_state: Dict) -> bool:
        """Only check tactical layer if in combat or near enemies"""
        combat = game_state.get('combat', {})
        in_combat = combat.get('in_combat', False)
        nearby_enemies = combat.get('nearby_enemy_count', 0)
        
        return in_combat or nearby_enemies > 0


class SubconsciousLayerStrategy(LayerStrategy):
    """Strategy for SUBCONSCIOUS layer - routine tasks"""
    
    @staticmethod
    async def pre_check(game_state: Dict) -> bool:
        """Check if not in emergency or combat"""
        character = game_state.get('character', {})
        combat = game_state.get('combat', {})
        
        hp_safe = character.get('hp_percent', 100) > 50
        not_in_combat = not combat.get('in_combat', False)
        
        return hp_safe and not_in_combat


class ConsciousLayerStrategy(LayerStrategy):
    """Strategy for CONSCIOUS layer - strategic planning"""
    
    @staticmethod
    async def pre_check(game_state: Dict) -> bool:
        """Check conscious layer only when idle"""
        character = game_state.get('character', {})
        
        # Check if character is idle (no current action)
        is_idle = game_state.get('state', '') in ['idle', 'standing']
        
        return is_idle
