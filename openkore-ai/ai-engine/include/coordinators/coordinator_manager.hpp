#pragma once
#include "coordinator_base.hpp"
#include <vector>
#include <memory>

namespace openkore_ai {
namespace coordinators {

class CoordinatorManager {
public:
    CoordinatorManager();
    
    // Initialize all coordinators
    void initialize();
    
    // Get recommendation from all active coordinators
    Action get_coordinator_decision(const GameState& state);
    
    // Get specific coordinator by name
    CoordinatorBase* get_coordinator(const std::string& name) const;
    
private:
    std::vector<std::unique_ptr<CoordinatorBase>> coordinators_;
    
    // Select best action from multiple coordinator recommendations
    Action select_best_action(const std::vector<std::pair<CoordinatorBase*, Action>>& recommendations) const;
};

} // namespace coordinators
} // namespace openkore_ai
