#pragma once
#include "../types.hpp"
#include <string>
#include <memory>

namespace openkore_ai {
namespace coordinators {

// Coordinator priority levels
enum class Priority {
    CRITICAL = 0,   // Life-threatening situations
    HIGH = 1,       // Important tactical decisions
    MEDIUM = 2,     // Normal operations
    LOW = 3,        // Optional optimizations
    IDLE = 4        // Background tasks
};

// Base class for all coordinators
class CoordinatorBase {
public:
    CoordinatorBase(const std::string& name, Priority default_priority);
    virtual ~CoordinatorBase() = default;
    
    // Check if this coordinator should handle current state
    virtual bool should_activate(const GameState& state) const = 0;
    
    // Make decision for this coordinator's domain
    virtual Action decide(const GameState& state) = 0;
    
    // Get coordinator name
    std::string get_name() const { return name_; }
    
    // Get current priority
    Priority get_priority() const { return priority_; }
    
protected:
    std::string name_;
    Priority priority_;
    
    // Helper to create action
    Action create_action(const std::string& type, const std::string& reason, float confidence = 0.8f) const;
};

} // namespace coordinators
} // namespace openkore_ai
