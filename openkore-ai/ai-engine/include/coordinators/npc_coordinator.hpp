#pragma once
#include "coordinator_base.hpp"

namespace openkore_ai {
namespace coordinators {

class NPCCoordinator : public CoordinatorBase {
public:
    NPCCoordinator();
    bool should_activate(const GameState& state) const override;
    Action decide(const GameState& state) override;

private:
    enum class DialogueState {
        IDLE,
        TALKING,
        MENU,
        BUYING,
        SELLING
    };
    
    // NPC interaction state
    int npc_interaction_range_;
    mutable std::string current_npc_id_;
    mutable DialogueState dialogue_state_;
    
    // Helper methods
    Action handle_active_dialogue(const GameState& state);
    Action initiate_npc_talk(const std::string& npc_id, const std::string& reason);
    std::string find_quest_npc(const GameState& state) const;
    std::string find_shop_npc(const GameState& state, const std::string& shop_type) const;
    bool check_need_potions(const GameState& state) const;
    bool has_nearby_shop_npc(const GameState& state) const;
    bool is_near_weight_limit(const GameState& state) const;
    int calculate_npc_distance(const GameState& state, const std::string& npc_id) const;
};

} // namespace coordinators
} // namespace openkore_ai
