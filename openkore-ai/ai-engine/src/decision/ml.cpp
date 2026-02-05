#include "../../include/decision/ml.hpp"
#include <iostream>

namespace openkore_ai {
namespace decision {

MLTier::MLTier() {
    std::cout << "[MLTier] Initialized (STUB - full implementation in Phase 6)" << std::endl;
    model_loaded_ = false;  // No model loaded yet
}

bool MLTier::should_handle(const GameState& state) const {
    // Phase 2: ML tier not yet functional
    return false;
}

Action MLTier::decide(const GameState& state) {
    if (!model_loaded_) {
        return decide_stub(state);
    }
    
    // TODO Phase 6: Implement ONNX model inference
    return decide_stub(state);
}

Action MLTier::decide_stub(const GameState& state) {
    Action action;
    action.type = "none";
    action.reason = "ML: Not implemented yet (Phase 2 stub)";
    action.confidence = 0.1f;
    return action;
}

} // namespace decision
} // namespace openkore_ai
