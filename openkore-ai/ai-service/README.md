# OpenKore AI Service (Python)

The Python AI Service provides advanced AI capabilities including LLM reasoning, multi-agent systems, memory management, and machine learning inference.

## Architecture

- **Port**: 9902
- **Protocol**: HTTP REST API (FastAPI) - **ZERO IPC**
- **Communication**: All HTTP-only, no socket-based IPC
- **Language**: Python 3.11+
- **Framework**: FastAPI + Uvicorn
- **Database**: SQLite with WAL mode
- **LLM Chain**: DeepSeek → OpenAI → Anthropic (failover)

## Critical Architecture Note

**THIS SERVICE USES 100% HTTP COMMUNICATION - NO IPC WHATSOEVER**

- ✅ HTTP REST API (FastAPI on port 9902)
- ✅ JSON request/response
- ✅ Standard HTTP POST/GET endpoints
- ❌ NO Unix sockets
- ❌ NO named pipes
- ❌ NO IPC communication
- ❌ NO multiprocessing.Pipe

## Features

- **LLM Integration**: Multi-provider chain with automatic fallback
- **OpenMemory SDK**: Five-sector memory system (episodic, semantic, procedural, emotional, reflective)
- **CrewAI Agents**: Multi-agent system with 4 specialized agents
- **SQLite Database**: Persistent storage for state, memories, and metrics
- **ML Inference**: ONNX Runtime for trained models
- **Async Architecture**: High-performance async I/O

## Prerequisites

### Python 3.11+

**Windows:**
- Download from: https://www.python.org/downloads/
- Or via Chocolatey: `choco install python311`

**Linux:**
```bash
# Ubuntu/Debian
sudo apt install python3.11 python3.11-venv python3.11-dev

# Arch Linux
sudo pacman -S python
```

**macOS:**
```bash
brew install python@3.11
```

## Installation

### 1. Create Virtual Environment

**Windows:**
```cmd
cd openkore-ai\ai-service
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**
```bash
cd openkore-ai/ai-service
python3.11 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
# Install from requirements.txt
pip install -r requirements.txt

# Or install in editable mode
pip install -e .
```

### 3. Verify Installation

```bash
python -c "import fastapi, openai, anthropic, crewai; print('All dependencies installed successfully')"
```

## Configuration

### Environment Variables

Create a [`.env`](.env) file in the `ai-service/` directory:

```bash
# LLM Provider API Keys (at least one required for LLM features)
DEEPSEEK_API_KEY=sk-your-deepseek-key-here
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Optional: Override defaults
AI_SERVICE_PORT=9902
AI_SERVICE_HOST=127.0.0.1
DATABASE_PATH=../data/openkore-ai.db
LOG_LEVEL=info
```

### Configuration File

Copy [`../config/ai-service.yaml`](../config/ai-service.yaml) to the `ai-service/` directory:

```yaml
server:
  host: "127.0.0.1"
  port: 9902

database:
  path: "../data/openkore-ai.db"
  wal_mode: true

llm:
  providers:
    - name: "deepseek"
      priority: 1
      api_key_env: "DEEPSEEK_API_KEY"
      model: "deepseek-chat"
    
    - name: "openai"
      priority: 2
      api_key_env: "OPENAI_API_KEY"
      model: "gpt-4-turbo-preview"
    
    - name: "anthropic"
      priority: 3
      api_key_env: "ANTHROPIC_API_KEY"
      model: "claude-3-opus-20240229"
```

## Running

### Quick Start (Recommended)

**Windows:**
```cmd
cd openkore-ai\ai-service
start_http_server.bat
```

**Linux/macOS:**
```bash
cd openkore-ai/ai-service
chmod +x start_http_server.sh
./start_http_server.sh
```

### Development Mode

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Run HTTP server with auto-reload
python src/main.py

# OR use uvicorn directly
uvicorn src.main:app --reload --host 127.0.0.1 --port 9902
```

### Production Mode

```bash
# Activate virtual environment
source venv/bin/activate

# Run with production settings
uvicorn src.main:app --host 127.0.0.1 --port 9902 --workers 4
```

The HTTP service will start on `http://127.0.0.1:9902`

## API Endpoints

### `POST /api/v1/reasoning`
Complex reasoning using LLM chain.

**Request:**
```json
{
  "query": "Should I fight this MVP boss or retreat?",
  "context": {
    "player_level": 99,
    "party_size": 3,
    "boss_name": "Baphomet",
    "recent_deaths": 2
  }
}
```

**Response:**
```json
{
  "decision": "retreat",
  "reasoning": "Party size too small for MVP, 2 recent deaths indicate danger",
  "confidence": 0.85,
  "provider": "deepseek",
  "latency_ms": 1200
}
```

### `POST /api/v1/memory/store`
Store experience in memory system.

**Request:**
```json
{
  "sector": "episodic",
  "event": {
    "type": "combat_victory",
    "location": "orc_dungeon_02",
    "enemies": ["Orc Warrior", "Orc Archer"],
    "outcome": "victory",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### `POST /api/v1/memory/query`
Query relevant memories.

**Request:**
```json
{
  "query": "What strategies worked against Orc Warriors?",
  "sectors": ["episodic", "procedural"],
  "limit": 5
}
```

### `POST /api/v1/agents/execute`
Execute CrewAI multi-agent task.

**Request:**
```json
{
  "task": "Plan optimal leveling strategy for level 85-90",
  "agents": ["strategic_planner", "resource_manager"],
  "context": {
    "current_level": 85,
    "available_time": "4 hours",
    "budget": 1000000
  }
}
```

### `GET /api/v1/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "llm_providers": {
    "deepseek": "available",
    "openai": "available",
    "anthropic": "available"
  }
}
```

## Development

### Project Structure

```
ai-service/
├── src/
│   ├── main.py              # FastAPI app entry point
│   ├── api/                 # API route handlers
│   ├── database/            # SQLite schemas and queries
│   ├── memory/              # OpenMemory integration
│   ├── agents/              # CrewAI agent definitions
│   ├── llm/                 # LLM provider chain
│   └── utils/               # Helper functions
├── tests/                   # Unit tests
├── requirements.txt         # Dependencies
└── pyproject.toml          # Project metadata
```

### Adding a New LLM Provider

1. Add provider config to [`config/ai-service.yaml`](../config/ai-service.yaml)
2. Implement provider in [`src/llm/providers/`](src/llm/providers/)
3. Register in [`src/llm/chain.py`](src/llm/chain.py)

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_memory.py
```

### Database Migrations

```bash
# Create new migration
python -m src.database.migrate create "Add player stats table"

# Apply migrations
python -m src.database.migrate upgrade

# Rollback
python -m src.database.migrate downgrade
```

## Dependencies

Key dependencies (see [`requirements.txt`](requirements.txt) for full list):

- **FastAPI** (0.109.0): Modern async web framework
- **Uvicorn** (0.27.0): ASGI server
- **OpenAI** (1.10.0): GPT-4 API client
- **Anthropic** (0.9.0): Claude API client
- **OpenMemory** (0.2.1): Memory system SDK
- **CrewAI** (0.11.0): Multi-agent framework
- **ONNX Runtime** (1.16.3): ML inference
- **aiosqlite** (0.19.0): Async SQLite

## Troubleshooting

### Import Errors

```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

### Database Locked

SQLite WAL mode should prevent this. If it occurs:

```bash
# Check for stale lock files
ls -la ../data/openkore-ai.db*

# Remove lock files (service must be stopped)
rm ../data/openkore-ai.db-wal ../data/openkore-ai.db-shm
```

### LLM Provider Errors

1. Verify API keys in `.env` file
2. Check provider status:
   ```bash
   curl http://127.0.0.1:9902/api/v1/health
   ```
3. Test provider directly:
   ```python
   from openai import OpenAI
   client = OpenAI(api_key="sk-...")
   response = client.chat.completions.create(...)
   ```

### Port 9902 Already in Use

Change the port in configuration or environment:

```bash
export AI_SERVICE_PORT=9903
uvicorn src.main:app --port 9903
```

Update C++ engine config to match new port.

## Performance Tips

1. **Workers**: Use multiple workers in production (`--workers 4`)
2. **LLM Caching**: Enable response caching for repeated queries
3. **Database**: Use WAL mode for better concurrency
4. **Async**: Always use async/await for I/O operations
5. **Timeout**: Set reasonable timeouts for LLM requests

## API Keys

### DeepSeek (Recommended, Lowest Cost)
- Sign up: https://platform.deepseek.com/
- Pricing: ~$0.14 per 1M tokens (cheapest)
- Model: `deepseek-chat`

### OpenAI (Fallback)
- Sign up: https://platform.openai.com/
- Pricing: ~$10 per 1M tokens
- Model: `gpt-4-turbo-preview`

### Anthropic (Final Fallback)
- Sign up: https://console.anthropic.com/
- Pricing: ~$15 per 1M tokens
- Model: `claude-3-opus-20240229`

**Note**: You only need ONE API key to start. The system will use available providers.

## Next Steps

- Proceed to Phase 1: Implement FastAPI server and LLM chain
- See [`../plans/`](../plans/) for detailed specifications
- Configure CrewAI agents
- Set up OpenMemory sectors
