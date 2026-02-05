#include "../../include/coordinators/coordinator_base.hpp"

namespace openkore_ai {
namespace coordinators {

CoordinatorBase::CoordinatorBase(const std::string& name, Priority default_priority)
    : name_(name), priority_(default_priority) {
}

Action CoordinatorBase::create_action(const std::string& type, const std::string& reason, float confidence) const {
    Action action;
    action.type = type;
    action.reason = name_ + ": " + reason;
    action.confidence = confidence;
    return action;
}

} // namespace coordinators
} // namespace openkore_ai
