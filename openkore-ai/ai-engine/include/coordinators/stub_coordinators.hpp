#pragma once
#include "coordinator_base.hpp"

// This file contains stub coordinators for Phase 5
// These will be fully implemented in later phases

namespace openkore_ai {
namespace coordinators {

// Companions Coordinator - Homunculus, mercenary, pet management
class CompanionsCoordinator : public CoordinatorBase {
public:
    CompanionsCoordinator();
    bool should_activate(const GameState& state) const override;
    Action decide(const GameState& state) override;
};

// Instances Coordinator - Dungeon runs, instance coordination
class InstancesCoordinator : public CoordinatorBase {
public:
    InstancesCoordinator();
    bool should_activate(const GameState& state) const override;
    Action decide(const GameState& state) override;
};

// Crafting Coordinator - Item crafting, refining, enchanting
class CraftingCoordinator : public CoordinatorBase {
public:
    CraftingCoordinator();
    bool should_activate(const GameState& state) const override;
    Action decide(const GameState& state) override;
};

// Environment Coordinator - Day/night cycles, weather, events
class EnvironmentCoordinator : public CoordinatorBase {
public:
    EnvironmentCoordinator();
    bool should_activate(const GameState& state) const override;
    Action decide(const GameState& state) override;
};

// Job-Specific Coordinator - Class-specific tactics and rotations
class JobSpecificCoordinator : public CoordinatorBase {
public:
    JobSpecificCoordinator();
    bool should_activate(const GameState& state) const override;
    Action decide(const GameState& state) override;
};

// PvP/WoE Coordinator - PvP combat, War of Emperium strategy
class PvPWoECoordinator : public CoordinatorBase {
public:
    PvPWoECoordinator();
    bool should_activate(const GameState& state) const override;
    Action decide(const GameState& state) override;
};

} // namespace coordinators
} // namespace openkore_ai
