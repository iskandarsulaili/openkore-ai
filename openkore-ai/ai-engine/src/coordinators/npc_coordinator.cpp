#include "../../include/coordinators/npc_coordinator.hpp"
#include <iostream>
#include <algorithm>

namespace openkore_ai {
namespace coordinators {

NPCCoordinator::NPCCoordinator() 
    : CoordinatorBase("NPCCoordinator", Priority::MEDIUM) {
    npc_interaction_range_ = 5;
    current_npc_id_ = "";
    dialogue_state_ = DialogueState::IDLE;
    
    std::cout << "[NPCCoordinator] Fully initialized" << std::endl;
}

bool NPCCoordinator::should_activate(const GameState& state) const {
    // Activate if in dialogue or need potions
    if (dialogue_state_ != DialogueState::IDLE) {
        return true;
    }
    
    // Check if need to buy potions
    return check_need_potions(state);
}

Action NPCCoordinator::decide(const GameState& state) {
    // Handle active dialogue
    if (dialogue_state_ != DialogueState::IDLE) {
        return handle_active_dialogue(state);
    }
    
    // Check if need potions
    if (check_need_potions(state)) {
        Action action = create_action("talk", "Need to buy consumables", 0.75f);
        action.parameters["target"] = "Tool Dealer";
        action.parameters["action"] = "buy_potions";
        return action;
    }
    
    return create_action("none", "NPC: No interaction needed", 0.1f);
}

Action NPCCoordinator::handle_active_dialogue(const GameState& state) {
    switch (dialogue_state_) {
        case DialogueState::TALKING:
            {
                Action action = create_action("npc_talk", "Continue dialogue", 0.90f);
                action.parameters["action"] = "continue";
                return action;
            }
        case DialogueState::MENU:
            {
                Action action = create_action("npc_menu", "Select menu option", 0.90f);
                action.parameters["option"] = "0";
                return action;
            }
        case DialogueState::BUYING:
            {
                Action action = create_action("npc_buy", "Purchase items", 0.90f);
                action.parameters["items"] = "potions";
                return action;
            }
        default:
            dialogue_state_ = DialogueState::IDLE;
            return create_action("npc_close", "Close dialogue", 0.80f);
    }
}

Action NPCCoordinator::initiate_npc_talk(const std::string& npc_id, const std::string& reason) {
    current_npc_id_ = npc_id;
    dialogue_state_ = DialogueState::TALKING;
    
    Action action = create_action("talk", reason, 0.85f);
    action.parameters["target"] = npc_id;
    return action;
}

std::string NPCCoordinator::find_quest_npc(const GameState& state) const {
    return "";
}

std::string NPCCoordinator::find_shop_npc(const GameState& state, const std::string& shop_type) const {
    return "";
}

bool NPCCoordinator::check_need_potions(const GameState& state) const {
    int hp_potion_count = 0;
    int sp_potion_count = 0;
    
    for (const auto& item : state.inventory) {
        if (item.name.find("Potion") != std::string::npos) {
            if (item.name.find("Red") != std::string::npos || 
                item.name.find("White") != std::string::npos) {
                hp_potion_count += item.amount;
            }
            if (item.name.find("Blue") != std::string::npos) {
                sp_potion_count += item.amount;
            }
        }
    }
    
    return hp_potion_count < 10 || sp_potion_count < 10;
}

bool NPCCoordinator::has_nearby_shop_npc(const GameState& state) const {
    return false;
}

bool NPCCoordinator::is_near_weight_limit(const GameState& state) const {
    if (state.character.max_weight == 0) return false;
    float weight_percent = static_cast<float>(state.character.weight) / state.character.max_weight;
    return weight_percent >= 0.80f;
}

int NPCCoordinator::calculate_npc_distance(const GameState& state, const std::string& npc_id) const {
    return 0;
}

} // namespace coordinators
} // namespace openkore_ai
