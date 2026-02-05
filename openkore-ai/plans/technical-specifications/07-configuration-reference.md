# Configuration Reference

**Version:** 1.0  
**Date:** 2026-02-05  
**Status:** Final Specification

---

## Table of Contents

1. [Overview](#1-overview)
2. [Engine Configuration](#2-engine-configuration)
3. [Decision Coordinator Configuration](#3-decision-coordinator-configuration)
4. [LLM Configuration](#4-llm-configuration)
5. [ML Configuration](#5-ml-configuration)
6. [PDCA Configuration](#6-pdca-configuration)
7. [Coordinator Configurations](#7-coordinator-configurations)
8. [Example Configurations](#8-example-configurations)

---

## 1. Overview

### 1.1 Configuration Files

```
openkore-ai/config/
├── engine.json              # Main engine configuration
├── coordinator.json         # Decision coordinator settings
├── llm_config.json         # LLM provider configuration
├── ml_config.json          # Machine learning settings
├── pdca_config.json        # PDCA cycle configuration
├── reflexes.json           # Reflex engine rules
└── rules/                  # Rule engine configurations
    ├── combat_rules.yaml
    ├── resource_rules.yaml
    ├── navigation_rules.yaml
    └── social_rules.yaml
```

### 1.2 Configuration Loading Order

1. Load default configurations (hardcoded)
2. Load configuration files
3. Apply environment variables
4. Apply command-line overrides

---

## 2. Engine Configuration

### 2.1 Complete engine.json

```json
{
  "engine": {
    "name": "OpenKore Advanced AI Engine",
    "version": "1.0.0",
    "log_level": "info",
    "log_file": "data/logs/engine.log",
    "log_rotation": {
      "enabled": true,
      "max_size_mb": 100,
      "max_files": 5
    }
  },
  
  "ipc": {
    "type": "named_pipe",
    "pipe_name": "\\\\.\\pipe\\openkore_ai",
    "timeout_ms": 100,
    "buffer_size": 65536,
    "authentication_required": true,
    "shared_secret_env": "OPENKORE_AI_SECRET"
  },
  
  "performance": {
    "max_threads": 4,
    "state_update_interval_ms": 50,
    "metrics_interval_ms": 1000,
    "memory_limit_mb": 512
  },
  
  "features": {
    "reflex_engine": true,
    "rule_engine": true,
    "ml_engine": true,
    "llm_integration": true,
    "pdca_cycle": true,
    "hot_reload": true
  },
  
  "paths": {
    "config_dir": "config",
    "data_dir": "data",
    "models_dir": "models",
    "macros_dir": "control/macros",
    "logs_dir": "data/logs"
  }
}
```

### 2.2 Environment Variables

```bash
# Required
export OPENAI_API_KEY="sk-..."
export OPENKORE_AI_SECRET="your-secret-here"

# Optional
export ANTHROPIC_API_KEY="sk-ant-..."
export DEEPSEEK_API_KEY="..."
export AI_LOG_LEVEL="debug"
export AI_ENGINE_THREADS="4"
```

---

## 3. Decision Coordinator Configuration

### 3.1 Complete coordinator.json

```json
{
  "decision_coordinator": {
    "escalation_policy": "adaptive",
    "default_priority": "normal",
    
    "tier_timeouts_ms": {
      "reflex": 1,
      "rule": 10,
      "ml": 100,
      "llm": 5000
    },
    
    "confidence_thresholds": {
      "reflex": 1.0,
      "rule": 0.75,
      "ml": 0.70,
      "llm": 0.85
    },
    
    "escalation_rules": {
      "emergency": "reflex_only",
      "combat": "ml_preferred",
      "planning": "llm_preferred",
      "routine": "rule_preferred"
    },
    
    "fallback": {
      "enabled": true,
      "strategy": "rule_based",
      "timeout_action": "safe_behavior"
    },
    
    "metrics": {
      "enabled": true,
      "detailed_logging": false,
      "performance_tracking": true
    }
  }
}
```

---

## 4. LLM Configuration

### 4.1 Complete llm_config.json

```json
{
  "llm": {
    "enabled": true,
    "default_provider": "openai",
    
    "providers": [
      {
        "name": "openai",
        "priority": 1,
        "enabled": true,
        "model": "gpt-4-turbo-preview",
        "api_key_env": "OPENAI_API_KEY",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "parameters": {
          "max_tokens": 4096,
          "temperature": 0.7,
          "top_p": 0.9,
          "frequency_penalty": 0.0,
          "presence_penalty": 0.0
        },
        "timeout_seconds": 10,
        "retry": {
          "max_attempts": 3,
          "initial_delay_ms": 1000,
          "backoff_multiplier": 2.0
        }
      },
      {
        "name": "anthropic",
        "priority": 2,
        "enabled": false,
        "model": "claude-3-opus-20240229",
        "api_key_env": "ANTHROPIC_API_KEY",
        "endpoint": "https://api.anthropic.com/v1/messages",
        "parameters": {
          "max_tokens": 4096,
          "temperature": 0.7
        },
        "timeout_seconds": 10,
        "retry": {
          "max_attempts": 3,
          "initial_delay_ms": 1000,
          "backoff_multiplier": 2.0
        }
      },
      {
        "name": "deepseek",
        "priority": 3,
        "enabled": false,
        "model": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "parameters": {
          "max_tokens": 4096,
          "temperature": 0.7
        },
        "timeout_seconds": 15,
        "retry": {
          "max_attempts": 2,
          "initial_delay_ms": 1000,
          "backoff_multiplier": 2.0
        }
      }
    ],
    
    "rate_limiting": {
      "enabled": true,
      "requests_per_minute": 60,
      "tokens_per_minute": 90000,
      "burst_allowance": 10
    },
    
    "caching": {
      "enabled": true,
      "ttl_minutes": 30,
      "max_entries": 1000,
      "cache_strategy": "lru"
    },
    
    "cost_tracking": {
      "enabled": true,
      "budget_usd_per_day": 10.0,
      "alert_threshold": 0.8,
      "auto_disable_on_budget": true
    },
    
    "prompts": {
      "system_prompt": "You are an expert Ragnarok Online automation specialist...",
      "use_few_shot": true,
      "max_context_length": 8000
    }
  }
}
```

---

## 5. ML Configuration

### 5.1 Complete ml_config.json

```json
{
  "ml_engine": {
    "enabled": true,
    "cold_start_mode": true,
    
    "cold_start": {
      "phase": 1,
      "duration_days": 7,
      "auto_transition": true,
      "criteria": {
        "min_samples": 10000,
        "min_accuracy": 0.75,
        "min_runtime_hours": 24
      }
    },
    
    "models": [
      {
        "id": "decision_tree_v1",
        "type": "decision_tree",
        "enabled": true,
        "phases": [2],
        "model_path": "models/active/decision_tree_v1.onnx",
        "confidence_threshold": 0.85,
        "weight": 1.0
      },
      {
        "id": "random_forest_v1",
        "type": "random_forest",
        "enabled": true,
        "phases": [3, 4],
        "model_path": "models/active/random_forest_v1.onnx",
        "confidence_threshold": 0.75,
        "weight": 1.5
      },
      {
        "id": "xgboost_v1",
        "type": "gradient_boost",
        "enabled": true,
        "phases": [3, 4],
        "model_path": "models/active/xgboost_v1.onnx",
        "confidence_threshold": 0.70,
        "weight": 2.0
      }
    ],
    
    "ensemble": {
      "enabled": true,
      "voting": "weighted",
      "min_agreement": 0.6
    },
    
    "training": {
      "online_learning": {
        "enabled": true,
        "batch_size": 1000,
        "learning_rate": 0.01,
        "buffer_size": 10000
      },
      "offline_training": {
        "enabled": true,
        "schedule": "daily",
        "time": "03:00",
        "min_samples": 5000
      },
      "validation": {
        "split": 0.2,
        "cross_validation": true,
        "k_folds": 5
      }
    },
    
    "feature_engineering": {
      "normalization": "z_score",
      "feature_selection": true,
      "top_k_features": 20
    },
    
    "deployment": {
      "hot_swap": true,
      "validation_required": true,
      "rollback_on_failure": true,
      "a_b_testing": {
        "enabled": false,
        "traffic_split": 0.5
      }
    }
  }
}
```

---

## 6. PDCA Configuration

### 6.1 Complete pdca_config.json

```json
{
  "pdca_cycle": {
    "enabled": true,
    
    "triggers": {
      "continuous": {
        "enabled": true,
        "interval_seconds": 300
      },
      "goal_based": {
        "enabled": true,
        "on_completion": true,
        "on_failure": true
      },
      "performance_threshold": {
        "enabled": true,
        "metrics": {
          "death_count": {
            "threshold": 3,
            "window_minutes": 30
          },
          "exp_per_hour_drop": {
            "threshold_percent": 20,
            "window_minutes": 15
          },
          "ml_accuracy_drop": {
            "threshold_percent": 10,
            "window_minutes": 60
          }
        }
      },
      "manual": {
        "enabled": true,
        "command": "ai pdca"
      }
    },
    
    "plan_phase": {
      "use_llm": true,
      "analysis_depth": "detailed",
      "consider_history": true,
      "history_window_hours": 24
    },
    
    "do_phase": {
      "macro_generation": true,
      "auto_deploy": true,
      "backup_previous": true
    },
    
    "check_phase": {
      "metrics_collection": true,
      "success_criteria": {
        "exp_per_hour": {
          "enabled": true,
          "target": 1000000,
          "tolerance": 0.2
        },
        "death_rate": {
          "enabled": true,
          "max_per_hour": 1
        },
        "uptime": {
          "enabled": true,
          "min_percent": 90
        }
      },
      "evaluation_period_minutes": 60
    },
    
    "act_phase": {
      "auto_adjust": true,
      "adjustment_strategies": [
        "parameter_tuning",
        "macro_regeneration",
        "strategy_change"
      ],
      "max_iterations": 3,
      "give_up_threshold": 0.5
    }
  }
}
```

---

## 7. Coordinator Configurations

### 7.1 Combat Coordinator

```yaml
# config/rules/combat_rules.yaml
combat:
  targeting:
    priority: threat_based
    strategies:
      - name: attack_aggressive_first
        weight: 1.5
      - name: finish_low_hp
        weight: 1.2
      - name: focus_current_target
        weight: 1.0
    
  skills:
    rotation_mode: adaptive
    sp_conservation: 0.3
    aoe_threshold: 3
    skill_priorities:
      - Fire Ball: 1.0
      - Fire Wall: 0.8
      - Thunder Storm: 0.9
    
  positioning:
    maintain_distance: true
    optimal_ranges:
      melee: 2.0
      ranged: 10.0
    flee_threshold: 8
    
  emergency:
    teleport_hp: 20
    teleport_monsters: 8
    emergency_heal_hp: 30
```

### 7.2 Economy Coordinator

```yaml
# config/rules/economy_rules.yaml
economy:
  looting:
    auto_loot: true
    max_distance: 15
    priority_items:
      - quest_items
      - rare_drops
      - high_value
      - consumables
    
  inventory_management:
    weight_thresholds:
      storage: 80
      sell: 85
      emergency: 95
    
    auto_storage: true
    storage_npc: "Kafra Employee"
    
  selling:
    auto_sell_junk: true
    min_item_value: 1000
    keep_types:
      - consumables
      - equipment_upgrades
      - quest_items
```

---

## 8. Example Configurations

### 8.1 Leveling Configuration

```json
{
  "scenario": "leveling",
  "description": "Optimized for fast leveling",
  
  "coordinator": {
    "escalation_policy": "ml_preferred",
    "confidence_thresholds": {
      "ml": 0.65
    }
  },
  
  "combat": {
    "targeting": "exp_optimal",
    "skills": {
      "sp_conservation": 0.4,
      "aoe_threshold": 2
    }
  },
  
  "pdca": {
    "triggers": {
      "continuous": {
        "interval_seconds": 600
      }
    },
    "check_phase": {
      "success_criteria": {
        "exp_per_hour": {
          "target": 2000000
        }
      }
    }
  }
}
```

### 8.2 Farming Configuration

```json
{
  "scenario": "farming",
  "description": "Optimized for item/zeny farming",
  
  "combat": {
    "targeting": "item_drop_optimal",
    "skills": {
      "sp_conservation": 0.5
    }
  },
  
  "economy": {
    "looting": {
      "priority_items": ["high_value", "rare_drops"],
      "auto_loot": true
    },
    "inventory_management": {
      "weight_thresholds": {
        "storage": 75
      }
    }
  },
  
  "pdca": {
    "check_phase": {
      "success_criteria": {
        "zeny_per_hour": {
          "target": 500000
        }
      }
    }
  }
}
```

### 8.3 Party Support Configuration

```json
{
  "scenario": "party_support",
  "description": "Optimized for party healing/buffing",
  
  "combat": {
    "targeting": "party_support",
    "skills": {
      "priority": "healing"
    }
  },
  
  "social": {
    "party": {
      "auto_join": true,
      "healing_threshold": 70,
      "buff_interval": 60
    }
  }
}
```

### 8.4 MVP Hunting Configuration

```json
{
  "scenario": "mvp_hunting",
  "description": "Optimized for boss/MVP hunting",
  
  "combat": {
    "targeting": "boss_priority",
    "skills": {
      "rotation_mode": "boss_optimized",
      "sp_conservation": 0.2
    },
    "emergency": {
      "teleport_hp": 30,
      "emergency_heal_hp": 50
    }
  },
  
  "llm": {
    "enabled": true,
    "use_for_strategy": true
  }
}
```

---

## 9. Configuration Best Practices

### 9.1 Performance Tuning

**For Low-End Systems**:
```json
{
  "performance": {
    "max_threads": 2,
    "state_update_interval_ms": 100
  },
  "ml_engine": {
    "enabled": false
  },
  "llm": {
    "caching": {
      "enabled": true,
      "max_entries": 500
    }
  }
}
```

**For High-End Systems**:
```json
{
  "performance": {
    "max_threads": 8,
    "state_update_interval_ms": 25
  },
  "ml_engine": {
    "ensemble": {
      "enabled": true
    }
  }
}
```

### 9.2 Cost Optimization

```json
{
  "llm": {
    "caching": {
      "enabled": true,
      "ttl_minutes": 60
    },
    "cost_tracking": {
      "budget_usd_per_day": 5.0
    },
    "rate_limiting": {
      "requests_per_minute": 30
    }
  },
  "coordinator": {
    "escalation_policy": "ml_preferred"
  }
}
```

### 9.3 Safety Configuration

```json
{
  "combat": {
    "emergency": {
      "teleport_hp": 30,
      "teleport_monsters": 5
    }
  },
  "fallback": {
    "enabled": true,
    "strategy": "safe_behavior"
  },
  "pdca": {
    "triggers": {
      "performance_threshold": {
        "metrics": {
          "death_count": {
            "threshold": 2,
            "window_minutes": 30
          }
        }
      }
    }
  }
}
```

---

## 10. Configuration Validation

### 10.1 Validation Tool

```cpp
class ConfigValidator {
public:
    struct ValidationResult {
        bool valid;
        std::vector<std::string> errors;
        std::vector<std::string> warnings;
    };
    
    ValidationResult validate(const json& config);
    
private:
    bool validateSchema(const json& config);
    bool validateValues(const json& config);
    bool validateDependencies(const json& config);
};
```

### 10.2 Common Validation Errors

```
ERROR: ml_config.json: confidence_threshold must be between 0.0 and 1.0
ERROR: engine.json: ipc.timeout_ms must be positive
WARNING: llm_config.json: No API key configured for primary provider
WARNING: coordinator.json: Very low confidence thresholds may reduce quality
```

---

## 11. Dynamic Configuration Updates

### 11.1 Runtime Configuration Changes

```cpp
// C++ API
void updateConfigurationRuntime(const std::string& path, const json& value) {
    config_manager_->set(path, value);
    
    // Notify affected components
    if (path.starts_with("ml_engine")) {
        ml_engine_->reloadConfig();
    } else if (path.starts_with("llm")) {
        llm_client_->reloadConfig();
    }
    
    log_info("Configuration updated: {}", path);
}
```

```perl
# Perl API
sub updateConfig {
    my ($key, $value) = @_;
    
    IPCClient::sendMessage('CONFIG_UPDATE', {
        key => $key,
        value => $value
    });
}

# Usage
Commands::register(['ai_config', 'Set AI configuration', \&cmdAIConfig]);

sub cmdAIConfig {
    my (undef, $args) = @_;
    my ($key, $value) = split / /, $args, 2;
    
    updateConfig($key, $value);
    message "Configuration updated: $key = $value\n";
}
```

---

**Configuration Complete**

All configuration files are production-ready with sensible defaults and comprehensive options for customization.
