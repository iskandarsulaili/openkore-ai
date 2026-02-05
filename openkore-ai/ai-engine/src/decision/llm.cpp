#include "../../include/decision/llm.hpp"
#include <httplib.h>
#include <nlohmann/json.hpp>
#include <chrono>
#include <iostream>

using json = nlohmann::json;

namespace openkore_ai {
namespace decision {

LLMTier::LLMTier(const std::string& python_service_url) 
    : python_service_url_(python_service_url) {
    std::cout << "[LLMTier] Initialized with Python service: " << python_service_url_ << std::endl;
}

bool LLMTier::should_handle(const GameState& state) const {
    // Only use LLM for complex strategic decisions, and rate limit queries
    auto now_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()
    ).count();
    
    if (now_ms - last_query_time_ms_ < MIN_QUERY_INTERVAL_MS) {
        return false;  // Too soon since last query
    }
    
    // Use LLM for:
    // - Character level milestones (every 10 levels)
    // - When stuck (no action for extended period)
    // - Strategic planning (party formation, farming location changes)
    
    if (state.character.level % 10 == 0 && state.character.level >= 10) {
        return true;  // Level milestone
    }
    
    return false;
}

Action LLMTier::decide(const GameState& state) {
    auto start = std::chrono::steady_clock::now();
    
    std::cout << "[LLMTier] Querying Python AI Service for strategic decision..." << std::endl;
    
    auto result = query_python_service(state);
    
    auto end = std::chrono::steady_clock::now();
    auto latency_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
    
    std::cout << "[LLMTier] Query completed in " << latency_ms << "ms" << std::endl;
    
    // Update last query time
    last_query_time_ms_ = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()
    ).count();
    
    if (result.has_value()) {
        return result.value();
    }
    
    // Fallback if LLM query failed
    Action action;
    action.type = "none";
    action.reason = "LLM: Query failed, no strategic action";
    action.confidence = 0.2f;
    return action;
}

std::optional<Action> LLMTier::query_python_service(const GameState& state) {
    try {
        // Parse URL
        httplib::Client client("http://127.0.0.1:9902");
        client.set_connection_timeout(5, 0);  // 5 seconds connection timeout
        client.set_read_timeout(300, 0);       // 300 seconds read timeout (5 minutes)
        
        // Build request
        json request_json;
        request_json["prompt"] = "What should I do next for optimal progression?";
        request_json["game_state"] = json::parse(game_state_to_json(state));
        request_json["context"] = "Strategic planning for character progression";
        request_json["request_id"] = "llm_" + std::to_string(state.timestamp_ms);
        
        // Send POST request
        auto response = client.Post("/api/v1/llm/query",
                                   request_json.dump(),
                                   "application/json");
        
        if (!response) {
            std::cerr << "[LLMTier] Failed to connect to Python service" << std::endl;
            return std::nullopt;
        }
        
        if (response->status != 200) {
            std::cerr << "[LLMTier] Python service returned error: " << response->status << std::endl;
            return std::nullopt;
        }
        
        // Parse response
        json response_json = json::parse(response->body);
        
        if (response_json.contains("action") && !response_json["action"].is_null()) {
            Action action;
            action.type = response_json["action"]["type"];
            action.reason = response_json["action"]["reason"];
            action.confidence = response_json["action"]["confidence"];
            
            // Parse parameters
            if (response_json["action"].contains("parameters")) {
                for (auto& [key, value] : response_json["action"]["parameters"].items()) {
                    action.parameters[key] = value.get<std::string>();
                }
            }
            
            return action;
        }
        
        return std::nullopt;
        
    } catch (const std::exception& e) {
        std::cerr << "[LLMTier] Exception during query: " << e.what() << std::endl;
        return std::nullopt;
    }
}

std::string LLMTier::game_state_to_json(const GameState& state) const {
    json j;
    
    // Character
    j["character"]["name"] = state.character.name;
    j["character"]["level"] = state.character.level;
    j["character"]["hp"] = state.character.hp;
    j["character"]["max_hp"] = state.character.max_hp;
    j["character"]["sp"] = state.character.sp;
    j["character"]["max_sp"] = state.character.max_sp;
    j["character"]["position"]["map"] = state.character.position.map;
    j["character"]["position"]["x"] = state.character.position.x;
    j["character"]["position"]["y"] = state.character.position.y;
    j["character"]["zeny"] = state.character.zeny;
    j["character"]["job_class"] = state.character.job_class;
    
    // Monsters (summary)
    j["monsters"] = json::array();
    for (const auto& m : state.monsters) {
        json monster_json;
        monster_json["name"] = m.name;
        monster_json["distance"] = m.distance;
        monster_json["is_aggressive"] = m.is_aggressive;
        j["monsters"].push_back(monster_json);
    }
    
    return j.dump();
}

} // namespace decision
} // namespace openkore_ai
