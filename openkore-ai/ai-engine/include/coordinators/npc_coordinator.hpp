#pragma once
#include "coordinator_base.hpp"

namespace openkore_ai {
namespace coordinators {

class NPCCoordinator : public CoordinatorBase {
public:
    NPCCoordinator();
    bool should_activate(const GameState& state) const override;
    Action decide(const GameState& state) override;
};

} // namespace coordinators
} // namespace openkore_ai
