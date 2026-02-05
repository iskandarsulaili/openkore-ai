#pragma once
#include "coordinator_base.hpp"

namespace openkore_ai {
namespace coordinators {

class ConsumablesCoordinator : public CoordinatorBase {
public:
    ConsumablesCoordinator();
    
    bool should_activate(const GameState& state) const override;
    Action decide(const GameState& state) override;

private:
    // Thresholds for consumable usage
    float hp_emergency_threshold_;
    float hp_warning_threshold_;
    float sp_emergency_threshold_;
    float sp_warning_threshold_;
    float weight_warning_threshold_;
    
    // Helper methods
    std::string find_best_hp_item(const GameState& state, bool emergency) const;
    std::string find_best_sp_item(const GameState& state, bool emergency) const;
    std::string find_item_to_drop(const GameState& state) const;
};

} // namespace coordinators
} // namespace openkore_ai
