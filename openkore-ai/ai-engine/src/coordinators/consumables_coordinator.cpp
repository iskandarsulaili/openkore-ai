#include "../../include/coordinators/consumables_coordinator.hpp"
#include <iostream>
#include <algorithm>

namespace openkore_ai {
namespace coordinators {

ConsumablesCoordinator::ConsumablesCoordinator() 
    : CoordinatorBase("ConsumablesCoordinator", Priority::MEDIUM) {
    hp_emergency_threshold_ = 0.30f;
    hp_warning_threshold_ = 0.50f;
    sp_emergency_threshold_ = 0.20f;
    sp_warning_threshold_ = 0.40f;
    weight_warning_threshold_ = 0.80f;
    
    std::cout << "[ConsumablesCoordinator] Fully initialized" << std::endl;
}

bool ConsumablesCoordinator::should_activate(const GameState& state) const {
    float hp_percent = state.character.max_hp > 0 
        ? static_cast<float>(state.character.hp) / state.character.max_hp 
        : 1.0f;
    
    float sp_percent = state.character.max_sp > 0 
        ? static_cast<float>(state.character.sp) / state.character.max_sp 
        : 1.0f;
    
    float weight_percent = state.character.max_weight > 0 
        ? static_cast<float>(state.character.weight) / state.character.max_weight 
        : 0.0f;
    
    return hp_percent < hp_warning_threshold_ 
        || sp_percent < sp_warning_threshold_
        || weight_percent > weight_warning_threshold_;
}

Action ConsumablesCoordinator::decide(const GameState& state) {
    float hp_percent = state.character.max_hp > 0 
        ? static_cast<float>(state.character.hp) / state.character.max_hp 
        : 1.0f;
    
    float sp_percent = state.character.max_sp > 0 
        ? static_cast<float>(state.character.sp) / state.character.max_sp 
        : 1.0f;
    
    float weight_percent = state.character.max_weight > 0 
        ? static_cast<float>(state.character.weight) / state.character.max_weight 
        : 0.0f;
    
    // Emergency HP
    if (hp_percent < hp_emergency_threshold_) {
        std::string item = find_best_hp_item(state, true);
        if (!item.empty()) {
            Action action = create_action("item", "EMERGENCY: HP critical", 0.95f);
            action.parameters["item"] = item;
            action.parameters["emergency"] = "true";
            return action;
        }
    }
    
    // Warning HP
    if (hp_percent < hp_warning_threshold_) {
        std::string item = find_best_hp_item(state, false);
        if (!item.empty()) {
            Action action = create_action("item", "HP low", 0.75f);
            action.parameters["item"] = item;
            return action;
        }
    }
    
    // Emergency SP
    if (sp_percent < sp_emergency_threshold_) {
        std::string item = find_best_sp_item(state, true);
        if (!item.empty()) {
            Action action = create_action("item", "SP critical", 0.85f);
            action.parameters["item"] = item;
            return action;
        }
    }
    
    // Warning SP
    if (sp_percent < sp_warning_threshold_) {
        std::string item = find_best_sp_item(state, false);
        if (!item.empty()) {
            Action action = create_action("item", "SP low", 0.65f);
            action.parameters["item"] = item;
            return action;
        }
    }
    
    // Overweight
    if (weight_percent > weight_warning_threshold_) {
        std::string item = find_item_to_drop(state);
        if (!item.empty()) {
            Action action = create_action("drop", "Overweight", 0.70f);
            action.parameters["item"] = item;
            action.parameters["amount"] = "1";
            return action;
        }
    }
    
    return create_action("none", "Consumables OK", 0.1f);
}

std::string ConsumablesCoordinator::find_best_hp_item(const GameState& state, bool emergency) const {
    std::vector<std::string> priority = emergency 
        ? std::vector<std::string>{"White Potion", "Red Potion", "Orange Potion", "Yellow Potion"}
        : std::vector<std::string>{"Red Potion", "Orange Potion", "Yellow Potion"};
    
    for (const auto& item_name : priority) {
        auto it = std::find_if(state.inventory.begin(), state.inventory.end(),
            [&item_name](const Item& item) {
                return item.name == item_name && item.amount > 0;
            });
        
        if (it != state.inventory.end()) {
            return item_name;
        }
    }
    
    return "";
}

std::string ConsumablesCoordinator::find_best_sp_item(const GameState& state, bool emergency) const {
    std::vector<std::string> sp_items = {"Blue Potion", "Royal Jelly"};
    
    for (const auto& item_name : sp_items) {
        auto it = std::find_if(state.inventory.begin(), state.inventory.end(),
            [&item_name](const Item& item) {
                return item.name == item_name && item.amount > 0;
            });
        
        if (it != state.inventory.end()) {
            return item_name;
        }
    }
    
    return "";
}

std::string ConsumablesCoordinator::find_item_to_drop(const GameState& state) const {
    std::vector<std::string> droppable = {"Jellopy", "Fluff", "Clover"};
    
    for (const auto& item_name : droppable) {
        auto it = std::find_if(state.inventory.begin(), state.inventory.end(),
            [&item_name](const Item& item) {
                return item.name == item_name && item.amount > 0;
            });
        
        if (it != state.inventory.end()) {
            return item_name;
        }
    }
    
    return "";
}

} // namespace coordinators
} // namespace openkore_ai
