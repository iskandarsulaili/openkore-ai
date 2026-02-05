#include "../../include/coordinators/stub_coordinators.hpp"
#include <iostream>

namespace openkore_ai {
namespace coordinators {

// Companions Coordinator
CompanionsCoordinator::CompanionsCoordinator()
    : CoordinatorBase("CompanionsCoordinator", Priority::LOW) {
    std::cout << "[CompanionsCoordinator] Fully initialized" << std::endl;
}

bool CompanionsCoordinator::should_activate(const GameState& state) const {
    // Simplified - can't detect companions without additional GameState fields
    return false;
}

Action CompanionsCoordinator::decide(const GameState& state) {
    return create_action("none", "Companions OK", 0.1f);
}

// Instances Coordinator
InstancesCoordinator::InstancesCoordinator()
    : CoordinatorBase("InstancesCoordinator", Priority::MEDIUM) {
    std::cout << "[InstancesCoordinator] Fully initialized" << std::endl;
}

bool InstancesCoordinator::should_activate(const GameState& state) const {
    return false;
}

Action InstancesCoordinator::decide(const GameState& state) {
    return create_action("none", "No instances active", 0.1f);
}

// Crafting Coordinator
CraftingCoordinator::CraftingCoordinator()
    : CoordinatorBase("CraftingCoordinator", Priority::LOW) {
    std::cout << "[CraftingCoordinator] Fully initialized" << std::endl;
}

bool CraftingCoordinator::should_activate(const GameState& state) const {
    return false;
}

Action CraftingCoordinator::decide(const GameState& state) {
    return create_action("none", "No crafting opportunities", 0.1f);
}

// Environment Coordinator
EnvironmentCoordinator::EnvironmentCoordinator()
    : CoordinatorBase("EnvironmentCoordinator", Priority::LOW) {
    std::cout << "[EnvironmentCoordinator] Fully initialized" << std::endl;
}

bool EnvironmentCoordinator::should_activate(const GameState& state) const {
    return false;
}

Action EnvironmentCoordinator::decide(const GameState& state) {
    return create_action("none", "Normal conditions", 0.1f);
}

// Job-Specific Coordinator
JobSpecificCoordinator::JobSpecificCoordinator()
    : CoordinatorBase("JobSpecificCoordinator", Priority::MEDIUM) {
    std::cout << "[JobSpecificCoordinator] Fully initialized" << std::endl;
}

bool JobSpecificCoordinator::should_activate(const GameState& state) const {
    // Activate for support classes when players nearby
    std::string job = state.character.job_class;
    if (job == "Priest" || job == "Sage") {
        return !state.nearby_players.empty();
    }
    
    // Activate for combat classes when monsters present
    return !state.monsters.empty();
}

Action JobSpecificCoordinator::decide(const GameState& state) {
    std::string job = state.character.job_class;
    
    // Priest healing
    if (job == "Priest" || job == "Acolyte") {
        for (const auto& player : state.nearby_players) {
            if (player.distance <= 9) {
                Action action = create_action("skill", "Heal party member", 0.90f);
                action.parameters["skill"] = "Heal";
                action.parameters["target"] = player.name;
                return action;
            }
        }
    }
    
    // Wizard AOE
    if (job == "Wizard" || job == "Magician") {
        if (state.monsters.size() >= 3) {
            Action action = create_action("skill", "AOE on monsters", 0.85f);
            action.parameters["skill"] = "Storm Gust";
            return action;
        }
    }
    
    return create_action("none", "No class-specific action", 0.1f);
}

// PvP/WoE Coordinator
PvPWoECoordinator::PvPWoECoordinator()
    : CoordinatorBase("PvPWoECoordinator", Priority::HIGH) {
    std::cout << "[PvPWoECoordinator] Fully initialized" << std::endl;
}

bool PvPWoECoordinator::should_activate(const GameState& state) const {
    // Would need pvp_zone flag in GameState
    return false;
}

Action PvPWoECoordinator::decide(const GameState& state) {
    return create_action("none", "Not in PvP zone", 0.1f);
}

} // namespace coordinators
} // namespace openkore_ai
