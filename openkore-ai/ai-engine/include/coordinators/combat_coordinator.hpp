#pragma once
#include "coordinator_base.hpp"

namespace openkore_ai {
namespace coordinators {

class CombatCoordinator : public CoordinatorBase {
public:
    CombatCoordinator();
    
    bool should_activate(const GameState& state) const override;
    Action decide(const GameState& state) override;
    
private:
    Monster select_target(const GameState& state) const;
    std::string select_skill(const GameState& state, const Monster& target) const;
    bool should_use_aoe(const GameState& state) const;
};

} // namespace coordinators
} // namespace openkore_ai
