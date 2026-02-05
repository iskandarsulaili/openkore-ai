#pragma once
#include "coordinator_base.hpp"

namespace openkore_ai {
namespace coordinators {

class EconomyCoordinator : public CoordinatorBase {
public:
    EconomyCoordinator();
    
    bool should_activate(const GameState& state) const override;
    Action decide(const GameState& state) override;
    
private:
    bool is_overweight(const GameState& state) const;
    bool should_sell_items(const GameState& state) const;
};

} // namespace coordinators
} // namespace openkore_ai
