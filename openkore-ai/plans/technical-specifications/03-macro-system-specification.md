# Macro System Specification

**Version:** 1.0  
**Date:** 2026-02-05  
**Status:** Final Specification

---

## Table of Contents

1. [Overview](#1-overview)
2. [Macro Template System](#2-macro-template-system)
3. [LLM Macro Generation](#3-llm-macro-generation)
4. [Hot-Reload Mechanism](#4-hot-reload-mechanism)
5. [Macro Repository](#5-macro-repository)
6. [Validation & Testing](#6-validation--testing)

---

## 1. Overview

### 1.1 Purpose

The Macro System enables:
- **Dynamic macro generation** by LLM based on game context
- **Template-based macro creation** for common patterns
- **Hot-reload** of macros without restarting OpenKore
- **Version control** and rollback capabilities
- **Performance tracking** of macro effectiveness

### 1.2 Design Goals

- **Flexible Templates**: Support variable substitution, conditionals, loops
- **LLM Integration**: Generate contextually appropriate macros
- **Zero-Downtime Reload**: Hot-swap macros during gameplay
- **Safety Validation**: Prevent infinite loops and dangerous commands
- **Performance Tracking**: Measure and optimize macro effectiveness

---

## 2. Macro Template System

### 2.1 Template Format

Templates use Handlebars-style syntax with OpenKore macro commands:

```
# Template: {{template_name}}
# Version: {{version}}
# Description: {{description}}
# Generated: {{timestamp}}

automacro {{name}} {
    {{#if location}}
    location {{location}}
    {{/if}}
    {{#each conditions}}
    {{this.type}} {{this.operator}} {{this.value}}
    {{/each}}
    call {{name}}_execute
}

macro {{name}}_execute {
    {{#each pre_actions}}
    do {{this.command}} {{this.parameters}}
    {{#if this.pause}}
    pause {{this.pause}}
    {{/if}}
    {{/each}}
    
    {{#if main_loop}}
    {{#each main_loop}}
    do {{this.command}} {{this.parameters}}
    pause {{this.pause}}
    {{/each}}
    {{/if}}
    
    {{#each post_actions}}
    do {{this.command}} {{this.parameters}}
    {{/each}}
}
```

### 2.2 Template Library

#### Combat Template

```handlebars
# Template: combat_rotation
# Purpose: Basic combat rotation with skill usage

automacro {{name}} {
    {{#if map}}
    location {{map}}
    {{/if}}
    monster {{monster_filter}}
    hp > {{hp_threshold}}
    sp > {{sp_threshold}}
    {{#if party_check}}
    aggressives {{max_aggressives}}
    {{/if}}
    call {{name}}_execute
}

macro {{name}}_execute {
    # Pre-combat buffs
    {{#each buffs}}
    do ss "{{skill}}" {{target}}
    pause {{cast_delay}}
    {{/each}}
    
    # Target selection
    do attack {{targeting_priority}}
    
    # Combat rotation
    {{#each rotation}}
    {{#if condition}}
    # Conditional: {{condition}}
    {{/if}}
    do ss "{{skill}}" {{target}}
    pause {{delay}}
    {{#if wait_for_completion}}
    do wait_for_cast
    {{/if}}
    {{/each}}
    
    # Resource management
    {{#if auto_heal}}
    do is "{{heal_item}}" if (hp% < {{heal_threshold}})
    {{/if}}
    {{#if auto_sp}}
    do is "{{sp_item}}" if (sp% < {{sp_restore_threshold}})
    {{/if}}
    
    # Loot
    {{#if auto_loot}}
    do take
    {{/if}}
}
```

#### Farming Template

```handlebars
# Template: farming_rotation
# Purpose: Efficient farming with route and resource management

automacro {{name}}_start {
    location {{map}}
    {{#if time_condition}}
    timeout {{timeout_seconds}}
    {{/if}}
    hp > {{min_hp}}
    sp > {{min_sp}}
    weight < {{max_weight}}
    call {{name}}_farm
}

macro {{name}}_farm {
    # Setup phase
    {{#if setup_required}}
    {{#each setup_actions}}
    do {{command}}
    pause {{delay}}
    {{/each}}
    {{/if}}
    
    # Movement pattern
    {{#if use_route}}
    {{#each route_points}}
    do move {{map}} {{x}} {{y}}
    pause {{move_delay}}
    {{/each}}
    {{else}}
    # Stay in area
    do conf attackAuto 2
    {{/if}}
    
    # Combat rotation
    call {{name}}_combat
    
    # Loot phase
    {{#if loot_priority}}
    {{#each loot_priority}}
    do take "{{item_name}}"
    {{/each}}
    {{else}}
    do take
    {{/if}}
    
    # Weight check
    {{#if storage_enabled}}
    do if (weight% > {{storage_threshold}}) call {{name}}_storage
    {{/if}}
    
    # Resource check
    {{#if consumable_check}}
    do if (inventory: "{{consumable}}" < {{min_amount}}) call {{name}}_restock
    {{/if}}
}

macro {{name}}_combat {
    {{#each combat_skills}}
    do ss "{{skill}}" {{target}}
    pause {{delay}}
    {{/each}}
}

macro {{name}}_storage {
    do move {{storage_map}} {{storage_x}} {{storage_y}}
    do talk {{storage_npc}}
    # Storage operations handled by other plugins
}
```

#### Party Support Template

```handlebars
# Template: party_support
# Purpose: Party healing and buffing

automacro {{name}}_heal {
    {{#each party_members}}
    party {{name}} {{hp_threshold}}
    {{/each}}
    sp > {{min_sp}}
    call {{name}}_heal_execute
}

macro {{name}}_heal_execute {
    # Priority healing
    {{#each heal_priority}}
    do if (party: "{{member}}" hp% < {{threshold}}) ss "{{heal_skill}}" "{{member}}"
    pause {{cast_delay}}
    {{/each}}
    
    # Area heal if multiple members low
    do if (party_low_hp_count > {{aoe_threshold}}) ss "{{aoe_heal}}" self
}

automacro {{name}}_buff {
    timeout {{buff_interval}}
    call {{name}}_buff_execute
}

macro {{name}}_buff_execute {
    {{#each buffs}}
    {{#if target_all}}
    # Buff all party members
    {{#each ../party_members}}
    do ss "{{../skill}}" "{{name}}"
    pause {{../cast_delay}}
    {{/each}}
    {{else}}
    do ss "{{skill}}" {{target}}
    pause {{cast_delay}}
    {{/if}}
    {{/each}}
}
```

#### Boss Fight Template

```handlebars
# Template: boss_strategy
# Purpose: Coordinated boss fight with phases

automacro {{name}}_boss {
    monster {{boss_name}}
    hp > {{min_hp}}
    sp > {{min_sp}}
    {{#if party_required}}
    party_size > {{min_party_size}}
    {{/if}}
    call {{name}}_boss_fight
}

macro {{name}}_boss_fight {
    # Pre-fight preparation
    {{#each preparations}}
    do {{command}}
    pause {{delay}}
    {{/each}}
    
    # Phase 1: Full HP
    log Boss fight started - Phase 1
    {{#each phase1_rotation}}
    do ss "{{skill}}" {{target}}
    pause {{delay}}
    {{/each}}
    
    # Emergency actions
    do if (hp% < {{emergency_hp}}) call {{name}}_emergency
    
    # Phase 2: Below 50% HP (if boss shows different pattern)
    {{#if phase2_exists}}
    # Detected by boss HP or status change
    {{#each phase2_rotation}}
    do ss "{{skill}}" {{target}}
    pause {{delay}}
    {{/each}}
    {{/if}}
    
    # Victory conditions
    log Boss defeated!
}

macro {{name}}_emergency {
    # Emergency teleport or heal
    {{#if emergency_teleport}}
    do ss "Teleport"
    {{else}}
    do is "{{emergency_item}}"
    {{/if}}
}
```

### 2.3 Template Parameter Schema

```json
{
  "template": "combat_rotation",
  "parameters": {
    "name": {
      "type": "string",
      "required": true,
      "description": "Unique macro name"
    },
    "map": {
      "type": "string",
      "required": false,
      "description": "Map restriction"
    },
    "monster_filter": {
      "type": "string",
      "required": true,
      "description": "Monster name or pattern"
    },
    "hp_threshold": {
      "type": "integer",
      "required": true,
      "default": 60,
      "min": 1,
      "max": 100,
      "description": "Minimum HP% to engage"
    },
    "sp_threshold": {
      "type": "integer",
      "required": true,
      "default": 30,
      "min": 1,
      "max": 100
    },
    "buffs": {
      "type": "array",
      "required": false,
      "items": {
        "skill": "string",
        "target": "string",
        "cast_delay": "float"
      }
    },
    "rotation": {
      "type": "array",
      "required": true,
      "items": {
        "skill": "string",
        "target": "string",
        "delay": "float",
        "condition": "string?"
      }
    }
  }
}
```

### 2.4 Template Rendering Engine

```cpp
class MacroTemplateEngine {
public:
    struct Template {
        std::string name;
        std::string content;
        json schema;
        std::vector<std::string> required_params;
    };
    
    std::string render(const Template& tmpl, const json& parameters);
    bool validate(const Template& tmpl, const json& parameters);
    
private:
    std::string evaluateExpression(const std::string& expr, const json& context);
    std::string processConditional(const std::string& block, const json& context);
    std::string processLoop(const std::string& block, const json& context);
};

// Example usage
MacroTemplateEngine engine;
auto combat_template = engine.loadTemplate("combat_rotation");

json params = {
    {"name", "wizard_farming"},
    {"map", "pay_fild04"},
    {"monster_filter", "Poring"},
    {"hp_threshold", 70},
    {"sp_threshold", 40},
    {"rotation", {
        {{"skill", "Fire Ball"}, {"target", "$target"}, {"delay", 0.5}},
        {{"skill", "Fire Wall"}, {"target", "self"}, {"delay", 1.0}}
    }}
};

std::string rendered_macro = engine.render(combat_template, params);
```

---

## 3. LLM Macro Generation

### 3.1 Prompt Engineering

#### System Prompt

```
You are an expert Ragnarok Online automation specialist. Your task is to generate OpenKore macro scripts that are:
- Syntactically correct
- Efficient and optimized
- Safe (no infinite loops)
- Contextually appropriate

You have access to:
- Current game state (character, monsters, location)
- Available skills and items
- Game mechanics knowledge
- OpenKore macro syntax

Always respond with valid macro code that can be directly executed.
```

#### Generation Prompt Template

```cpp
std::string buildMacroGenerationPrompt(const Goal& goal, const GameState& state) {
    return R"(
Generate an OpenKore macro for the following objective:

**Objective:** )" + goal.description + R"(

**Character Information:**
- Class: )" + state.character.job_class + R"(
- Level: )" + std::to_string(state.character.level) + R"(
- Location: )" + state.current_map + R"( ()" + 
    std::to_string(state.character.position.x) + "," + 
    std::to_string(state.character.position.y) + R"()
- HP: )" + std::to_string(state.character.hp) + "/" + 
    std::to_string(state.character.max_hp) + R"(
- SP: )" + std::to_string(state.character.sp) + "/" + 
    std::to_string(state.character.max_sp) + R"(

**Available Skills:**
)" + formatSkills(state.character.skills) + R"(

**Available Items:**
)" + formatInventory(state.character.inventory) + R"(

**Current Situation:**
- Nearby Monsters: )" + formatMonsters(state.monsters) + R"(
- Party Members: )" + formatParty(state.party) + R"(

**OpenKore Macro Syntax Reference:**

```
# Automacro: Defines trigger conditions
automacro myTrigger {
    hp > 50                    # HP percentage
    sp > 30                    # SP percentage
    location prontera          # Map restriction
    monster Poring             # Monster name
    aggressives 0              # Max aggressive monsters
    timeout 60                 # Execute every N seconds
    call myMacro              # Call this macro
}

# Macro: Defines execution block
macro myMacro {
    do ss "Fire Ball" $target  # Use skill on target
    pause 1.0                  # Wait 1 second
    do attack                  # Basic attack
    do move prontera 150 150   # Move to coordinates
    do is "Red Potion"        # Use item
    do take                    # Pick up items
}

# Conditionals (inline)
do if (hp% < 50) is "White Potion"

# Variables
$target                        # Current target
$map                          # Current map
@args                         # Macro arguments
```

**Requirements:**
1. Generate a complete, executable macro
2. Include appropriate automacro triggers
3. Handle resource management (HP/SP)
4. Include safety checks
5. Use appropriate pauses to prevent spam
6. Add comments for clarity

**Output Format:**
Provide only the macro code, no explanations outside code comments.
)";
}
```

### 3.2 Prompt Examples

#### Example 1: Farming Request

```
**Objective:** Farm Porings in Prontera Field for 1 hour

**LLM Output:**
```txt
# Farming Macro: Poring Farm
# Generated: 2026-02-05 16:30:00
# Duration: 1 hour

automacro poring_farm_start {
    location pay_fild04
    hp > 70
    sp > 40
    weight < 80
    timeout 5
    call poring_farm_execute
}

macro poring_farm_execute {
    # Ensure proper configuration
    do conf attackAuto 2
    do conf attackDistance 1.5
    
    # Target Poring
    do attack Poring
    
    # Wait for combat to complete
    pause 1.0
    
    # Pick up loot
    do take
    pause 0.5
    
    # Weight check
    do if (weight% > 80) call emergency_storage
}

automacro poring_farm_heal {
    hp < 70
    sp > 10
    call heal_self
}

macro heal_self {
    do is "Red Potion"
    pause 1.0
}

macro emergency_storage {
    # Move to Prontera storage
    do move prontera 150 150
    pause 2.0
    do talk storage
    log Emergency storage triggered
}
```

#### Example 2: Boss Strategy

```
**Objective:** Defeat Baphomet with party support

**LLM Output:**
```txt
# Boss Macro: Baphomet Strategy
# Generated: 2026-02-05 16:35:00
# Party-based boss fight

automacro baphomet_engage {
    monster Baphomet
    hp > 80
    sp > 60
    party_size > 3
    call baphomet_fight
}

macro baphomet_fight {
    log Engaging Baphomet - Stay coordinated!
    
    # Pre-fight buffs
    do ss "Blessing" self
    pause 1.0
    do ss "Increase AGI" self
    pause 1.0
    
    # Main DPS rotation for Wizard
    do ss "Fire Ball" Baphomet
    pause 1.5
    do ss "Fire Wall" self
    pause 2.0
    
    # Check HP
    do if (hp% < 50) call baphomet_emergency
    
    # Continue DPS
    do ss "Fire Ball" Baphomet
    pause 1.5
}

macro baphomet_emergency {
    log HP critical - teleporting!
    do ss "Teleport"
    pause 2.0
}

automacro baphomet_victory {
    monster Baphomet
    dead Baphomet
    call baphomet_loot
}

macro baphomet_loot {
    log Baphomet defeated!
    do take
    pause 2.0
}
```

### 3.3 Post-Processing & Validation

```cpp
class MacroPostProcessor {
public:
    struct ValidationResult {
        bool valid;
        std::vector<std::string> errors;
        std::vector<std::string> warnings;
        std::vector<std::string> suggestions;
    };
    
    // Validate generated macro
    ValidationResult validate(const std::string& macro_content);
    
    // Add safety guards
    std::string addSafetyChecks(const std::string& macro_content);
    
    // Optimize macro
    std::string optimize(const std::string& macro_content);
    
private:
    bool checkSyntax(const std::string& content);
    bool checkInfiniteLoops(const std::string& content);
    bool checkDangerousCommands(const std::string& content);
    bool checkPauseDistribution(const std::string& content);
};

// Safety checks to add
std::string MacroPostProcessor::addSafetyChecks(const std::string& content) {
    std::string safe_content = content;
    
    // Add timeout to automacros without one
    safe_content = addDefaultTimeouts(safe_content);
    
    // Add emergency HP checks
    safe_content = addEmergencyChecks(safe_content);
    
    // Add weight checks before storage operations
    safe_content = addWeightChecks(safe_content);
    
    // Add pause after skill usage if missing
    safe_content = addMissingPauses(safe_content);
    
    return safe_content;
}
```

### 3.4 LLM Macro Generator Implementation

```cpp
class LLMMacroGenerator {
public:
    struct GenerationRequest {
        Goal goal;
        GameState state;
        std::optional<std::string> template_hint;
        json additional_context;
    };
    
    struct GeneratedMacro {
        std::string name;
        std::string content;
        std::string description;
        float llm_confidence;
        json generation_metadata;
    };
    
    std::optional<GeneratedMacro> generate(const GenerationRequest& request);
    
private:
    std::unique_ptr<LLMClient> llm_client_;
    std::unique_ptr<MacroPostProcessor> post_processor_;
    std::unique_ptr<MacroTemplateEngine> template_engine_;
    
    std::string buildPrompt(const GenerationRequest& request);
    GeneratedMacro parseResponse(const std::string& llm_response);
};

std::optional<GeneratedMacro> LLMMacroGenerator::generate(
    const GenerationRequest& request) {
    
    // Build prompt
    std::string prompt = buildPrompt(request);
    
    // Query LLM
    LLMClient::Request llm_request{
        .prompt = prompt,
        .model = "gpt-4-turbo",
        .max_tokens = 2048,
        .temperature = 0.7
    };
    
    auto llm_response = llm_client_->query(llm_request);
    if (!llm_response || !llm_response->success) {
        log_error("LLM query failed: {}", llm_response->error);
        return std::nullopt;
    }
    
    // Parse macro from response
    auto macro = parseResponse(llm_response->content);
    
    // Validate
    auto validation = post_processor_->validate(macro.content);
    if (!validation.valid) {
        log_error("Generated macro validation failed");
        for (const auto& error : validation.errors) {
            log_error("  - {}", error);
        }
        return std::nullopt;
    }
    
    // Add safety checks
    macro.content = post_processor_->addSafetyChecks(macro.content);
    
    // Optimize
    macro.content = post_processor_->optimize(macro.content);
    
    return macro;
}
```

---

## 4. Hot-Reload Mechanism

### 4.1 File Watching

```cpp
class MacroFileWatcher {
public:
    MacroFileWatcher(const std::filesystem::path& watch_dir);
    
    void start();
    void stop();
    
    enum class FileEvent {
        CREATED,
        MODIFIED,
        DELETED
    };
    
    using ChangeCallback = std::function<void(
        const std::filesystem::path& file, FileEvent event)>;
    void setCallback(ChangeCallback callback);
    
private:
    std::filesystem::path watch_dir_;
    std::atomic<bool> running_;
    std::thread watcher_thread_;
    ChangeCallback callback_;
    
    // File modification times
    std::unordered_map<std::filesystem::path, 
                       std::filesystem::file_time_type> file_times_;
    
    void watchLoop();
    void checkForChanges();
};

void MacroFileWatcher::watchLoop() {
    while (running_) {
        try {
            checkForChanges();
        } catch (const std::exception& e) {
            log_error("File watch error: {}", e.what());
        }
        
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }
}

void MacroFileWatcher::checkForChanges() {
    for (const auto& entry : std::filesystem::directory_iterator(watch_dir_)) {
        if (entry.path().extension() != ".txt") continue;
        
        auto current_time = std::filesystem::last_write_time(entry.path());
        
        auto it = file_times_.find(entry.path());
        if (it == file_times_.end()) {
            // New file
            file_times_[entry.path()] = current_time;
            if (callback_) {
                callback_(entry.path(), FileEvent::CREATED);
            }
        } else if (it->second != current_time) {
            // Modified file
            file_times_[entry.path()] = current_time;
            if (callback_) {
                callback_(entry.path(), FileEvent::MODIFIED);
            }
        }
    }
}
```

### 4.2 Reload Handler (Perl Side)

```perl
package MacroReloader;

use strict;
use warnings;
use Globals;
use Plugins;
use Macro::Data;
use Macro::Parser;

our $watcher;
our $watch_dir = "$Plugins::current_plugin_folder/../../control/macros/generated";

sub initialize {
    message "[MacroReloader] Initializing hot-reload system\n", "plugins";
    
    # Register AI_pre hook for periodic checking
    Plugins::addHook('AI_pre', \&checkForChanges);
    
    message "[MacroReloader] Watching: $watch_dir\n", "plugins";
}

sub checkForChanges {
    # Receive notification from C++ engine via IPC
    my $message = IPCClient::receiveMessage(1);  # 1ms timeout
    
    return unless $message;
    return unless $message->{type} eq 'MACRO_RELOAD';
    
    my $macro_file = $message->{payload}{macro_file};
    message "[MacroReloader] Reloading macro: $macro_file\n", "success";
    
    reloadMacro($macro_file);
}

sub reloadMacro {
    my ($file) = @_;
    
    # Stop current macro if it's the one being reloaded
    my $current_macro = $Macro::Data::queue->[0]{macro} if $Macro::Data::queue;
    my $file_name = basename($file);
    
    my $was_running = 0;
    if ($current_macro && $current_macro eq $file_name) {
        message "[MacroReloader] Stopping current macro for reload\n";
        Macro::Runner::stop();
        $was_running = 1;
    }
    
    # Clear old macro from memory
    clearMacroFromMemory($file_name);
    
    # Parse new macro
    my $success = eval {
        Macro::Parser::parseMacroFile($file);
        return 1;
    };
    
    if ($success) {
        message "[MacroReloader] Successfully reloaded: $file\n", "success";
        
        # Restart if it was running
        if ($was_running) {
            message "[MacroReloader] Restarting macro\n";
            Macro::Runner::call($file_name);
        }
        
        # Send ACK to C++ engine
        IPCClient::sendMessage('MACRO_COMMAND_ACK', {
            success => 1,
            macro_file => $file
        });
        
    } else {
        error "[MacroReloader] Failed to reload: $file - $@\n";
        
        # Send error to C++ engine
        IPCClient::sendMessage('MACRO_COMMAND_ACK', {
            success => 0,
            macro_file => $file,
            error => $@
        });
    }
}

sub clearMacroFromMemory {
    my ($macro_name) = @_;
    
    # Remove from macro list
    delete $Macro::Data::macroList{$macro_name};
    
    # Remove automacros
    foreach my $automacro (keys %Macro::Data::automacroList) {
        if ($Macro::Data::automacroList{$automacro}{call} eq $macro_name) {
            delete $Macro::Data::automacroList{$automacro};
        }
    }
}

1;
```

### 4.3 Atomic Reload Strategy

```cpp
class MacroReloadManager {
public:
    struct ReloadResult {
        bool success;
        std::string error_message;
        std::optional<std::string> previous_version;
    };
    
    ReloadResult reloadMacro(const std::filesystem::path& file);
    bool rollbackMacro(const std::string& macro_name);
    
private:
    struct MacroBackup {
        std::string content;
        Timestamp backup_time;
    };
    
    std::unordered_map<std::string, std::deque<MacroBackup>> backup_history_;
    size_t max_backups_per_macro_ = 10;
    
    void createBackup(const std::string& macro_name, const std::string& content);
};

ReloadResult MacroReloadManager::reloadMacro(const std::filesystem::path& file) {
    // Read new macro content
    std::string new_content = readFile(file);
    
    // Validate before applying
    auto validation = validator_->validate(new_content);
    if (!validation.valid) {
        return ReloadResult{
            .success = false,
            .error_message = "Validation failed: " + validation.errors[0]
        };
    }
    
    // Create backup of current version
    std::string macro_name = file.stem().string();
    if (auto current = getCurrentMacro(macro_name)) {
        createBackup(macro_name, *current);
    }
    
    // Send reload command to Perl
    json command = {
        {"command", "reload"},
        {"macro_file", file.string()}
    };
    
    ipc_->sendMessage(MessageType::MACRO_COMMAND, command);
    
    // Wait for ACK
    auto response = ipc_->receiveMessage(5000);  // 5 second timeout
    
    if (!response || response->payload["success"] != true) {
        // Reload failed, rollback
        log_error("Macro reload failed, rolling back");
        rollbackMacro(macro_name);
        
        return ReloadResult{
            .success = false,
            .error_message = response ? 
                response->payload["error"].get<std::string>() : "Timeout"
        };
    }
    
    return ReloadResult{.success = true};
}
```

---

## 5. Macro Repository

### 5.1 Directory Structure

```
openkore-ai/control/macros/
├── generated/           # AI-generated macros
│   ├── farming_rotation_v1.txt
│   ├── farming_rotation_v2.txt
│   ├── boss_strategy_v1.txt
│   └── .metadata/      # Metadata for each macro
│       ├── farming_rotation_v1.json
│       └── farming_rotation_v2.json
├── templates/          # Template library
│   ├── combat_rotation.tmpl
│   ├── farming_pattern.tmpl
│   ├── party_support.tmpl
│   └── boss_strategy.tmpl
├── active/            # Currently active macros (symlinks)
│   └── current_farming.txt -> ../generated/farming_rotation_v2.txt
└── user/              # User-created macros
    └── custom_macro.txt
```

### 5.2 Macro Metadata

```json
{
  "macro_name": "farming_rotation_v2",
  "version": 2,
  "created_at": "2026-02-05T16:30:00Z",
  "created_by": "llm",
  "generator": "gpt-4-turbo",
  "description": "Optimized farming rotation for Poring in pay_fild04",
  "template_used": "farming_pattern",
  "parameters": {
    "monster": "Poring",
    "map": "pay_fild04",
    "hp_threshold": 70,
    "sp_threshold": 40
  },
  "performance": {
    "execution_count": 156,
    "success_count": 148,
    "failure_count": 8,
    "avg_execution_time_s": 45.2,
    "total_runtime_hours": 1.96,
    "metrics": {
      "exp_per_hour": 850000,
      "kills_per_hour": 120,
      "death_count": 0
    }
  },
  "replaced_version": "farming_rotation_v1",
  "status": "active"
}
```

### 5.3 Version Management

```cpp
class MacroVersionManager {
public:
    struct MacroVersion {
        std::string name;
        int32_t version;
        std::filesystem::path file_path;
        Timestamp created_at;
        std::string created_by;
        json metadata;
    };
    
    int32_t saveMacro(const std::string& name, const std::string& content, 
                     const json& metadata);
    std::optional<MacroVersion> getVersion(const std::string& name, int32_t version);
    std::vector<MacroVersion> getHistory(const std::string& name);
    bool activateVersion(const std::string& name, int32_t version);
    
private:
    std::filesystem::path base_path_;
    std::unordered_map<std::string, std::vector<MacroVersion>> versions_;
    
    int32_t getNextVersion(const std::string& name);
    void saveMetadata(const MacroVersion& version);
};

int32_t MacroVersionManager::saveMacro(const std::string& name, 
                                       const std::string& content,
                                       const json& metadata) {
    int32_t version = getNextVersion(name);
    
    // Generate file path
    std::filesystem::path file_path = base_path_ / "generated" / 
        (name + "_v" + std::to_string(version) + ".txt");
    
    // Write macro file
    std::ofstream file(file_path);
    file << "# Macro: " << name << " v" << version << "\n";
    file << "# Generated: " << getCurrentTimestamp() << "\n";
    file << "# " << metadata.value("description", "No description") << "\n\n";
    file << content;
    file.close();
    
    // Create version record
    MacroVersion ver{
        .name = name,
        .version = version,
        .file_path = file_path,
        .created_at = getCurrentTimestampMs(),
        .created_by = metadata.value("created_by", "unknown"),
        .metadata = metadata
    };
    
    versions_[name].push_back(ver);
    saveMetadata(ver);
    
    log_info("Saved macro: {} v{}", name, version);
    return version;
}
```

---

## 6. Validation & Testing

### 6.1 Syntax Validation

```cpp
class MacroValidator {
public:
    struct ValidationResult {
        bool valid;
        std::vector<std::string> errors;
        std::vector<std::string> warnings;
    };
    
    ValidationResult validate(const std::string& macro_content);
    
private:
    bool validateAutomacro(const std::string& block);
    bool validateMacro(const std::string& block);
    bool checkCommands(const std::vector<std::string>& commands);
    bool checkInfiniteLoops(const std::string& content);
};

ValidationResult MacroValidator::validate(const std::string& content) {
    ValidationResult result{.valid = true};
    
    // Check for automacro definitions
    std::regex automacro_regex(R"(automacro\s+(\w+)\s*\{)");
    std::smatch matches;
    
    if (!std::regex_search(content, matches, automacro_regex)) {
        result.errors.push_back("No automacro definition found");
        result.valid = false;
    }
    
    // Check for balanced braces
    int brace_count = 0;
    for (char c : content) {
        if (c == '{') brace_count++;
        else if (c == '}') brace_count--;
        
        if (brace_count < 0) {
            result.errors.push_back("Unbalanced braces");
            result.valid = false;
            break;
        }
    }
    
    if (brace_count != 0) {
        result.errors.push_back("Unmatched braces");
        result.valid = false;
    }
    
    // Check for infinite loops
    if (checkInfiniteLoops(content)) {
        result.errors.push_back("Potential infinite loop detected");
        result.valid = false;
    }
    
    // Check for required pauses
    std::regex do_command(R"(do\s+\w+)");
    std::regex pause_command(R"(pause\s+[\d.]+)");
    
    auto do_count = std::distance(
        std::sregex_iterator(content.begin(), content.end(), do_command),
        std::sregex_iterator()
    );
    
    auto pause_count = std::distance(
        std::sregex_iterator(content.begin(), content.end(), pause_command),
        std::sregex_iterator()
    );
    
    if (do_count > 5 && pause_count < do_count / 3) {
        result.warnings.push_back(
            "Consider adding more pauses to prevent command spam");
    }
    
    return result;
}
```

### 6.2 Performance Tracking

```cpp
struct MacroPerformance {
    std::string macro_name;
    uint32_t execution_count;
    uint32_t success_count;
    uint32_t failure_count;
    
    float avg_execution_time_s;
    float total_runtime_hours;
    
    struct Metrics {
        uint64_t exp_gained;
        uint32_t kills;
        uint32_t deaths;
        uint64_t zeny_gained;
    } metrics;
    
    float getSuccessRate() const {
        return execution_count > 0 ? 
            static_cast<float>(success_count) / execution_count : 0.0f;
    }
    
    float getExpPerHour() const {
        return total_runtime_hours > 0 ? 
            metrics.exp_gained / total_runtime_hours : 0.0f;
    }
};
```

---

## 7. Integration Example

### 7.1 Complete Workflow

```cpp
// C++ Engine - Generate and deploy macro
void deployMacroForGoal(const Goal& goal, const GameState& state) {
    // Step 1: Generate macro
    LLMMacroGenerator generator;
    auto request = LLMMacroGenerator::GenerationRequest{
        .goal = goal,
        .state = state
    };
    
    auto generated = generator.generate(request);
    if (!generated) {
        log_error("Failed to generate macro");
        return;
    }
    
    // Step 2: Save with versioning
    MacroVersionManager version_manager;
    int32_t version = version_manager.saveMacro(
        generated->name,
        generated->content,
        generated->generation_metadata
    );
    
    // Step 3: Activate macro
    version_manager.activateVersion(generated->name, version);
    
    // Step 4: Notify Perl to reload
    json command = {
        {"command", "execute"},
        {"macro_name", generated->name},
        {"macro_file", version_manager.getVersion(generated->name, version)->file_path}
    };
    
    ipc_->sendMessage(MessageType::MACRO_COMMAND, command);
    
    log_info("Deployed macro: {} v{}", generated->name, version);
}
```

---

**Next Document**: [ML Pipeline Specification](04-ml-pipeline-specification.md)
