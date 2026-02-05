#include "../../include/coordinators/navigation_coordinator.hpp"
#include <iostream>
#include <cmath>
#include <algorithm>

namespace openkore_ai {
namespace coordinators {

NavigationCoordinator::NavigationCoordinator() 
    : CoordinatorBase("NavigationCoordinator", Priority::LOW) {
    stuck_threshold_ = 3;
    stuck_counter_ = 0;
    last_position_x_ = -1;
    last_position_y_ = -1;
    
    std::cout << "[NavigationCoordinator] Fully initialized" << std::endl;
}

bool NavigationCoordinator::should_activate(const GameState& state) const {
    // Only activate if stuck
    return is_stuck(state);
}

Action NavigationCoordinator::decide(const GameState& state) {
    if (is_stuck(state)) {
        return handle_stuck(state);
    }
    
    return create_action("none", "Navigation OK", 0.1f);
}

bool NavigationCoordinator::is_stuck(const GameState& state) const {
    // Check if position hasn't changed
    if (last_position_x_ == state.character.position.x && 
        last_position_y_ == state.character.position.y) {
        return stuck_counter_ >= stuck_threshold_;
    }
    return false;
}

Action NavigationCoordinator::handle_stuck(const GameState& state) {
    std::cout << "[NavigationCoordinator] Stuck detected" << std::endl;
    
    // Check for teleport items
    auto has_fly_wing = std::find_if(state.inventory.begin(), state.inventory.end(),
        [](const Item& item) {
            return item.name == "Fly Wing" && item.amount > 0;
        });
    
    if (has_fly_wing != state.inventory.end()) {
        Action action = create_action("item", "Stuck - using Fly Wing", 0.90f);
        action.parameters["item"] = "Fly Wing";
        return action;
    }
    
    // Random walk
    Action action = create_action("move", "Stuck - random walk", 0.80f);
    action.parameters["x"] = std::to_string(state.character.position.x + (rand() % 5 - 2));
    action.parameters["y"] = std::to_string(state.character.position.y + (rand() % 5 - 2));
    return action;
}

Action NavigationCoordinator::navigate_to_destination(const GameState& state) const {
    // Update stuck tracking
    NavigationCoordinator* mutable_this = const_cast<NavigationCoordinator*>(this);
    if (last_position_x_ == state.character.position.x && last_position_y_ == state.character.position.y) {
        mutable_this->stuck_counter_++;
    } else {
        mutable_this->stuck_counter_ = 0;
        mutable_this->last_position_x_ = state.character.position.x;
        mutable_this->last_position_y_ = state.character.position.y;
    }
    
    return create_action("none", "No destination", 0.1f);
}

std::string NavigationCoordinator::find_nearest_portal(const GameState& state) const {
    return "";
}

int NavigationCoordinator::calculate_distance(int x1, int y1, int x2, int y2) const {
    int dx = std::abs(x2 - x1);
    int dy = std::abs(y2 - y1);
    return std::max(dx, dy);
}

} // namespace coordinators
} // namespace openkore_ai
