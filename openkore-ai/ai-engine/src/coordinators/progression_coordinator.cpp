#include "../../include/coordinators/progression_coordinator.hpp"
#include <iostream>

namespace openkore_ai {
namespace coordinators {

ProgressionCoordinator::ProgressionCoordinator() 
    : CoordinatorBase("ProgressionCoordinator", Priority::LOW) {
    last_stat_point_check_ = 0;
    last_skill_point_check_ = 0;
    
    std::cout << "[ProgressionCoordinator] Fully initialized" << std::endl;
}

bool ProgressionCoordinator::should_activate(const GameState& state) const {
    // For now, keep simple - can expand later
    return false;
}

Action ProgressionCoordinator::decide(const GameState& state) {
    int level = state.character.level;
    std::string job_class = state.character.job_class;
    
    // Job change milestones
    if (level == 10 && job_class == "Novice") {
        Action action = create_action("job_change", "Ready for First Job at level 10", 0.90f);
        action.parameters["target_job"] = "auto";
        return action;
    }
    
    if (level == 50 && is_first_job(job_class)) {
        Action action = create_action("job_change", "Ready for Second Job at level 50", 0.90f);
        action.parameters["target_job"] = "auto";
        return action;
    }
    
    return create_action("none", "Progression on track", 0.1f);
}

Action ProgressionCoordinator::allocate_stat_points(const GameState& state) const {
    std::string primary_stat = get_primary_stat_for_job(state.character.job_class);
    
    Action action = create_action("add_stat", "Allocate stat to " + primary_stat, 0.85f);
    action.parameters["stat"] = primary_stat;
    action.parameters["points"] = "1";
    return action;
}

Action ProgressionCoordinator::allocate_skill_points(const GameState& state) const {
    std::string skill = get_recommended_skill_for_job(state.character.job_class, state.character.level);
    
    if (!skill.empty()) {
        Action action = create_action("add_skill", "Learn " + skill, 0.85f);
        action.parameters["skill"] = skill;
        return action;
    }
    
    return create_action("none", "No skill recommendation", 0.1f);
}

std::string ProgressionCoordinator::get_primary_stat_for_job(const std::string& job_class) const {
    if (job_class.find("Sword") != std::string::npos || job_class.find("Knight") != std::string::npos) {
        return "STR";
    } else if (job_class.find("Magi") != std::string::npos || job_class.find("Wizard") != std::string::npos) {
        return "INT";
    } else if (job_class.find("Arch") != std::string::npos || job_class.find("Hunter") != std::string::npos) {
        return "DEX";
    } else if (job_class.find("Thief") != std::string::npos || job_class.find("Assassin") != std::string::npos) {
        return "AGI";
    }
    
    return "STR";
}

std::string ProgressionCoordinator::get_secondary_stat_for_job(const std::string& job_class) const {
    return "VIT";
}

std::string ProgressionCoordinator::get_recommended_skill_for_job(const std::string& job_class, int level) const {
    if (job_class == "Swordsman") return "Bash";
    if (job_class == "Magician") return "Fire Bolt";
    if (job_class == "Archer") return "Double Strafe";
    return "";
}

bool ProgressionCoordinator::is_first_job(const std::string& job_class) const {
    return job_class == "Swordsman" || job_class == "Magician" || 
           job_class == "Archer" || job_class == "Acolyte" || 
           job_class == "Merchant" || job_class == "Thief";
}

} // namespace coordinators
} // namespace openkore_ai
