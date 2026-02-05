#pragma once
#include <string>
#include <vector>
#include <map>
#include <optional>
#include <chrono>

namespace openkore_ai {

// Character state
struct CharacterState {
    std::string name;
    int level;
    int base_exp;
    int job_exp;
    int hp;
    int max_hp;
    int sp;
    int max_sp;
    struct Position {
        std::string map;
        int x;
        int y;
    } position;
    int weight;
    int max_weight;
    int zeny;
    std::string job_class;
    std::vector<std::string> status_effects;
};

// Monster data
struct Monster {
    std::string id;
    std::string name;
    int hp;
    int max_hp;
    int distance;
    bool is_aggressive;
};

// Item data
struct Item {
    std::string id;
    std::string name;
    int amount;
    std::string type;
};

// Player data
struct Player {
    std::string name;
    int level;
    std::string guild;
    int distance;
    bool is_party_member;
};

// Game state (comprehensive)
struct GameState {
    CharacterState character;
    std::vector<Monster> monsters;
    std::vector<Item> inventory;
    std::vector<Player> nearby_players;
    std::map<std::string, std::string> party_members;
    long long timestamp_ms;
};

// Action to execute
struct Action {
    std::string type;  // "attack", "skill", "move", "item", "talk", "sit", "stand", "none"
    std::map<std::string, std::string> parameters;
    std::string reason;
    float confidence;
};

// Decision tier enum
enum class DecisionTier {
    REFLEX,   // <1ms - immediate reactions
    RULES,    // <10ms - rule-based logic
    ML,       // <100ms - machine learning
    LLM       // 30-300s - language model reasoning
};

// Decision request
struct DecisionRequest {
    GameState game_state;
    std::string request_id;
    long long timestamp_ms;
};

// Decision response
struct DecisionResponse {
    Action action;
    DecisionTier tier_used;
    long long latency_ms;
    std::string request_id;
};

// Health check response
struct HealthResponse {
    std::string status;  // "healthy", "degraded", "unhealthy"
    std::map<std::string, bool> components;
    long long uptime_seconds;
};

} // namespace openkore_ai
