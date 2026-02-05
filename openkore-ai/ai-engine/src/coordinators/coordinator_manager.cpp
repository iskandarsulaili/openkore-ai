#include "../../include/coordinators/coordinator_manager.hpp"
#include "../../include/coordinators/combat_coordinator.hpp"
#include "../../include/coordinators/economy_coordinator.hpp"
#include "../../include/coordinators/navigation_coordinator.hpp"
#include "../../include/coordinators/social_coordinator.hpp"
#include "../../include/coordinators/consumables_coordinator.hpp"
#include "../../include/coordinators/progression_coordinator.hpp"
#include "../../include/coordinators/npc_coordinator.hpp"
#include "../../include/coordinators/planning_coordinator.hpp"
#include "../../include/coordinators/stub_coordinators.hpp"
#include <iostream>
#include <algorithm>

namespace openkore_ai {
namespace coordinators {

CoordinatorManager::CoordinatorManager() {
    std::cout << "[CoordinatorManager] Initializing..." << std::endl;
}

void CoordinatorManager::initialize() {
    // Initialize all 14 coordinators
    // Fully implemented coordinators
    coordinators_.push_back(std::make_unique<CombatCoordinator>());
    coordinators_.push_back(std::make_unique<EconomyCoordinator>());
    
    // Basic stub coordinators
    coordinators_.push_back(std::make_unique<NavigationCoordinator>());
    coordinators_.push_back(std::make_unique<NPCCoordinator>());
    coordinators_.push_back(std::make_unique<PlanningCoordinator>());
    coordinators_.push_back(std::make_unique<SocialCoordinator>());
    coordinators_.push_back(std::make_unique<ConsumablesCoordinator>());
    coordinators_.push_back(std::make_unique<ProgressionCoordinator>());
    
    // Stub coordinators from stub_coordinators.hpp
    coordinators_.push_back(std::make_unique<CompanionsCoordinator>());
    coordinators_.push_back(std::make_unique<InstancesCoordinator>());
    coordinators_.push_back(std::make_unique<CraftingCoordinator>());
    coordinators_.push_back(std::make_unique<EnvironmentCoordinator>());
    coordinators_.push_back(std::make_unique<JobSpecificCoordinator>());
    coordinators_.push_back(std::make_unique<PvPWoECoordinator>());
    
    std::cout << "[CoordinatorManager] Initialized " << coordinators_.size() << " coordinators" << std::endl;
}

Action CoordinatorManager::get_coordinator_decision(const GameState& state) {
    std::vector<std::pair<CoordinatorBase*, Action>> recommendations;
    
    // Collect recommendations from active coordinators
    for (auto& coordinator : coordinators_) {
        if (coordinator->should_activate(state)) {
            Action action = coordinator->decide(state);
            if (action.type != "none") {
                recommendations.push_back({coordinator.get(), action});
                std::cout << "[CoordinatorManager] " << coordinator->get_name() 
                         << " recommends: " << action.type << std::endl;
            }
        }
    }
    
    if (recommendations.empty()) {
        Action no_action;
        no_action.type = "none";
        no_action.reason = "CoordinatorManager: No coordinator recommendations";
        no_action.confidence = 0.5f;
        return no_action;
    }
    
    // Select best action
    return select_best_action(recommendations);
}

Action CoordinatorManager::select_best_action(
    const std::vector<std::pair<CoordinatorBase*, Action>>& recommendations) const {
    
    // Priority-based selection: Lower priority value = higher priority
    auto best = std::min_element(recommendations.begin(), recommendations.end(),
        [](const auto& a, const auto& b) {
            // First by priority (lower is better)
            if (a.first->get_priority() != b.first->get_priority()) {
                return a.first->get_priority() < b.first->get_priority();
            }
            // Then by confidence (higher is better)
            return a.second.confidence > b.second.confidence;
        });
    
    if (best != recommendations.end()) {
        std::cout << "[CoordinatorManager] Selected action from " << best->first->get_name() 
                 << " (priority: " << static_cast<int>(best->first->get_priority()) 
                 << ", confidence: " << best->second.confidence << ")" << std::endl;
        return best->second;
    }
    
    Action no_action;
    no_action.type = "none";
    no_action.reason = "CoordinatorManager: Selection failed";
    no_action.confidence = 0.3f;
    return no_action;
}

CoordinatorBase* CoordinatorManager::get_coordinator(const std::string& name) const {
    for (const auto& coordinator : coordinators_) {
        if (coordinator->get_name() == name) {
            return coordinator.get();
        }
    }
    return nullptr;
}

} // namespace coordinators
} // namespace openkore_ai
