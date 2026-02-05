#pragma once
#include "../types.hpp"
#include <string>
#include <optional>

namespace openkore_ai {
namespace decision {

class LLMTier {
public:
    LLMTier(const std::string& python_service_url);
    
    // Check if LLM tier should handle this (complex situations)
    bool should_handle(const GameState& state) const;
    
    // Make LLM-based decision (30-300s)
    Action decide(const GameState& state);
    
private:
    std::string python_service_url_;
    mutable long long last_query_time_ms_ = 0;
    static constexpr long long MIN_QUERY_INTERVAL_MS = 60000;  // 1 minute between LLM queries
    
    // HTTP client for Python service
    std::optional<Action> query_python_service(const GameState& state);
    
    // Helper to convert game state to JSON
    std::string game_state_to_json(const GameState& state) const;
};

} // namespace decision
} // namespace openkore_ai
