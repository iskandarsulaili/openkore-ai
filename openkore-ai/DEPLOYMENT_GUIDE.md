# OpenKore Advanced AI - Deployment Guide

## Prerequisites

### Required Software
- **C++ Compiler**: MSVC 2022, GCC 11+, or Clang 14+
- **CMake**: 3.20 or higher
- **Python**: 3.11 or higher
- **Perl**: 5.16 or higher (comes with OpenKore)
- **Git**: For version control (optional)

### Required Libraries
- **C++**: cpp-httplib (auto-downloaded), nlohmann-json (auto-downloaded)
- **Python**: See [`ai-service/requirements.txt`](ai-service/requirements.txt)

## Installation Steps

### Step 1: Build C++ AI Engine

```bash
cd openkore-ai/ai-engine
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
```

**Output**: `ai-engine/build/Release/ai-engine.exe`

### Step 2: Install Python Dependencies

```bash
cd openkore-ai/ai-service
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Configure API Keys

Edit [`ai-service/.env`](ai-service/.env):
```
DEEPSEEK_API_KEY=your_key_here
# Optional fallbacks:
# OPENAI_API_KEY=your_key_here
# ANTHROPIC_API_KEY=your_key_here
```

Or use existing [`secret.txt`](../../secret.txt) (already configured).

### Step 4: Configure Personality (Optional)

Edit [`config/plugin.yaml`](config/plugin.yaml) to adjust:
- Chattiness, friendliness, helpfulness
- Social interaction preferences
- Reputation tier thresholds

### Step 5: Install Perl Plugin

Copy [`plugins/godtier-ai/`](plugins/godtier-ai/) to OpenKore's plugins folder:
```bash
copy /Y openkore-ai\plugins\godtier-ai\*.pm <openkore_root>\plugins\
```

Enable in OpenKore's `control/sys.txt`:
```
loadPlugins GodTierAI
```

## Running the System

### Start Servers (3 terminals)

**Terminal 1: C++ AI Engine**
```bash
cd openkore-ai/ai-engine/build/Release
ai-engine.exe
```

**Terminal 2: Python AI Service**
```bash
cd openkore-ai/ai-service
venv\Scripts\activate
cd src
python main.py
```

**Terminal 3: OpenKore**
```bash
cd openkore-ai
start.exe
```

## Verification

### Health Checks
```bash
# C++ Engine
curl http://127.0.0.1:9901/api/v1/health

# Python Service
curl http://127.0.0.1:9902/api/v1/health
```

### Run Integration Tests
```bash
cd openkore-ai
python test_integration_e2e.py
```

## Production Deployment Options

### Option 1: Windows Service
Use NSSM (Non-Sucking Service Manager) to run as Windows services.

### Option 2: Docker (Cross-platform)
```dockerfile
# Dockerfile for Python Service
FROM python:3.11-slim
WORKDIR /app
COPY ai-service/requirements.txt .
RUN pip install -r requirements.txt
COPY ai-service/src ./src
CMD ["python", "src/main.py"]
```

### Option 3: Systemd (Linux)
Create systemd service files for auto-start on boot.

## Monitoring

### Logs
- C++ Engine: Console output
- Python Service: `ai-service/logs/ai-service.log`
- Database: SQLite file at `ai-service/data/openkore-ai.db`

### Metrics Endpoints
- C++ Metrics: `GET http://127.0.0.1:9901/api/v1/metrics`
- Python Health: `GET http://127.0.0.1:9902/api/v1/health`

## Troubleshooting

### Port Conflicts
If ports 9901 or 9902 are in use, edit:
- [`config/ai-engine.yaml`](config/ai-engine.yaml) - Change `port: 9901`
- [`config/ai-service.yaml`](config/ai-service.yaml) - Change `port: 9902`

### DeepSeek API Errors
- Check API key in `.env` file
- Verify internet connection
- Check API status: https://api.deepseek.com/

### Database Lock Issues
- Ensure WAL mode is enabled (automatic)
- Check file permissions on `data/` directory
- Only one Python service instance should run

## Security

- **API Keys**: Store in `.env`, never commit to Git
- **Database**: File-based, local access only
- **HTTP**: Localhost only (127.0.0.1), not exposed to internet
- **C++ Executable**: Compiled binary, harder to reverse-engineer than scripts

## Backup & Recovery

### Critical Files to Backup
- `ai-service/data/openkore-ai.db` - All game history and memories
- `config/*.yaml` - Configuration files
- `macros/` - Generated macros

### Recovery
- Database: SQLite supports `.backup` command
- Macros: Automatic backups in `macros/backups/`
- Configs: Version control recommended

## Performance Tuning

### For Low-End Systems
- Reduce PDCA cycle frequency in config
- Decrease LLM query rate
- Use simpler ML models

### For High-End Systems
- Enable more coordinators
- Increase PDCA cycle frequency
- Add additional ML models for specialized tasks
