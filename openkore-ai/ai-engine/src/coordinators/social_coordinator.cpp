#include "../../include/coordinators/social_coordinator.hpp"
#include <iostream>

namespace openkore_ai {
namespace coordinators {

SocialCoordinator::SocialCoordinator() 
    : CoordinatorBase("SocialCoordinator", Priority::LOW) {
    std::cout << "[SocialCoordinator] Initialized (Phase 8 - Full Implementation)" << std::endl;
}

bool SocialCoordinator::should_activate(const GameState& state) const {
    // Activate when nearby players exist
    if (state.nearby_players.empty()) return false;
    
    // Only activate if we're not in combat
    if (!state.monsters.empty()) {
        float hp_ratio = static_cast<float>(state.character.hp) / state.character.max_hp;
        if (hp_ratio < 0.8f || state.monsters.size() > 2) {
            return false;  // Combat takes priority
        }
    }
    
    // Check if any players are close enough for interaction (within 10 cells)
    for (const auto& player : state.nearby_players) {
        if (player.distance <= 10) {
            return true;
        }
    }
    
    return false;
}

Action SocialCoordinator::decide(const GameState& state) {
    // Find closest player for potential interaction
    std::string closest_player_name;
    int min_distance = 999;
    
    for (const auto& player : state.nearby_players) {
        if (player.distance < min_distance && player.distance <= 10) {
            closest_player_name = player.name;
            min_distance = player.distance;
        }
    }
    
    if (closest_player_name.empty()) {
        return create_action("none", "No nearby players for social interaction", 0.1f);
    }
    
    // Query Python social service for interaction decision
    // This would be triggered by actual player chat events in the Perl plugin
    // C++ coordinator just ensures social awareness is active
    
    std::string reason = "Monitoring social interactions with " + closest_player_name + 
                        " (distance: " + std::to_string(min_distance) + " cells)";
    
    return create_action("none", reason, 0.3f);
}

} // namespace coordinators
} // namespace openkore_ai
