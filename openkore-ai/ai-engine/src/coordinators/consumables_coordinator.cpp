#include "../../include/coordinators/consumables_coordinator.hpp"
#include <iostream>

namespace openkore_ai {
namespace coordinators {

ConsumablesCoordinator::ConsumablesCoordinator() 
    : CoordinatorBase("ConsumablesCoordinator", Priority::MEDIUM) {
    std::cout << "[ConsumablesCoordinator] Initialized (stub)" << std::endl;
}

bool ConsumablesCoordinator::should_activate(const GameState& state) const {
    // Stub: Not fully implemented yet
    return false;
}

Action ConsumablesCoordinator::decide(const GameState& state) {
    return create_action("none", "Consumables coordinator not fully implemented (stub)", 0.1f);
}

} // namespace coordinators
} // namespace openkore_ai
