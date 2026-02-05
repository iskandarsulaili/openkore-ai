#include "../../include/coordinators/progression_coordinator.hpp"
#include <iostream>

namespace openkore_ai {
namespace coordinators {

ProgressionCoordinator::ProgressionCoordinator() 
    : CoordinatorBase("ProgressionCoordinator", Priority::LOW) {
    std::cout << "[ProgressionCoordinator] Initialized (stub)" << std::endl;
}

bool ProgressionCoordinator::should_activate(const GameState& state) const {
    // Stub: Not fully implemented yet
    return false;
}

Action ProgressionCoordinator::decide(const GameState& state) {
    return create_action("none", "Progression coordinator not fully implemented (stub)", 0.1f);
}

} // namespace coordinators
} // namespace openkore_ai
