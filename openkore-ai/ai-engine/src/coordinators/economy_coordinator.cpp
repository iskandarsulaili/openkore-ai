#include "../../include/coordinators/economy_coordinator.hpp"
#include <iostream>

namespace openkore_ai {
namespace coordinators {

EconomyCoordinator::EconomyCoordinator() 
    : CoordinatorBase("EconomyCoordinator", Priority::MEDIUM) {
    std::cout << "[EconomyCoordinator] Initialized" << std::endl;
}

bool EconomyCoordinator::should_activate(const GameState& state) const {
    // Activate when overweight or inventory is full
    return is_overweight(state) || should_sell_items(state);
}

Action EconomyCoordinator::decide(const GameState& state) {
    // Check if overweight
    if (is_overweight(state)) {
        return create_action("move", "Overweight, returning to storage", 0.85f);
    }
    
    // Check if should sell items
    if (should_sell_items(state)) {
        return create_action("move", "Inventory full, going to sell items", 0.80f);
    }
    
    return create_action("none", "Economy check passed", 0.5f);
}

bool EconomyCoordinator::is_overweight(const GameState& state) const {
    float weight_ratio = static_cast<float>(state.character.weight) / state.character.max_weight;
    return weight_ratio > 0.85f;  // 85% weight threshold
}

bool EconomyCoordinator::should_sell_items(const GameState& state) const {
    // Check if inventory has many items (simplified)
    return state.inventory.size() > 50;
}

} // namespace coordinators
} // namespace openkore_ai
