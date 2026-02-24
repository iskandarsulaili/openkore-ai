"""
Trigger Registry
Central registry for all triggers across layers with thread-safe operations
"""

import threading
import json
from typing import Dict, List, Optional
from pathlib import Path
from collections import defaultdict
from loguru import logger
from datetime import datetime

from .models import Trigger, TriggerCondition, TriggerAction, LayerPriority


class TriggerRegistry:
    """
    Central registry for all triggers across layers
    Thread-safe operations for concurrent access
    """
    
    def __init__(self):
        self.triggers: Dict[str, Trigger] = {}
        self.triggers_by_layer: Dict[LayerPriority, List[Trigger]] = defaultdict(list)
        self._lock = threading.RLock()
        
    def register(self, trigger: Trigger) -> bool:
        """
        Register a trigger in the registry
        Thread-safe operation
        
        Args:
            trigger: Trigger instance to register
            
        Returns:
            bool: True if registered successfully, False if already exists
        """
        with self._lock:
            if trigger.trigger_id in self.triggers:
                logger.warning(f"Trigger {trigger.trigger_id} already registered, updating...")
                # Remove from layer list
                old_trigger = self.triggers[trigger.trigger_id]
                if old_trigger in self.triggers_by_layer[old_trigger.layer]:
                    self.triggers_by_layer[old_trigger.layer].remove(old_trigger)
            
            # Register trigger
            self.triggers[trigger.trigger_id] = trigger
            self.triggers_by_layer[trigger.layer].append(trigger)
            
            # Sort triggers in layer by priority (lower number = higher priority)
            self._sort_layer_triggers(trigger.layer)
            
            logger.info(f"Registered trigger '{trigger.name}' (ID: {trigger.trigger_id}) in layer {trigger.layer.name}")
            return True
    
    def _sort_layer_triggers(self, layer: LayerPriority):
        """Sort triggers in a layer by priority (thread-safe, called within lock)"""
        self.triggers_by_layer[layer].sort(key=lambda t: t.priority)
    
    def get_triggers_for_layer(self, layer: LayerPriority) -> List[Trigger]:
        """
        Get all enabled triggers for a layer, sorted by priority
        
        Args:
            layer: Layer to retrieve triggers for
            
        Returns:
            List of enabled triggers sorted by priority
        """
        with self._lock:
            return [t for t in self.triggers_by_layer[layer] if t.enabled]
    
    def get_trigger(self, trigger_id: str) -> Optional[Trigger]:
        """
        Get specific trigger by ID
        
        Args:
            trigger_id: Unique trigger identifier
            
        Returns:
            Trigger instance or None if not found
        """
        with self._lock:
            return self.triggers.get(trigger_id)
    
    def enable_trigger(self, trigger_id: str) -> bool:
        """Enable a trigger"""
        with self._lock:
            trigger = self.triggers.get(trigger_id)
            if trigger:
                trigger.enabled = True
                logger.info(f"Enabled trigger {trigger_id}")
                return True
            return False
    
    def disable_trigger(self, trigger_id: str) -> bool:
        """Disable a trigger"""
        with self._lock:
            trigger = self.triggers.get(trigger_id)
            if trigger:
                trigger.enabled = False
                logger.info(f"Disabled trigger {trigger_id}")
                return True
            return False
    
    def update_trigger_stats(self, trigger_id: str, success: bool, execution_time_ms: float = 0):
        """
        Update trigger execution statistics
        
        Args:
            trigger_id: Trigger to update
            success: Whether execution was successful
            execution_time_ms: Execution time in milliseconds
        """
        with self._lock:
            trigger = self.triggers.get(trigger_id)
            if trigger:
                trigger.execution_count += 1
                if success:
                    trigger.success_count += 1
                else:
                    trigger.failure_count += 1
                trigger.last_executed = datetime.now()
                
                logger.debug(
                    f"Trigger {trigger_id} stats updated: "
                    f"executions={trigger.execution_count}, "
                    f"success_rate={trigger.get_success_rate():.1f}%, "
                    f"execution_time={execution_time_ms:.2f}ms"
                )
    
    def get_statistics(self) -> Dict:
        """Get registry statistics"""
        with self._lock:
            stats = {
                "total_triggers": len(self.triggers),
                "enabled_triggers": sum(1 for t in self.triggers.values() if t.enabled),
                "layers": {}
            }
            
            for layer in LayerPriority:
                layer_triggers = self.triggers_by_layer[layer]
                stats["layers"][layer.name] = {
                    "total": len(layer_triggers),
                    "enabled": sum(1 for t in layer_triggers if t.enabled),
                    "total_executions": sum(t.execution_count for t in layer_triggers),
                    "total_successes": sum(t.success_count for t in layer_triggers)
                }
            
            return stats
    
    def load_from_config(self, config_path: str) -> int:
        """
        Load triggers from JSON configuration file
        
        Args:
            config_path: Path to triggers_config.json
            
        Returns:
            Number of triggers loaded
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            logger.error(f"Trigger configuration file not found: {config_path}")
            return 0
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            triggers_data = config_data.get('triggers', [])
            loaded_count = 0
            
            for trigger_data in triggers_data:
                try:
                    # Parse condition
                    condition_data = trigger_data['condition']
                    condition = self._parse_condition(condition_data)
                    
                    # Parse action
                    action_data = trigger_data['action']
                    action = TriggerAction(
                        handler=action_data['handler'],
                        params=action_data.get('params', {}),
                        async_execution=action_data.get('async_execution', False),
                        timeout=action_data.get('timeout')
                    )
                    
                    # Create trigger
                    trigger = Trigger(
                        trigger_id=trigger_data['trigger_id'],
                        name=trigger_data['name'],
                        layer=LayerPriority[trigger_data['layer']],
                        priority=trigger_data['priority'],
                        condition=condition,
                        action=action,
                        cooldown=trigger_data['cooldown'],
                        enabled=trigger_data.get('enabled', True),
                        description=trigger_data.get('description'),
                        tags=trigger_data.get('tags', [])
                    )
                    
                    self.register(trigger)
                    loaded_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to load trigger {trigger_data.get('trigger_id', 'unknown')}: {e}")
                    continue
            
            logger.success(f"Loaded {loaded_count} triggers from {config_path}")
            return loaded_count
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in trigger configuration: {e}")
            return 0
        except Exception as e:
            logger.error(f"Failed to load trigger configuration: {e}")
            return 0
    
    def _parse_condition(self, condition_data: Dict) -> TriggerCondition:
        """Parse condition from configuration data"""
        condition_type = condition_data['type']
        
        if condition_type == 'simple':
            return TriggerCondition(
                type='simple',
                field=condition_data.get('field'),
                operator=condition_data.get('operator'),
                value=condition_data.get('value')
            )
        
        elif condition_type == 'compound':
            # Recursively parse sub-conditions
            sub_checks = []
            for check_data in condition_data.get('checks', []):
                sub_checks.append(self._parse_condition(check_data))
            
            return TriggerCondition(
                type='compound',
                compound_operator=condition_data.get('compound_operator'),
                checks=sub_checks
            )
        
        elif condition_type == 'custom':
            return TriggerCondition(
                type='custom',
                custom_params=condition_data.get('custom_params', {})
            )
        
        else:
            raise ValueError(f"Unknown condition type: {condition_type}")
    
    def clear(self):
        """Clear all triggers from registry"""
        with self._lock:
            self.triggers.clear()
            self.triggers_by_layer.clear()
            logger.info("Cleared all triggers from registry")
