# Configuration Reference

**Version:** 2.1
**Date:** 2026-02-05
**Status:** Final Specification
**Update:** DeepSeek as default LLM provider, social interaction config, concurrency settings

---

## Table of Contents

1. [Overview](#1-overview)
2. [Engine Configuration](#2-engine-configuration)
3. [HTTP REST API Configuration](#3-http-rest-api-configuration)
4. [Python Service Configuration](#4-python-service-configuration)
5. [Decision Coordinator Configuration](#5-decision-coordinator-configuration)
6. [LLM Configuration](#6-llm-configuration)
7. [ML Configuration](#7-ml-configuration)
8. [PDCA Configuration](#8-pdca-configuration)
9. [OpenMemory SDK Configuration](#9-openmemory-sdk-configuration)
10. [CrewAI Configuration](#10-crewai-configuration)
11. [Game Lifecycle Configuration](#11-game-lifecycle-configuration)
12. [Coordinator Configurations](#12-coordinator-configurations)
13. [Example Configurations](#13-example-configurations)

---

## 1. Overview

### 1.1 Configuration Files

```
openkore-ai/config/
├── engine.json              # Main engine configuration
├── http_api.json           # HTTP REST API settings
├── python_service.json     # Python AI service configuration
├── coordinator.json         # Decision coordinator settings
├── llm_config.json         # LLM provider configuration (updated timeouts)
├── ml_config.json          # Machine learning settings
├── pdca_config.json        # PDCA cycle configuration
├── openmemory_config.json  # OpenMemory SDK settings
├── crewai_config.json      # CrewAI agent configuration
├── lifecycle_autonomy.yaml # Game lifecycle automation
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
  
  "communication": {
    "type": "http_rest",
    "http_server": {
      "host": "127.0.0.1",
      "port": 9901,
      "enable_ssl": false,
      "ssl_cert": "",
      "ssl_key": ""
    },
    "timeout_ms": 10000,
    "authentication_required": true,
    "token_secret_env": "OPENKORE_AI_TOKEN",
    "rate_limit_per_second": 100
  },
  
  "python_service": {
    "enabled": true,
    "url": "http://localhost:9902",
    "health_check_interval_seconds": 30,
    "timeout_seconds": 120,
    "retry_attempts": 3
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
export DEEPSEEK_API_KEY="sk-deepseek-xxxxx"
export OPENKORE_AI_TOKEN="your-secret-token-here"

# Optional (fallbacks)
export OPENAI_API_KEY="sk-openai-xxxxx"
export ANTHROPIC_API_KEY="sk-ant-xxxxx"

# Service configuration
export AI_LOG_LEVEL="debug"
export AI_ENGINE_THREADS="4"
export PYTHON_SERVICE_URL="http://localhost:9902"
export LLM_PRIMARY_PROVIDER="deepseek"
```

---

## 3. HTTP REST API Configuration

### 3.1 Complete http_api.json

```json
{
  "http_server": {
    "host": "127.0.0.1",
    "port": 9901,
    "enable_ssl": false,
    "ssl_cert_path": "certs/server.crt",
    "ssl_key_path": "certs/server.key",
    "max_connections": 100,
    "keep_alive": true,
    "keep_alive_timeout_seconds": 60
  },
  
  "authentication": {
    "enabled": true,
    "token_secret_env": "OPENKORE_AI_TOKEN",
    "token_expiry_hours": 24,
    "require_https": false
  },
  
  "rate_limiting": {
    "enabled": true,
    "requests_per_second": 100,
    "burst_size": 150,
    "per_client": true
  },
  
  "cors": {
    "enabled": false,
    "allowed_origins": ["http://localhost:3000"],
    "allowed_methods": ["GET", "POST"],
    "allowed_headers": ["Content-Type", "Authorization"]
  },
  
  "timeouts": {
    "handshake_ms": 5000,
    "state_update_ms": 10000,
    "macro_execute_ms": 30000,
    "llm_simple_ms": 30000,
    "llm_strategic_ms": 300000,
    "health_check_ms": 5000
  },
  
  "compression": {
    "enabled": true,
    "min_size_bytes": 1024,
    "algorithms": ["gzip", "deflate"]
  },
  
  "logging": {
    "log_requests": true,
    "log_responses": false,
    "log_errors": true,
    "log_file": "data/logs/http_api.log"
  },
  
  "monitoring": {
    "metrics_enabled": true,
    "health_endpoint": "/api/v1/health",
    "metrics_endpoint": "/api/v1/metrics",
    "prometheus_export": false
  }
}
```

### 3.2 WebSocket Configuration

```json
{
  "websocket": {
    "enabled": true,
    "path": "/ws/state-stream",
    "max_connections": 10,
    "ping_interval_seconds": 30,
    "timeout_seconds": 60,
    "buffer_size_kb": 64
  }
}
```

---

## 4. Python Service Configuration

### 4.1 Complete python_service.json

```json
{
  "python_service": {
    "enabled": true,
    "url": "http://localhost:9902",
    "startup": {
      "auto_start": true,
      "command": "python -m uvicorn main:app --host 127.0.0.1 --port 9902",
      "working_directory": "python-service",
      "startup_timeout_seconds": 30
    },
    
    "health_check": {
      "enabled": true,
      "interval_seconds": 30,
      "timeout_seconds": 5,
      "retry_attempts": 3,
      "endpoint": "/api/health"
    },
    
    "timeouts": {
      "memory_store_ms": 5000,
      "memory_retrieve_ms": 20000,
      "crew_execute_simple_ms": 60000,
      "crew_execute_complex_ms": 300000
    },
    
    "retry": {
      "enabled": true,
      "max_attempts": 3,
      "backoff_multiplier": 2,
      "max_backoff_seconds": 10
    },
    
    "fallback": {
      "on_failure": "use_cache",
      "cache_ttl_seconds": 300
    }
  },
  
  "database": {
    "path": "data/openkore_ai.db",
    "backup": {
      "enabled": true,
      "interval_hours": 24,
      "max_backups": 7,
      "backup_directory": "data/backups"
    }
  }
}
```

### 4.2 Python Service Environment

```bash
# Python service environment variables
export PYTHON_SERVICE_PORT=9902
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export SQLITE_DB_PATH="data/openkore_ai.db"
export LOG_LEVEL="INFO"
```

---

## 5. Decision Coordinator Configuration

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
      "llm_simple": 30000,
      "llm_strategic": 300000
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

## 6. LLM Configuration

### 6.1 Complete llm_config.json (Updated Timeouts)

```json
{
  "llm": {
    "enabled": true,
    "default_provider": "deepseek",
    
    "providers": [
      {
        "name": "deepseek",
        "priority": 1,
        "enabled": true,
        "model": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "parameters": {
          "max_tokens": 4096,
          "temperature": 0.7,
          "top_p": 0.95,
          "frequency_penalty": 0.0,
          "presence_penalty": 0.0
        },
        "timeout_seconds": 30,
        "retry": {
          "max_attempts": 3,
          "initial_delay_ms": 1000,
          "backoff_multiplier": 2.0
        },
        "cost_per_1m_tokens": {
          "input": 0.14,
          "output": 0.28,
          "currency": "USD"
        }
      },
      {
        "name": "openai",
        "priority": 2,
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
        "timeout_seconds": 30,
        "retry": {
          "max_attempts": 2,
          "initial_delay_ms": 1000,
          "backoff_multiplier": 2.0
        },
        "cost_per_1m_tokens": {
          "input": 10.00,
          "output": 30.00,
          "currency": "USD"
        }
      },
      {
        "name": "anthropic",
        "priority": 3,
        "enabled": false,
        "model": "claude-3-opus-20240229",
        "api_key_env": "ANTHROPIC_API_KEY",
        "endpoint": "https://api.anthropic.com/v1/messages",
        "parameters": {
          "max_tokens": 4096,
          "temperature": 0.7
        },
        "timeout_seconds": 30,
        "retry": {
          "max_attempts": 2,
          "initial_delay_ms": 1000,
          "backoff_multiplier": 2.0
        },
        "cost_per_1m_tokens": {
          "input": 15.00,
          "output": 75.00,
          "currency": "USD"
        }
      }
    ],
    
    "fallback_strategy": {
      "enabled": true,
      "on_primary_failure": "use_next_priority",
      "on_all_failure": "use_cache_or_rule_engine"
    },
    
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
      "budget_usd_per_day": 1.0,
      "alert_threshold": 0.8,
      "auto_disable_on_budget": true,
      "estimated_monthly_cost_usd": 4.20
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

## 7. ML Configuration

(Keep existing ML configuration as is - renumbered from 5 to 7)

---

## 8. PDCA Configuration

(Keep existing PDCA configuration as is - renumbered from 6 to 8)

---

## 9. OpenMemory SDK Configuration

### 9.1 Complete openmemory_config.json

```json
{
  "openmemory": {
    "enabled": true,
    "embedding_model": "synthetic",
    "embedding_dimension": 384,
    "similarity_threshold": 0.75,
    "max_memories": 10000,
    
    "memory_types": {
      "episodic": {
        "enabled": true,
        "retention_days": 90,
        "importance_threshold": 0.3,
        "max_per_session": 1000
      },
      "semantic": {
        "enabled": true,
        "retention_days": 365,
        "importance_threshold": 0.5,
        "consolidation_enabled": true
      },
      "procedural": {
        "enabled": true,
        "retention_days": 180,
        "update_on_use": true,
        "success_rate_tracking": true
      }
    },
    
    "consolidation": {
      "enabled": true,
      "interval_hours": 24,
      "similarity_threshold": 0.90,
      "merge_strategy": "weighted_average"
    },
    
    "decay": {
      "enabled": true,
      "decay_factor": 0.995,
      "min_importance": 0.1
    },
    
    "retrieval": {
      "default_top_k": 5,
      "max_top_k": 20,
      "use_time_weighting": true,
      "use_importance_weighting": true
    }
  },
  
  "synthetic_embeddings": {
    "method": "tfidf",
    "vocabulary_size": 10000,
    "min_df": 2,
    "max_df": 0.95,
    "use_idf": true,
    "smooth_idf": true,
    "sublinear_tf": true
  }
}
```

### 9.2 Memory Storage Settings

```json
{
  "storage": {
    "database_path": "data/openkore_ai.db",
    "batch_insert_size": 100,
    "auto_commit_interval_seconds": 30,
    "vacuum_interval_days": 7,
    
    "performance": {
      "wal_mode": true,
      "cache_size_mb": 50,
      "page_size": 4096,
      "journal_mode": "WAL"
    }
  }
}
```

---

## 10. CrewAI Configuration

### 10.1 Complete crewai_config.json

```json
{
  "crewai": {
    "enabled": true,
    "default_process": "sequential",
    "verbose": true,
    
    "llm_config": {
      "provider": "openai",
      "model": "gpt-4",
      "temperature": 0.7,
      "max_tokens": 2000,
      "timeout_seconds": 120
    },
    
    "agents": {
      "strategic_planner": {
        "enabled": true,
        "role": "Strategic Planner",
        "goal": "Develop long-term character progression strategies",
        "backstory": "Expert at Ragnarok Online meta-game and optimization",
        "allow_delegation": false,
        "max_iter": 15,
        "max_rpm": 10
      },
      
      "combat_tactician": {
        "enabled": true,
        "role": "Combat Tactician",
        "goal": "Optimize combat strategies and skill rotations",
        "backstory": "Specialist in combat mechanics and enemy AI patterns",
        "allow_delegation": false,
        "max_iter": 10,
        "max_rpm": 15
      },
      
      "resource_manager": {
        "enabled": true,
        "role": "Resource Manager",
        "goal": "Manage inventory, zeny, and consumables efficiently",
        "backstory": "Expert at economic optimization and resource allocation",
        "allow_delegation": false,
        "max_iter": 10,
        "max_rpm": 15
      },
      
      "performance_analyst": {
        "enabled": true,
        "role": "Performance Analyst",
        "goal": "Analyze performance metrics and identify improvements",
        "backstory": "Data analyst specializing in game performance optimization",
        "allow_delegation": false,
        "max_iter": 8,
        "max_rpm": 10
      }
    },
    
    "task_types": {
      "strategic": {
        "agents": ["strategic_planner", "combat_tactician", "resource_manager"],
        "process": "sequential",
        "timeout_seconds": 180
      },
      "tactical": {
        "agents": ["combat_tactician"],
        "process": "sequential",
        "timeout_seconds": 60
      },
      "economic": {
        "agents": ["resource_manager"],
        "process": "sequential",
        "timeout_seconds": 60
      },
      "analysis": {
        "agents": ["performance_analyst"],
        "process": "sequential",
        "timeout_seconds": 120
      }
    },
    
    "decision_threshold": {
      "use_crew_if_complexity": "high",
      "use_crew_if_time_horizon_hours": 5,
      "use_crew_if_cost_exceeds": 1000000,
      "always_use_for": ["character_build", "strategic_planning"]
    }
  }
}
```

### 10.2 Agent Interaction Patterns

```json
{
  "interaction_patterns": {
    "collaboration": {
      "share_context": true,
      "sequential_handoff": true,
      "validate_results": true
    },
    
    "conflict_resolution": {
      "strategy": "weighted_vote",
      "weights": {
        "strategic_planner": 1.5,
        "combat_tactician": 1.0,
        "resource_manager": 1.0,
        "performance_analyst": 1.2
      }
    }
  }
}
```

---

## 11. Game Lifecycle Configuration

### 11.1 Complete lifecycle_autonomy.yaml

```yaml
lifecycle:
  character_creation:
    enabled: true
    auto_select_job: true
    job_selection_criteria:
      - efficiency
      - versatility
      - endgame_potential
    default_preferences:
      playstyle: balanced
      content_focus: pve
      party_preference: flexible
  
  autonomous_goal_generation:
    enabled: true
    goal_count: 5
    regeneration_interval_hours: 24
    llm_provider: openai
    crew_ai_enabled: true
    creativity_temperature: 0.8
    
  stages:
    novice_training:
      target_level: 10
      farming_locations:
        - Training Grounds
        - Prontera Field
      skill_priorities:
        - basic_skill
      
    early_game:
      level_range: [10, 50]
      job_change_priority: critical
      equipment_budget_percent: 0.2
      farming_efficiency_target: 80000  # exp/hour
      
    mid_game:
      level_range: [50, 99]
      equipment_budget_percent: 0.3
      farming_efficiency_target: 500000  # exp/hour
      mvp_hunting_enabled: false
      
    late_game:
      level_range: [99, 175]
      equipment_budget_percent: 0.4
      farming_efficiency_target: 1000000  # exp/hour
      mvp_hunting_enabled: true
      
    post_endgame:
      endless_mode: true
      activity_diversity: 0.7
      avoid_repetition_count: 3
      generate_creative_goals: true
  
  quest_automation:
    enabled: true
    auto_complete_essential: true
    auto_complete_job_specific: true
    skip_optional: false
    llm_assistance: true
    
  equipment_progression:
    enabled: true
    auto_upgrade: true
    budget_percentage: 0.3
    prioritize_bis: true
    consider_future_jobs: true
    
  resource_management:
    zeny_thresholds:
      minimum: 100000
      optimal: 1000000
      emergency: 50000
    consumable_thresholds:
      healing_potions: 100
      sp_potions: 50
      arrows: 500
      buff_items: 20
    auto_restock: true
    restock_trigger_percent: 0.3
    
  performance_targets:
    exp_per_hour_minimum: 100000
    zeny_per_hour_minimum: 50000
    death_rate_maximum: 0.5
    goal_completion_rate_minimum: 0.8
    
  safety:
    emergency_teleport_hp: 0.2
    emergency_logout_enabled: true
    avoid_pvp_maps: true
    max_continuous_hours: 8
    break_interval_hours: 2
    break_duration_minutes: 15
```

### 11.2 Job Path Configurations

```yaml
job_paths:
  swordsman_knight:
    priority: high
    difficulty: 3
    stat_priorities: [STR, VIT, AGI]
    equipment_path:
      - Sword
      - Spear
      - Two-Hand Sword
    farming_locations:
      early: [Prontera Culvert, Ant Hell]
      mid: [Clock Tower, Glast Heim]
      late: [Abyss Lake, Thanatos Tower]
    
  mage_wizard:
    priority: high
    difficulty: 2
    stat_priorities: [INT, DEX, VIT]
    equipment_path:
      - Rod
      - Staff
      - Ancient Staff
    farming_locations:
      early: [Geffen Tower, Orc Village]
      mid: [Clock Tower, Magma Dungeon]
      late: [Thanatos Tower, Endless Tower]
  
  # ... configurations for all 12 job paths
```

---

## 12. Coordinator Configurations

(Keep existing coordinator configurations as is - renumbered from 7 to 12)

---

## 13. Example Configurations

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
