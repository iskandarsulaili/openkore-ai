#pragma once
#include "coordinator_base.hpp"

namespace openkore_ai {
namespace coordinators {

class NavigationCoordinator : public CoordinatorBase {
public:
    NavigationCoordinator();
    
    bool should_activate(const GameState& state) const override;
    Action decide(const GameState& state) override;

private:
    // Stuck detection
    mutable int stuck_counter_;
    int stuck_threshold_;
    mutable int last_position_x_;
    mutable int last_position_y_;
    
    // Helper methods
    bool is_stuck(const GameState& state) const;
    Action handle_stuck(const GameState& state);
    Action navigate_to_destination(const GameState& state) const;
    std::string find_nearest_portal(const GameState& state) const;
    int calculate_distance(int x1, int y1, int x2, int y2) const;
};

} // namespace coordinators
} // namespace openkore_ai
