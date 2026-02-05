#include "../../include/decision/ml.hpp"
#include <iostream>
#include <httplib.h>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace openkore_ai {
namespace decision {

MLTier::MLTier() {
    std::cout << "[MLTier] Initialized (Phase 6 - ML Pipeline ready)" << std::endl;
    model_loaded_ = false;  // Will be set true when model available
    
    // Check if ONNX model exists
    // TODO: Load ONNX model if available
}

bool MLTier::should_handle(const GameState& state) const {
    // Phase 6: Check with Python service if ML should be used
    // For now, defer to Python service cold-start manager
    return false;  // Python service will handle ML queries
}

Action MLTier::decide(const GameState& state) {
    // Phase 6: Query Python service for ML prediction
    return query_ml_service(state);
}

Action MLTier::query_ml_service(const GameState& state) {
    try {
        httplib::Client client("http://127.0.0.1:9902");
        client.set_read_timeout(5, 0);
        
        // Build request
        json request_json;
        request_json["game_state"] = state_to_json(state);
        request_json["request_type"] = "ml_prediction";
        
        auto response = client.Post("/api/v1/ml/predict",
                                   request_json.dump(),
                                   "application/json");
        
        if (response && response->status == 200) {
            json result = json::parse(response->body);
            
            Action action;
            action.type = result["action"]["type"];
            action.reason = result["action"]["reason"];
            action.confidence = result["action"]["confidence"];
            
            // Parse parameters
            if (result["action"].contains("parameters")) {
                for (auto& [key, value] : result["action"]["parameters"].items()) {
                    if (value.is_string()) {
                        action.parameters[key] = value.get<std::string>();
                    } else {
                        action.parameters[key] = value.dump();
                    }
                }
            }
            
            std::cout << "[MLTier] Prediction: " << action.type 
                     << " (confidence: " << action.confidence << ")" << std::endl;
            
            return action;
        } else {
            std::cerr << "[MLTier] HTTP error: " 
                     << (response ? response->status : -1) << std::endl;
        }
        
    } catch (const std::exception& e) {
        std::cerr << "[MLTier] Query failed: " << e.what() << std::endl;
    }
    
    return decide_stub(state);
}

json MLTier::state_to_json(const GameState& state) const {
    json j;
    
    // Character info
    j["character"]["level"] = state.character.level;
    j["character"]["hp"] = state.character.hp;
    j["character"]["max_hp"] = state.character.max_hp;
    j["character"]["sp"] = state.character.sp;
    j["character"]["max_sp"] = state.character.max_sp;
    j["character"]["weight"] = state.character.weight;
    j["character"]["max_weight"] = state.character.max_weight;
    j["character"]["zeny"] = state.character.zeny;
    j["character"]["base_exp"] = state.character.base_exp;
    j["character"]["job_exp"] = state.character.job_exp;
    j["character"]["status_effects"] = json::array();
    
    // Monsters
    j["monsters"] = json::array();
    for (const auto& monster : state.monsters) {
        json m;
        m["name"] = monster.name;
        m["hp"] = monster.hp;
        m["max_hp"] = monster.max_hp;
        m["distance"] = monster.distance;
        m["is_aggressive"] = monster.is_aggressive;
        j["monsters"].push_back(m);
    }
    
    // Inventory
    j["inventory"] = json::array();
    for (const auto& item : state.inventory) {
        json i;
        i["name"] = item.name;
        i["amount"] = item.amount;
        i["type"] = item.type;
        j["inventory"].push_back(i);
    }
    
    // Players
    j["nearby_players"] = json::array();
    
    return j;
}

Action MLTier::decide_stub(const GameState& state) {
    Action action;
    action.type = "none";
    action.reason = "ML: Model not loaded or service unavailable";
    action.confidence = 0.1f;
    return action;
}

} // namespace decision
} // namespace openkore_ai
