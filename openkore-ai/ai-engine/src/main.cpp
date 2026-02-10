#include <httplib.h>
#include <nlohmann/json.hpp>
#include <iostream>
#include <memory>
#include <thread>
#include <chrono>
#include <mutex>
#include <filesystem>
#include <exception>
#ifdef _WIN32
#include <windows.h>
#endif
#include "types.hpp"
#include "decision/reflex.hpp"
#include "decision/rules.hpp"
#include "decision/ml.hpp"
#include "decision/llm.hpp"
#include "coordinators/coordinator_manager.hpp"
#include "logger.hpp"

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
        for (const auto& player_json : j["nearby_players"]) {
            Player player;
            player.name = player_json["name"];
            player.level = player_json["level"];
            player.guild = player_json.value("guild", "");
            player.distance = player_json["distance"];
            player.is_party_member = player_json.value("is_party_member", false);
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

// Helper function for early error reporting (before logger is ready)
void report_early_error(const std::string& message) {
    std::cerr << "[CRITICAL ERROR] " << message << std::endl;
#ifdef _WIN32
    MessageBoxA(NULL, message.c_str(), "AI Engine - Critical Error", MB_OK | MB_ICONERROR);
#endif
}

int main() {
    // PHASE 1: Early initialization checks (before any complex operations)
    try {
        std::cout << "[STARTUP] AI Engine starting..." << std::endl;
        std::cout << "[STARTUP] Working directory: " << std::filesystem::current_path().string() << std::endl;
        
        // Validate logs directory can be created
        std::cout << "[STARTUP] Creating logs directory..." << std::endl;
        try {
            std::filesystem::create_directories("logs");
            if (!std::filesystem::exists("logs")) {
                throw std::runtime_error("Failed to create logs directory - directory does not exist after creation");
            }
            if (!std::filesystem::is_directory("logs")) {
                throw std::runtime_error("'logs' exists but is not a directory");
            }
            std::cout << "[STARTUP] Logs directory ready: " << std::filesystem::absolute("logs").string() << std::endl;
        } catch (const std::exception& e) {
            std::string error_msg = std::string("Failed to create logs directory: ") + e.what();
            report_early_error(error_msg);
            return 1;
        }
        
        // PHASE 2: Initialize logger
        std::cout << "[STARTUP] Initializing logger..." << std::endl;
        try {
            using namespace openkore_ai::logging;
            Logger::initialize("logs");
            Logger::info("========================================");
            Logger::info("OpenKore AI Engine v1.0.0 (Phase 5)");
            Logger::info("Starting HTTP server on http://127.0.0.1:9901");
            Logger::info("Working directory: " + std::filesystem::current_path().string());
            Logger::info("========================================");
            std::cout << "[STARTUP] Logger initialized successfully" << std::endl;
        } catch (const std::exception& e) {
            std::string error_msg = std::string("Failed to initialize logger: ") + e.what();
            report_early_error(error_msg);
            return 1;
        }
        
        // PHASE 3: Create HTTP server
        using namespace openkore_ai::logging;
        std::cout << "[STARTUP] Creating HTTP server..." << std::endl;
        std::unique_ptr<httplib::Server> server;
        try {
            server = std::make_unique<httplib::Server>();
            Logger::info("HTTP server instance created");
            std::cout << "[STARTUP] HTTP server created successfully" << std::endl;
        } catch (const std::exception& e) {
            std::string error_msg = std::string("Failed to create HTTP server: ") + e.what();
            Logger::error(error_msg);
            report_early_error(error_msg);
            return 1;
        }
        
        // PHASE 4: Initialize decision tiers
        std::cout << "[STARTUP] Initializing decision tiers..." << std::endl;
        try {
            Logger::info("Initializing decision tiers...");
            
            Logger::debug("Creating ReflexTier...");
            reflex_tier = std::make_unique<decision::ReflexTier>();
            
            Logger::debug("Creating RulesTier...");
            rules_tier = std::make_unique<decision::RulesTier>();
            
            Logger::debug("Creating MLTier...");
            ml_tier = std::make_unique<decision::MLTier>();
            
            Logger::debug("Creating LLMTier...");
            llm_tier = std::make_unique<decision::LLMTier>("http://127.0.0.1:9902");
            
            Logger::info("All decision tiers initialized successfully");
            std::cout << "[STARTUP] Decision tiers initialized successfully" << std::endl;
        } catch (const std::exception& e) {
            std::string error_msg = std::string("Failed to initialize decision tiers: ") + e.what();
            Logger::error(error_msg);
            report_early_error(error_msg);
            return 1;
        }
        
        // PHASE 5: Initialize coordinator framework
        std::cout << "[STARTUP] Initializing coordinator framework..." << std::endl;
        try {
            Logger::info("Initializing coordinator framework (Phase 5)...");
            coordinator_manager = std::make_unique<coordinators::CoordinatorManager>();
            coordinator_manager->initialize();
            Logger::info("Coordinator framework initialized successfully");
            std::cout << "[STARTUP] Coordinator framework initialized successfully" << std::endl;
        } catch (const std::exception& e) {
            std::string error_msg = std::string("Failed to initialize coordinator framework: ") + e.what();
            Logger::error(error_msg);
            report_early_error(error_msg);
            return 1;
        }
    
        // PHASE 6: Register HTTP endpoints
        std::cout << "[STARTUP] Registering HTTP endpoints..." << std::endl;
        Logger::info("Registering HTTP endpoints...");
        
        // POST /api/v1/decide - Main decision endpoint
        server->Post("/api/v1/decide", [](const httplib::Request& req, httplib::Response& res) {
        using namespace openkore_ai::logging;
        auto start_time = std::chrono::steady_clock::now();
        
        try {
            // Log incoming request
            Logger::log_request("POST", "/api/v1/decide", req.body, req.body.size());
            
            json request_json = json::parse(req.body);
            GameState state = parse_game_state(request_json["game_state"]);
            std::string request_id = request_json.value("request_id", "unknown");
            
            std::ostringstream msg;
            msg << "Request " << request_id
                << " - Character: " << state.character.name
                << " (Lv " << state.character.level << ", "
                << state.character.hp << "/" << state.character.max_hp << " HP)";
            Logger::info(msg.str(), "DECIDE");
            
            // Make decision using multi-tier system
            DecisionResponse decision = make_decision(state, request_id);
            
            // Build response
            json response_json;
            response_json["action"] = action_to_json(decision.action);
            response_json["tier_used"] = tier_to_string(decision.tier_used);
            response_json["latency_ms"] = decision.latency_ms;
            response_json["request_id"] = decision.request_id;
            
            std::ostringstream resp_msg;
            resp_msg << "Response: " << decision.action.type
                     << " via " << tier_to_string(decision.tier_used)
                     << " (" << decision.latency_ms << "ms)";
            Logger::info(resp_msg.str(), "DECIDE");
            
            res.set_content(response_json.dump(), "application/json");
            res.status = 200;
            
            // Log response
            auto end_time = std::chrono::steady_clock::now();
            auto latency_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time).count();
            Logger::log_response("/api/v1/decide", 200, latency_ms, response_json.dump());
            
        } catch (const std::exception& e) {
            Logger::error(std::string("Exception: ") + e.what(), "DECIDE");
            
            json error_json;
            error_json["error"] = e.what();
            res.set_content(error_json.dump(), "application/json");
            res.status = 500;
            
            // Log error response
            auto end_time = std::chrono::steady_clock::now();
            auto latency_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time).count();
            Logger::log_response("/api/v1/decide", 500, latency_ms, error_json.dump());
        }
    });
    
        // GET /api/v1/health - Health check endpoint
        server->Get("/api/v1/health", [](const httplib::Request&, httplib::Response& res) {
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
        server->Get("/api/v1/metrics", [](const httplib::Request&, httplib::Response& res) {
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
    
        Logger::info("All HTTP endpoints registered");
        std::cout << "[STARTUP] HTTP endpoints registered successfully" << std::endl;
        
        // PHASE 7: Start server
        std::cout << "[STARTUP] Starting HTTP server on 127.0.0.1:9901..." << std::endl;
        Logger::info("========================================");
        Logger::info("Server ready. Starting listener...");
        Logger::info("Endpoint: http://127.0.0.1:9901");
        Logger::info("Logs directory: " + std::filesystem::absolute("logs").string());
        Logger::info("========================================");
        
        std::cout << "========================================" << std::endl;
        std::cout << "AI Engine is running!" << std::endl;
        std::cout << "Endpoint: http://127.0.0.1:9901" << std::endl;
        std::cout << "Press Ctrl+C to stop" << std::endl;
        std::cout << "========================================" << std::endl;
        
        if (!server->listen("127.0.0.1", 9901)) {
            std::string error_msg = "Failed to start server on port 9901 - port may be in use or access denied";
            Logger::error(error_msg);
            report_early_error(error_msg);
            Logger::cleanup();
            return 1;
        }
        
        // Server stopped
        Logger::info("Server stopped");
        Logger::cleanup();
        return 0;
        
    } catch (const std::exception& e) {
        std::string error_msg = std::string("Unhandled exception in main: ") + e.what();
        std::cerr << "[FATAL] " << error_msg << std::endl;
        report_early_error(error_msg);
        
        try {
            using namespace openkore_ai::logging;
            Logger::error(error_msg);
            Logger::cleanup();
        } catch (...) {
            // Logger might not be initialized
        }
        
        return 1;
    } catch (...) {
        std::string error_msg = "Unknown exception in main()";
        std::cerr << "[FATAL] " << error_msg << std::endl;
        report_early_error(error_msg);
        
        try {
            using namespace openkore_ai::logging;
            Logger::error(error_msg);
            Logger::cleanup();
        } catch (...) {
            // Logger might not be initialized
        }
        
        return 1;
    }
}
