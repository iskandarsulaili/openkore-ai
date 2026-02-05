#pragma once
#include "../types.hpp"
#include <chrono>

namespace openkore_ai {
namespace decision {

class ReflexTier {
public:
    ReflexTier();
    
    // Check if reflex tier should handle this situation
    bool should_handle(const GameState& state) const;
    
    // Make reflex decision (<1ms)
    Action decide(const GameState& state);
    
private:
    // Emergency checks
    bool is_hp_critical(const GameState& state) const;
    bool is_sp_low(const GameState& state) const;
    bool is_being_attacked(const GameState& state) const;
    bool has_dangerous_status(const GameState& state) const;
    bool is_overweight(const GameState& state) const;
    
    // Thresholds
    static constexpr float HP_CRITICAL_THRESHOLD = 0.25f;  // 25%
    static constexpr float HP_LOW_THRESHOLD = 0.40f;       // 40%
    static constexpr float SP_LOW_THRESHOLD = 0.20f;       // 20%
    static constexpr float WEIGHT_CRITICAL_THRESHOLD = 0.90f;  // 90%
};

} // namespace decision
} // namespace openkore_ai
