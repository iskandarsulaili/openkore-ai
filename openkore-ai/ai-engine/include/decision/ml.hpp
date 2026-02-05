#pragma once
#include "../types.hpp"

namespace openkore_ai {
namespace decision {

class MLTier {
public:
    MLTier();
    
    // Check if ML tier is available and should handle this
    bool should_handle(const GameState& state) const;
    
    // Make ML-based decision (<100ms)
    // Phase 2: STUB - will be fully implemented in Phase 6
    Action decide(const GameState& state);
    
private:
    bool model_loaded_ = false;
    
    // Stub helper
    Action decide_stub(const GameState& state);
};

} // namespace decision
} // namespace openkore_ai
