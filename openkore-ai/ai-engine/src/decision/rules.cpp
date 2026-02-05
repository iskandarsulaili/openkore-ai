#include "../../include/decision/rules.hpp"
#include <algorithm>
#include <limits>
#include <iostream>

namespace openkore_ai {
namespace decision {

RulesTier::RulesTier() {
    std::cout << "[RulesTier] Initialized" << std::endl;
}

bool RulesTier::should_handle(const GameState& state) const {
    // Rules tier handles non-emergency tactical situations
    return !state.monsters.empty() || should_heal(state);
}

Action RulesTier::decide(const GameState& state) {
    // Decision priority:
    // 1. Healing (non-emergency)
    // 2. Combat
    // 3. Positioning
    
    if (should_heal(state)) {
        return decide_healing(state);
    }
    
    if (should_attack(state)) {
        return decide_combat(state);
    }
    
    if (!is_in_safe_position(state)) {
        return decide_positioning(state);
    }
    
    // No tactical action needed
    Action action;
    action.type = "none";
    action.reason = "Rules: No tactical action required";
    action.confidence = 0.6f;
    return action;
}

Action RulesTier::decide_combat(const GameState& state) {
    Monster target = find_best_target(state);
    
    Action action;
    action.confidence = 0.8f;
    
    if (target.id.empty()) {
        action.type = "none";
        action.reason = "Rules: No valid target found";
        return action;
    }
    
    // Check if we have enough SP for skills
    float sp_ratio = static_cast<float>(state.character.sp) / state.character.max_sp;
    
    if (sp_ratio > SP_SKILL_THRESHOLD && target.distance <= 10) {
        // Use skill attack
        action.type = "skill";
        action.parameters["skill"] = "Bash";  // Example skill
        action.parameters["target"] = target.id;
        action.reason = "Rules: Using skill attack on " + target.name;
    } else {
        // Use basic attack
        action.type = "attack";
        action.parameters["target"] = target.id;
        action.reason = "Rules: Basic attack on " + target.name;
    }
    
    return action;
}

Action RulesTier::decide_targeting(const GameState& state) {
    // This is called by decide_combat
    Action action;
    action.type = "none";
    action.reason = "Rules: Targeting logic (handled by combat)";
    action.confidence = 0.7f;
    return action;
}

Action RulesTier::decide_positioning(const GameState& state) {
    Action action;
    action.confidence = 0.7f;
    
    // If too many aggressive monsters nearby, retreat
    int aggressive_count = 0;
    for (const auto& monster : state.monsters) {
        if (monster.is_aggressive && monster.distance <= SAFE_DISTANCE) {
            aggressive_count++;
        }
    }
    
    if (aggressive_count >= 3) {
        action.type = "move";
        action.parameters["direction"] = "away";
        action.reason = "Rules: Too many aggressive monsters, retreating";
        return action;
    }
    
    action.type = "none";
    action.reason = "Rules: Position is safe";
    return action;
}

Action RulesTier::decide_healing(const GameState& state) {
    Action action;
    action.confidence = 0.75f;
    
    float hp_ratio = static_cast<float>(state.character.hp) / state.character.max_hp;
    
    if (hp_ratio < HP_HEAL_THRESHOLD) {
        action.type = "item";
        action.parameters["item"] = "Red Potion";
        action.reason = "Rules: HP below 60%, healing";
        return action;
    }
    
    action.type = "none";
    action.reason = "Rules: HP sufficient";
    return action;
}

Monster RulesTier::find_best_target(const GameState& state) const {
    Monster best_target;
    best_target.id = "";
    
    if (state.monsters.empty()) {
        return best_target;
    }
    
    // Targeting priority:
    // 1. Aggressive monsters attacking us
    // 2. Closest monsters within attack range
    // 3. Weakest monsters (lowest HP)
    
    int min_distance = std::numeric_limits<int>::max();
    
    for (const auto& monster : state.monsters) {
        // Skip monsters too far away
        if (monster.distance > MAX_ATTACK_DISTANCE) {
            continue;
        }
        
        // Prioritize aggressive monsters
        if (monster.is_aggressive && monster.distance < min_distance) {
            best_target = monster;
            min_distance = monster.distance;
        } else if (!monster.is_aggressive && best_target.id.empty() && monster.distance < min_distance) {
            best_target = monster;
            min_distance = monster.distance;
        }
    }
    
    return best_target;
}

bool RulesTier::should_attack(const GameState& state) const {
    // Attack if there are monsters within range and we're healthy enough
    if (state.monsters.empty()) {
        return false;
    }
    
    float hp_ratio = static_cast<float>(state.character.hp) / state.character.max_hp;
    if (hp_ratio < 0.4f) {
        return false;  // Too low HP to attack
    }
    
    // Check if any monster is in attack range
    for (const auto& monster : state.monsters) {
        if (monster.distance <= MAX_ATTACK_DISTANCE) {
            return true;
        }
    }
    
    return false;
}

bool RulesTier::should_heal(const GameState& state) const {
    float hp_ratio = static_cast<float>(state.character.hp) / state.character.max_hp;
    return hp_ratio < HP_HEAL_THRESHOLD && hp_ratio > 0.25f;  // Not critical, but needs healing
}

bool RulesTier::is_in_safe_position(const GameState& state) const {
    // Position is safe if not surrounded by aggressive monsters
    int aggressive_count = 0;
    for (const auto& monster : state.monsters) {
        if (monster.is_aggressive && monster.distance <= SAFE_DISTANCE) {
            aggressive_count++;
        }
    }
    return aggressive_count < 3;
}

} // namespace decision
} // namespace openkore_ai
