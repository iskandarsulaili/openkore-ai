# Data Structures Reference

**Version:** 1.0  
**Date:** 2026-02-05  
**Status:** Final Specification

---

## Table of Contents

1. [Overview](#1-overview)
2. [Game State Structures](#2-game-state-structures)
3. [Decision Structures](#3-decision-structures)
4. [ML Structures](#4-ml-structures)
5. [Configuration Structures](#5-configuration-structures)
6. [Utility Structures](#6-utility-structures)

---

## 1. Overview

### 1.1 Design Principles

- **C++20 Compatible**: Use modern C++ features (std::optional, designated initializers, etc.)
- **Serialization-Friendly**: All structures can be converted to/from JSON
- **Memory-Efficient**: Minimize padding, use appropriate data types
- **Cache-Friendly**: Hot data grouped together
- **Type-Safe**: Strong typing with enums and type aliases

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

**Next Document**: [Macro System Specification](03-macro-system-specification.md)
