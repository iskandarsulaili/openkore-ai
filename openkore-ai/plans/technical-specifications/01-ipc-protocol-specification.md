# HTTP REST API Protocol Specification

**Version:** 2.1
**Date:** 2026-02-05
**Status:** Final Specification
**Update:** Added social interaction endpoints, concurrency controls, race condition prevention

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [REST API Specification](#3-rest-api-specification)
4. [Request/Response Formats](#4-requestresponse-formats)
5. [WebSocket Real-Time Streaming](#5-websocket-real-time-streaming)
6. [Error Handling](#6-error-handling)
7. [Authentication & Security](#7-authentication--security)
8. [Performance Requirements](#8-performance-requirements)
9. [Implementation Examples](#9-implementation-examples)
10. [Social Interaction Endpoints](#10-social-interaction-endpoints)
11. [Concurrency Controls](#11-concurrency-controls)

---

## 1. Overview

### 1.1 Purpose

The HTTP REST API protocol enables communication between three processes:
- **OpenKore Perl Process**: Game client interface
- **C++ Core Engine Process**: AI decision-making engine
- **Python AI Service Process**: Advanced AI components (OpenMemory SDK, CrewAI)

### 1.2 Why HTTP REST API?

**Problems with Named Pipes:**
- Windows Named Pipes have reliability issues
- Difficult to debug and monitor
- Platform-specific implementations
- Limited tooling support

**Benefits of HTTP REST:**
- ✅ Cross-platform standard protocol
- ✅ Easy debugging with curl, Postman, browser
- ✅ Language-agnostic (Python easily consumes)
- ✅ Built-in HTTP monitoring tools
- ✅ WebSocket support for real-time streaming
- ✅ RESTful design scales better
- ✅ Standard error codes and semantics

### 1.3 Design Goals

- **Low Latency**: < 10ms round-trip for state updates (target: <20ms acceptable)
- **Reliable**: Standard HTTP retry and error handling
- **Debuggable**: Human-readable JSON, standard HTTP tools
- **Secure**: Token authentication, localhost-only by default
- **Scalable**: Can add Python service without protocol changes

### 1.4 Service Ports

| Service | Port | Purpose | Technology |
|---------|------|---------|------------|
| **C++ Engine** | 9901 | Main AI decision engine | cpp-httplib / Crow |
| **Python AI Service** | 9902 | OpenMemory SDK, CrewAI | FastAPI / uvicorn |
| **OpenKore Perl** | - | Game client (HTTP client only) | LWP::UserAgent |

---

## 2. Architecture

### 2.1 Three-Process Architecture

```mermaid
graph TB
    subgraph "Process 1: OpenKore (Perl)"
        Perl[OpenKore Core]
        Plugin[AI Plugin]
        HTTPClient[HTTP Client]
    end
    
    subgraph "Process 2: C++ Engine :9901"
        HTTPServer[HTTP REST Server]
        Router[API Router]
        DecisionEngine[Decision Engine]
        Coordinator[Coordinators]
    end
    
    subgraph "Process 3: Python Service :9902"
        FastAPI[FastAPI Server]
        OpenMemory[OpenMemory SDK]
        CrewAI[CrewAI Framework]
        SQLite[(SQLite DB)]
    end
    
    Perl --> Plugin
    Plugin --> HTTPClient
    HTTPClient -->|REST API| HTTPServer
    HTTPServer --> Router
    Router --> DecisionEngine
    DecisionEngine --> Coordinator
    
    DecisionEngine -->|REST API| FastAPI
    FastAPI --> OpenMemory
    FastAPI --> CrewAI
    OpenMemory --> SQLite
    CrewAI --> SQLite
    
    style Perl fill:#f9f,stroke:#333
    style DecisionEngine fill:#9cf,stroke:#333
    style FastAPI fill:#9f9,stroke:#333
```

### 2.2 Communication Flow

```mermaid
sequenceDiagram
    participant P as Perl Plugin
    participant C as C++ Engine :9901
    participant Py as Python Service :9902
    
    Note over P,Py: Startup & Handshake
    C->>C: Start HTTP server on :9901
    Py->>Py: Start FastAPI on :9902
    P->>C: POST /api/v1/handshake
    C-->>P: 200 OK {session_id}
    
    Note over P,Py: Game Loop
    loop Every AI Tick (50-100ms)
        P->>C: POST /api/v1/state
        C->>C: Check Reflex/Rule tier
        
        alt Fast decision (Reflex/Rule)
            C-->>P: 200 OK {action}
        else Need ML/LLM
            C->>Py: POST /api/crew/execute
            Py->>Py: CrewAI processing
            Py-->>C: 200 OK {decision}
            C-->>P: 200 OK {action}
        end
    end
    
    Note over P,Py: Health Monitoring
    loop Every 30 seconds
        P->>C: GET /api/v1/health
        C-->>P: 200 OK {status}
        C->>Py: GET /api/health
        Py-->>C: 200 OK {status}
    end
```

---

## 3. REST API Specification

### 3.1 C++ Engine API Endpoints

#### Base URL
```
http://localhost:9901/api/v1
```

#### Authentication
All requests must include authentication token in header:
```
Authorization: Bearer <token>
```

---

### 3.2 Connection Management

#### POST /api/v1/handshake

**Purpose:** Establish connection and exchange capabilities

**Request:**
```json
{
  "client": "OpenKore",
  "client_version": "3.2.0",
  "pid": 12345,
  "capabilities": [
    "state_updates",
    "macro_execution",
    "hot_reload"
  ],
  "authentication_token": "sha256_hash"
}
```

**Response: 200 OK**
```json
{
  "status": "success",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "server": "OpenKore AI Engine",
  "server_version": "2.0.0",
  "capabilities": [
    "reflex_engine",
    "rule_engine",
    "ml_engine",
    "llm_integration",
    "python_service"
  ],
  "python_service_available": true,
  "server_time": 1738744800000
}
```

**Response: 401 Unauthorized**
```json
{
  "status": "error",
  "error_code": "INVALID_TOKEN",
  "message": "Authentication token is invalid or expired"
}
```

---

#### GET /api/v1/health

**Purpose:** Health check for monitoring

**Response: 200 OK**
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "active_sessions": 1,
  "decision_engines": {
    "reflex": "operational",
    "rule": "operational",
    "ml": "operational",
    "llm": "operational"
  },
  "python_service": {
    "status": "healthy",
    "url": "http://localhost:9902",
    "response_time_ms": 5
  },
  "performance": {
    "avg_response_time_ms": 8.5,
    "requests_per_second": 20,
    "error_rate": 0.001
  }
}
```

**Response: 503 Service Unavailable**
```json
{
  "status": "unhealthy",
  "issues": [
    "Python service not responding",
    "ML models not loaded"
  ]
}
```

---

### 3.3 State Management

#### POST /api/v1/state

**Purpose:** Send current game state for decision making

**Frequency:** Every AI tick (~50-100ms)

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1738744800000,
  "tick_number": 12345,
  "player": {
    "id": 150001,
    "name": "PlayerName",
    "level": 85,
    "job": "Knight",
    "job_level": 50,
    "hp": 5234,
    "hp_max": 8500,
    "sp": 423,
    "sp_max": 650,
    "position": {
      "x": 150,
      "y": 200,
      "map": "prontera"
    },
    "status": ["active"],
    "weight": 1500,
    "weight_max": 2400
  },
  "monsters": [
    {
      "id": 200001,
      "name": "Poring",
      "level": 1,
      "hp_percent": 100,
      "position": {"x": 155, "y": 205},
      "distance": 7.07,
      "aggressive": false
    }
  ],
  "items": [
    {
      "id": 501,
      "name": "Red Potion",
      "quantity": 50
    }
  ],
  "party": [],
  "skills": [
    {"id": 5, "name": "Bash", "level": 10, "sp_cost": 8}
  ]
}
```

**Response: 200 OK (Fast Decision)**
```json
{
  "status": "success",
  "decision_tier": "reflex",
  "processing_time_ms": 2,
  "action": {
    "type": "attack",
    "target_id": 200001,
    "skill_id": 5,
    "priority": "high",
    "reason": "Emergency reflex: monster too close"
  }
}
```

**Response: 200 OK (ML Decision)**
```json
{
  "status": "success",
  "decision_tier": "ml",
  "processing_time_ms": 45,
  "action": {
    "type": "move",
    "target_position": {"x": 160, "y": 210},
    "reason": "ML predicted optimal farming position",
    "confidence": 0.92
  }
}
```

**Response: 202 Accepted (LLM Processing)**
```json
{
  "status": "processing",
  "decision_tier": "llm",
  "task_id": "llm-task-12345",
  "estimated_time_seconds": 30,
  "fallback_action": {
    "type": "idle",
    "reason": "LLM processing strategic decision"
  }
}
```

**Response: 400 Bad Request**
```json
{
  "status": "error",
  "error_code": "INVALID_STATE",
  "message": "Missing required field: player.position",
  "details": {
    "field": "player.position",
    "expected": "object with x, y, map"
  }
}
```

---

#### GET /api/v1/action/{task_id}

**Purpose:** Poll for long-running LLM decision results

**Response: 200 OK (Completed)**
```json
{
  "status": "completed",
  "task_id": "llm-task-12345",
  "processing_time_ms": 28500,
  "action": {
    "type": "macro",
    "macro_name": "strategic_farm_rotation",
    "reason": "LLM generated optimal farming strategy"
  }
}
```

**Response: 202 Accepted (Still Processing)**
```json
{
  "status": "processing",
  "task_id": "llm-task-12345",
  "elapsed_seconds": 15,
  "estimated_remaining_seconds": 15,
  "progress": 0.5
}
```

---

### 3.4 Macro Management

#### POST /api/v1/macro/execute

**Purpose:** Execute a specific macro

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "macro_name": "heal_routine",
  "parameters": {
    "hp_threshold": 0.5,
    "item_preference": "White Potion"
  }
}
```

**Response: 200 OK**
```json
{
  "status": "success",
  "macro_name": "heal_routine",
  "execution_id": "exec-12345",
  "started": true
}
```

---

#### POST /api/v1/macro/generate

**Purpose:** Request LLM to generate new macro

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "purpose": "Efficient leveling at Clock Tower 3F",
  "constraints": {
    "avoid_mvp": true,
    "max_distance_from_spawn": 50,
    "consumable_budget": 10000
  },
  "context": {
    "character_level": 85,
    "character_job": "Knight",
    "available_skills": ["Bash", "Provoke", "Magnum Break"]
  }
}
```

**Response: 202 Accepted**
```json
{
  "status": "processing",
  "task_id": "macro-gen-12345",
  "estimated_time_seconds": 60,
  "webhook_url": "/api/v1/macro/status/macro-gen-12345"
}
```

---

#### GET /api/v1/macro/status/{task_id}

**Purpose:** Check macro generation status

**Response: 200 OK**
```json
{
  "status": "completed",
  "task_id": "macro-gen-12345",
  "macro_name": "clock_tower_3f_leveling",
  "macro_content": "# Generated macro content here...",
  "file_path": "control/macros/clock_tower_3f_leveling.txt",
  "estimated_efficiency": "120% vs manual play"
}
```

---

### 3.5 Configuration Management

#### POST /api/v1/config/reload

**Purpose:** Hot-reload configuration

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "config_type": "rules",
  "reason": "User updated combat rules"
}
```

**Response: 200 OK**
```json
{
  "status": "success",
  "config_reloaded": "rules",
  "rules_loaded": 45,
  "validation_errors": []
}
```

---

#### GET /api/v1/config/{config_type}

**Purpose:** Query current configuration

**Response: 200 OK**
```json
{
  "config_type": "llm",
  "current_config": {
    "provider": "openai",
    "model": "gpt-4",
    "timeout_seconds": 300,
    "max_tokens": 2000
  }
}
```

---

### 3.6 Metrics & Monitoring

#### GET /api/v1/metrics

**Purpose:** Get performance metrics

**Response: 200 OK**
```json
{
  "timestamp": 1738744800000,
  "uptime_seconds": 3600,
  "decision_stats": {
    "total_decisions": 72000,
    "reflex_decisions": 45000,
    "rule_decisions": 20000,
    "ml_decisions": 6500,
    "llm_decisions": 500
  },
  "performance": {
    "avg_response_time_ms": {
      "reflex": 0.8,
      "rule": 5.2,
      "ml": 42.0,
      "llm": 15000.0
    },
    "requests_per_second": 20.0,
    "error_rate": 0.002
  },
  "resource_usage": {
    "cpu_percent": 25.0,
    "memory_mb": 256,
    "threads": 4
  }
}
```

---

#### POST /api/v1/metrics/log

**Purpose:** Log decision for metrics tracking

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "decision_tier": "ml",
  "action_type": "attack",
  "success": true,
  "outcome": {
    "monster_killed": true,
    "exp_gained": 1250,
    "damage_taken": 450
  },
  "processing_time_ms": 45
}
```

**Response: 200 OK**
```json
{
  "status": "logged",
  "log_id": "log-12345"
}
```

---

### 3.7 Python AI Service Endpoints

#### Base URL
```
http://localhost:9902/api
```

---

#### POST /api/memory/store

**Purpose:** Store episodic memory in OpenMemory SDK

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "event": {
    "type": "combat",
    "timestamp": 1738744800000,
    "location": "prontera",
    "actors": ["Player", "Poring"],
    "outcome": "success",
    "exp_gained": 1250,
    "damage_taken": 450
  },
  "importance": 0.7
}
```

**Response: 200 OK**
```json
{
  "status": "success",
  "memory_id": "mem-12345",
  "embedding_generated": true,
  "stored_at": 1738744800000
}
```

---

#### POST /api/memory/retrieve

**Purpose:** Retrieve similar past situations

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_state": {
    "location": "prontera",
    "level": 85,
    "job": "Knight",
    "situation": "multiple monsters nearby"
  },
  "top_k": 5
}
```

**Response: 200 OK**
```json
{
  "status": "success",
  "memories": [
    {
      "memory_id": "mem-12340",
      "similarity": 0.92,
      "event": {
        "type": "combat",
        "outcome": "success",
        "strategy_used": "AOE skill rotation"
      },
      "timestamp": 1738744700000
    }
  ],
  "query_time_ms": 15
}
```

---

#### POST /api/crew/execute

**Purpose:** Execute CrewAI multi-agent task

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_type": "strategic",
  "context": {
    "character": {
      "level": 85,
      "job": "Knight",
      "zeny": 5000000,
      "current_goal": "Reach level 90"
    },
    "constraints": {
      "time_budget_hours": 10,
      "consumable_budget": 500000
    }
  },
  "timeout_seconds": 120
}
```

**Response: 200 OK**
```json
{
  "status": "success",
  "task_id": "crew-12345",
  "result": {
    "strategic_plan": {
      "farming_location": "Clock Tower 3F",
      "estimated_exp_per_hour": 800000,
      "estimated_time_hours": 8.5,
      "equipment_recommendations": ["Upgrade weapon to +7"],
      "consumable_requirements": {
        "white_potions": 200,
        "blue_potions": 100
      }
    },
    "combat_strategy": {
      "skill_rotation": ["Bash", "Magnum Break", "Bash", "Bash"],
      "hp_threshold_heal": 0.5,
      "sp_management": "Use blue potion at 30% SP"
    },
    "resource_plan": {
      "zeny_allocation": {
        "consumables": 300000,
        "equipment": 200000,
        "reserve": 4500000
      }
    }
  },
  "processing_time_ms": 85000,
  "agents_involved": ["strategic_planner", "combat_tactician", "resource_manager"]
}
```

---

#### GET /api/health

**Purpose:** Python service health check

**Response: 200 OK**
```json
{
  "status": "healthy",
  "services": {
    "openmemory": "operational",
    "crewai": "operational",
    "database": "operational"
  },
  "database": {
    "size_mb": 150,
    "memories_stored": 12500,
    "last_backup": 1738740000000
  }
}
```

---

## 4. Request/Response Formats

### 4.1 Standard Response Envelope

All API responses follow this structure:

**Success Response:**
```json
{
  "status": "success",
  "data": { ... },
  "metadata": {
    "timestamp": 1738744800000,
    "processing_time_ms": 45,
    "version": "2.0"
  }
}
```

**Error Response:**
```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": { ... }
  },
  "metadata": {
    "timestamp": 1738744800000,
    "request_id": "req-12345"
  }
}
```

### 4.2 HTTP Status Codes

| Code | Meaning | Use Case |
|------|---------|----------|
| **200** | OK | Request successful |
| **201** | Created | Resource created (macro generated) |
| **202** | Accepted | Long-running task started (LLM processing) |
| **400** | Bad Request | Invalid request data |
| **401** | Unauthorized | Authentication failed |
| **404** | Not Found | Resource not found |
| **408** | Request Timeout | Request took too long |
| **429** | Too Many Requests | Rate limit exceeded |
| **500** | Internal Server Error | Server error |
| **503** | Service Unavailable | Service down or unhealthy |

### 4.3 Content Types

**Request:**
- Content-Type: `application/json`
- Accept: `application/json`

**Response:**
- Content-Type: `application/json; charset=utf-8`

---

## 5. WebSocket Real-Time Streaming

### 5.1 WebSocket Connection

**Purpose:** Real-time state streaming for high-frequency updates

**URL:** `ws://localhost:9901/ws/state-stream`

**Benefits:**
- Lower latency than HTTP polling
- Bi-directional communication
- Server can push updates proactively

### 5.2 Connection Flow

```javascript
// JavaScript example (Perl will use similar WebSocket library)
const ws = new WebSocket('ws://localhost:9901/ws/state-stream');

ws.on('open', () => {
    // Send authentication
    ws.send(JSON.stringify({
        type: 'auth',
        token: 'sha256_hash'
    }));
});

ws.on('message', (data) => {
    const message = JSON.parse(data);
    
    if (message.type === 'action') {
        executeAction(message.action);
    }
});

// Send state updates
ws.send(JSON.stringify({
    type: 'state',
    data: currentGameState
}));
```

### 5.3 WebSocket Message Types

**Client → Server:**

```json
{
  "type": "state",
  "timestamp": 1738744800000,
  "data": { "player": {...}, "monsters": [...] }
}
```

**Server → Client:**

```json
{
  "type": "action",
  "timestamp": 1738744800001,
  "decision_tier": "reflex",
  "data": {
    "type": "attack",
    "target_id": 200001
  }
}
```

**Server → Client (Status Update):**

```json
{
  "type": "status",
  "message": "LLM processing strategic plan... 45s elapsed",
  "progress": 0.75
}
```

---

## 6. Error Handling

### 6.1 Error Codes

| Code | Meaning | Recovery Strategy |
|------|---------|-------------------|
| `INVALID_TOKEN` | Authentication failed | Re-authenticate with handshake |
| `INVALID_STATE` | Malformed state data | Validate and resend |
| `TIMEOUT` | Request timeout | Retry with exponential backoff |
| `SERVICE_UNAVAILABLE` | Python service down | Fall back to C++ ML/Rules |
| `RATE_LIMIT` | Too many requests | Reduce request frequency |
| `INTERNAL_ERROR` | Server error | Log and retry |

### 6.2 Retry Strategy

**Exponential Backoff:**

```python
def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except RequestTimeout:
            if attempt < max_retries - 1:
                sleep(2 ** attempt)  # 1s, 2s, 4s
            else:
                raise
```

### 6.3 Fallback Chain

```
Primary:   HTTP REST API call
           ↓ (on failure)
Fallback:  Use cached decision
           ↓ (on failure)
Emergency: Reflex engine default action
```

---

## 7. Authentication & Security

### 7.1 Token-Based Authentication

**Token Generation:**
```bash
# Shared secret stored in environment variable
echo -n "shared_secret_$(date +%s)" | sha256sum
```

**Token in Request:**
```http
POST /api/v1/state HTTP/1.1
Host: localhost:9901
Authorization: Bearer e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
Content-Type: application/json
```

### 7.2 Security Measures

1. **Localhost Only:** Server binds to `127.0.0.1` only
2. **Token Authentication:** All requests require valid token
3. **HTTPS Option:** Support SSL/TLS for sensitive environments
4. **Rate Limiting:** 100 requests/second per client
5. **Request Validation:** JSON schema validation on all inputs

### 7.3 Configuration

```json
{
  "http_server": {
    "host": "127.0.0.1",
    "port": 9901,
    "enable_ssl": false,
    "ssl_cert": "path/to/cert.pem",
    "ssl_key": "path/to/key.pem",
    "token_secret_env": "OPENKORE_AI_TOKEN",
    "rate_limit_per_second": 100
  }
}
```

---

## 8. Performance Requirements

### 8.1 Latency Targets

| Operation | Target | Acceptable | Maximum |
|-----------|--------|------------|---------|
| **Handshake** | < 10ms | < 20ms | 50ms |
| **State Update (Reflex)** | < 5ms | < 10ms | 20ms |
| **State Update (Rule)** | < 10ms | < 20ms | 50ms |
| **State Update (ML)** | < 50ms | < 100ms | 200ms |
| **LLM Simple Call** | < 5s | < 30s | 60s |
| **LLM Strategic Plan** | < 120s | < 300s | 600s |
| **Memory Store** | < 10ms | < 20ms | 50ms |
| **Memory Retrieve** | < 20ms | < 50ms | 100ms |
| **CrewAI Task** | < 60s | < 300s | 600s |

### 8.2 Throughput Targets

- **Requests/Second:** 20-30 (AI tick rate)
- **Concurrent Sessions:** 10+ (future multi-character support)
- **Uptime:** 99.9% (< 1 hour downtime per month)

### 8.3 Optimization Strategies

1. **HTTP/2:** Use HTTP/2 for multiplexing and header compression
2. **Keep-Alive:** Reuse connections (persistent connections)
3. **Compression:** gzip compression for large responses
4. **Caching:** Cache frequently accessed data
5. **Connection Pooling:** Maintain connection pool

---

## 9. Implementation Examples

### 9.1 C++ Server (cpp-httplib)

```cpp
#include <httplib.h>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

class AIEngineHTTPServer {
public:
    AIEngineHTTPServer(int port = 9901) : port_(port) {
        setupRoutes();
    }
    
    void start() {
        server_.listen("127.0.0.1", port_);
    }
    
private:
    httplib::Server server_;
    int port_;
    DecisionEngine decision_engine_;
    
    void setupRoutes() {
        // Handshake
        server_.Post("/api/v1/handshake", [this](const httplib::Request& req, httplib::Response& res) {
            auto body = json::parse(req.body);
            
            // Authenticate
            if (!authenticate(body["authentication_token"])) {
                res.status = 401;
                res.set_content(json{
                    {"status", "error"},
                    {"error_code", "INVALID_TOKEN"}
                }.dump(), "application/json");
                return;
            }
            
            // Create session
            std::string session_id = generateSessionId();
            
            res.set_content(json{
                {"status", "success"},
                {"session_id", session_id},
                {"server", "OpenKore AI Engine"},
                {"server_version", "2.0.0"}
            }.dump(), "application/json");
        });
        
        // State update
        server_.Post("/api/v1/state", [this](const httplib::Request& req, httplib::Response& res) {
            auto start = std::chrono::high_resolution_clock::now();
            
            // Parse state
            auto state = json::parse(req.body);
            
            // Make decision
            auto decision = decision_engine_.makeDecision(state);
            
            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
            
            res.set_content(json{
                {"status", "success"},
                {"decision_tier", decision.tier},
                {"processing_time_ms", duration.count()},
                {"action", decision.action}
            }.dump(), "application/json");
        });
        
        // Health check
        server_.Get("/api/v1/health", [this](const httplib::Request& req, httplib::Response& res) {
            res.set_content(json{
                {"status", "healthy"},
                {"uptime_seconds", getUptimeSeconds()},
                {"decision_engines", {
                    {"reflex", "operational"},
                    {"rule", "operational"},
                    {"ml", "operational"},
                    {"llm", "operational"}
                }}
            }.dump(), "application/json");
        });
    }
    
    bool authenticate(const std::string& token) {
        // Verify token against stored hash
        return token == getenv("OPENKORE_AI_TOKEN");
    }
    
    std::string generateSessionId() {
        // Generate UUID
        return "550e8400-e29b-41d4-a716-446655440000";
    }
};

int main() {
    AIEngineHTTPServer server(9901);
    std::cout << "Starting AI Engine HTTP server on :9901" << std::endl;
    server.start();
    return 0;
}
```

### 9.2 Perl Client (LWP::UserAgent)

```perl
package OpenKore::AI::HTTPClient;

use strict;
use warnings;
use LWP::UserAgent;
use JSON;
use Time::HiRes qw(time);

sub new {
    my ($class, %args) = @_;
    my $self = {
        base_url => $args{base_url} || 'http://localhost:9901/api/v1',
        token => $args{token} || $ENV{OPENKORE_AI_TOKEN},
        ua => LWP::UserAgent->new(timeout => 30, keep_alive => 5),
        session_id => undef
    };
    bless $self, $class;
    return $self;
}

sub handshake {
    my ($self) = @_;
    
    my $response = $self->{ua}->post(
        $self->{base_url} . '/handshake',
        'Content-Type' => 'application/json',
        'Authorization' => 'Bearer ' . $self->{token},
        Content => encode_json({
            client => 'OpenKore',
            client_version => '3.2.0',
            pid => $$,
            capabilities => ['state_updates', 'macro_execution'],
            authentication_token => $self->{token}
        })
    );
    
    if ($response->is_success) {
        my $data = decode_json($response->content);
        $self->{session_id} = $data->{session_id};
        return 1;
    }
    
    return 0;
}

sub sendState {
    my ($self, $game_state) = @_;
    
    my $start_time = time();
    
    my $response = $self->{ua}->post(
        $self->{base_url} . '/state',
        'Content-Type' => 'application/json',
        'Authorization' => 'Bearer ' . $self->{token},
        Content => encode_json({
            session_id => $self->{session_id},
            timestamp => int(time() * 1000),
            %$game_state
        })
    );
    
    my $latency = (time() - $start_time) * 1000;  # Convert to ms
    
    if ($response->is_success) {
        my $data = decode_json($response->content);
        $data->{network_latency_ms} = $latency;
        return $data;
    }
    
    return {status => 'error', error => $response->status_line};
}

sub checkHealth {
    my ($self) = @_;
    
    my $response = $self->{ua}->get(
        $self->{base_url} . '/health',
        'Authorization' => 'Bearer ' . $self->{token}
    );
    
    if ($response->is_success) {
        return decode_json($response->content);
    }
    
    return {status => 'unhealthy'};
}

1;
```

### 9.3 Python Service (FastAPI)

```python
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import uvicorn
import time

app = FastAPI(title="OpenKore AI Python Service", version="2.0")

# Models
class MemoryStoreRequest(BaseModel):
    session_id: str
    event: dict
    importance: float = 0.5

class MemoryRetrieveRequest(BaseModel):
    session_id: str
    current_state: dict
    top_k: int = 5

class CrewTaskRequest(BaseModel):
    session_id: str
    task_type: str
    context: dict
    timeout_seconds: int = 120

# Endpoints
@app.post("/api/memory/store")
async def store_memory(request: MemoryStoreRequest):
    """Store episodic memory in OpenMemory SDK"""
    
    # Store in OpenMemory
    memory_id = memory_manager.store_episodic_memory(request.event)
    
    return {
        "status": "success",
        "memory_id": memory_id,
        "embedding_generated": True,
        "stored_at": int(time.time() * 1000)
    }

@app.post("/api/memory/retrieve")
async def retrieve_memories(request: MemoryRetrieveRequest):
    """Retrieve similar past situations"""
    
    start_time = time.time()
    
    memories = memory_manager.retrieve_similar_situations(
        request.current_state,
        k=request.top_k
    )
    
    query_time_ms = (time.time() - start_time) * 1000
    
    return {
        "status": "success",
        "memories": memories,
        "query_time_ms": query_time_ms
    }

@app.post("/api/crew/execute")
async def execute_crew_task(request: CrewTaskRequest):
    """Execute CrewAI multi-agent task"""
    
    start_time = time.time()
    
    if request.task_type == "strategic":
        result = crew_manager.execute_strategic_planning(request.context)
    elif request.task_type == "analysis":
        result = crew_manager.analyze_performance(request.context)
    else:
        raise HTTPException(400, f"Unknown task type: {request.task_type}")
    
    processing_time_ms = (time.time() - start_time) * 1000
    
    return {
        "status": "success",
        "task_id": f"crew-{int(time.time())}",
        "result": result,
        "processing_time_ms": processing_time_ms
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    
    return {
        "status": "healthy",
        "services": {
            "openmemory": "operational",
            "crewai": "operational",
            "database": "operational"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9902)
```

---

## 10. Social Interaction Endpoints

**Full Specification:** See [`09-social-interaction-system.md`](09-social-interaction-system.md)

### 10.1 Process Chat Message

```
POST /api/v1/social/chat/process
```

**Request:**
```json
{
  "sender_id": 12345,
  "sender_name": "PlayerName",
  "message": "hey wanna party?",
  "channel": "whisper",
  "conversation_id": "conv_12345_67890"
}
```

**Response:**
```json
{
  "should_respond": true,
  "response_message": "sure why not",
  "delay_ms": 2500,
  "reasoning": "Friendly player, not busy",
  "reputation_adjustment": 1
}
```

### 10.2 Evaluate Trade Request

```
POST /api/v1/social/trade/evaluate
```

**Request:**
```json
{
  "trader_id": 12345,
  "trader_name": "PlayerName",
  "our_items": [{"id": 501, "name": "Red Potion", "amount": 10}],
  "their_items": [{"id": 502, "name": "Orange Potion", "amount": 10}],
  "zeny_offered": 0
}
```

**Response:**
```json
{
  "decision": "accept",
  "reasoning": "Fair trade with friendly player",
  "is_fair": true,
  "fair_value_ratio": 1.0,
  "is_scam": false,
  "response_message": "ok deal"
}
```

### 10.3 Get Player Reputation

```
GET /api/v1/social/reputation/{player_id}
```

**Response:**
```json
{
  "player_id": 12345,
  "player_name": "PlayerName",
  "reputation_score": 65,
  "reputation_tier": "friendly",
  "total_interactions": 45,
  "positive_interactions": 38,
  "negative_interactions": 2,
  "flags": {
    "is_friend": true,
    "is_guild_member": false,
    "is_blacklisted": false
  }
}
```

### 10.4 Adjust Reputation

```
POST /api/v1/social/reputation/adjust
```

**Request:**
```json
{
  "player_id": 12345,
  "delta": -30,
  "reason": "Attempted trade scam"
}
```

---

## 11. Concurrency Controls

**Full Specification:** See [`10-concurrency-and-race-conditions.md`](10-concurrency-and-race-conditions.md)

### 11.1 Request Serialization

All HTTP requests for the same session are processed serially to prevent race conditions:

```cpp
class HTTPRequestSerializer {
    // Per-session request queue
    std::unordered_map<std::string, RequestQueue> session_queues_;
    
    void enqueueRequest(const std::string& session_id, HTTPRequest request);
    void processQueue(const std::string& session_id);
};
```

**Guarantees:**
- Requests from same session are processed in order
- No concurrent state updates for same session
- Requests from different sessions can process concurrently

### 11.2 State Update Mutex

Game state updates are protected with read-write locks:

```cpp
class ThreadSafeGameState {
    mutable std::shared_mutex state_mutex_;
    
    // Multiple readers allowed
    GameState readState() const {
        std::shared_lock<std::shared_mutex> lock(state_mutex_);
        return state_;
    }
    
    // Exclusive write access
    void updateState(const GameState& new_state) {
        std::unique_lock<std::shared_mutex> lock(state_mutex_);
        state_ = new_state;
    }
};
```

### 11.3 Timeout Handling

All locks have timeout protection:

```cpp
// Lock with timeout
if (try_lock_with_timeout(mutex, std::chrono::milliseconds(5000))) {
    // Process request
} else {
    // Timeout - return error
    return HTTPResponse{503, "Service unavailable - timeout"};
}
```

### 11.4 Concurrent Request Limits

**Per-Session Limits:**
- Max 1 concurrent request per session (serialized)
- Max 100 concurrent requests across all sessions
- Queue depth limit: 1000 requests per session

**Global Limits:**
- Connection pool size: 100 connections
- Thread pool size: 8 worker threads
- Request timeout: 30 seconds (extendable to 300s for LLM)

### 11.5 Database Concurrency

SQLite WAL mode enabled for concurrent access:

```sql
PRAGMA journal_mode = WAL;      -- Allow concurrent reads
PRAGMA busy_timeout = 5000;     -- Wait 5s for locks
PRAGMA synchronous = NORMAL;    -- Balance safety/performance
```

**Transaction Isolation:**
- Read operations use DEFERRED transactions (concurrent reads)
- Write operations use IMMEDIATE transactions (acquire lock early)
- No long-running transactions (< 100ms target)

---

## Summary

This HTTP REST API specification provides:

✅ **Modern Protocol** - Replace Named Pipes with HTTP REST
✅ **Three-Process Architecture** - C++ Engine + Python Service + Perl Client
✅ **Complete API** - 20+ endpoints for all operations
✅ **Social Interactions** - Chat, trade, party, reputation endpoints
✅ **Concurrency Controls** - Request serialization, mutex protection, timeouts
✅ **WebSocket Support** - Real-time streaming option
✅ **Python Integration** - OpenMemory SDK and CrewAI endpoints
✅ **Security** - Token authentication and localhost-only
✅ **Performance** - <10ms latency targets for fast decisions
✅ **Debuggability** - Standard HTTP tools, JSON format
✅ **Production-Ready** - Error handling, retry logic, monitoring
✅ **Race Condition Prevention** - Thread-safe by design

**Migration Path:** The specification includes both HTTP REST (primary) and maintains compatibility concepts, allowing gradual transition from Named Pipes implementation.

---

**Next Steps:** Implement HTTP server in C++ engine using cpp-httplib or Crow framework, update Perl plugin to use LWP::UserAgent HTTP client, and deploy Python FastAPI service.

**Related Documents:**
- [`09-social-interaction-system.md`](09-social-interaction-system.md) - Social interaction details
- [`10-concurrency-and-race-conditions.md`](10-concurrency-and-race-conditions.md) - Concurrency patterns
