#pragma once
#include "../types.hpp"

namespace openkore_ai {
namespace decision {

class RulesTier {
public:
    RulesTier();
    
    // Check if rules tier should handle this situation
    bool should_handle(const GameState& state) const;
    
    // Make rule-based decision (<10ms)
    Action decide(const GameState& state);
    
private:
    // Combat rules
    Action decide_combat(const GameState& state);
    Action decide_targeting(const GameState& state);
    Action decide_positioning(const GameState& state);
    Action decide_healing(const GameState& state);
    
    // Helper functions
    Monster find_best_target(const GameState& state) const;
    bool should_attack(const GameState& state) const;
    bool should_heal(const GameState& state) const;
    bool is_in_safe_position(const GameState& state) const;
    
    // Thresholds
    static constexpr float HP_HEAL_THRESHOLD = 0.60f;       // 60%
    static constexpr float SP_SKILL_THRESHOLD = 0.30f;      // 30%
    static constexpr int MAX_ATTACK_DISTANCE = 15;
    static constexpr int SAFE_DISTANCE = 8;
};

} // namespace decision
} // namespace openkore_ai
