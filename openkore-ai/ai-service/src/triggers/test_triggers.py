"""
Basic tests for the trigger system
Verifies core functionality: registration, evaluation, execution, coordination
"""

import asyncio
import sys
import io
from pathlib import Path

# Fix Windows console encoding issue
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from triggers import (
    Trigger,
    TriggerCondition,
    TriggerAction,
    LayerPriority,
    TriggerRegistry,
    TriggerEvaluator,
    TriggerExecutor,
    TriggerCoordinator,
    StateManager
)


def test_trigger_models():
    """Test trigger data models"""
    print("\n=== Test 1: Trigger Models ===")
    
    # Create a simple trigger
    condition = TriggerCondition(
        type='simple',
        field='character.hp_percent',
        operator='<=',
        value=25
    )
    
    action = TriggerAction(
        handler='test.handler',
        params={'method': 'heal'},
        async_execution=False,
        timeout=1.0
    )
    
    trigger = Trigger(
        trigger_id='test_hp_critical',
        name='Test HP Critical',
        layer=LayerPriority.REFLEX,
        priority=1,
        condition=condition,
        action=action,
        cooldown=1
    )
    
    print(f" Created trigger: {trigger.name}")
    print(f"  Layer: {trigger.layer.name}")
    print(f"  Priority: {trigger.priority}")
    print(f"  Cooldown: {trigger.cooldown}s")
    print(f"  Can execute: {trigger.can_execute()}")
    
    return True


def test_trigger_registry():
    """Test trigger registry"""
    print("\n=== Test 2: Trigger Registry ===")
    
    registry = TriggerRegistry()
    
    # Create test triggers
    for i in range(3):
        trigger = Trigger(
            trigger_id=f'test_trigger_{i}',
            name=f'Test Trigger {i}',
            layer=LayerPriority.REFLEX,
            priority=i + 1,
            condition=TriggerCondition(type='simple', field='test', operator='==', value=i),
            action=TriggerAction(handler='test.handler', params={}),
            cooldown=1
        )
        registry.register(trigger)
    
    print(f" Registered 3 triggers")
    
    # Test retrieval
    triggers = registry.get_triggers_for_layer(LayerPriority.REFLEX)
    print(f" Retrieved {len(triggers)} triggers for REFLEX layer")
    
    # Verify sorting by priority
    priorities = [t.priority for t in triggers]
    print(f"  Priorities: {priorities}")
    assert priorities == [1, 2, 3], "Triggers not sorted by priority"
    
    # Test statistics
    stats = registry.get_statistics()
    print(f" Statistics: {stats['total_triggers']} total triggers")
    
    return True


def test_trigger_evaluator():
    """Test condition evaluation"""
    print("\n=== Test 3: Trigger Evaluator ===")
    
    evaluator = TriggerEvaluator()
    
    # Test simple condition
    game_state = {
        'character': {
            'hp_percent': 20,
            'sp_percent': 50
        }
    }
    
    # Test HP critical condition
    hp_condition = TriggerCondition(
        type='simple',
        field='character.hp_percent',
        operator='<=',
        value=25
    )
    
    result = evaluator.evaluate_condition(hp_condition, game_state)
    print(f" HP Critical (20 <= 25): {result}")
    assert result == True, "HP critical condition should be True"
    
    # Test compound condition
    compound_condition = TriggerCondition(
        type='compound',
        compound_operator='AND',
        checks=[
            TriggerCondition(type='simple', field='character.hp_percent', operator='<=', value=30),
            TriggerCondition(type='simple', field='character.sp_percent', operator='>', value=40)
        ]
    )
    
    result = evaluator.evaluate_condition(compound_condition, game_state)
    print(f" Compound AND (HP<=30 AND SP>40): {result}")
    assert result == True, "Compound condition should be True"
    
    # Test cooldown
    trigger = Trigger(
        trigger_id='test_cooldown',
        name='Test Cooldown',
        layer=LayerPriority.REFLEX,
        priority=1,
        condition=hp_condition,
        action=TriggerAction(handler='test', params={}),
        cooldown=5
    )
    
    can_execute = evaluator.check_cooldown(trigger)
    print(f" Cooldown check (never executed): {can_execute}")
    assert can_execute == True, "Should be able to execute on first run"
    
    return True


async def test_trigger_executor():
    """Test action execution"""
    print("\n=== Test 4: Trigger Executor ===")
    
    # Create test handler
    def test_handler(game_state, **kwargs):
        return {
            "action": "test_action",
            "params": kwargs,
            "result": "success"
        }
    
    handler_registry = {
        'test.handler': test_handler
    }
    
    executor = TriggerExecutor(handler_registry)
    
    # Create test trigger
    trigger = Trigger(
        trigger_id='test_exec',
        name='Test Execution',
        layer=LayerPriority.REFLEX,
        priority=1,
        condition=TriggerCondition(type='simple', field='test', operator='==', value=1),
        action=TriggerAction(
            handler='test.handler',
            params={'method': 'heal', 'amount': 100},
            async_execution=False,
            timeout=1.0
        ),
        cooldown=1
    )
    
    game_state = {'character': {'hp': 50}}
    
    result = await executor.execute_action(trigger, game_state)
    
    print(f" Execution result: {result.success}")
    print(f"  Execution time: {result.execution_time_ms:.2f}ms")
    print(f"  Action: {result.result.get('action')}")
    
    assert result.success == True, "Execution should succeed"
    assert result.result['action'] == 'test_action', "Wrong action returned"
    
    return True


async def test_trigger_coordinator():
    """Test coordination across layers"""
    print("\n=== Test 5: Trigger Coordinator ===")
    
    # Setup components
    registry = TriggerRegistry()
    evaluator = TriggerEvaluator()
    
    # Test handler
    def emergency_handler(game_state, **kwargs):
        return {
            "action": "emergency_heal",
            "params": kwargs,
            "reason": "HP critical"
        }
    
    handler_registry = {
        'test.emergency': emergency_handler
    }
    
    executor = TriggerExecutor(handler_registry)
    state_manager = StateManager()
    
    coordinator = TriggerCoordinator(registry, evaluator, executor, state_manager)
    
    # Register test trigger
    trigger = Trigger(
        trigger_id='hp_emergency',
        name='HP Emergency',
        layer=LayerPriority.REFLEX,
        priority=1,
        condition=TriggerCondition(
            type='simple',
            field='character.hp_percent',
            operator='<=',
            value=25
        ),
        action=TriggerAction(
            handler='test.emergency',
            params={'method': 'fastest'},
            async_execution=False,
            timeout=1.0
        ),
        cooldown=1
    )
    
    registry.register(trigger)
    
    # Test with critical HP
    game_state = {
        'character': {
            'hp_percent': 20,
            'sp_percent': 80
        }
    }
    
    result = await coordinator.process_game_state(game_state)
    
    print(f" Coordinator result: {result}")
    assert result is not None, "Should return action for critical HP"
    assert result['action'] == 'emergency_heal', "Wrong action returned"
    
    # Test with safe HP (no trigger should fire)
    game_state['character']['hp_percent'] = 80
    result = await coordinator.process_game_state(game_state)
    
    print(f" Safe HP result: {result}")
    assert result is None, "Should not fire trigger when HP is safe"
    
    # Test statistics
    stats = coordinator.get_statistics()
    print(f" Coordinator stats:")
    print(f"  Total checks: {stats['total_checks']}")
    print(f"  Triggers fired: {stats['total_triggers_fired']}")
    
    return True


def test_state_manager():
    """Test state management"""
    print("\n=== Test 6: State Manager ===")
    
    state = StateManager()
    
    # Test basic operations
    state.set('test_key', 'test_value')
    value = state.get('test_key')
    print(f" Set and get: {value}")
    assert value == 'test_value', "State get/set failed"
    
    # Test layer-specific state
    state.set_layer_state(LayerPriority.REFLEX, 'hp_check_count', 5)
    layer_value = state.get_layer_state(LayerPriority.REFLEX, 'hp_check_count')
    print(f" Layer state: {layer_value}")
    assert layer_value == 5, "Layer state get/set failed"
    
    # Test statistics
    stats = state.get_statistics()
    print(f" State statistics:")
    print(f"  Global state size: {stats['global_state_size']}")
    print(f"  Total gets: {stats['total_gets']}")
    print(f"  Total sets: {stats['total_sets']}")
    
    return True


async def test_config_loading():
    """Test loading triggers from configuration file"""
    print("\n=== Test 7: Config Loading ===")
    
    registry = TriggerRegistry()
    
    # Path to triggers_config.json
    config_path = Path(__file__).parent.parent.parent / "data" / "triggers_config.json"
    
    if config_path.exists():
        loaded_count = registry.load_from_config(str(config_path))
        print(f" Loaded {loaded_count} triggers from config")
        
        stats = registry.get_statistics()
        print(f" Distribution across layers:")
        for layer, info in stats['layers'].items():
            print(f"  {layer}: {info['enabled']} enabled / {info['total']} total")
        
        assert loaded_count > 0, "Should load at least one trigger"
        return True
    else:
        print(f"⚠ Config file not found: {config_path}")
        print("  (This is OK for basic tests)")
        return True


async def main():
    """Run all tests"""
    print("=" * 60)
    print("TRIGGER SYSTEM TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Models", test_trigger_models),
        ("Registry", test_trigger_registry),
        ("Evaluator", test_trigger_evaluator),
        ("Executor", test_trigger_executor),
        ("Coordinator", test_trigger_coordinator),
        ("State Manager", test_state_manager),
        ("Config Loading", test_config_loading),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            results.append((name, result, None))
            print(f"\n✅ {name} test PASSED")
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"\n❌ {name} test FAILED: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for name, result, error in results:
        status = "✅ PASS" if result else f"❌ FAIL"
        print(f"{status} - {name}")
        if error:
            print(f"        Error: {error}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
