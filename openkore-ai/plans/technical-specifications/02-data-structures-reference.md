# Data Structures Reference

**Version:** 2.1
**Date:** 2026-02-05
**Status:** Final Specification
**Update:** Added social interaction structures, concurrency primitives, player reputation system

---

## Table of Contents

1. [Overview](#1-overview)
2. [Game State Structures](#2-game-state-structures)
3. [Decision Structures](#3-decision-structures)
4. [ML Structures](#4-ml-structures)
5. [Configuration Structures](#5-configuration-structures)
6. [Utility Structures](#6-utility-structures)
7. [SQLite Database Schemas](#7-sqlite-database-schemas)
8. [OpenMemory SDK Structures](#8-openmemory-sdk-structures)
9. [CrewAI Agent Structures](#9-crewai-agent-structures)
10. [HTTP REST Data Transfer Objects](#10-http-rest-data-transfer-objects)

---

## 1. Overview

### 1.1 Design Principles

- **C++20 Compatible**: Use modern C++ features (std::optional, designated initializers, etc.)
- **Serialization-Friendly**: All structures can be converted to/from JSON (HTTP REST)
- **Memory-Efficient**: Minimize padding, use appropriate data types
- **Cache-Friendly**: Hot data grouped together
- **Type-Safe**: Strong typing with enums and type aliases
- **Cross-Language**: Compatible with Python (JSON serialization)
- **Database-Ready**: SQLite schema definitions included

### 1.2 Common Types

```cpp
// Type aliases for clarity
using PlayerId = uint32_t;
using MonsterId = uint32_t;
using ItemId = uint32_t;
using SkillId = uint32_t;
using MapCoord = int16_t;
using Percentage = float;  // 0.0 to 100.0
using Timestamp = uint64_t;  // Milliseconds since epoch

// Common enums
enum class Direction : uint8_t {
    NORTH = 0,
    NORTHEAST = 1,
    EAST = 2,
    SOUTHEAST = 3,
    SOUTH = 4,
    SOUTHWEST = 5,
    WEST = 6,
    NORTHWEST = 7
};

enum class AIState {
    MANUAL,
    AUTO,
    IDLE,
    DEAD,
    TELEPORTING,
    STORAGE_OPENED,
    TALKING_NPC
};
```

---

## 2. Game State Structures

### 2.1 Position

```cpp
struct Position {
    MapCoord x;
    MapCoord y;
    std::string map;
    
    // Utility methods
    float distance(const Position& other) const {
        if (map != other.map) return std::numeric_limits<float>::infinity();
        float dx = x - other.x;
        float dy = y - other.y;
        return std::sqrt(dx * dx + dy * dy);
    }
    
    bool operator==(const Position& other) const {
        return x == other.x && y == other.y && map == other.map;
    }
    
    // Serialization
    json toJson() const {
        return {{"x", x}, {"y", y}, {"map", map}};
    }
    
    static Position fromJson(const json& j) {
        return Position{
            .x = j["x"].get<MapCoord>(),
            .y = j["y"].get<MapCoord>(),
            .map = j["map"].get<std::string>()
        };
    }
};
```

### 2.2 Character State

```cpp
struct CharacterState {
    // Identity
    PlayerId id;
    std::string name;
    std::string job_class;
    
    // Vital stats
    int32_t hp;
    int32_t max_hp;
    int32_t sp;
    int32_t max_sp;
    Percentage hp_percent;  // Cached for performance
    Percentage sp_percent;
    
    // Level
    uint16_t level;
    uint16_t job_level;
    uint64_t exp;
    uint64_t exp_max;
    uint64_t job_exp;
    uint64_t job_exp_max;
    
    // Position & movement
    Position position;
    Direction facing;
    bool is_moving;
    
    // Weight & resources
    int32_t weight;
    int32_t max_weight;
    Percentage weight_percent;
    uint64_t zeny;
    
    // Status
    std::vector<StatusEffect> status_effects;
    bool is_dead;
    bool is_sitting;
    bool is_casting;
    uint32_t cast_target_id;
    
    // Skills
    std::unordered_map<std::string, SkillInfo> skills;
    
    // Inventory & Equipment
    std::vector<InventoryItem> inventory;
    EquipmentSet equipment;
    
    // Computed properties
    bool isBuffed() const {
        return std::any_of(status_effects.begin(), status_effects.end(),
            [](const StatusEffect& s) { return s.is_positive; });
    }
    
    bool isDebuffed() const {
        return std::any_of(status_effects.begin(), status_effects.end(),
            [](const StatusEffect& s) { return !s.is_positive; });
    }
    
    bool canUseSkill(const std::string& skill_name) const {
        auto it = skills.find(skill_name);
        if (it == skills.end()) return false;
        return sp >= it->second.sp_cost && 
               it->second.cooldown_remaining_ms == 0;
    }
};
```

### 2.3 Status Effect

```cpp
struct StatusEffect {
    uint16_t status_id;
    std::string name;
    bool is_positive;
    uint32_t remaining_ms;
    uint32_t duration_ms;
    
    // Effect modifiers (optional)
    struct Modifiers {
        std::optional<int16_t> atk_bonus;
        std::optional<int16_t> def_bonus;
        std::optional<Percentage> aspd_bonus;
        std::optional<Percentage> movement_speed;
    } modifiers;
    
    bool isExpiring(uint32_t threshold_ms = 5000) const {
        return remaining_ms < threshold_ms;
    }
    
    Percentage percentRemaining() const {
        return (static_cast<float>(remaining_ms) / duration_ms) * 100.0f;
    }
};
```

### 2.4 Skill Info

```cpp
struct SkillInfo {
    SkillId skill_id;
    std::string name;
    uint8_t level;
    uint8_t max_level;
    int32_t sp_cost;
    uint32_t cooldown_ms;
    uint32_t cooldown_remaining_ms;
    uint32_t cast_time_ms;
    float range;
    
    enum class TargetType {
        NONE,
        SELF,
        ENEMY,
        ALLY,
        GROUND,
        ANY
    } target_type;
    
    enum class SkillType {
        OFFENSIVE,
        DEFENSIVE,
        SUPPORT,
        BUFF,
        DEBUFF,
        PASSIVE
    } skill_type;
    
    bool isReady() const {
        return cooldown_remaining_ms == 0;
    }
    
    bool canAfford(int32_t current_sp) const {
        return current_sp >= sp_cost;
    }
};
```

### 2.5 Monster State

```cpp
struct Monster {
    MonsterId id;               // Runtime ID
    uint16_t name_id;          // Monster type ID
    std::string name;
    
    // Stats
    uint16_t level;
    Position position;
    Direction facing;
    
    // Health (estimated)
    Percentage hp_percent;
    bool hp_known;
    
    // Behavior
    bool is_aggressive;
    bool is_boss;
    bool is_mvp;
    
    // Combat state
    bool is_attacking_me;
    bool is_attacking_party;
    uint32_t damage_to_me;
    uint32_t damage_from_me;
    
    // Computed properties
    float distance_to_player;
    float threat_level;        // 0.0 to 10.0
    
    // Timing
    Timestamp first_seen;
    Timestamp last_seen;
    
    // Calculate threat based on multiple factors
    float calculateThreat(const CharacterState& player) const {
        float threat = 0.0f;
        
        // Base threat from level difference
        int level_diff = level - player.level;
        threat += level_diff * 0.1f;
        
        // Threat from aggression
        if (is_attacking_me) threat += 5.0f;
        else if (is_aggressive) threat += 2.0f;
        
        // Proximity threat
        float proximity_factor = std::max(0.0f, 1.0f - (distance_to_player / 20.0f));
        threat += proximity_factor * 3.0f;
        
        // Boss modifier
        if (is_boss || is_mvp) threat *= 2.0f;
        
        return std::clamp(threat, 0.0f, 10.0f);
    }
    
    bool isInRange(float range) const {
        return distance_to_player <= range;
    }
};
```

### 2.6 Player State

```cpp
struct Player {
    PlayerId id;
    std::string name;
    Position position;
    
    // Guild & Party
    std::string guild_name;
    bool is_guild_member;
    bool is_party_member;
    bool is_friend;
    
    // Combat
    bool is_pvp_target;
    bool is_in_combat;
    
    // Equipment visibility (optional)
    struct VisibleEquipment {
        std::optional<uint16_t> weapon;
        std::optional<uint16_t> shield;
        std::optional<uint16_t> head_top;
    } equipment;
    
    float distance_to_me;
};
```

### 2.7 Item on Ground

```cpp
struct ItemOnGround {
    uint32_t item_id;
    ItemId item_type_id;
    std::string name;
    Position position;
    uint32_t amount;
    
    Timestamp appeared_at;
    uint32_t ownership_id;  // 0 if anyone can pick up
    
    enum class ItemValue {
        JUNK,
        LOW,
        MEDIUM,
        HIGH,
        RARE
    } estimated_value;
    
    float distance_to_player;
    
    bool canPickUp(PlayerId player_id) const {
        return ownership_id == 0 || ownership_id == player_id;
    }
    
    bool isExpiring() const {
        auto age = getCurrentTimestamp() - appeared_at;
        return age > 50000;  // 50 seconds (items disappear at 60s)
    }
};
```

### 2.8 Party State

```cpp
struct PartyMember {
    PlayerId id;
    std::string name;
    Position position;
    Percentage hp_percent;
    Percentage sp_percent;
    bool is_online;
    bool is_in_range;
    float distance_to_me;
};

struct PartyState {
    std::string party_name;
    bool is_organized;
    std::vector<PartyMember> members;
    
    size_t getMemberCount() const {
        return std::count_if(members.begin(), members.end(),
            [](const PartyMember& m) { return m.is_online; });
    }
    
    std::optional<PartyMember> getMemberById(PlayerId id) const {
        auto it = std::find_if(members.begin(), members.end(),
            [id](const PartyMember& m) { return m.id == id; });
        return it != members.end() ? std::optional{*it} : std::nullopt;
    }
    
    std::vector<PartyMember> getMembersNeedingHelp(Percentage hp_threshold = 50.0f) const {
        std::vector<PartyMember> result;
        std::copy_if(members.begin(), members.end(), std::back_inserter(result),
            [hp_threshold](const PartyMember& m) { 
                return m.is_online && m.hp_percent < hp_threshold; 
            });
        return result;
    }
};
```

### 2.9 Complete Game State

```cpp
struct GameState {
    Timestamp timestamp;
    
    // Player
    CharacterState character;
    
    // Entities
    std::vector<Monster> monsters;
    std::vector<Player> players;
    std::vector<ItemOnGround> items_on_ground;
    std::vector<NPC> npcs;
    
    // Party & Social
    std::optional<PartyState> party;
    std::optional<GuildState> guild;
    
    // Map & Environment
    std::string current_map;
    MapInfo map_info;
    WeatherCondition weather;
    
    // AI State
    AIState ai_state;
    std::optional<uint32_t> current_target_id;
    
    // Inventory summary
    struct InventorySummary {
        size_t item_count;
        Percentage weight_percent;
        uint32_t consumable_count;
        bool has_emergency_items;
    } inventory_summary;
    
    // Computed properties
    size_t getMonsterCount() const { return monsters.size(); }
    size_t getPlayerCount() const { return players.size(); }
    size_t getItemCount() const { return items_on_ground.size(); }
    
    std::vector<Monster> getMonstersInRange(float range) const {
        std::vector<Monster> result;
        std::copy_if(monsters.begin(), monsters.end(), std::back_inserter(result),
            [range](const Monster& m) { return m.distance_to_player <= range; });
        return result;
    }
    
    std::vector<Monster> getAggressiveMonsters() const {
        std::vector<Monster> result;
        std::copy_if(monsters.begin(), monsters.end(), std::back_inserter(result),
            [](const Monster& m) { return m.is_aggressive || m.is_attacking_me; });
        return result;
    }
    
    float getMaxThreatLevel() const {
        if (monsters.empty()) return 0.0f;
        return std::max_element(monsters.begin(), monsters.end(),
            [](const Monster& a, const Monster& b) { 
                return a.threat_level < b.threat_level; 
            })->threat_level;
    }
    
    bool isInDanger() const {
        return character.hp_percent < 30.0f || 
               getAggressiveMonsters().size() > 5 ||
               getMaxThreatLevel() > 7.0f;
    }
};
```

---

## 3. Decision Structures

### 3.1 Action

```cpp
enum class ActionType {
    NO_ACTION,
    MOVE_TO,
    ATTACK,
    USE_SKILL,
    USE_ITEM,
    PICK_ITEM,
    TALK_NPC,
    EXECUTE_MACRO,
    SEND_COMMAND,
    CHANGE_STATE,
    TELEPORT,
    SIT,
    STAND,
    STORAGE_GET,
    STORAGE_PUT
};

struct Action {
    ActionType type;
    std::unordered_map<std::string, json> parameters;
    int32_t priority;              // Higher = more important
    uint32_t timeout_ms;
    std::optional<Action> fallback_action;
    
    // Factory methods
    static Action NoAction() {
        return Action{.type = ActionType::NO_ACTION, .priority = 0};
    }
    
    static Action MoveTo(const Position& pos, int32_t priority = 50) {
        return Action{
            .type = ActionType::MOVE_TO,
            .parameters = {
                {"map", pos.map},
                {"x", pos.x},
                {"y", pos.y}
            },
            .priority = priority,
            .timeout_ms = 30000
        };
    }
    
    static Action UseSkill(const std::string& skill, uint32_t target_id, 
                          int32_t priority = 70) {
        return Action{
            .type = ActionType::USE_SKILL,
            .parameters = {
                {"skill", skill},
                {"target_id", target_id}
            },
            .priority = priority,
            .timeout_ms = 5000
        };
    }
    
    static Action UseItem(const std::string& item_name, int32_t priority = 80) {
        return Action{
            .type = ActionType::USE_ITEM,
            .parameters = {
                {"item", item_name}
            },
            .priority = priority,
            .timeout_ms = 2000
        };
    }
    
    static Action ExecuteMacro(const std::string& macro_name, 
                               const json& params = {}, int32_t priority = 60) {
        return Action{
            .type = ActionType::EXECUTE_MACRO,
            .parameters = {
                {"macro_name", macro_name},
                {"parameters", params}
            },
            .priority = priority,
            .timeout_ms = 60000
        };
    }
    
    json toJson() const;
    static Action fromJson(const json& j);
};
```

### 3.2 Decision Request

```cpp
enum class DecisionPriority {
    LOW = 0,
    NORMAL = 1,
    HIGH = 2,
    CRITICAL = 3
};

struct DecisionRequest {
    GameState state;
    DecisionPriority priority;
    uint64_t deadline_us;          // Microsecond deadline
    std::string decision_context;   // "combat", "navigation", "resource_management"
    
    static DecisionRequest fromGameState(const GameState& state, 
                                         DecisionPriority priority = DecisionPriority::NORMAL) {
        uint64_t deadline = 100000;  // 100ms default
        
        if (state.isInDanger()) {
            priority = DecisionPriority::CRITICAL;
            deadline = 50000;  // 50ms for danger
        }
        
        return DecisionRequest{
            .state = state,
            .priority = priority,
            .deadline_us = deadline
        };
    }
};
```

### 3.3 Decision Response

```cpp
enum class DecisionTier {
    REFLEX,     // Level 0: < 1ms
    RULE,       // Level 1: < 10ms
    ML,         // Level 2: < 100ms
    LLM         // Level 3: 1-5s
};

struct DecisionResponse {
    Action action;
    DecisionTier tier;
    uint64_t processing_time_us;
    float confidence;              // 0.0 to 1.0
    std::string reasoning;
    std::string model_version;     // For ML/LLM tiers
    
    // Metadata
    struct Metadata {
        std::vector<std::string> considered_actions;
        std::unordered_map<std::string, float> action_scores;
        std::string decision_id;
    } metadata;
    
    bool isHighConfidence() const {
        return confidence >= 0.8f;
    }
    
    bool meetsDeadline(uint64_t deadline_us) const {
        return processing_time_us <= deadline_us;
    }
};
```

### 3.4 Rule Structure

```cpp
struct Condition {
    enum class Type {
        HP, SP, WEIGHT, LEVEL, MONSTER_COUNT, MONSTER_DISTANCE,
        PLAYER_COUNT, ITEM_COUNT, STATUS_EFFECT, MAP, TIME,
        PARTY_SIZE, ZENY, INVENTORY_ITEM
    } type;
    
    enum class Operator {
        EQUAL, NOT_EQUAL, GREATER, LESS, GREATER_EQUAL, LESS_EQUAL,
        IN, NOT_IN, CONTAINS, NOT_CONTAINS, EXISTS, NOT_EXISTS
    } op;
    
    json value;
    
    bool evaluate(const GameState& state) const;
};

struct Rule {
    std::string id;
    std::string name;
    std::string category;
    std::vector<Condition> conditions;
    Action action;
    int32_t priority;
    bool enabled;
    
    // State tracking
    uint32_t execution_count;
    uint32_t success_count;
    Timestamp last_executed;
    
    float getSuccessRate() const {
        return execution_count > 0 ? 
            static_cast<float>(success_count) / execution_count : 0.0f;
    }
    
    bool matchesState(const GameState& state) const {
        return std::all_of(conditions.begin(), conditions.end(),
            [&state](const Condition& c) { return c.evaluate(state); });
    }
};
```

---

## 4. ML Structures

### 4.1 Feature Vector

```cpp
struct FeatureVector {
    // Character features (8)
    float hp_ratio;
    float sp_ratio;
    float weight_ratio;
    float level_normalized;        // level / 175.0
    float job_level_normalized;    // job_level / 70.0
    float zeny_log;               // log10(zeny + 1)
    int32_t status_effect_count;
    int32_t buff_count;
    
    // Combat features (10)
    int32_t monster_count;
    float avg_monster_level;
    float avg_monster_distance;
    float min_monster_distance;
    float max_threat_level;
    int32_t aggressive_monster_count;
    int32_t attacking_me_count;
    float total_damage_received;
    float total_damage_dealt;
    int32_t kill_count_session;
    
    // Environment features (6)
    int32_t player_count_nearby;
    int32_t party_member_count;
    int32_t item_count_ground;
    float map_difficulty;          // Estimated 0-10
    int32_t time_of_day;          // 0-23
    float time_since_last_combat;  // seconds
    
    // Temporal features (4)
    float time_since_last_death;
    float time_since_last_teleport;
    float session_duration;
    float combat_time_ratio;
    
    // Total: 28 features
    
    static constexpr size_t FEATURE_COUNT = 28;
    
    std::vector<float> toVector() const {
        return {
            hp_ratio, sp_ratio, weight_ratio, level_normalized, job_level_normalized,
            zeny_log, static_cast<float>(status_effect_count), 
            static_cast<float>(buff_count),
            static_cast<float>(monster_count), avg_monster_level, avg_monster_distance,
            min_monster_distance, max_threat_level, 
            static_cast<float>(aggressive_monster_count),
            static_cast<float>(attacking_me_count), total_damage_received,
            total_damage_dealt, static_cast<float>(kill_count_session),
            static_cast<float>(player_count_nearby), 
            static_cast<float>(party_member_count),
            static_cast<float>(item_count_ground), map_difficulty,
            static_cast<float>(time_of_day), time_since_last_combat,
            time_since_last_death, time_since_last_teleport,
            session_duration, combat_time_ratio
        };
    }
    
    static FeatureVector fromGameState(const GameState& state);
};
```

### 4.2 Training Record

```cpp
struct TrainingRecord {
    std::string id;                // UUID
    Timestamp timestamp;
    
    // Input
    GameState state;
    FeatureVector features;
    
    // Decision
    struct Decision {
        DecisionTier tier;
        Action action;
        std::string reasoning;
        float confidence;
    } decision;
    
    // Outcome
    struct Outcome {
        bool success;
        float reward;               // -1.0 to 1.0
        
        struct Metrics {
            int32_t exp_gained;
            int32_t damage_taken;
            int32_t damage_dealt;
            float time_elapsed_s;
            bool died;
        } metrics;
        
        Timestamp outcome_timestamp;
    } outcome;
    
    // For supervised learning
    ActionType getLabel() const {
        return decision.action.type;
    }
    
    // For reinforcement learning
    float getReward() const {
        return outcome.reward;
    }
};
```

### 4.3 Model Metadata

```cpp
struct ModelMetadata {
    std::string model_id;
    std::string model_name;
    std::string model_type;        // "decision_tree", "random_forest", "neural_net"
    std::string version;
    
    // Training info
    Timestamp trained_at;
    size_t training_samples;
    size_t validation_samples;
    
    // Performance metrics
    struct Metrics {
        float accuracy;
        float precision;
        float recall;
        float f1_score;
        std::unordered_map<std::string, float> per_class_accuracy;
    } metrics;
    
    // Hyperparameters
    json hyperparameters;
    
    // Deployment info
    std::string model_path;
    size_t model_size_bytes;
    float inference_time_avg_ms;
    
    bool isProduction() const {
        return metrics.accuracy >= 0.85f;
    }
};
```

### 4.4 Model Prediction

```cpp
struct Prediction {
    Action action;
    float confidence;
    std::string reasoning;
    
    // Probability distribution over all actions
    std::unordered_map<ActionType, float> action_probabilities;
    
    // Feature importance (for interpretability)
    std::vector<std::pair<std::string, float>> feature_importance;
    
    uint64_t inference_time_us;
    
    ActionType getPredictedClass() const {
        return action.type;
    }
    
    std::vector<ActionType> getTopKActions(size_t k) const {
        std::vector<std::pair<ActionType, float>> sorted_actions(
            action_probabilities.begin(), action_probabilities.end());
        
        std::partial_sort(sorted_actions.begin(), 
                         sorted_actions.begin() + k,
                         sorted_actions.end(),
                         [](const auto& a, const auto& b) { return a.second > b.second; });
        
        std::vector<ActionType> result;
        for (size_t i = 0; i < k && i < sorted_actions.size(); i++) {
            result.push_back(sorted_actions[i].first);
        }
        return result;
    }
};
```

---

## 5. Configuration Structures

### 5.1 Engine Configuration

```cpp
struct EngineConfig {
    std::string name;
    std::string version;
    std::string log_level;
    std::string log_file;
    
    struct IPC {
        std::string type;          // "named_pipe", "unix_socket", "tcp"
        std::string address;
        uint32_t timeout_ms;
        uint32_t buffer_size;
        bool authentication_required;
    } ipc;
    
    struct DecisionCoordinator {
        std::string escalation_policy;
        std::unordered_map<std::string, uint32_t> tier_timeouts_ms;
        std::unordered_map<std::string, float> confidence_thresholds;
        bool fallback_enabled;
        bool metrics_logging;
    } coordinator;
    
    static EngineConfig loadFromFile(const std::string& path);
    void saveToFile(const std::string& path) const;
};
```

### 5.2 LLM Configuration

```cpp
struct LLMConfig {
    struct Provider {
        std::string name;
        int32_t priority;
        std::string model;
        std::string api_key_env;
        std::string endpoint;
        uint32_t max_tokens;
        float temperature;
        uint32_t timeout_seconds;
        uint32_t retry_attempts;
    };
    
    std::vector<Provider> providers;
    bool fallback_enabled;
    bool cache_enabled;
    uint32_t cache_ttl_minutes;
    
    Provider getPrimaryProvider() const {
        return *std::min_element(providers.begin(), providers.end(),
            [](const Provider& a, const Provider& b) { 
                return a.priority < b.priority; 
            });
    }
};
```

---

## 6. Utility Structures

### 6.1 Metrics

```cpp
struct PerformanceMetrics {
    // Combat metrics
    uint32_t kills;
    uint32_t deaths;
    uint64_t exp_gained;
    uint64_t damage_dealt;
    uint64_t damage_taken;
    float avg_kill_time_s;
    
    // Resource metrics
    uint64_t zeny_gained;
    uint32_t items_picked;
    uint32_t potions_used;
    float avg_weight_percent;
    
    // Efficiency metrics
    float uptime_percent;
    float combat_time_percent;
    float idle_time_percent;
    float exp_per_hour;
    
    // Decision metrics
    uint32_t reflex_decisions;
    uint32_t rule_decisions;
    uint32_t ml_decisions;
    uint32_t llm_decisions;
    float avg_decision_time_ms;
    
    float getEfficiencyScore() const {
        return (uptime_percent * 0.4f) + 
               (combat_time_percent * 0.3f) +
               (exp_per_hour / 1000000.0f * 0.3f);  // Normalize EXP/hr
    }
};
```

### 6.2 Error Information

```cpp
struct ErrorInfo {
    enum class Severity {
        INFO,
        WARNING,
        ERROR,
        CRITICAL
    } severity;
    
    std::string error_code;
    std::string error_message;
    std::string component;
    Timestamp timestamp;
    
    json details;
    std::optional<std::string> stack_trace;
    
    bool isCritical() const {
        return severity == Severity::CRITICAL;
    }
};
```

---

## Appendix A: Serialization Helpers

```cpp
// JSON serialization for all major structures
namespace json_serialization {
    json serialize(const GameState& state);
    GameState deserializeGameState(const json& j);
    
    json serialize(const Action& action);
    Action deserializeAction(const json& j);
    
    json serialize(const FeatureVector& features);
    FeatureVector deserializeFeatures(const json& j);
}
```

---

## Appendix B: Memory Layout Optimization

Structures are ordered to minimize padding:

```cpp
// Good: 24 bytes (no padding)
struct Optimized {
    uint64_t a;  // 8 bytes
    uint64_t b;  // 8 bytes
    uint32_t c;  // 4 bytes
    uint32_t d;  // 4 bytes
};

// Bad: 32 bytes (8 bytes padding)
struct Unoptimized {
    uint64_t a;  // 8 bytes
    uint32_t c;  // 4 bytes + 4 bytes padding
    uint64_t b;  // 8 bytes
    uint32_t d;  // 4 bytes + 4 bytes padding
};
```

---

## 7. SQLite Database Schemas

### 7.1 Overview

SQLite provides persistent storage for game state, memory, metrics, and lifecycle tracking.

**Database File:** `data/openkore_ai.db`

### 7.2 Player Sessions Table

```sql
CREATE TABLE player_sessions (
    session_id TEXT PRIMARY KEY,
    character_name TEXT NOT NULL,
    character_id INTEGER NOT NULL,
    start_time INTEGER NOT NULL,
    end_time INTEGER,
    total_exp_gained INTEGER DEFAULT 0,
    total_job_exp_gained INTEGER DEFAULT 0,
    total_zeny_earned INTEGER DEFAULT 0,
    start_level INTEGER NOT NULL,
    end_level INTEGER,
    start_job_level INTEGER NOT NULL,
    end_job_level INTEGER,
    monsters_killed INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    quests_completed INTEGER DEFAULT 0,
    session_metadata TEXT,  -- JSON
    UNIQUE(character_name, start_time)
);

CREATE INDEX idx_sessions_character ON player_sessions(character_name);
CREATE INDEX idx_sessions_time ON player_sessions(start_time DESC);
```

**C++ Structure:**
```cpp
struct PlayerSession {
    std::string session_id;
    std::string character_name;
    uint32_t character_id;
    Timestamp start_time;
    std::optional<Timestamp> end_time;
    uint64_t total_exp_gained;
    uint64_t total_job_exp_gained;
    uint64_t total_zeny_earned;
    uint16_t start_level;
    std::optional<uint16_t> end_level;
    uint16_t start_job_level;
    std::optional<uint16_t> end_job_level;
    uint32_t monsters_killed;
    uint32_t deaths;
    uint32_t quests_completed;
    json session_metadata;
    
    json toJson() const;
    static PlayerSession fromDb(sqlite3_stmt* stmt);
};
```

### 7.3 Memories Table (OpenMemory SDK)

```sql
CREATE TABLE memories (
    memory_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    memory_type TEXT NOT NULL,  -- 'episodic', 'semantic', 'procedural'
    content TEXT NOT NULL,       -- JSON content
    embedding BLOB,              -- Synthetic embedding vector (384 dims)
    importance REAL DEFAULT 0.5, -- 0.0 to 1.0
    access_count INTEGER DEFAULT 0,
    last_accessed INTEGER,
    metadata TEXT,               -- JSON extra data
    FOREIGN KEY (session_id) REFERENCES player_sessions(session_id)
);

CREATE INDEX idx_memories_session ON memories(session_id);
CREATE INDEX idx_memories_type ON memories(memory_type);
CREATE INDEX idx_memories_importance ON memories(importance DESC);
CREATE INDEX idx_memories_timestamp ON memories(timestamp DESC);
```

**Python Structure (Pydantic):**
```python
from pydantic import BaseModel
from typing import Optional, List
import numpy as np

class Memory(BaseModel):
    memory_id: str
    session_id: str
    timestamp: int
    memory_type: str  # 'episodic', 'semantic', 'procedural'
    content: dict
    embedding: Optional[List[float]] = None  # 384-dim vector
    importance: float = 0.5
    access_count: int = 0
    last_accessed: Optional[int] = None
    metadata: Optional[dict] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def to_db_tuple(self):
        """Convert to SQLite insert tuple"""
        import json
        import pickle
        
        return (
            self.memory_id,
            self.session_id,
            self.timestamp,
            self.memory_type,
            json.dumps(self.content),
            pickle.dumps(np.array(self.embedding)) if self.embedding else None,
            self.importance,
            self.access_count,
            self.last_accessed,
            json.dumps(self.metadata) if self.metadata else None
        )
```

### 7.4 Decision Log Table

```sql
CREATE TABLE decision_log (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    game_state TEXT NOT NULL,    -- JSON snapshot
    decision_tier TEXT NOT NULL,  -- 'reflex', 'rule', 'ml', 'llm'
    action_taken TEXT NOT NULL,   -- JSON action
    action_type TEXT NOT NULL,    -- 'attack', 'move', 'skill', etc.
    target_id INTEGER,
    success BOOLEAN,
    outcome TEXT,                 -- JSON result
    reward REAL,                  -- Reinforcement learning reward
    processing_time_ms REAL,
    confidence REAL,              -- Decision confidence (0-1)
    FOREIGN KEY (session_id) REFERENCES player_sessions(session_id)
);

CREATE INDEX idx_decisions_session ON decision_log(session_id);
CREATE INDEX idx_decisions_tier ON decision_log(decision_tier);
CREATE INDEX idx_decisions_type ON decision_log(action_type);
CREATE INDEX idx_decisions_timestamp ON decision_log(timestamp DESC);
```

**C++ Structure:**
```cpp
struct DecisionLogEntry {
    uint64_t decision_id;
    std::string session_id;
    Timestamp timestamp;
    json game_state;
    std::string decision_tier;  // "reflex", "rule", "ml", "llm"
    json action_taken;
    std::string action_type;
    std::optional<uint32_t> target_id;
    std::optional<bool> success;
    std::optional<json> outcome;
    std::optional<float> reward;
    float processing_time_ms;
    std::optional<float> confidence;
    
    static std::string insertSql();
    std::vector<std::any> getValues() const;
};
```

### 7.5 Performance Metrics Table

```sql
CREATE TABLE metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    metric_unit TEXT,
    metric_metadata TEXT,  -- JSON extra data
    FOREIGN KEY (session_id) REFERENCES player_sessions(session_id)
);

CREATE INDEX idx_metrics_session ON metrics(session_id);
CREATE INDEX idx_metrics_name ON metrics(metric_name);
CREATE INDEX idx_metrics_timestamp ON metrics(timestamp DESC);

-- Common metric names:
-- 'exp_per_hour', 'zeny_per_hour', 'monsters_per_hour',
-- 'deaths_per_hour', 'decision_latency_ms', 'api_latency_ms'
```

### 7.6 Game Lifecycle State Table

```sql
CREATE TABLE lifecycle_state (
    character_name TEXT PRIMARY KEY,
    current_level INTEGER DEFAULT 1,
    current_job TEXT DEFAULT 'Novice',
    job_level INTEGER DEFAULT 1,
    current_stage TEXT NOT NULL,  -- Lifecycle stage enum
    current_goal TEXT,             -- JSON goal object
    goal_history TEXT,             -- JSON array of completed goals
    rebirth_count INTEGER DEFAULT 0,
    total_playtime_hours REAL DEFAULT 0,
    equipment_value INTEGER DEFAULT 0,
    last_updated INTEGER NOT NULL,
    lifecycle_metadata TEXT        -- JSON
);

CREATE INDEX idx_lifecycle_stage ON lifecycle_state(current_stage);
CREATE INDEX idx_lifecycle_updated ON lifecycle_state(last_updated DESC);
```

**Python Structure:**
```python
class LifecycleState(BaseModel):
    character_name: str
    current_level: int = 1
    current_job: str = "Novice"
    job_level: int = 1
    current_stage: str
    current_goal: Optional[dict] = None
    goal_history: List[dict] = []
    rebirth_count: int = 0
    total_playtime_hours: float = 0.0
    equipment_value: int = 0
    last_updated: int
    lifecycle_metadata: Optional[dict] = None
```

### 7.7 Equipment History Table

```sql
CREATE TABLE equipment_history (
    equipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_name TEXT NOT NULL,
    slot TEXT NOT NULL,  -- 'weapon', 'armor', 'headgear_upper', etc.
    item_name TEXT NOT NULL,
    item_id INTEGER NOT NULL,
    refine_level INTEGER DEFAULT 0,
    cards TEXT,  -- JSON array of card IDs
    acquired_at INTEGER NOT NULL,
    acquisition_method TEXT,  -- 'purchase', 'drop', 'quest', 'craft'
    cost INTEGER DEFAULT 0,
    replaced_at INTEGER,
    replaced_by TEXT,
    FOREIGN KEY (character_name) REFERENCES lifecycle_state(character_name)
);

CREATE INDEX idx_equipment_character ON equipment_history(character_name);
CREATE INDEX idx_equipment_slot ON equipment_history(slot);
CREATE INDEX idx_equipment_acquired ON equipment_history(acquired_at DESC);
```

---

## 8. OpenMemory SDK Structures

### 8.1 Overview

OpenMemory SDK provides memory management with synthetic embeddings (no external API dependencies).

**Implementation:** Python library for memory storage and retrieval

### 8.2 Memory Configuration

```python
from openmemory import MemoryConfig, EmbeddingModel

class OpenMemoryConfiguration:
    """Configuration for OpenMemory SDK"""
    
    config = MemoryConfig(
        embedding_model="synthetic",  # No OpenAI/external API
        embedding_dim=384,            # Smaller dimension for performance
        similarity_threshold=0.75,    # Minimum similarity for retrieval
        max_memories=10000,           # Maximum memories to store
        decay_factor=0.995,           # Importance decay over time
        consolidation_threshold=100   # Memories before consolidation
    )
```

### 8.3 Memory Types

```python
from enum import Enum

class MemoryType(str, Enum):
    EPISODIC = "episodic"      # Specific game events
    SEMANTIC = "semantic"       # General knowledge
    PROCEDURAL = "procedural"   # Learned behaviors/skills

class EpisodicMemory(BaseModel):
    """Specific game event memory"""
    event_type: str  # 'combat', 'death', 'level_up', 'quest', 'trade'
    location: dict   # {'map': str, 'x': int, 'y': int}
    actors: List[str]  # Involved entities
    outcome: str     # 'success', 'failure', 'partial'
    rewards: Optional[dict] = None
    damage_taken: Optional[int] = None
    duration_seconds: Optional[float] = None

class SemanticMemory(BaseModel):
    """General knowledge memory"""
    concept: str     # 'monster_weakness', 'map_layout', 'quest_solution'
    knowledge: dict  # Structured knowledge
    source: str      # 'experience', 'llm', 'manual'
    confidence: float = 1.0

class ProceduralMemory(BaseModel):
    """Learned behavior memory"""
    skill_name: str
    context: dict    # When to use this skill
    success_rate: float
    usage_count: int
    avg_reward: float
```

### 8.4 Memory Manager

```python
from openmemory import OpenMemory

class GameMemoryManager:
    """Manages game memories using OpenMemory SDK"""
    
    def __init__(self, db_path: str):
        self.memory = OpenMemory(
            config=OpenMemoryConfiguration.config,
            db_path=db_path
        )
    
    def store_episodic_memory(self, event: dict) -> str:
        """Store game event as episodic memory"""
        memory_id = self.memory.store(
            content=event,
            memory_type=MemoryType.EPISODIC,
            importance=self._calculate_importance(event)
        )
        return memory_id
    
    def retrieve_similar_situations(
        self,
        current_state: dict,
        k: int = 5
    ) -> List[dict]:
        """Retrieve similar past situations"""
        query = self._state_to_query(current_state)
        
        memories = self.memory.search(
            query=query,
            top_k=k,
            memory_types=[MemoryType.EPISODIC]
        )
        
        return memories
    
    def _calculate_importance(self, event: dict) -> float:
        """Calculate memory importance (0.0-1.0)"""
        importance = 0.5  # Base
        
        # High importance events
        high_importance_events = [
            'death', 'level_up', 'job_change',
            'mvp_kill', 'rare_drop'
        ]
        if event.get('type') in high_importance_events:
            importance += 0.3
        
        # Reward-based importance
        if 'reward' in event and event['reward'] > 0:
            importance += min(0.2, event['reward'] / 10000)
        
        return min(1.0, importance)
```

### 8.5 Synthetic Embedding Strategy

```python
class SyntheticEmbeddingGenerator:
    """Generate embeddings without external APIs"""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.vocab = self._build_vocabulary()
        self.idf = self._calculate_idf()
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate TF-IDF based embedding"""
        # Tokenize
        tokens = self._tokenize(text)
        
        # Calculate TF-IDF
        tf_idf = self._calculate_tf_idf(tokens)
        
        # Project to fixed dimension
        embedding = self._project_to_dimension(tf_idf)
        
        # Normalize
        return embedding / np.linalg.norm(embedding)
    
    def semantic_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """Calculate cosine similarity"""
        return np.dot(embedding1, embedding2)
```

---

## 9. CrewAI Agent Structures

### 9.1 Overview

CrewAI provides multi-agent framework for complex decision-making scenarios.

**Implementation:** Python library with LLM-powered agents

### 9.2 Agent Definitions

```python
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI

class AgentRole(str, Enum):
    STRATEGIC_PLANNER = "strategic_planner"
    COMBAT_TACTICIAN = "combat_tactician"
    RESOURCE_MANAGER = "resource_manager"
    PERFORMANCE_ANALYST = "performance_analyst"

class AgentConfig(BaseModel):
    """Configuration for a single agent"""
    role: AgentRole
    goal: str
    backstory: str
    llm_model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000
    verbose: bool = True
```

### 9.3 Strategic Planner Agent

```python
strategic_planner = Agent(
    role="Strategic Planner",
    goal="Develop long-term character progression strategies",
    backstory="""
    You are an expert Ragnarok Online strategist with deep knowledge of:
    - Character progression paths and job systems
    - Equipment progression and BiS (Best-in-Slot) items
    - Efficient leveling strategies and farming locations
    - Quest chains and unlockable content
    - Economic optimization (zeny farming and spending)
    
    Your expertise comes from analyzing thousands of successful players
    and understanding optimal progression patterns for each job class.
    """,
    llm=ChatOpenAI(model="gpt-4", temperature=0.7),
    verbose=True,
    allow_delegation=False
)
```

### 9.4 Combat Tactician Agent

```python
combat_tactician = Agent(
    role="Combat Tactician",
    goal="Optimize combat strategies and skill rotations",
    backstory="""
    You are a specialist in Ragnarok Online combat mechanics:
    - Skill damage calculations and element interactions
    - Monster AI patterns and weaknesses
    - Optimal skill rotations for different situations
    - Positioning and kiting strategies
    - Buff management and resource efficiency
    
    You analyze combat scenarios to recommend the most effective
    approach for each situation based on character build and enemies.
    """,
    llm=ChatOpenAI(model="gpt-4", temperature=0.5),
    verbose=True,
    allow_delegation=False
)
```

### 9.5 Resource Manager Agent

```python
resource_manager = Agent(
    role="Resource Manager",
    goal="Manage inventory, zeny, and consumables efficiently",
    backstory="""
    You are an expert at economic optimization in Ragnarok Online:
    - Zeny farming efficiency and profit maximization
    - Resource allocation and budget management
    - Market analysis and trading strategies
    - Inventory management and storage optimization
    - Cost-benefit analysis for equipment upgrades
    
    Your goal is to ensure the character always has necessary resources
    while maximizing long-term wealth accumulation.
    """,
    llm=ChatOpenAI(model="gpt-4", temperature=0.6),
    verbose=True,
    allow_delegation=False
)
```

### 9.6 Performance Analyst Agent

```python
performance_analyst = Agent(
    role="Performance Analyst",
    goal="Analyze performance metrics and identify improvements",
    backstory="""
    You are a data analyst specializing in gaming performance:
    - Statistical analysis of game metrics
    - Bottleneck identification and optimization
    - A/B testing and strategy comparison
    - Learning curve analysis and skill development
    - Efficiency measurement (exp/hour, zeny/hour, etc.)
    
    You use data-driven approaches to identify what's working well
    and what needs improvement in the character's gameplay.
    """,
    llm=ChatOpenAI(model="gpt-4", temperature=0.3),
    verbose=True,
    allow_delegation=False
)
```

### 9.7 Crew Task Structure

```python
class CrewTask(BaseModel):
    """Task for CrewAI execution"""
    task_type: str  # 'strategic', 'tactical', 'resource', 'analysis'
    description: str
    expected_output: str
    context: dict
    agent: AgentRole
    timeout_seconds: int = 300

class CrewExecutionResult(BaseModel):
    """Result from CrewAI execution"""
    task_id: str
    task_type: str
    status: str  # 'success', 'failed', 'timeout'
    result: dict
    agents_involved: List[str]
    processing_time_ms: float
    token_usage: Optional[dict] = None
```

### 9.8 Crew Manager

```python
class OpenKoreAgentCrew:
    """CrewAI-based multi-agent system"""
    
    def __init__(self, llm_config: dict):
        self.llm = ChatOpenAI(**llm_config)
        self._initialize_agents()
    
    def execute_strategic_planning(self, context: dict) -> dict:
        """Execute strategic planning using multiple agents"""
        
        # Define tasks
        strategic_task = Task(
            description=f"Analyze and create progression plan: {context}",
            agent=self.strategic_planner,
            expected_output="Detailed progression plan with milestones"
        )
        
        combat_task = Task(
            description=f"Design combat strategy: {context}",
            agent=self.combat_tactician,
            expected_output="Combat strategy with skill priorities"
        )
        
        resource_task = Task(
            description=f"Create resource management plan: {context}",
            agent=self.resource_manager,
            expected_output="Resource allocation strategy"
        )
        
        # Create and execute crew
        crew = Crew(
            agents=[
                self.strategic_planner,
                self.combat_tactician,
                self.resource_manager
            ],
            tasks=[strategic_task, combat_task, resource_task],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff()
        return self._parse_crew_result(result)
```

### 9.9 When to Use CrewAI vs Single LLM

```python
class DecisionComplexity(Enum):
    SIMPLE = "simple"          # Single LLM call
    MODERATE = "moderate"       # Single LLM with context
    COMPLEX = "complex"         # CrewAI multi-agent
    CRITICAL = "critical"       # CrewAI with validation

def select_decision_method(scenario: dict) -> DecisionComplexity:
    """Determine appropriate decision method"""
    
    # Time horizon
    if scenario.get('time_horizon_hours', 0) > 10:
        return DecisionComplexity.COMPLEX
    
    # Multiple objectives
    if len(scenario.get('objectives', [])) > 3:
        return DecisionComplexity.COMPLEX
    
    # High stakes (expensive decision)
    if scenario.get('cost', 0) > 1000000:
        return DecisionComplexity.CRITICAL
    
    # Simple tactical decision
    if scenario.get('type') == 'tactical':
        return DecisionComplexity.SIMPLE
    
    return DecisionComplexity.MODERATE
```

---

## 10. HTTP REST Data Transfer Objects

### 10.1 Overview

Data structures for HTTP REST API communication between processes.

### 10.2 Request DTOs

```cpp
// C++ Request structures

struct HandshakeRequest {
    std::string client;
    std::string client_version;
    int32_t pid;
    std::vector<std::string> capabilities;
    std::string authentication_token;
    
    json toJson() const;
    static HandshakeRequest fromJson(const json& j);
};

struct StateUpdateRequest {
    std::string session_id;
    Timestamp timestamp;
    uint64_t tick_number;
    CharacterState player;
    std::vector<Monster> monsters;
    std::vector<InventoryItem> items;
    std::vector<PartyMember> party;
    std::vector<SkillInfo> skills;
    
    json toJson() const;
};

struct MacroExecuteRequest {
    std::string session_id;
    std::string macro_name;
    json parameters;
    
    json toJson() const;
};
```

### 10.3 Response DTOs

```cpp
// C++ Response structures

struct ActionResponse {
    std::string status;  // "success", "processing", "error"
    std::string decision_tier;  // "reflex", "rule", "ml", "llm"
    float processing_time_ms;
    Action action;
    std::optional<std::string> reason;
    std::optional<float> confidence;
    
    json toJson() const;
    static ActionResponse fromJson(const json& j);
};

struct HealthCheckResponse {
    std::string status;  // "healthy", "unhealthy"
    uint64_t uptime_seconds;
    uint32_t active_sessions;
    std::map<std::string, std::string> decision_engines;
    std::optional<PythonServiceStatus> python_service;
    PerformanceMetrics performance;
    
    json toJson() const;
};
```

### 10.4 Python DTOs

```python
# Python Pydantic models for FastAPI

from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class MemoryStoreRequest(BaseModel):
    session_id: str
    event: dict
    importance: float = Field(default=0.5, ge=0.0, le=1.0)

class MemoryStoreResponse(BaseModel):
    status: str
    memory_id: str
    embedding_generated: bool
    stored_at: int

class MemoryRetrieveRequest(BaseModel):
    session_id: str
    current_state: dict
    top_k: int = Field(default=5, ge=1, le=20)

class MemoryRetrieveResponse(BaseModel):
    status: str
    memories: List[dict]
    query_time_ms: float

class CrewTaskRequest(BaseModel):
    session_id: str
    task_type: str  # 'strategic', 'combat', 'resource', 'analysis'
    context: dict
    timeout_seconds: int = Field(default=120, ge=10, le=600)

class CrewTaskResponse(BaseModel):
    status: str
    task_id: str
    result: dict
    processing_time_ms: float
    agents_involved: List[str]
```

### 10.5 JSON Serialization Helpers

```cpp
// C++ JSON serialization utilities

namespace Serialization {
    // Convert game state to JSON for HTTP
    json gameStateToJson(const GameState& state) {
        return json{
            {"player", state.player.toJson()},
            {"monsters", monstersToJsonArray(state.monsters)},
            {"items", itemsToJsonArray(state.items)},
            {"timestamp", state.timestamp}
        };
    }
    
    // Parse JSON response from HTTP
    ActionResponse parseActionResponse(const std::string& json_str) {
        auto j = json::parse(json_str);
        return ActionResponse::fromJson(j);
    }
    
    // Validate JSON schema
    bool validateSchema(const json& data, const std::string& schema_name) {
        // JSON schema validation
        return true;  // Implement using nlohmann::json-schema-validator
    }
}
```

### 7.7 Social Interaction Tables

**See:** [`09-social-interaction-system.md`](09-social-interaction-system.md) for complete specification

#### Player Reputation Table

```sql
CREATE TABLE player_reputation (
    player_id INTEGER PRIMARY KEY,
    player_name TEXT NOT NULL UNIQUE,
    reputation_score INTEGER NOT NULL DEFAULT 0 CHECK(reputation_score >= -100 AND reputation_score <= 100),
    reputation_tier TEXT NOT NULL DEFAULT 'neutral',
    
    total_interactions INTEGER DEFAULT 0,
    positive_interactions INTEGER DEFAULT 0,
    negative_interactions INTEGER DEFAULT 0,
    
    first_seen INTEGER NOT NULL,
    last_seen INTEGER NOT NULL,
    last_interaction INTEGER,
    
    is_friend BOOLEAN DEFAULT 0,
    is_guild_member BOOLEAN DEFAULT 0,
    is_whitelisted BOOLEAN DEFAULT 0,
    is_blacklisted BOOLEAN DEFAULT 0,
    attempted_scam BOOLEAN DEFAULT 0,
    
    preferred_language TEXT,
    detected_personality TEXT,
    notes TEXT,
    
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX idx_reputation_score ON player_reputation(reputation_score DESC);
CREATE INDEX idx_reputation_tier ON player_reputation(reputation_tier);
CREATE INDEX idx_reputation_blacklisted ON player_reputation(is_blacklisted);
```

#### Interaction History Table

```sql
CREATE TABLE interaction_history (
    interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    interaction_type TEXT NOT NULL,
    interaction_subtype TEXT,
    channel TEXT,
    request_content TEXT,
    our_response TEXT,
    outcome TEXT NOT NULL,
    reputation_delta INTEGER DEFAULT 0,
    metadata TEXT,
    
    FOREIGN KEY (session_id) REFERENCES player_sessions(session_id),
    FOREIGN KEY (player_id) REFERENCES player_reputation(player_id)
);

CREATE INDEX idx_interaction_player ON interaction_history(player_id);
CREATE INDEX idx_interaction_type ON interaction_history(interaction_type);
CREATE INDEX idx_interaction_timestamp ON interaction_history(timestamp DESC);
```

#### Chat History Table

```sql
CREATE TABLE chat_history (
    chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    channel TEXT NOT NULL,
    sender_id INTEGER,
    sender_name TEXT NOT NULL,
    message_content TEXT NOT NULL,
    is_outgoing BOOLEAN DEFAULT 0,
    generated_by TEXT,
    requires_response BOOLEAN DEFAULT 0,
    metadata TEXT,
    
    FOREIGN KEY (session_id) REFERENCES player_sessions(session_id),
    FOREIGN KEY (sender_id) REFERENCES player_reputation(player_id)
);

CREATE INDEX idx_chat_conversation ON chat_history(conversation_id);
CREATE INDEX idx_chat_timestamp ON chat_history(timestamp DESC);
```

### 7.8 Social Interaction C++ Structures

```cpp
// Player Reputation
struct PlayerReputation {
    uint32_t player_id;
    std::string player_name;
    int32_t reputation_score;  // -100 to 100
    std::string reputation_tier;
    
    struct Stats {
        uint32_t total_interactions;
        uint32_t positive_interactions;
        uint32_t negative_interactions;
    } stats;
    
    struct Flags {
        bool is_friend;
        bool is_guild_member;
        bool is_whitelisted;
        bool is_blacklisted;
        bool attempted_scam;
    } flags;
    
    json toJson() const;
    static PlayerReputation fromDb(sqlite3_stmt* stmt);
};

// Chat Context
struct ChatContext {
    std::string conversation_id;
    std::string sender_name;
    uint32_t sender_id;
    std::string channel;  // "whisper", "party", "guild"
    std::vector<ChatMessage> history;
    float sender_reputation;
    
    json toJson() const;
};

// Interaction Decision
struct InteractionDecision {
    bool accept;
    std::optional<std::string> response_message;
    std::optional<Action> response_action;
    std::string reasoning;
    
    json toJson() const;
};
```

### 7.9 Concurrency Structures

**See:** [`10-concurrency-and-race-conditions.md`](10-concurrency-and-race-conditions.md) for complete specification

```cpp
// Thread-safe game state wrapper
class ThreadSafeGameState {
private:
    GameState state_;
    mutable std::shared_mutex state_mutex_;
    std::atomic<uint64_t> version_{0};
    
public:
    GameState readState() const;
    void updateState(const GameState& new_state);
    uint64_t getVersion() const;
};

// Lock info for deadlock detection
struct LockInfo {
    std::thread::id thread_id;
    std::string lock_name;
    uint32_t lock_order;
    Timestamp acquired_at;
    std::string stack_trace;
};

// Versioned value for optimistic locking
template<typename T>
class VersionedValue {
private:
    T value_;
    std::atomic<uint64_t> version_{0};
    mutable std::shared_mutex mutex_;
    
public:
    struct ReadResult {
        T value;
        uint64_t version;
    };
    
    ReadResult read() const;
    void write(const T& new_value);
    bool writeIfVersion(const T& new_value, uint64_t expected_version);
};

// Transaction state
struct TransactionState {
    std::string transaction_id;
    Timestamp started_at;
    std::vector<std::string> operations;
    bool committed;
    std::optional<std::string> rollback_reason;
};
```

---

**Next Document**: [Macro System Specification](03-macro-system-specification.md)
