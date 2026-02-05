#pragma once
#include "coordinator_base.hpp"

namespace openkore_ai {
namespace coordinators {

class ConsumablesCoordinator : public CoordinatorBase {
public:
    ConsumablesCoordinator();
    
    bool should_activate(const GameState& state) const override;
    Action decide(const GameState& state) override;
};

} // namespace coordinators
} // namespace openkore_ai
