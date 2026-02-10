"""
Trigger Evaluator
Evaluates trigger conditions against game state with optimized short-circuit logic
"""

import operator
from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime

from .models import Trigger, TriggerCondition


class TriggerEvaluator:
    """
    Evaluates trigger conditions against game state
    Supports simple, compound, and custom conditions with short-circuit evaluation
    """
    
    # Operator mapping for simple conditions
    OPERATORS = {
        '==': operator.eq,
        '!=': operator.ne,
        '>': operator.gt,
        '<': operator.lt,
        '>=': operator.ge,
        '<=': operator.le,
        'in': lambda a, b: a in b,
        'not_in': lambda a, b: a not in b,
        'contains': lambda a, b: b in a,
    }
    
    def __init__(self):
        self.custom_functions = {}
        self._evaluation_count = 0
    
    def register_custom_function(self, name: str, func: callable):
        """
        Register a custom condition evaluation function
        
        Args:
            name: Function name to reference in config
            func: Callable that takes (game_state, params) and returns bool
        """
        self.custom_functions[name] = func
        logger.info(f"Registered custom condition function: {name}")
    
    def evaluate_condition(self, condition: TriggerCondition, game_state: Dict) -> bool:
        """
        Evaluate a condition against current game state
        
        Args:
            condition: Condition to evaluate
            game_state: Current game state dictionary
            
        Returns:
            bool: True if condition is met, False otherwise
        """
        self._evaluation_count += 1
        
        try:
            if condition.type == 'simple':
                return self._evaluate_simple(condition, game_state)
            elif condition.type == 'compound':
                return self._evaluate_compound(condition, game_state)
            elif condition.type == 'custom':
                return self._evaluate_custom(condition, game_state)
            else:
                logger.error(f"Unknown condition type: {condition.type}")
                return False
                
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    def _evaluate_simple(self, condition: TriggerCondition, game_state: Dict) -> bool:
        """
        Evaluate simple field comparison
        
        Args:
            condition: Simple condition with field, operator, value
            game_state: Current game state
            
        Returns:
            bool: Comparison result
        """
        try:
            # Extract field value from nested game_state
            field_value = self._get_nested_value(game_state, condition.field)
            
            if field_value is None:
                logger.debug(f"Field '{condition.field}' not found in game state")
                return False
            
            # Get operator function
            op_func = self.OPERATORS.get(condition.operator)
            if op_func is None:
                logger.error(f"Unknown operator: {condition.operator}")
                return False
            
            # Perform comparison
            result = op_func(field_value, condition.value)
            
            logger.debug(
                f"Simple condition: {condition.field} ({field_value}) "
                f"{condition.operator} {condition.value} = {result}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in simple condition evaluation: {e}")
            return False
    
    def _evaluate_compound(self, condition: TriggerCondition, game_state: Dict) -> bool:
        """
        Evaluate compound AND/OR/NOT conditions with short-circuit logic
        
        Args:
            condition: Compound condition with operator and sub-checks
            game_state: Current game state
            
        Returns:
            bool: Combined result
        """
        if not condition.checks:
            logger.warning("Compound condition has no sub-checks")
            return False
        
        operator_type = condition.compound_operator.upper()
        
        try:
            if operator_type == 'AND':
                # Short-circuit: return False on first failure
                for check in condition.checks:
                    if not self.evaluate_condition(check, game_state):
                        return False
                return True
            
            elif operator_type == 'OR':
                # Short-circuit: return True on first success
                for check in condition.checks:
                    if self.evaluate_condition(check, game_state):
                        return True
                return False
            
            elif operator_type == 'NOT':
                # Negate the result of the first check
                if condition.checks:
                    return not self.evaluate_condition(condition.checks[0], game_state)
                return False
            
            else:
                logger.error(f"Unknown compound operator: {condition.compound_operator}")
                return False
                
        except Exception as e:
            logger.error(f"Error in compound condition evaluation: {e}")
            return False
    
    def _evaluate_custom(self, condition: TriggerCondition, game_state: Dict) -> bool:
        """
        Evaluate custom function condition
        
        Args:
            condition: Custom condition with function reference
            game_state: Current game state
            
        Returns:
            bool: Function result
        """
        try:
            # Check if custom function is directly provided
            if condition.custom_function:
                return condition.custom_function(game_state, condition.custom_params or {})
            
            # Check if function is registered by name
            func_name = condition.custom_params.get('function_name') if condition.custom_params else None
            if func_name and func_name in self.custom_functions:
                func = self.custom_functions[func_name]
                return func(game_state, condition.custom_params or {})
            
            logger.error(f"Custom function not found or not provided")
            return False
            
        except Exception as e:
            logger.error(f"Error in custom condition evaluation: {e}")
            return False
    
    def _get_nested_value(self, data: Dict, path: str, default=None) -> Any:
        """
        Get value from nested dictionary using dot notation
        
        Args:
            data: Dictionary to search
            path: Dot-separated path (e.g., 'character.hp_percent')
            default: Default value if path not found
            
        Returns:
            Value at path or default
        """
        try:
            keys = path.split('.')
            value = data
            
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                    if value is None:
                        return default
                else:
                    return default
            
            return value
            
        except Exception as e:
            logger.debug(f"Error getting nested value for path '{path}': {e}")
            return default
    
    def check_cooldown(self, trigger: Trigger) -> bool:
        """
        Check if trigger cooldown has expired
        
        Args:
            trigger: Trigger to check
            
        Returns:
            bool: True if trigger can execute (cooldown expired or never executed)
        """
        if trigger.last_executed is None:
            return True
        
        elapsed = (datetime.now() - trigger.last_executed).total_seconds()
        can_execute = elapsed >= trigger.cooldown
        
        if not can_execute:
            logger.debug(
                f"Trigger {trigger.trigger_id} on cooldown: "
                f"{elapsed:.1f}s elapsed, {trigger.cooldown}s required"
            )
        
        return can_execute
    
    def get_statistics(self) -> Dict:
        """Get evaluator statistics"""
        return {
            "total_evaluations": self._evaluation_count,
            "custom_functions_registered": len(self.custom_functions)
        }


# ============================================================================
# BUILT-IN CUSTOM CONDITION FUNCTIONS
# ============================================================================

def condition_hp_critical(game_state: Dict, params: Dict) -> bool:
    """Check if HP is critically low with zone-based thresholds"""
    hp_percent = game_state.get('character', {}).get('hp_percent', 100)
    
    # Dynamic thresholds based on zone danger
    zone_type = game_state.get('zone', {}).get('type', 'safe')
    
    thresholds = {
        'safe': 20,      # Towns, safe zones
        'normal': 30,    # Regular hunting grounds
        'dangerous': 40, # PvP zones, high-level areas
        'boss': 50       # Boss fights
    }
    
    threshold = thresholds.get(zone_type, 30)
    return hp_percent <= threshold


def condition_sp_low(game_state: Dict, params: Dict) -> bool:
    """Check if SP is low enough to warrant attention"""
    sp_percent = game_state.get('character', {}).get('sp_percent', 100)
    threshold = params.get('threshold', 20)
    return sp_percent <= threshold


def condition_job_advancement_ready(game_state: Dict, params: Dict) -> bool:
    """Check if character meets job advancement requirements"""
    character = game_state.get('character', {})
    
    level = character.get('level', 1)
    job_level = character.get('job_level', 1)
    job_class = character.get('job_class', 'Novice')
    
    # Novice -> First Job (level 10/10 or higher based on server)
    if job_class == 'Novice':
        min_base = params.get('min_base_level', 10)
        min_job = params.get('min_job_level', 10)
        return level >= min_base and job_level >= min_job
    
    # First Job -> Second Job (varies by server, typically 40/40+)
    # This would be expanded with more complex logic
    
    return False


def condition_inventory_full(game_state: Dict, params: Dict) -> bool:
    """Check if inventory is full or nearly full"""
    inventory = game_state.get('inventory', {})
    current = inventory.get('item_count', 0)
    max_items = inventory.get('max_items', 100)
    
    threshold_percent = params.get('threshold_percent', 90)
    usage_percent = (current / max_items * 100) if max_items > 0 else 0
    
    return usage_percent >= threshold_percent


def condition_weight_heavy(game_state: Dict, params: Dict) -> bool:
    """Check if character is overweight"""
    character = game_state.get('character', {})
    current_weight = character.get('weight', 0)
    max_weight = character.get('max_weight', 1000)
    
    threshold_percent = params.get('threshold_percent', 80)
    weight_percent = (current_weight / max_weight * 100) if max_weight > 0 else 0
    
    return weight_percent >= threshold_percent


def condition_under_attack(game_state: Dict, params: Dict) -> bool:
    """Check if character is being attacked"""
    combat = game_state.get('combat', {})
    
    # Check if being targeted
    is_targeted = combat.get('is_targeted', False)
    attacking_count = combat.get('attacking_monster_count', 0)
    
    return is_targeted or attacking_count > 0


def condition_skill_ready(game_state: Dict, params: Dict) -> bool:
    """Check if a specific skill is ready to use"""
    skill_id = params.get('skill_id')
    if not skill_id:
        return False
    
    skills = game_state.get('character', {}).get('skills', {})
    skill = skills.get(skill_id, {})
    
    # Check if skill is available and not on cooldown
    is_learned = skill.get('learned', False)
    sp_cost = skill.get('sp_cost', 0)
    current_sp = game_state.get('character', {}).get('sp', 0)
    on_cooldown = skill.get('on_cooldown', False)
    
    return is_learned and current_sp >= sp_cost and not on_cooldown
