#include "../../include/coordinators/planning_coordinator.hpp"
#include <iostream>

namespace openkore_ai {
namespace coordinators {

PlanningCoordinator::PlanningCoordinator() 
    : CoordinatorBase("PlanningCoordinator", Priority::LOW) {
    current_plan_step_ = 0;
    has_active_plan_ = false;
    
    std::cout << "[PlanningCoordinator] Fully initialized" << std::endl;
}

bool PlanningCoordinator::should_activate(const GameState& state) const {
    if (has_active_plan_ && current_plan_step_ < active_plan_.size()) {
        return true;
    }
    
    return needs_complex_planning(state);
}

Action PlanningCoordinator::decide(const GameState& state) {
    if (!has_active_plan_ || active_plan_.empty()) {
        create_plan_for_current_situation(state);
    }
    
    if (has_active_plan_ && current_plan_step_ < active_plan_.size()) {
        Action step = active_plan_[current_plan_step_];
        current_plan_step_++;
        
        if (current_plan_step_ >= active_plan_.size()) {
            has_active_plan_ = false;
            current_plan_step_ = 0;
            active_plan_.clear();
        }
        
        return step;
    }
    
    return create_action("none", "No plan active", 0.1f);
}

bool PlanningCoordinator::needs_complex_planning(const GameState& state) const {
    int threats = static_cast<int>(state.monsters.size());
    float hp_percent = state.character.max_hp > 0 
        ? static_cast<float>(state.character.hp) / state.character.max_hp 
        : 1.0f;
    
    return threats >= 3 && hp_percent < 0.30f;
}

void PlanningCoordinator::create_plan_for_current_situation(const GameState& state) {
    active_plan_.clear();
    current_plan_step_ = 0;
    has_active_plan_ = false;
    
    int threats = static_cast<int>(state.monsters.size());
    float hp_percent = state.character.max_hp > 0 
        ? static_cast<float>(state.character.hp) / state.character.max_hp 
        : 1.0f;
    
    if (threats >= 3 && hp_percent < 0.30f) {
        Action step1 = create_action("item", "Plan: Emergency heal", 0.95f);
        step1.parameters["item"] = "White Potion";
        active_plan_.push_back(step1);
        
        Action step2 = create_action("move", "Plan: Retreat", 0.90f);
        step2.parameters["direction"] = "retreat";
        active_plan_.push_back(step2);
        
        has_active_plan_ = true;
    }
}

bool PlanningCoordinator::check_need_resupply(const GameState& state) const {
    int potion_count = 0;
    for (const auto& item : state.inventory) {
        if (item.name.find("Potion") != std::string::npos) {
            potion_count += item.amount;
        }
    }
    return potion_count < 5;
}

} // namespace coordinators
} // namespace openkore_ai
