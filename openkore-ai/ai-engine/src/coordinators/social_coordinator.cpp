#include "../../include/coordinators/social_coordinator.hpp"
#include <iostream>

namespace openkore_ai {
namespace coordinators {

SocialCoordinator::SocialCoordinator() 
    : CoordinatorBase("SocialCoordinator", Priority::LOW) {
    std::cout << "[SocialCoordinator] Initialized (stub - important for Phase 8)" << std::endl;
}

bool SocialCoordinator::should_activate(const GameState& state) const {
    // Stub: Will be fully implemented in Phase 8
    return false;
}

Action SocialCoordinator::decide(const GameState& state) {
    return create_action("none", "Social coordinator not fully implemented (stub for Phase 8)", 0.1f);
}

} // namespace coordinators
} // namespace openkore_ai
