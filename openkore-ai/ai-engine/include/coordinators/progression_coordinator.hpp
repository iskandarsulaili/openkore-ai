#pragma once
#include "coordinator_base.hpp"

namespace openkore_ai {
namespace coordinators {

class ProgressionCoordinator : public CoordinatorBase {
public:
    ProgressionCoordinator();
    
    bool should_activate(const GameState& state) const override;
    Action decide(const GameState& state) override;

private:
    // Tracking for stat/skill allocation
    mutable int last_stat_point_check_;
    mutable int last_skill_point_check_;
    
    // Helper methods
    Action allocate_stat_points(const GameState& state) const;
    Action allocate_skill_points(const GameState& state) const;
    std::string get_primary_stat_for_job(const std::string& job_class) const;
    std::string get_secondary_stat_for_job(const std::string& job_class) const;
    std::string get_recommended_skill_for_job(const std::string& job_class, int level) const;
    bool is_first_job(const std::string& job_class) const;
};

} // namespace coordinators
} // namespace openkore_ai
