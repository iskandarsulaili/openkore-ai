#include "../../include/coordinators/combat_coordinator.hpp"
#include <algorithm>
#include <iostream>

namespace openkore_ai {
namespace coordinators {

CombatCoordinator::CombatCoordinator() 
    : CoordinatorBase("CombatCoordinator", Priority::HIGH) {
    std::cout << "[CombatCoordinator] Initialized" << std::endl;
}

bool CombatCoordinator::should_activate(const GameState& state) const {
    // Activate when monsters are present and character is healthy
    if (state.monsters.empty()) return false;
    
    float hp_ratio = static_cast<float>(state.character.hp) / state.character.max_hp;
    return hp_ratio > 0.5f;  // Only fight if HP > 50%
}

Action CombatCoordinator::decide(const GameState& state) {
    Monster target = select_target(state);
    
    if (target.id.empty()) {
        return create_action("none", "No valid combat target", 0.5f);
    }
    
    // Check if AOE is better
    if (should_use_aoe(state)) {
        Action action = create_action("skill", "Multiple targets, using AOE", 0.85f);
        action.parameters["skill"] = "Magnum Break";  // Example AOE
        action.parameters["target_area"] = "self";
        return action;
    }
    
    // Single target combat
    std::string skill = select_skill(state, target);
    
    if (!skill.empty()) {
        Action action = create_action("skill", "Using optimal skill on " + target.name, 0.9f);
        action.parameters["skill"] = skill;
        action.parameters["target"] = target.id;
        return action;
    }
    
    // Fallback to basic attack
    Action action = create_action("attack", "Basic attack on " + target.name, 0.75f);
    action.parameters["target"] = target.id;
    return action;
}

Monster CombatCoordinator::select_target(const GameState& state) const {
    // Priority: Aggressive > Closest > Weakest
    Monster best_target;
    best_target.id = "";
    
    int min_distance = 999;
    
    for (const auto& monster : state.monsters) {
        if (monster.distance > 15) continue;  // Out of range
        
        // Prioritize aggressive monsters
        if (monster.is_aggressive) {
            if (monster.distance < min_distance) {
                best_target = monster;
                min_distance = monster.distance;
            }
        } else if (best_target.id.empty() && monster.distance < min_distance) {
            best_target = monster;
            min_distance = monster.distance;
        }
    }
    
    return best_target;
}

std::string CombatCoordinator::select_skill(const GameState& state, const Monster& target) const {
    float sp_ratio = static_cast<float>(state.character.sp) / state.character.max_sp;
    
    // Only use skills if we have enough SP
    if (sp_ratio < 0.3f) return "";
    
    // Job-specific skills (simplified)
    if (state.character.job_class == "Knight" || state.character.job_class == "Swordsman") {
        return "Bash";
    } else if (state.character.job_class == "Wizard" || state.character.job_class == "Magician") {
        return "Fire Bolt";
    } else if (state.character.job_class == "Hunter" || state.character.job_class == "Archer") {
        return "Double Strafe";
    }
    
    return "";  // No skill available
}

bool CombatCoordinator::should_use_aoe(const GameState& state) const {
    // Use AOE if 3+ monsters within 5 cells
    int nearby_count = 0;
    for (const auto& monster : state.monsters) {
        if (monster.distance <= 5) {
            nearby_count++;
        }
    }
    return nearby_count >= 3;
}

} // namespace coordinators
} // namespace openkore_ai
