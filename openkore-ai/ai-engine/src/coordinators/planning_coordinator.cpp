#include "../../include/coordinators/planning_coordinator.hpp"
#include <iostream>

namespace openkore_ai {
namespace coordinators {

PlanningCoordinator::PlanningCoordinator() 
    : CoordinatorBase("PlanningCoordinator", Priority::LOW) {
    std::cout << "[PlanningCoordinator] Initialized (stub)" << std::endl;
}

bool PlanningCoordinator::should_activate(const GameState& state) const {
    return false;
}

Action PlanningCoordinator::decide(const GameState& state) {
    return create_action("none", "Planning coordinator stub", 0.1f);
}

} // namespace coordinators
} // namespace openkore_ai
