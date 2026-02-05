#include "../../include/coordinators/navigation_coordinator.hpp"
#include <iostream>

namespace openkore_ai {
namespace coordinators {

NavigationCoordinator::NavigationCoordinator() 
    : CoordinatorBase("NavigationCoordinator", Priority::LOW) {
    std::cout << "[NavigationCoordinator] Initialized (stub)" << std::endl;
}

bool NavigationCoordinator::should_activate(const GameState& state) const {
    // Stub: Not fully implemented yet
    return false;
}

Action NavigationCoordinator::decide(const GameState& state) {
    return create_action("none", "Navigation coordinator not fully implemented (stub)", 0.1f);
}

} // namespace coordinators
} // namespace openkore_ai
