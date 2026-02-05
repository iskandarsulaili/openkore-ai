#pragma once
#include "../types.hpp"
#include <nlohmann/json.hpp>

namespace openkore_ai {
namespace decision {

class MLTier {
public:
    MLTier();
    
    // Check if ML tier is available and should handle this
    bool should_handle(const GameState& state) const;
    
    // Make ML-based decision (<100ms)
    // Phase 6: Full implementation with Python service integration
    Action decide(const GameState& state);
    
private:
    bool model_loaded_ = false;
    
    // Phase 6: ML service integration
    Action query_ml_service(const GameState& state);
    nlohmann::json state_to_json(const GameState& state) const;
    
    // Stub helper
    Action decide_stub(const GameState& state);
};

} // namespace decision
} // namespace openkore_ai
