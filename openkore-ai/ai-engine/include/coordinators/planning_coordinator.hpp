#pragma once
#include "coordinator_base.hpp"

namespace openkore_ai {
namespace coordinators {

class PlanningCoordinator : public CoordinatorBase {
public:
    PlanningCoordinator();
    bool should_activate(const GameState& state) const override;
    Action decide(const GameState& state) override;

private:
    // Planning state
    mutable std::vector<Action> active_plan_;
    mutable int current_plan_step_;
    mutable bool has_active_plan_;
    
    // Helper methods
    bool needs_complex_planning(const GameState& state) const;
    void create_plan_for_current_situation(const GameState& state);
    bool check_need_resupply(const GameState& state) const;
};

} // namespace coordinators
} // namespace openkore_ai
