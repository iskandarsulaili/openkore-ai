#include <httplib.h>
#include <nlohmann/json.hpp>
#include <iostream>
#include <memory>
#include <thread>
#include <chrono>
#include <mutex>
#include "types.hpp"
#include "decision/reflex.hpp"
#include "decision/rules.hpp"
#include "decision/ml.hpp"
#include "decision/llm.hpp"
#include "coordinators/coordinator_manager.hpp"

using json = nlohmann::json;
using namespace openkore_ai;

// Global state
auto start_time = std::chrono::steady_clock::now();

// Global decision tiers
std::unique_ptr<decision::ReflexTier> reflex_tier;
std::unique_ptr<decision::RulesTier> rules_tier;
std::unique_ptr<decision::MLTier> ml_tier;
std::unique_ptr<decision::LLMTier> llm_tier;

// Global coordinator manager (Phase 5)
std::unique_ptr<coordinators::CoordinatorManager> coordinator_manager;

// Statistics
struct DecisionStats {
    uint64_t reflex_count = 0;
    uint64_t rules_count = 0;
    uint64_t ml_count = 0;
    uint64_t llm_count = 0;
    uint64_t total_count = 0;
    double avg_latency_ms = 0.0;
    std::mutex stats_mutex;
} stats;

// Convert JSON to GameState
GameState parse_game_state(const json& j) {
    GameState state;
    
    // Parse character
    state.character.name = j["character"]["name"];
    state.character.level = j["character"]["level"];
    state.character.hp = j["character"]["hp"];
    state.character.max_hp = j["character"]["max_hp"];
    state.character.sp = j["character"]["sp"];
    state.character.max_sp = j["character"]["max_sp"];
    state.character.position.map = j["character"]["position"]["map"];
    state.character.position.x = j["character"]["position"]["x"];
    state.character.position.y = j["character"]["position"]["y"];
    state.character.weight = j["character"]["weight"];
    state.character.max_weight = j["character"]["max_weight"];
    state.character.zeny = j["character"]["zeny"];
    state.character.job_class = j["character"]["job_class"];
    
    // Parse status effects
    if (j["character"].contains("status_effects")) {
        for (const auto& effect : j["character"]["status_effects"]) {
            state.character.status_effects.push_back(effect);
        }
    }
    
    // Parse monsters
    if (j.contains("monsters")) {
        for (const auto& m : j["monsters"]) {
            Monster monster;
            monster.id = m["id"];
            monster.name = m["name"];
            monster.hp = m.value("hp", 0);
            monster.max_hp = m.value("max_hp", 0);
            monster.distance = m["distance"];
            monster.is_aggressive = m.value("is_aggressive", false);
            state.monsters.push_back(monster);
        }
    }
    
    // Parse inventory
    if (j.contains("inventory")) {
        for (const auto& i : j["inventory"]) {
            Item item;
            item.id = i["id"];
            item.name = i["name"];
            item.amount = i["amount"];
            item.type = i["type"];
            state.inventory.push_back(item);
        }
    }
    
    // Parse nearby players
    if (j.contains("nearby_players")) {
        for (const auto& p : j["nearby_players"]) {
            Player player;
            player.name = p["name"];
            player.level = p["level"];
            player.guild = p.value("guild", "");
            player.distance = p["distance"];
            player.is_party_member = p.value("is_party_member", false);
            state.nearby_players.push_back(player);
        }
    }
    
    state.timestamp_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()
    ).count();
    
    return state;
}

// Convert Action to JSON
json action_to_json(const Action& action) {
    json j;
    j["type"] = action.type;
    j["parameters"] = action.parameters;
    j["reason"] = action.reason;
    j["confidence"] = action.confidence;
    return j;
}

// Convert DecisionTier to string
std::string tier_to_string(DecisionTier tier) {
    switch (tier) {
        case DecisionTier::REFLEX: return "reflex";
        case DecisionTier::RULES: return "rules";
        case DecisionTier::ML: return "ml";
        case DecisionTier::LLM: return "llm";
        default: return "unknown";
    }
}

// Multi-tier decision function
DecisionResponse make_decision(const GameState& state, const std::string& request_id) {
    auto start = std::chrono::steady_clock::now();
    
    DecisionResponse response;
    response.request_id = request_id;
    
    // Tier 1: Reflex (<1ms)
    if (reflex_tier->should_handle(state)) {
        response.action = reflex_tier->decide(state);
        response.tier_used = DecisionTier::REFLEX;
        std::lock_guard<std::mutex> lock(stats.stats_mutex);
        stats.reflex_count++;
        stats.total_count++;
        goto done;
    }
    
    // Phase 5: Consult coordinator system (operates at tactical/rules level)
    {
        Action coordinator_action = coordinator_manager->get_coordinator_decision(state);
        if (coordinator_action.type != "none") {
            response.action = coordinator_action;
            response.tier_used = DecisionTier::RULES;  // Coordinators operate at tactical level
            std::lock_guard<std::mutex> lock(stats.stats_mutex);
            stats.rules_count++;
            stats.total_count++;
            goto done;
        }
    }
    
    // Tier 2: Rules (<10ms)
    if (rules_tier->should_handle(state)) {
        response.action = rules_tier->decide(state);
        response.tier_used = DecisionTier::RULES;
        std::lock_guard<std::mutex> lock(stats.stats_mutex);
        stats.rules_count++;
        stats.total_count++;
        goto done;
    }
    
    // Tier 3: ML (<100ms) - Phase 2: Stub
    if (ml_tier->should_handle(state)) {
        response.action = ml_tier->decide(state);
        response.tier_used = DecisionTier::ML;
        std::lock_guard<std::mutex> lock(stats.stats_mutex);
        stats.ml_count++;
        stats.total_count++;
        goto done;
    }
    
    // Tier 4: LLM (30-300s)
    if (llm_tier->should_handle(state)) {
        response.action = llm_tier->decide(state);
        response.tier_used = DecisionTier::LLM;
        std::lock_guard<std::mutex> lock(stats.stats_mutex);
        stats.llm_count++;
        stats.total_count++;
        goto done;
    }
    
    // No tier handled this - default action
    response.action.type = "none";
    response.action.reason = "No tier required action";
    response.action.confidence = 0.5f;
    response.tier_used = DecisionTier::REFLEX;
    
done:
    auto end = std::chrono::steady_clock::now();
    response.latency_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
    
    // Update average latency
    {
        std::lock_guard<std::mutex> lock(stats.stats_mutex);
        if (stats.total_count > 0) {
            stats.avg_latency_ms = (stats.avg_latency_ms * (stats.total_count - 1) + response.latency_ms) / stats.total_count;
        } else {
            stats.avg_latency_ms = response.latency_ms;
        }
    }
    
    return response;
}

int main() {
    httplib::Server server;
    
    std::cout << "OpenKore AI Engine v1.0.0 (Phase 5)" << std::endl;
    std::cout << "Starting HTTP server on http://127.0.0.1:9901" << std::endl;
    
    // Initialize decision tiers
    std::cout << "Initializing decision tiers..." << std::endl;
    reflex_tier = std::make_unique<decision::ReflexTier>();
    rules_tier = std::make_unique<decision::RulesTier>();
    ml_tier = std::make_unique<decision::MLTier>();
    llm_tier = std::make_unique<decision::LLMTier>("http://127.0.0.1:9902");
    std::cout << "All decision tiers initialized successfully" << std::endl;
    
    // Initialize coordinator framework (Phase 5)
    std::cout << "\nInitializing coordinator framework (Phase 5)..." << std::endl;
    coordinator_manager = std::make_unique<coordinators::CoordinatorManager>();
    coordinator_manager->initialize();
    std::cout << "Coordinator framework initialized successfully\n" << std::endl;
    
    // POST /api/v1/decide - Main decision endpoint
    server.Post("/api/v1/decide", [](const httplib::Request& req, httplib::Response& res) {
        try {
            json request_json = json::parse(req.body);
            GameState state = parse_game_state(request_json["game_state"]);
            std::string request_id = request_json.value("request_id", "unknown");
            
            std::cout << "[DECIDE] Request " << request_id 
                     << " - Character: " << state.character.name 
                     << " (Lv " << state.character.level << ", "
                     << state.character.hp << "/" << state.character.max_hp << " HP)" << std::endl;
            
            // Make decision using multi-tier system
            DecisionResponse decision = make_decision(state, request_id);
            
            // Build response
            json response_json;
            response_json["action"] = action_to_json(decision.action);
            response_json["tier_used"] = tier_to_string(decision.tier_used);
            response_json["latency_ms"] = decision.latency_ms;
            response_json["request_id"] = decision.request_id;
            
            std::cout << "[DECIDE] Response: " << decision.action.type 
                     << " via " << tier_to_string(decision.tier_used)
                     << " (" << decision.latency_ms << "ms)" << std::endl;
            
            res.set_content(response_json.dump(), "application/json");
            res.status = 200;
            
        } catch (const std::exception& e) {
            json error_json;
            error_json["error"] = e.what();
            res.set_content(error_json.dump(), "application/json");
            res.status = 500;
            std::cerr << "[ERROR] " << e.what() << std::endl;
        }
    });
    
    // GET /api/v1/health - Health check endpoint
    server.Get("/api/v1/health", [](const httplib::Request&, httplib::Response& res) {
        auto now = std::chrono::steady_clock::now();
        long long uptime_seconds = std::chrono::duration_cast<std::chrono::seconds>(now - start_time).count();
        
        json health_json;
        health_json["status"] = "healthy";
        health_json["components"]["reflex_tier"] = true;
        health_json["components"]["rules_tier"] = true;
        health_json["components"]["ml_tier"] = false;     // Stub only
        health_json["components"]["llm_tier"] = true;
        health_json["components"]["coordinator_framework"] = true;  // Phase 5
        health_json["uptime_seconds"] = uptime_seconds;
        health_json["version"] = "1.0.0-phase5";
        
        res.set_content(health_json.dump(), "application/json");
        res.status = 200;
    });
    
    // GET /api/v1/metrics - Metrics endpoint
    server.Get("/api/v1/metrics", [](const httplib::Request&, httplib::Response& res) {
        std::lock_guard<std::mutex> lock(stats.stats_mutex);
        
        json metrics_json;
        metrics_json["requests_total"] = stats.total_count;
        metrics_json["requests_by_tier"]["reflex"] = stats.reflex_count;
        metrics_json["requests_by_tier"]["rules"] = stats.rules_count;
        metrics_json["requests_by_tier"]["ml"] = stats.ml_count;
        metrics_json["requests_by_tier"]["llm"] = stats.llm_count;
        metrics_json["avg_latency_ms"] = stats.avg_latency_ms;
        
        res.set_content(metrics_json.dump(), "application/json");
        res.status = 200;
    });
    
    // Start server
    std::cout << "Server ready. Listening for requests..." << std::endl;
    if (!server.listen("127.0.0.1", 9901)) {
        std::cerr << "Failed to start server" << std::endl;
        return 1;
    }
    
    return 0;
}
