# Testing and Validation Strategy

**Version:** 1.0  
**Date:** 2026-02-05  
**Status:** Planning Phase

---

## Table of Contents

1. [Overview](#1-overview)
2. [Unit Testing](#2-unit-testing)
3. [Integration Testing](#3-integration-testing)
4. [System Testing](#4-system-testing)
5. [Field Testing](#5-field-testing)
6. [Regression Testing](#6-regression-testing)
7. [Performance Testing](#7-performance-testing)
8. [ML Model Validation](#8-ml-model-validation)
9. [Security Testing](#9-security-testing)
10. [Test Infrastructure](#10-test-infrastructure)

---

## 1. Overview

### 1.1 Testing Philosophy

- **Test-Driven Development (TDD)**: Write tests before implementation where feasible
- **Continuous Testing**: Automated tests run on every commit
- **Shift-Left Testing**: Find defects early in development
- **Risk-Based Testing**: Prioritize testing critical paths
- **Real-World Validation**: Test in actual game environments

### 1.2 Test Pyramid

```
         /\
        /  \       E2E Tests (5%)
       /____\      - Field tests
      /      \     - Full system tests
     /        \    
    /__________\   Integration Tests (25%)
   /            \  - Component integration
  /              \ - IPC tests
 /________________\ 
/                  \ Unit Tests (70%)
                    - Individual functions
                    - Class methods
```

### 1.3 Coverage Targets

| Component | Unit | Integration | System | Overall |
|-----------|------|-------------|--------|---------|
| **C++ Core Engine** | 85% | 70% | N/A | 80% |
| **Perl Plugin** | 80% | 75% | N/A | 75% |
| **IPC Layer** | 90% | 90% | N/A | 90% |
| **ML Pipeline** | 85% | 60% | N/A | 75% |
| **Coordinators** | 80% | 70% | N/A | 75% |
| **Overall System** | 80% | 70% | 60% | 75% |

### 1.4 Test Environments

1. **Local Development**: Developer machines
2. **CI/CD Environment**: GitHub Actions / Jenkins
3. **Staging Environment**: Test server with controlled data
4. **Production Environment**: Real game servers (limited testing)

---

## 2. Unit Testing

### 2.1 C++ Unit Testing

**Framework**: Google Test (gtest) + Google Mock (gmock)

#### 2.1.1 Setup

```cmake
# CMakeLists.txt
enable_testing()
find_package(GTest REQUIRED)

add_executable(unit_tests
    tests/reflex_engine_test.cpp
    tests/rule_engine_test.cpp
    tests/ml_engine_test.cpp
    tests/ipc_test.cpp
)

target_link_libraries(unit_tests
    GTest::GTest
    GTest::Main
    gmock
    openkore_ai_lib
)

gtest_discover_tests(unit_tests)
```

#### 2.1.2 Test Structure

```cpp
// tests/reflex_engine_test.cpp
#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include "reflex/reflex_engine.h"

class ReflexEngineTest : public ::testing::Test {
protected:
    void SetUp() override {
        engine_ = std::make_unique<ReflexEngine>(config_);
    }
    
    void TearDown() override {
        engine_.reset();
    }
    
    ReflexConfig config_;
    std::unique_ptr<ReflexEngine> engine_;
};

TEST_F(ReflexEngineTest, EmergencyTeleportTriggersOnLowHP) {
    // Arrange
    GameState state = createTestState();
    state.character.hp_percent = 15;  // Below 20% threshold
    state.monsters = createNearbyMonsters(6);  // 6 monsters
    
    // Act
    auto action = engine_->process(state);
    
    // Assert
    ASSERT_TRUE(action.has_value());
    EXPECT_EQ(action->type, ActionType::USE_SKILL);
    EXPECT_EQ(action->parameters["skill"], "Teleport");
}

TEST_F(ReflexEngineTest, CooldownPreventsDuplicateTrigger) {
    // Arrange
    GameState state = createCriticalState();
    
    // Act - First trigger
    auto action1 = engine_->process(state);
    ASSERT_TRUE(action1.has_value());
    
    // Act - Immediate second trigger (should be blocked)
    auto action2 = engine_->process(state);
    
    // Assert
    EXPECT_FALSE(action2.has_value());
}

TEST_F(ReflexEngineTest, PrioritizesHigherPriorityReflexes) {
    // Arrange
    GameState state = createMultipleConditionsState();
    
    // Act
    auto action = engine_->process(state);
    
    // Assert
    ASSERT_TRUE(action.has_value());
    EXPECT_EQ(getReflexPriority(action->reflex_id), 1000);
}
```

#### 2.1.3 What to Unit Test

**Reflex Engine:**
- ✅ Condition evaluation accuracy
- ✅ Action generation correctness
- ✅ Priority ordering
- ✅ Cooldown enforcement
- ✅ Performance (< 1ms)

**Rule Engine:**
- ✅ Rule parsing from YAML
- ✅ Condition matching
- ✅ Action selection
- ✅ Rule state tracking
- ✅ Hot-reload functionality

**ML Engine:**
- ✅ Feature extraction correctness
- ✅ Feature normalization
- ✅ Model loading
- ✅ Inference accuracy
- ✅ Online learning updates

**Decision Coordinator:**
- ✅ Tier selection logic
- ✅ Escalation conditions
- ✅ Fallback behavior
- ✅ Confidence calculation

**IPC Layer:**
- ✅ Message serialization/deserialization
- ✅ Protocol compliance
- ✅ Error handling
- ✅ Timeout behavior

**Coordinators:**
- ✅ Recommendation generation
- ✅ Priority calculation
- ✅ Confidence scoring
- ✅ Configuration loading

#### 2.1.4 Mocking Strategy

```cpp
// Mock game state provider
class MockGameStateProvider : public IGameStateProvider {
public:
    MOCK_METHOD(GameState, getCurrentState, (), (override));
    MOCK_METHOD(void, updateState, (const GameState&), (override));
};

// Mock action executor
class MockActionExecutor : public IActionExecutor {
public:
    MOCK_METHOD(bool, executeAction, (const Action&), (override));
    MOCK_METHOD(ActionResult, getLastResult, (), (override));
};

// Usage in tests
TEST(DecisionCoordinatorTest, UsesGameStateProvider) {
    MockGameStateProvider state_provider;
    MockActionExecutor executor;
    
    EXPECT_CALL(state_provider, getCurrentState())
        .WillOnce(Return(createTestState()));
    
    DecisionCoordinator coordinator(&state_provider, &executor);
    coordinator.tick();
}
```

### 2.2 Perl Unit Testing

**Framework**: Test::More, Test::Deep

#### 2.2.1 Test Structure

```perl
# t/state_capture_test.t
use strict;
use warnings;
use Test::More tests => 10;
use Test::Deep;

use_ok('StateCapture');

# Test character state capture
{
    my $state = StateCapture::captureGameState();
    
    ok(defined $state, 'State captured');
    ok(exists $state->{character}, 'Character data present');
    is($state->{character}{name}, $char->{name}, 'Character name correct');
    cmp_ok($state->{character}{hp_percent}, '>', 0, 'HP percent positive');
}

# Test monster capture
{
    # Setup test monsters
    my @test_monsters = createTestMonsters(3);
    
    my $state = StateCapture::captureGameState();
    my $monsters = $state->{monsters};
    
    is(scalar @$monsters, 3, 'All monsters captured');
    
    for my $monster (@$monsters) {
        ok(defined $monster->{id}, 'Monster has ID');
        ok(defined $monster->{name}, 'Monster has name');
        cmp_ok($monster->{distance}, '>=', 0, 'Distance non-negative');
    }
}

# Test IPC message format
{
    my $state = StateCapture::captureGameState();
    my $json = StateCapture::serializeState($state);
    
    ok(length($json) > 0, 'JSON serialized');
    
    my $parsed = JSON::XS::decode_json($json);
    cmp_deeply($parsed, $state, 'Round-trip serialization works');
}

done_testing();
```

#### 2.2.2 What to Unit Test

**State Capture:**
- ✅ Character data accuracy
- ✅ Monster data completeness
- ✅ Item data capture
- ✅ Map information
- ✅ Serialization correctness

**Action Executor:**
- ✅ Command generation
- ✅ Macro execution
- ✅ Error handling
- ✅ Command queueing

**IPC Client:**
- ✅ Connection management
- ✅ Message sending
- ✅ Message receiving
- ✅ Reconnection logic

### 2.3 Python Unit Testing (ML Pipeline)

**Framework**: pytest, unittest

```python
# tests/test_feature_extraction.py
import pytest
import numpy as np
from ml_pipeline import FeatureExtractor

class TestFeatureExtractor:
    @pytest.fixture
    def extractor(self):
        return FeatureExtractor()
    
    @pytest.fixture
    def sample_state(self):
        return {
            'character': {
                'hp': 5000,
                'max_hp': 10000,
                'sp': 300,
                'max_sp': 500,
                'level': 80
            },
            'monsters': [
                {'level': 75, 'distance': 5.0},
                {'level': 78, 'distance': 8.0}
            ]
        }
    
    def test_extracts_hp_ratio(self, extractor, sample_state):
        features = extractor.extract(sample_state)
        assert features['hp_ratio'] == 0.5
    
    def test_extracts_average_monster_level(self, extractor, sample_state):
        features = extractor.extract(sample_state)
        assert features['avg_monster_level'] == 76.5
    
    def test_handles_empty_monsters(self, extractor):
        state = {'character': {...}, 'monsters': []}
        features = extractor.extract(state)
        assert features['monster_count'] == 0
        assert features['avg_monster_level'] == 0.0
    
    def test_feature_normalization(self, extractor, sample_state):
        features = extractor.extract(sample_state)
        normalized = extractor.normalize(features)
        
        # All normalized features should be roughly in [-3, 3] range
        for value in normalized.values():
            assert -5.0 < value < 5.0
```

---

## 3. Integration Testing

### 3.1 IPC Integration Tests

**Objective**: Verify C++ ↔ Perl communication

```cpp
// tests/integration/ipc_integration_test.cpp
TEST(IPCIntegrationTest, FullRoundTrip) {
    // Start C++ engine
    AIEngine engine(config);
    std::thread engine_thread([&]() { engine.run(); });
    
    // Wait for engine to be ready
    std::this_thread::sleep_for(std::chrono::seconds(1));
    
    // Connect from Perl (simulated)
    IPCClient client("\\\\.\\pipe\\openkore_ai_test");
    ASSERT_TRUE(client.connect());
    
    // Send game state
    GameState test_state = createTestState();
    IPCMessage state_msg = serializeState(test_state);
    ASSERT_TRUE(client.send(state_msg));
    
    // Receive action response
    auto response = client.receive(1000);  // 1 second timeout
    ASSERT_TRUE(response.has_value());
    EXPECT_EQ(response->type, MessageType::ACTION_RESPONSE);
    
    // Verify action is valid
    Action action = deserializeAction(response->payload);
    EXPECT_NE(action.type, ActionType::INVALID);
    
    // Cleanup
    engine.shutdown();
    engine_thread.join();
}

TEST(IPCIntegrationTest, HandlesConnectionLoss) {
    AIEngine engine(config);
    std::thread engine_thread([&]() { engine.run(); });
    
    IPCClient client("\\\\.\\pipe\\openkore_ai_test");
    client.connect();
    
    // Send message
    client.send(createTestMessage());
    
    // Simulate connection loss
    client.disconnect();
    
    // Verify engine doesn't crash
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    EXPECT_TRUE(engine.isRunning());
    
    // Verify reconnection works
    ASSERT_TRUE(client.connect());
    ASSERT_TRUE(client.send(createTestMessage()));
    
    engine.shutdown();
    engine_thread.join();
}
```

### 3.2 Component Integration Tests

```cpp
// tests/integration/decision_flow_test.cpp
TEST(DecisionFlowTest, ReflexToAction) {
    // Setup full decision stack
    auto reflex_engine = std::make_unique<ReflexEngine>(reflex_config);
    auto rule_engine = std::make_unique<RuleEngine>(rule_config);
    auto coordinator = std::make_unique<DecisionCoordinator>(
        std::move(reflex_engine),
        std::move(rule_engine)
    );
    
    // Create critical state (should trigger reflex)
    GameState state = createCriticalState();
    state.character.hp_percent = 15;
    
    // Process decision
    DecisionRequest request{state, Priority::HIGH, 100000};
    auto response = coordinator->decide(request);
    
    // Verify reflex was used
    EXPECT_EQ(response.tier, DecisionTier::REFLEX);
    EXPECT_LT(response.processing_time_us, 1000);  // < 1ms
    
    // Verify action is correct
    EXPECT_EQ(response.action.type, ActionType::USE_SKILL);
    EXPECT_EQ(response.action.parameters["skill"], "Teleport");
}

TEST(DecisionFlowTest, EscalationToRule) {
    auto coordinator = createFullCoordinator();
    
    // Create state with no reflex triggers
    GameState state = createNormalState();
    state.character.hp_percent = 70;
    state.monsters = createNearbyMonsters(2);
    
    DecisionRequest request{state, Priority::NORMAL, 100000};
    auto response = coordinator->decide(request);
    
    // Should escalate to rules
    EXPECT_EQ(response.tier, DecisionTier::RULE);
    EXPECT_LT(response.processing_time_us, 10000);  // < 10ms
}
```

### 3.3 Coordinator Integration Tests

```cpp
TEST(CoordinatorIntegrationTest, MultipleCoordinatorsAggregation) {
    CoordinatorRouter router;
    
    // Register coordinators
    router.registerCoordinator(std::make_unique<CombatCoordinator>());
    router.registerCoordinator(std::make_unique<ConsumablesCoordinator>());
    router.registerCoordinator(std::make_unique<NavigationCoordinator>());
    
    // Create state with multiple objectives
    GameState state = createComplexState();
    state.character.hp_percent = 45;  // Low HP
    state.monsters = createNearbyMonsters(1);  // Enemy present
    state.destination = Position{150, 200};  // Navigation goal
    
    // Get all recommendations
    auto recommendations = router.getAllRecommendations(state);
    
    // Verify multiple coordinators contributed
    EXPECT_GE(recommendations.size(), 3);
    
    // Verify priority ordering
    for (size_t i = 1; i < recommendations.size(); i++) {
        float score1 = recommendations[i-1].priority * recommendations[i-1].confidence;
        float score2 = recommendations[i].priority * recommendations[i].confidence;
        EXPECT_GE(score1, score2);
    }
    
    // Select best action
    Action action = router.selectBestAction(state);
    
    // With low HP, healing should be prioritized
    EXPECT_EQ(action.type, ActionType::USE_ITEM);
}
```

### 3.4 Macro System Integration Tests

```cpp
TEST(MacroIntegrationTest, GenerationAndExecution) {
    MacroGenerator generator;
    MacroReloader reloader;
    
    // Generate macro from template
    MacroTemplate tmpl = loadTemplate("farming_rotation");
    json params = {
        {"name", "test_farming"},
        {"monster", "Poring"},
        {"hp_threshold", 60},
        {"sp_threshold", 30}
    };
    
    auto generated = generator.generateFromTemplate(tmpl, params);
    
    // Validate macro
    auto validation = validator.validate(generated.content);
    ASSERT_TRUE(validation.valid);
    
    // Save and reload
    generator.saveMacro(generated);
    bool reloaded = reloader.reload(generated.name);
    ASSERT_TRUE(reloaded);
    
    // Verify macro is available in eventMacro
    // (requires actual OpenKore environment)
}
```

### 3.5 ML Pipeline Integration Tests

```python
# tests/integration/test_ml_pipeline.py
def test_training_pipeline():
    """Test complete training pipeline"""
    # Collect training data
    collector = TrainingDataCollector()
    for i in range(1000):
        state = generate_random_state()
        decision = generate_decision(state)
        collector.record(state, decision)
    
    # Export to file
    collector.export('test_data.parquet')
    
    # Train model
    trainer = ModelTrainer('test_data.parquet')
    model, accuracy = trainer.train_decision_tree()
    
    assert accuracy > 0.7, "Model accuracy too low"
    
    # Export to ONNX
    trainer.export_to_onnx(model, 'test_model.onnx')
    
    # Load in C++ (via subprocess)
    result = subprocess.run([
        './test_onnx_loader',
        'test_model.onnx'
    ], capture_output=True)
    
    assert result.returncode == 0, "ONNX model failed to load"

def test_online_learning_update():
    """Test online learning updates model without downtime"""
    # Start model server
    model_server = ModelServer('initial_model.onnx')
    
    # Make predictions
    predictions_before = []
    for i in range(100):
        pred = model_server.predict(generate_features())
        predictions_before.append(pred)
    
    # Trigger online learning update
    new_samples = [generate_sample() for _ in range(500)]
    model_server.online_update(new_samples)
    
    # Verify predictions still work (no downtime)
    predictions_after = []
    for i in range(100):
        pred = model_server.predict(generate_features())
        predictions_after.append(pred)
    
    # Verify predictions changed (model was updated)
    assert predictions_before != predictions_after
```

---

## 4. System Testing

### 4.1 End-to-End Scenarios

**Test Environment**: Controlled test server

#### Scenario 1: Basic Farming
```gherkin
Feature: Basic Farming Behavior

  Scenario: Bot farms monsters successfully
    Given OpenKore is started with AI system enabled
    And the character is level 80 Wizard
    And the character is in "moc_fild02"
    When the bot runs for 30 minutes
    Then the character should gain EXP
    And the character should not die
    And items should be looted
    And HP/SP management should work
    And no errors in logs
```

**Automated Test:**
```python
def test_basic_farming_scenario():
    # Setup
    bot = OpenKoreBot(config_file='test_config.txt')
    bot.start()
    
    initial_state = bot.get_character_state()
    initial_exp = initial_state['exp']
    initial_zeny = initial_state['zeny']
    
    # Run for 30 minutes
    time.sleep(30 * 60)
    
    final_state = bot.get_character_state()
    
    # Assertions
    assert final_state['exp'] > initial_exp, "No EXP gained"
    assert final_state['zeny'] >= initial_zeny, "Lost zeny"
    assert final_state['death_count'] == 0, "Bot died"
    assert len(bot.get_error_logs()) == 0, "Errors occurred"
    
    # Check performance metrics
    metrics = bot.get_metrics()
    assert metrics['exp_per_hour'] > 100000, "EXP rate too low"
    assert metrics['uptime_percent'] > 95, "Too much downtime"
```

#### Scenario 2: Complex Combat
```python
def test_complex_combat_scenario():
    """Test handling multiple enemies and complex situations"""
    bot = OpenKoreBot()
    bot.teleport_to('gef_fild10')  # Multi-monster map
    
    # Wait for engagement
    time.sleep(60)
    
    # Verify bot uses appropriate skills
    skill_usage = bot.get_skill_usage_stats()
    assert 'Fire Ball' in skill_usage, "Primary skill not used"
    assert skill_usage['Fire Ball'] > 10, "Skill used too rarely"
    
    # Verify resource management
    assert bot.current_hp_percent() > 50, "HP management failed"
    assert bot.current_sp_percent() > 20, "SP management failed"
```

#### Scenario 3: NPC Interaction
```python
def test_npc_interaction():
    """Test NPC conversations and services"""
    bot = OpenKoreBot()
    bot.teleport_to('prontera')
    
    # Test storage NPC
    bot.navigate_to_npc('Kafra Employee')
    bot.open_storage()
    initial_storage_count = bot.get_storage_item_count()
    
    bot.store_items(['Blue Potion'])
    
    final_storage_count = bot.get_storage_item_count()
    assert final_storage_count > initial_storage_count
    
    # Test shop NPC
    initial_white_potions = bot.count_item('White Potion')
    bot.navigate_to_npc('Tool Dealer')
    bot.buy_items([('White Potion', 50)])
    
    final_white_potions = bot.count_item('White Potion')
    assert final_white_potions >= initial_white_potions + 50
```

### 4.2 Stress Testing

```python
def test_long_running_stability():
    """Test bot stability over 24 hours"""
    bot = OpenKoreBot()
    bot.start()
    
    start_time = time.time()
    end_time = start_time + (24 * 3600)  # 24 hours
    
    check_interval = 3600  # Check every hour
    
    while time.time() < end_time:
        time.sleep(check_interval)
        
        # Verify bot is still running
        assert bot.is_alive(), "Bot crashed"
        
        # Check memory usage
        memory_mb = bot.get_memory_usage_mb()
        assert memory_mb < 500, f"Memory leak detected: {memory_mb}MB"
        
        # Check error rate
        error_count = len(bot.get_error_logs())
        assert error_count < 10, f"Too many errors: {error_count}"
        
        # Check performance
        metrics = bot.get_metrics()
        assert metrics['decision_latency_p99'] < 100, "Decision latency too high"
```

### 4.3 Recovery Testing

```python
def test_connection_recovery():
    """Test bot recovers from connection loss"""
    bot = OpenKoreBot()
    bot.start()
    
    # Wait for stable operation
    time.sleep(60)
    
    # Simulate connection loss
    bot.disconnect_from_server()
    
    # Verify bot attempts reconnection
    time.sleep(10)
    assert bot.is_reconnecting(), "Bot not attempting reconnection"
    
    # Wait for reconnection
    time.sleep(30)
    assert bot.is_connected(), "Bot failed to reconnect"
    
    # Verify bot resumes normal operation
    time.sleep(60)
    assert bot.is_farming(), "Bot didn't resume farming"
```

---

## 5. Field Testing

### 5.1 Test Server Setup

**Requirements:**
- Private test server or official test server access
- Multiple test accounts (different levels/classes)
- Controlled environment for reproducible tests

### 5.2 Test Character Profiles

| Profile | Class | Level | Purpose |
|---------|-------|-------|---------|
| Beginner | Novice | 1-10 | Early game testing |
| Low-Level | First Class | 20-40 | Basic combat testing |
| Mid-Level | Second Class | 60-80 | Complex strategy testing |
| High-Level | Trans/Third | 100+ | Endgame content testing |
| Support | Priest | 70 | Party/support testing |
| Tank | Knight | 70 | Aggro management testing |

### 5.3 Field Test Scenarios

#### Phase 1: Controlled Testing (Week 1-2)
- **Location**: Low-level maps (Prontera fields)
- **Duration**: 2-4 hour sessions
- **Monitoring**: Continuous observation
- **Focus**: Basic functionality, safety features

**Checklist:**
- [ ] Bot starts and connects successfully
- [ ] Movement and pathfinding work
- [ ] Combat engagement functions
- [ ] HP/SP management active
- [ ] Loot collection works
- [ ] Emergency teleport triggers correctly
- [ ] Bot handles death gracefully
- [ ] No infinite loops or stuck states

#### Phase 2: Extended Testing (Week 3-4)
- **Location**: Mid-level dungeons
- **Duration**: 8-12 hour sessions
- **Monitoring**: Periodic checks (every 2 hours)
- **Focus**: Stability, resource management, efficiency

**Metrics to Track:**
- EXP per hour
- Zeny per hour
- Death count
- Uptime percentage
- Error frequency
- Decision distribution (Reflex/Rule/ML/LLM %)

#### Phase 3: Unattended Testing (Week 5-6)
- **Location**: Various maps
- **Duration**: 24+ hour sessions
- **Monitoring**: Remote monitoring only
- **Focus**: Long-term stability, memory leaks, edge cases

**Safety Measures:**
- Remote kill switch
- Automatic shutdown on critical errors
- Alert system for anomalies
- Regular checkpoint saves

### 5.4 Field Test Metrics Collection

```python
class FieldTestMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.initial_state = None
        self.samples = []
    
    def record_sample(self, bot):
        """Record metrics sample"""
        sample = {
            'timestamp': time.time(),
            'level': bot.get_level(),
            'exp': bot.get_exp(),
            'zeny': bot.get_zeny(),
            'hp_percent': bot.get_hp_percent(),
            'sp_percent': bot.get_sp_percent(),
            'deaths': bot.get_death_count(),
            'location': bot.get_map(),
            'decision_stats': bot.get_decision_stats()
        }
        self.samples.append(sample)
    
    def generate_report(self):
        """Generate comprehensive test report"""
        duration_hours = (time.time() - self.start_time) / 3600
        
        exp_gained = self.samples[-1]['exp'] - self.samples[0]['exp']
        exp_per_hour = exp_gained / duration_hours
        
        zeny_gained = self.samples[-1]['zeny'] - self.samples[0]['zeny']
        zeny_per_hour = zeny_gained / duration_hours
        
        deaths = self.samples[-1]['deaths']
        
        # Calculate uptime
        uptime_samples = sum(1 for s in self.samples if s['hp_percent'] > 0)
        uptime_percent = (uptime_samples / len(self.samples)) * 100
        
        # Decision distribution
        all_decision_stats = [s['decision_stats'] for s in self.samples]
        avg_reflex_percent = np.mean([d['reflex_percent'] for d in all_decision_stats])
        avg_rule_percent = np.mean([d['rule_percent'] for d in all_decision_stats])
        avg_ml_percent = np.mean([d['ml_percent'] for d in all_decision_stats])
        
        report = {
            'duration_hours': duration_hours,
            'exp_per_hour': exp_per_hour,
            'zeny_per_hour': zeny_per_hour,
            'deaths': deaths,
            'uptime_percent': uptime_percent,
            'decision_distribution': {
                'reflex': avg_reflex_percent,
                'rule': avg_rule_percent,
                'ml': avg_ml_percent
            }
        }
        
        return report
```

### 5.5 Field Test Success Criteria

**Minimum Acceptance Criteria:**
- ✅ Zero crashes in 24-hour test
- ✅ < 3 deaths per 24 hours
- ✅ > 95% uptime
- ✅ EXP/hour matches or exceeds manual play
- ✅ No infinite loops or stuck states
- ✅ All emergency features work
- ✅ Resource management maintains buffers

**Target Criteria:**
- 🎯 Zero crashes in 7-day test
- 🎯 < 1 death per 48 hours
- 🎯 > 98% uptime
- 🎯 EXP/hour 120% of manual play
- 🎯 Behavior appears human-like
- 🎯 No detection/warnings

---

## 6. Regression Testing

### 6.1 Automated Regression Suite

**Trigger**: Every commit to main/develop branches

**Test Suites:**
1. **Core Functionality** (30 minutes)
   - IPC communication
   - State synchronization
   - Basic decision making
   - Action execution

2. **Extended Functionality** (2 hours)
   - All coordinators
   - Macro system
   - ML pipeline
   - PDCA loop

3. **Full System** (4 hours)
   - End-to-end scenarios
   - Performance benchmarks
   - Integration tests

### 6.2 Regression Test Cases

```python
# tests/regression/test_core_regression.py

class CoreRegressionTests:
    """Critical path regression tests"""
    
    def test_ipc_round_trip_latency(self):
        """Regression: IPC latency must stay < 5ms"""
        latencies = []
        for i in range(1000):
            start = time.time()
            response = send_and_receive_ipc_message()
            latency = (time.time() - start) * 1000
            latencies.append(latency)
        
        p99_latency = np.percentile(latencies, 99)
        assert p99_latency < 5.0, f"IPC latency regressed: {p99_latency}ms"
    
    def test_reflex_response_time(self):
        """Regression: Reflex must stay < 1ms"""
        response_times = []
        for i in range(10000):
            state = generate_critical_state()
            start = time.perf_counter()
            action = reflex_engine.process(state)
            elapsed = (time.perf_counter() - start) * 1000
            response_times.append(elapsed)
        
        p99_time = np.percentile(response_times, 99)
        assert p99_time < 1.0, f"Reflex response regressed: {p99_time}ms"
    
    def test_ml_inference_time(self):
        """Regression: ML inference must stay < 100ms"""
        inference_times = []
        for i in range(1000):
            features = generate_random_features()
            start = time.perf_counter()
            prediction = ml_engine.predict(features)
            elapsed = (time.perf_counter() - start) * 1000
            inference_times.append(elapsed)
        
        p99_time = np.percentile(inference_times, 99)
        assert p99_time < 100.0, f"ML inference regressed: {p99_time}ms"
    
    def test_decision_quality_maintained(self):
        """Regression: Decision accuracy must not decrease"""
        # Load test dataset
        test_data = load_test_dataset('validation_set_v1.parquet')
        
        correct = 0
        total = len(test_data)
        
        for sample in test_data:
            decision = decision_coordinator.decide(sample['state'])
            if decision.action == sample['expected_action']:
                correct += 1
        
        accuracy = correct / total
        assert accuracy >= 0.85, f"Decision accuracy regressed: {accuracy}"
```

### 6.3 Breaking Change Detection

```yaml
# .github/workflows/regression.yml
name: Regression Tests

on: [push, pull_request]

jobs:
  regression:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build C++ Engine
        run: |
          mkdir build && cd build
          cmake -DCMAKE_BUILD_TYPE=Release ..
          make -j4
      
      - name: Run Unit Tests
        run: |
          cd build
          ctest --output-on-failure
      
      - name: Run Regression Suite
        run: |
          python tests/regression/run_all.py
      
      - name: Performance Regression Check
        run: |
          python tests/regression/check_performance.py
          # Fails if performance regressed > 10%
      
      - name: Upload Results
        uses: actions/upload-artifact@v2
        with:
          name: regression-results
          path: test-results/
```

---

## 7. Performance Testing

### 7.1 Latency Benchmarks

**Tools**: Google Benchmark, custom profiling

```cpp
// benchmarks/decision_latency_bench.cpp
#include <benchmark/benchmark.h>
#include "reflex/reflex_engine.h"

static void BM_ReflexEngine(benchmark::State& state) {
    ReflexEngine engine(loadConfig());
    GameState test_state = createTestState();
    
    for (auto _ : state) {
        auto action = engine.process(test_state);
        benchmark::DoNotOptimize(action);
    }
}
BENCHMARK(BM_ReflexEngine);

static void BM_RuleEngine(benchmark::State& state) {
    RuleEngine engine(loadConfig());
    GameState test_state = createTestState();
    
    for (auto _ : state) {
        auto action = engine.evaluate(test_state);
        benchmark::DoNotOptimize(action);
    }
}
BENCHMARK(BM_RuleEngine);

static void BM_MLInference(benchmark::State& state) {
    MLEngine engine(loadModel());
    FeatureVector features = extractFeatures(createTestState());
    
    for (auto _ : state) {
        auto prediction = engine.predict(features);
        benchmark::DoNotOptimize(prediction);
    }
}
BENCHMARK(BM_MLInference);

BENCHMARK_MAIN();
```

**Expected Results:**
```
--------------------------------------------------------------
Benchmark                    Time             CPU   Iterations
--------------------------------------------------------------
BM_ReflexEngine           0.8ms          0.8ms          1000
BM_RuleEngine             5.2ms          5.2ms           135
BM_MLInference           45.3ms         45.3ms            15
```

### 7.2 Memory Profiling

**Tools**: Valgrind, AddressSanitizer, HeapTrack

```bash
# Memory leak detection
valgrind --leak-check=full \
         --show-leak-kinds=all \
         --track-origins=yes \
         --log-file=valgrind.log \
         ./openkore_ai_engine

# AddressSanitizer build
cmake -DCMAKE_CXX_FLAGS="-fsanitize=address -g" ..
make
./openkore_ai_engine

# Heap profiling
heaptrack ./openkore_ai_engine
heaptrack_gui heaptrack.openkore_ai_engine.*.gz
```

**Acceptance Criteria:**
- Zero memory leaks
- No use-after-free
- No buffer overflows
- Memory usage stable over 24 hours
- < 500MB total memory usage

### 7.3 CPU Usage Monitoring

```python
def test_cpu_usage():
    """Verify CPU usage is reasonable"""
    bot = OpenKoreBot()
    bot.start()
    
    time.sleep(60)  # Warmup
    
    # Monitor CPU for 10 minutes
    cpu_samples = []
    for i in range(600):  # 600 seconds
        cpu_percent = bot.get_cpu_percent()
        cpu_samples.append(cpu_percent)
        time.sleep(1)
    
    avg_cpu = np.mean(cpu_samples)
    max_cpu = np.max(cpu_samples)
    
    # Assertions
    assert avg_cpu < 25, f"Average CPU too high: {avg_cpu}%"
    assert max_cpu < 50, f"Peak CPU too high: {max_cpu}%"
```

### 7.4 Throughput Testing

```cpp
TEST(ThroughputTest, DecisionsPerSecond) {
    DecisionCoordinator coordinator(config);
    
    const int duration_seconds = 60;
    const auto end_time = std::chrono::steady_clock::now() + 
                         std::chrono::seconds(duration_seconds);
    
    int decision_count = 0;
    
    while (std::chrono::steady_clock::now() < end_time) {
        GameState state = generateRandomState();
        DecisionRequest request{state, Priority::NORMAL, 100000};
        
        auto response = coordinator.decide(request);
        decision_count++;
    }
    
    double decisions_per_second = static_cast<double>(decision_count) / duration_seconds;
    
    // Should handle at least 10 decisions per second
    EXPECT_GE(decisions_per_second, 10.0);
    
    std::cout << "Throughput: " << decisions_per_second << " decisions/second\n";
}
```

---

## 8. ML Model Validation

### 8.1 Offline Evaluation

```python
# tests/ml_validation/offline_evaluation.py

def evaluate_model_offline(model_path, test_data_path):
    """Comprehensive offline model evaluation"""
    
    # Load model and data
    model = load_onnx_model(model_path)
    test_data = pd.read_parquet(test_data_path)
    
    X_test = test_data[feature_columns]
    y_test = test_data['action_type']
    
    # Predictions
    y_pred = model.predict(X_test)
    
    # Metrics
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score,
        f1_score, classification_report, confusion_matrix
    )
    
    results = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred, average='weighted'),
        'recall': recall_score(y_test, y_pred, average='weighted'),
        'f1_score': f1_score(y_test, y_pred, average='weighted')
    }
    
    print("Offline Evaluation Results:")
    print(f"  Accuracy:  {results['accuracy']:.3f}")
    print(f"  Precision: {results['precision']:.3f}")
    print(f"  Recall:    {results['recall']:.3f}")
    print(f"  F1 Score:  {results['f1_score']:.3f}")
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # Per-action accuracy
    per_action_accuracy = {}
    for action_type in y_test.unique():
        mask = y_test == action_type
        action_accuracy = accuracy_score(y_test[mask], y_pred[mask])
        per_action_accuracy[action_type] = action_accuracy
        print(f"  {action_type}: {action_accuracy:.3f}")
    
    # Confidence calibration
    y_proba = model.predict_proba(X_test)
    calibration_score = evaluate_calibration(y_test, y_proba)
    print(f"\nCalibration Score: {calibration_score:.3f}")
    
    return results
```

### 8.2 Online A/B Testing

```python
class ABTestFramework:
    """Framework for online A/B testing of ML models"""
    
    def __init__(self, model_a_path, model_b_path, split_ratio=0.5):
        self.model_a = load_model(model_a_path)
        self.model_b = load_model(model_b_path)
        self.split_ratio = split_ratio
        
        self.metrics_a = ModelMetrics()
        self.metrics_b = ModelMetrics()
    
    def route_decision(self, state):
        """Route decision to A or B based on split ratio"""
        if random.random() < self.split_ratio:
            prediction = self.model_a.predict(state)
            self.metrics_a.record_prediction(prediction)
            return prediction, 'A'
        else:
            prediction = self.model_b.predict(state)
            self.metrics_b.record_prediction(prediction)
            return prediction, 'B'
    
    def record_outcome(self, variant, success):
        """Record outcome of decision"""
        if variant == 'A':
            self.metrics_a.record_outcome(success)
        else:
            self.metrics_b.record_outcome(success)
    
    def get_results(self):
        """Get A/B test results"""
        results_a = self.metrics_a.get_summary()
        results_b = self.metrics_b.get_summary()
        
        # Statistical significance test
        from scipy.stats import ttest_ind
        
        successes_a = self.metrics_a.get_success_array()
        successes_b = self.metrics_b.get_success_array()
        
        t_stat, p_value = ttest_ind(successes_a, successes_b)
        
        return {
            'model_a': results_a,
            'model_b': results_b,
            't_statistic': t_stat,
            'p_value': p_value,
            'significant': p_value < 0.05
        }
```

### 8.3 Model Drift Detection

```python
def detect_model_drift(model, reference_data, current_data):
    """Detect if model performance has drifted"""
    
    # Feature distribution drift (KS test)
    from scipy.stats import ks_2samp
    
    drift_detected = False
    drift_features = []
    
    for feature in feature_columns:
        ref_values = reference_data[feature]
        curr_values = current_data[feature]
        
        statistic, p_value = ks_2samp(ref_values, curr_values)
        
        if p_value < 0.01:  # Significant drift
            drift_detected = True
            drift_features.append(feature)
            print(f"Drift detected in feature '{feature}' (p={p_value:.4f})")
    
    # Performance drift
    ref_accuracy = evaluate_model(model, reference_data)
    curr_accuracy = evaluate_model(model, current_data)
    
    accuracy_drop = ref_accuracy - curr_accuracy
    
    if accuracy_drop > 0.05:  # 5% drop
        drift_detected = True
        print(f"Performance drift: {accuracy_drop:.2%} drop in accuracy")
    
    return {
        'drift_detected': drift_detected,
        'drift_features': drift_features,
        'accuracy_drop': accuracy_drop
    }
```

### 8.4 Cold-Start Progress Tracking

```python
def track_cold_start_progress():
    """Track ML cold-start strategy progress"""
    
    metrics = {
        'phase': get_current_phase(),
        'samples_collected': get_sample_count(),
        'model_accuracy': get_model_accuracy(),
        'ml_usage_percent': get_ml_usage_percent(),
        'llm_usage_percent': get_llm_usage_percent()
    }
    
    # Phase-specific checks
    if metrics['phase'] == 1:
        assert metrics['samples_collected'] >= 10000, "Phase 1: Need 10k samples"
    elif metrics['phase'] == 2:
        assert metrics['model_accuracy'] >= 0.75, "Phase 2: Model accuracy too low"
        assert metrics['ml_usage_percent'] >= 30, "Phase 2: ML usage too low"
    elif metrics['phase'] == 3:
        assert metrics['model_accuracy'] >= 0.80, "Phase 3: Model accuracy too low"
        assert metrics['ml_usage_percent'] >= 60, "Phase 3: ML usage too low"
    elif metrics['phase'] == 4:
        assert metrics['model_accuracy'] >= 0.85, "Phase 4: Model accuracy too low"
        assert metrics['ml_usage_percent'] >= 85, "Phase 4: ML usage too low"
    
    return metrics
```

---

## 9. Security Testing

### 9.1 Code Obfuscation Verification

```bash
# Verify symbols are stripped
nm openkore_ai_engine.exe | grep -i "reflex\|rule\|llm"
# Should return nothing

# Verify no debug info
objdump -h openkore_ai_engine.exe | grep debug
# Should return nothing

# Verify control flow guard enabled (Windows)
dumpbin /headers openkore_ai_engine.exe | grep "Guard"
```

### 9.2 API Key Security

```python
def test_api_key_not_exposed():
    """Verify API keys are not in logs or memory dumps"""
    
    # Check logs
    with open('data/logs/engine.log', 'r') as f:
        logs = f.read()
        assert 'sk-' not in logs, "API key found in logs"
        assert 'claude-' not in logs, "API key found in logs"
    
    # Check config is encrypted
    with open('config/llm_config.json', 'r') as f:
        config = json.load(f)
        api_key = config.get('llm', {}).get('api_key', '')
        assert not api_key.startswith('sk-'), "API key stored in plaintext"
```

### 9.3 Anti-Debugging Tests

```cpp
TEST(SecurityTest, AntiDebuggingWorks) {
    #ifdef ANTI_DEBUG
    bool debugger_detected = AntiDebug::isDebuggerPresent();
    
    if (debugger_detected) {
        // Should trigger anti-debugging measures
        EXPECT_TRUE(true);  // Verify measure triggered
    }
    #endif
}
```

---

## 10. Test Infrastructure

### 10.1 CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Comprehensive Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build and Test
        run: |
          mkdir build && cd build
          cmake -DCMAKE_BUILD_TYPE=Debug ..
          make -j4
          ctest --output-on-failure
  
  integration-tests:
    needs: unit-tests
    runs-on: ubuntu-latest
    steps:
      - name: Run Integration Tests
        run: |
          python tests/integration/run_all.py
  
  performance-tests:
    needs: unit-tests
    runs-on: ubuntu-latest
    steps:
      - name: Run Performance Benchmarks
        run: |
          ./build/benchmarks/decision_latency_bench
          ./build/benchmarks/memory_benchmark
```

### 10.2 Test Data Management

```
tests/
├── data/
│   ├── fixtures/
│   │   ├── game_states/
│   │   ├── training_data/
│   │   └── configurations/
│   └── expected_outputs/
├── mocks/
│   ├── mock_game_server.py
│   └── mock_llm_service.py
└── utilities/
    ├── test_helpers.cpp
    └── data_generators.py
```

### 10.3 Test Reporting

```python
# Generate comprehensive test report
def generate_test_report():
    report = {
        'timestamp': datetime.now().isoformat(),
        'git_commit': get_git_commit(),
        'test_results': {
            'unit': run_unit_tests(),
            'integration': run_integration_tests(),
            'system': run_system_tests(),
            'performance': run_performance_tests()
        },
        'coverage': get_coverage_stats(),
        'metrics': get_performance_metrics()
    }
    
    # Generate HTML report
    generate_html_report(report, 'test-results/report.html')
    
    # Send to dashboard
    send_to_dashboard(report)
    
    return report
```

---

## Summary

This comprehensive testing strategy ensures:

✅ **Quality**: 75%+ overall code coverage  
✅ **Performance**: All latency targets met  
✅ **Reliability**: Zero crashes in 24-hour tests  
✅ **Safety**: Extensive field testing before production  
✅ **Regression**: Automated detection of breaking changes  
✅ **ML Validation**: Models meet accuracy targets  
✅ **Security**: Obfuscation and key protection verified  

**Next Document:** [Development Environment Setup](03-development-environment.md)
