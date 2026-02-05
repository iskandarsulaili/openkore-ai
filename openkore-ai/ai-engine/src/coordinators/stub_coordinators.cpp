#include "../../include/coordinators/stub_coordinators.hpp"
#include <iostream>

namespace openkore_ai {
namespace coordinators {

// Companions Coordinator
CompanionsCoordinator::CompanionsCoordinator() 
    : CoordinatorBase("CompanionsCoordinator", Priority::LOW) {
    std::cout << "[CompanionsCoordinator] Initialized (stub)" << std::endl;
}

bool CompanionsCoordinator::should_activate(const GameState& state) const {
    return false;
}

Action CompanionsCoordinator::decide(const GameState& state) {
    return create_action("none", "Companions coordinator stub", 0.1f);
}

// Instances Coordinator
InstancesCoordinator::InstancesCoordinator() 
    : CoordinatorBase("InstancesCoordinator", Priority::MEDIUM) {
    std::cout << "[InstancesCoordinator] Initialized (stub)" << std::endl;
}

bool InstancesCoordinator::should_activate(const GameState& state) const {
    return false;
}

Action InstancesCoordinator::decide(const GameState& state) {
    return create_action("none", "Instances coordinator stub", 0.1f);
}

// Crafting Coordinator
CraftingCoordinator::CraftingCoordinator() 
    : CoordinatorBase("CraftingCoordinator", Priority::LOW) {
    std::cout << "[CraftingCoordinator] Initialized (stub)" << std::endl;
}

bool CraftingCoordinator::should_activate(const GameState& state) const {
    return false;
}

Action CraftingCoordinator::decide(const GameState& state) {
    return create_action("none", "Crafting coordinator stub", 0.1f);
}

// Environment Coordinator
EnvironmentCoordinator::EnvironmentCoordinator() 
    : CoordinatorBase("EnvironmentCoordinator", Priority::LOW) {
    std::cout << "[EnvironmentCoordinator] Initialized (stub)" << std::endl;
}

bool EnvironmentCoordinator::should_activate(const GameState& state) const {
    return false;
}

Action EnvironmentCoordinator::decide(const GameState& state) {
    return create_action("none", "Environment coordinator stub", 0.1f);
}

// Job-Specific Coordinator
JobSpecificCoordinator::JobSpecificCoordinator() 
    : CoordinatorBase("JobSpecificCoordinator", Priority::MEDIUM) {
    std::cout << "[JobSpecificCoordinator] Initialized (stub)" << std::endl;
}

bool JobSpecificCoordinator::should_activate(const GameState& state) const {
    return false;
}

Action JobSpecificCoordinator::decide(const GameState& state) {
    return create_action("none", "Job-specific coordinator stub", 0.1f);
}

// PvP/WoE Coordinator
PvPWoECoordinator::PvPWoECoordinator() 
    : CoordinatorBase("PvPWoECoordinator", Priority::HIGH) {
    std::cout << "[PvPWoECoordinator] Initialized (stub)" << std::endl;
}

bool PvPWoECoordinator::should_activate(const GameState& state) const {
    return false;
}

Action PvPWoECoordinator::decide(const GameState& state) {
    return create_action("none", "PvP/WoE coordinator stub", 0.1f);
}

} // namespace coordinators
} // namespace openkore_ai
