#include "../../include/coordinators/npc_coordinator.hpp"
#include <iostream>

namespace openkore_ai {
namespace coordinators {

NPCCoordinator::NPCCoordinator() 
    : CoordinatorBase("NPCCoordinator", Priority::MEDIUM) {
    std::cout << "[NPCCoordinator] Initialized (stub)" << std::endl;
}

bool NPCCoordinator::should_activate(const GameState& state) const {
    return false;
}

Action NPCCoordinator::decide(const GameState& state) {
    return create_action("none", "NPC coordinator stub", 0.1f);
}

} // namespace coordinators
} // namespace openkore_ai
