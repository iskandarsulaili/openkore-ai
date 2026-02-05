# OpenKore AI System - Technical Specifications Index

**Version:** 1.1
**Date:** 2026-02-05
**Status:** Specification Phase
**Update:** Added specifications 09 and 10 for social interactions and concurrency

---

## Overview

This directory contains comprehensive technical specifications for implementing the OpenKore AI system as defined in the [Advanced AI Architecture](../advanced-ai-architecture.md).

**Total Specifications:** 10 documents covering all aspects of the system

**Version 1.1 Updates:**
- ✅ Added specification 09: Social Interaction System
- ✅ Added specification 10: Concurrency and Race Conditions
- ✅ Updated all documents with DeepSeek as primary LLM provider

## Document Structure

### 1. [IPC Protocol Specification](01-ipc-protocol-specification.md)
Complete inter-process communication protocol between Perl and C++, including:
- Message format and serialization
- Complete message catalog
- Request/Response patterns
- Error handling and status codes
- Protocol versioning

### 2. [Data Structures Reference](02-data-structures-reference.md)
All C++ data structures used throughout the system:
- Game state structures (Character, Monster, Map, etc.)
- Decision structures (Actions, Rules, Features)
- Training data structures
- Configuration schemas

### 3. [Macro System Specification](03-macro-system-specification.md)
Comprehensive macro generation and management:
- Template syntax and format
- LLM prompt engineering for generation
- Hot-reload mechanism implementation
- Validation and versioning

### 4. [ML Pipeline Specification](04-ml-pipeline-specification.md)
Complete machine learning implementation:
- Cold-start strategy phases (Days 1-30+)
- Feature engineering
- Training data collection and storage
- Model training pipeline
- Deployment and hot-swap

### 5. [Coordinator Specifications](05-coordinator-specifications.md)
Detailed specifications for all 14 coordinators:
- Combat, Economy, Navigation, NPC
- Planning, Social, Consumables, Progression
- Companions, Instances, Crafting, Environment
- Job-Specific, PvP/WoE

### 6. [Integration Guide](06-integration-guide.md)
How to integrate with existing OpenKore ecosystem:
- Plugin compatibility matrix
- Hook priorities and execution order
- Conflict resolution strategies
- State sharing mechanisms

### 7. [Configuration Reference](07-configuration-reference.md)
Complete configuration file specifications:
- Engine configuration
- Decision coordinator settings
- Reflex, Rule, ML, LLM configurations
- PDCA cycle settings
- Example configurations for common scenarios

### 8. [Game Lifecycle Autonomy](08-game-lifecycle-autonomy.md)
Complete game lifecycle automation:
- Character creation automation
- All 12 job path strategies
- Lifecycle stages (Novice → Endgame)
- Autonomous goal generation
- Quest automation framework
- Equipment progression system

### 9. [Social Interaction System](09-social-interaction-system.md) ⭐ **NEW**
Human-like social interaction management:
- Natural language chat via DeepSeek LLM
- Personality engine (8 configurable traits)
- 7 interaction categories (chat, buff, trade, duel, party, guild, other)
- Player reputation system (6 tiers)
- Context-aware decision making
- Scam detection and safety measures
- Multi-language support
- 2,000+ lines of specifications

### 10. [Concurrency and Race Conditions](10-concurrency-and-race-conditions.md) ⭐ **NEW**
Comprehensive concurrency control:
- Thread-safe HTTP REST API
- Multi-process synchronization (Perl + C++ + Python)
- SQLite WAL mode for concurrent access
- Safe macro hot-reload during execution
- ML model hot-swap during inference
- PDCA cycle mutual exclusion
- Lock hierarchies and deadlock prevention
- 9 critical race condition scenarios
- 2,500+ lines of specifications

---

## Usage Guidelines

### For Implementers
1. Read the architecture document first to understand the overall system design
2. Review these technical specifications in order
3. Use the specifications as the definitive reference during implementation
4. All code must match these specifications exactly

### For Reviewers
1. Check implementation against these specifications
2. Verify all edge cases are handled
3. Ensure performance requirements are met
4. Confirm configuration matches reference

### For Maintainers
1. Keep specifications up-to-date with implementation changes
2. Document any deviations with clear reasoning
3. Update version numbers when specifications change

---

## Critical Requirements

All implementations MUST:

1. ✅ **Be Production-Ready**: No mocks, stubs, or placeholders
2. ✅ **Be C++20 Compatible**: Use modern C++ features appropriately
3. ✅ **Be Performance-Oriented**: Meet all latency budgets
4. ✅ **Be Extensible**: Easy to add new components
5. ✅ **Work in openkore-ai/ Directory**: Not root directory
6. ✅ **Be Real Implementations**: All code must be fully functional

---

## Document Conventions

### Code Examples
- C++20 syntax used throughout
- Complete, compilable examples
- No pseudo-code unless explicitly marked

### Configuration Examples
- JSON for structured data
- YAML for rule definitions
- All examples are valid and tested

### Naming Conventions
- **C++**: `PascalCase` for classes, `snake_case` for functions/variables
- **Perl**: `camelCase` for functions, `$snake_case` for variables
- **Files**: `kebab-case.ext`

### Versioning
- Semantic versioning (MAJOR.MINOR.PATCH)
- Document version tracks specification version
- Implementation version may differ

---

## Next Steps

1. Review all specifications in order
2. Ask clarifying questions if needed
3. Begin implementation in Code mode
4. Use specifications as acceptance criteria

---

**Related Documents:**
- [Advanced AI Architecture](../advanced-ai-architecture.md) - High-level system design
- [CRITICAL-ENHANCEMENTS-PLAN.md](../CRITICAL-ENHANCEMENTS-PLAN.md) - Enhancement implementation plan
- [Implementation Plan](../implementation-plan/) - Development roadmap
- [Testing Strategy](../implementation-plan/02-testing-strategy.md) - QA approach

---

**Last Updated:** 2026-02-05
**Document Count:** 10 specifications
**Status:** ✅ Complete and ready for implementation
