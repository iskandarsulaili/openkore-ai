#include "../../include/decision/reflex.hpp"
#include <algorithm>
#include <iostream>

namespace openkore_ai {
namespace decision {

ReflexTier::ReflexTier() {
    std::cout << "[ReflexTier] Initialized" << std::endl;
}

bool ReflexTier::should_handle(const GameState& state) const {
    // Only handle true emergencies
    if (is_hp_critical(state)) return true;
    if (has_dangerous_status(state)) return true;
    if (is_overweight(state)) return true;
    
    // Being attacked with low HP (not critical but concerning)
    if (is_being_attacked(state)) {
        float hp_ratio = static_cast<float>(state.character.hp) / state.character.max_hp;
        if (hp_ratio < HP_LOW_THRESHOLD) {
            return true;
        }
    }
    
    // SP low for magic classes
    if (is_sp_low(state)) {
        return true;
    }
    
    return false;
}

Action ReflexTier::decide(const GameState& state) {
    Action action;
    action.confidence = 0.95f;
    
    // Priority 1: Critical HP - use healing item immediately
    if (is_hp_critical(state)) {
        action.type = "item";
        action.parameters["item"] = "White Potion";
        action.reason = "Reflex: HP critical (<25%), emergency healing";
        return action;
    }
    
    // Priority 2: Dangerous status effects (stunned, frozen, stone curse)
    if (has_dangerous_status(state)) {
        action.type = "item";
        action.parameters["item"] = "Green Potion";  // Status recovery
        action.reason = "Reflex: Dangerous status effect detected";
        return action;
    }
    
    // Priority 3: Being attacked with low HP
    if (is_hp_critical(state) || (state.character.hp < state.character.max_hp * HP_LOW_THRESHOLD && is_being_attacked(state))) {
        action.type = "item";
        action.parameters["item"] = "Red Potion";
        action.reason = "Reflex: Low HP while under attack";
        return action;
    }
    
    // Priority 4: Overweight (can't move efficiently)
    if (is_overweight(state)) {
        action.type = "command";
        action.parameters["command"] = "storage";
        action.reason = "Reflex: Overweight, need to store items";
        return action;
    }
    
    // Priority 5: Low SP (for magic users)
    if (is_sp_low(state)) {
        action.type = "item";
        action.parameters["item"] = "Blue Potion";
        action.reason = "Reflex: SP critically low";
        return action;
    }
    
    // No reflex action needed
    action.type = "none";
    action.reason = "Reflex: No emergency detected";
    action.confidence = 0.5f;
    return action;
}

bool ReflexTier::is_hp_critical(const GameState& state) const {
    if (state.character.max_hp == 0) return false;
    float hp_ratio = static_cast<float>(state.character.hp) / state.character.max_hp;
    return hp_ratio < HP_CRITICAL_THRESHOLD;
}

bool ReflexTier::is_sp_low(const GameState& state) const {
    if (state.character.max_sp == 0) return false;
    float sp_ratio = static_cast<float>(state.character.sp) / state.character.max_sp;
    return sp_ratio < SP_LOW_THRESHOLD;
}

bool ReflexTier::is_being_attacked(const GameState& state) const {
    // Check if any nearby monsters are aggressive
    for (const auto& monster : state.monsters) {
        if (monster.is_aggressive && monster.distance <= 5) {
            return true;
        }
    }
    return false;
}

bool ReflexTier::has_dangerous_status(const GameState& state) const {
    // Dangerous status effects that need immediate action
    const std::vector<std::string> dangerous_statuses = {
        "Stunned", "Frozen", "Stone Curse", "Sleep", "Blind", "Silence"
    };
    
    for (const auto& status : state.character.status_effects) {
        for (const auto& dangerous : dangerous_statuses) {
            if (status == dangerous) {
                return true;
            }
        }
    }
    return false;
}

bool ReflexTier::is_overweight(const GameState& state) const {
    if (state.character.max_weight == 0) return false;
    float weight_ratio = static_cast<float>(state.character.weight) / state.character.max_weight;
    return weight_ratio >= WEIGHT_CRITICAL_THRESHOLD;
}

} // namespace decision
} // namespace openkore_ai
