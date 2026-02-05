#pragma once
#include "coordinator_base.hpp"

namespace openkore_ai {
namespace coordinators {

class NavigationCoordinator : public CoordinatorBase {
public:
    NavigationCoordinator();
    
    bool should_activate(const GameState& state) const override;
    Action decide(const GameState& state) override;
};

} // namespace coordinators
} // namespace openkore_ai
