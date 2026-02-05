# OpenKore Advanced AI - Deployment Package v1.0.0

## Package Contents

This deployment package contains a complete, production-ready AI system for Ragnarok Online with full autonomy capabilities.

### Core Components

```
openkore-ai/
├── ai-engine/                 # C++ AI Engine (Port 9901)
│   ├── src/                   # Source code
│   │   ├── main.cpp          # Entry point
│   │   ├── http_server.cpp   # HTTP REST API
│   │   ├── decision_system.cpp # Multi-tier decision
│   │   ├── reflex_tier.cpp   # <1ms emergency responses
│   │   ├── rules_tier.cpp    # <10ms tactical decisions
│   │   └── coordinators/     # 14 specialized coordinators
│   ├── CMakeLists.txt        # Build configuration
│   └── build/Release/        # Compiled binary (Windows)
│
├── ai-service/               # Python AI Service (Port 9902)
│   ├── src/                  # Source code
│   │   ├── main.py          # FastAPI entry point
│   │   ├── database/        # SQLite manager (8 tables)
│   │   ├── memory/          # OpenMemory integration
│   │   ├── agents/          # CrewAI 4-agent system
│   │   ├── llm/             # LLM provider chain
│   │   ├── pdca/            # PDCA cycle (Plan-Do-Check-Act)
│   │   ├── ml/              # ML pipeline + cold-start
│   │   └── social/          # Social intelligence + chat
│   ├── requirements.txt     # Python dependencies
│   ├── data/                # SQLite database (auto-created)
│   └── logs/                # Service logs
│
├── plugins/                  # Perl Plugins
│   └── godtier-ai/          # OpenKore integration plugin
│       ├── GodTierAI.pm     # Main plugin file
│       └── README.md        # Plugin documentation
│
├── config/                   # Configuration Files
│   ├── ai-engine.yaml       # C++ engine config
│   ├── ai-service.yaml      # Python service config
│   ├── plugin.yaml          # Personality & social settings
│   └── README.md            # Configuration guide
│
├── macros/                   # Generated Macros
│   ├── farming.txt          # Auto-generated farming strategies
│   ├── healing.txt          # Auto-generated healing routines
│   ├── resource_management.txt
│   └── backups/             # Automatic macro backups
│
├── plans/                    # Complete Documentation
│   ├── PROJECT-PROPOSAL.md  # Executive summary
│   ├── TECHNICAL-ARCHITECTURE.md # System design
│   ├── technical-specifications/ # 10 detailed specs
│   └── implementation-plan/ # 9-phase roadmap
│
└── tests/                    # Test Suite
    ├── test_phase1.py       # HTTP Bridge
    ├── test_phase2.py       # Multi-Tier Decision
    ├── test_phase3.py       # Python AI Service
    ├── test_phase4.py       # PDCA Cycle
    ├── test_integration_e2e.py # End-to-End
    └── test_all_phases.py   # Comprehensive suite
```

## System Requirements

### Hardware
- **CPU**: 2+ cores, 2.0 GHz+ (Intel/AMD)
- **RAM**: 4 GB minimum, 8 GB recommended
- **Disk**: 500 MB for system, 10 GB for database growth
- **Network**: Broadband internet for LLM API

### Software
- **OS**: Windows 10/11, Linux (Ubuntu 20.04+), macOS 11+
- **C++ Compiler**: MSVC 2022 (Windows), GCC 11+ (Linux), Clang 14+ (macOS)
- **CMake**: 3.20+
- **Python**: 3.11+
- **Perl**: 5.16+ (included with OpenKore)

## Installation Instructions

### Step 1: Extract Package
```bash
# Extract to desired location
cd /path/to/openkore
unzip openkore-advanced-ai-v1.0.0.zip
```

### Step 2: Build C++ Engine
```bash
cd openkore-ai/ai-engine
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release

# Verify binary
./build/Release/ai-engine --version
```

### Step 3: Install Python Dependencies
```bash
cd ../ai-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 4: Configure API Keys
```bash
cd ai-service
cp .env.example .env
# Edit .env and add your DeepSeek API key
echo "DEEPSEEK_API_KEY=sk-your-key-here" >> .env
```

### Step 5: Run System
```bash
# Terminal 1: C++ Engine
cd ai-engine/build/Release
./ai-engine

# Terminal 2: Python Service
cd ai-service/src
python main.py

# Terminal 3: OpenKore
cd ../../
./start.exe
```

## Verification

### Health Checks
```bash
# C++ Engine
curl http://127.0.0.1:9901/api/v1/health

# Python Service
curl http://127.0.0.1:9902/api/v1/health
```

### Run Tests
```bash
cd openkore-ai
python test_integration_e2e.py  # ~2 minutes
python test_all_phases.py       # ~5 minutes
```

## Configuration

### Basic Configuration
Edit [`config/ai-engine.yaml`](config/ai-engine.yaml):
```yaml
server:
  host: "127.0.0.1"
  port: 9901
  threads: 4

tiers:
  reflex_enabled: true
  rules_enabled: true
  ml_enabled: true
  llm_enabled: true
```

Edit [`config/ai-service.yaml`](config/ai-service.yaml):
```yaml
server:
  host: "127.0.0.1"
  port: 9902

llm:
  provider: "deepseek"
  timeout: 60
  rate_limit_per_minute: 1
```

### Personality Configuration
Edit [`config/plugin.yaml`](config/plugin.yaml):
```yaml
personality:
  chattiness: 0.7      # 0.0-1.0 (quiet to chatty)
  friendliness: 0.8    # 0.0-1.0 (cold to warm)
  helpfulness: 0.6     # 0.0-1.0 (selfish to helpful)
```

## Production Deployment

### Option 1: Windows Service (NSSM)
```powershell
# Install NSSM
choco install nssm

# Install C++ Engine as service
nssm install OpenKoreAIEngine "C:\path\to\ai-engine.exe"
nssm start OpenKoreAIEngine

# Install Python Service
nssm install OpenKoreAIService "C:\path\to\python.exe" "C:\path\to\main.py"
nssm start OpenKoreAIService
```

### Option 2: Docker
```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY ai-service/requirements.txt .
RUN pip install -r requirements.txt
COPY ai-service/src ./src
ENV PYTHONUNBUFFERED=1
CMD ["python", "src/main.py"]
```

```bash
docker build -t openkore-ai-service .
docker run -d -p 9902:9902 --name ai-service openkore-ai-service
```

### Option 3: Systemd (Linux)
```ini
# /etc/systemd/system/openkore-ai-engine.service
[Unit]
Description=OpenKore Advanced AI - C++ Engine
After=network.target

[Service]
Type=simple
User=openkore
WorkingDirectory=/opt/openkore-ai/ai-engine/build/Release
ExecStart=/opt/openkore-ai/ai-engine/build/Release/ai-engine
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable openkore-ai-engine
sudo systemctl start openkore-ai-engine
```

## Monitoring

### Logs
- **C++ Engine**: Console output (stdout)
- **Python Service**: `ai-service/logs/ai-service.log`
- **Database**: `ai-service/data/openkore-ai.db`

### Metrics
- **C++ Metrics**: `GET http://127.0.0.1:9901/api/v1/metrics`
- **Python Health**: `GET http://127.0.0.1:9902/api/v1/health`

### Performance Monitoring
```bash
# Real-time decision latency
curl http://127.0.0.1:9901/api/v1/metrics | jq '.latency'

# Database size
du -h ai-service/data/openkore-ai.db

# Python memory usage
ps aux | grep python
```

## Backup & Recovery

### Critical Files
```bash
# Backup script
tar -czf openkore-ai-backup-$(date +%Y%m%d).tar.gz \
  ai-service/data/openkore-ai.db \
  ai-service/.env \
  config/*.yaml \
  macros/*.txt
```

### Recovery
```bash
# Restore from backup
tar -xzf openkore-ai-backup-20260205.tar.gz
```

## Troubleshooting

### Port Conflicts
```bash
# Check if ports are in use
netstat -an | grep 9901  # C++ Engine
netstat -an | grep 9902  # Python Service

# Change ports in config files if needed
```

### Database Issues
```bash
# Check database integrity
sqlite3 ai-service/data/openkore-ai.db "PRAGMA integrity_check;"

# Vacuum database (cleanup)
sqlite3 ai-service/data/openkore-ai.db "VACUUM;"
```

### DeepSeek API Errors
1. Verify API key in `.env` file
2. Check internet connectivity
3. Test API directly: `curl https://api.deepseek.com/v1/models`
4. Check API quota: https://platform.deepseek.com/usage

## Performance Optimization

### Low-End Systems
```yaml
# config/ai-engine.yaml
tiers:
  ml_enabled: false        # Disable ML for lower CPU usage
  llm_rate_limit: 0.5      # Reduce LLM queries

# config/ai-service.yaml
pdca:
  cycle_interval: 7200     # Longer cycle interval (2 hours)
```

### High-End Systems
```yaml
# config/ai-engine.yaml
server:
  threads: 8               # More HTTP threads

# config/ai-service.yaml
ml:
  enable_gpu: true         # GPU acceleration (if available)
pdca:
  cycle_interval: 1800     # Faster cycles (30 minutes)
```

## Security Checklist

- [ ] API keys stored in `.env` (not committed to Git)
- [ ] HTTP services bound to localhost only (127.0.0.1)
- [ ] Database file permissions set to user-only (chmod 600)
- [ ] Firewall rules block external access to ports 9901, 9902
- [ ] Regular backups configured
- [ ] Log rotation enabled

## Support Resources

- **Documentation**: [`plans/`](plans/) directory
- **Tests**: [`test_all_phases.py`](test_all_phases.py)
- **Performance**: [`PERFORMANCE_REPORT.md`](PERFORMANCE_REPORT.md)
- **Race Conditions**: [`RACE_CONDITION_VALIDATION.md`](RACE_CONDITION_VALIDATION.md)
- **Deployment**: [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md)

## Version History

### v1.0.0 (2026-02-05)
- ✅ Phase 0-9 complete
- ✅ Multi-tier decision system (Reflex/Rules/ML/LLM)
- ✅ PDCA continuous improvement
- ✅ Social intelligence with personality
- ✅ 14 specialized coordinators
- ✅ Race condition prevention
- ✅ Comprehensive test suite
- ✅ Production deployment ready

## License

This project extends OpenKore. See OpenKore's GPL license for details.

---

**Package Version**: 1.0.0  
**Release Date**: 2026-02-05  
**Status**: ✅ Production Ready  
**Monthly Cost**: $4.20 (DeepSeek LLM)
