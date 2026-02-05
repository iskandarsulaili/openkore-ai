# OpenKore Advanced AI System

A next-generation AI system for OpenKore that combines multi-tier decision-making, LLM reasoning, multi-agent coordination, and human-like personality.

## 🏗️ Architecture

Three-process architecture with clean separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                      OpenKore (Perl)                        │
│                  ↓ Game State (HTTP POST)                   │
├─────────────────────────────────────────────────────────────┤
│              C++ AI Engine (Port 9901)                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Multi-Tier Decision System                          │   │
│  │  • Reflex (<1ms)   - Emergency responses             │   │
│  │  • Rules (<10ms)   - Heuristic logic                 │   │
│  │  • ML (<100ms)     - Trained models                  │   │
│  │  • LLM (varies)    - Complex reasoning               │   │
│  └─────────────────────────────────────────────────────┘   │
│                  ↓ Complex Queries (HTTP)                   │
├─────────────────────────────────────────────────────────────┤
│            Python AI Service (Port 9902)                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • LLM Provider Chain (DeepSeek→OpenAI→Anthropic)   │   │
│  │  • OpenMemory SDK (5 memory sectors)                 │   │
│  │  • CrewAI Multi-Agent System                         │   │
│  │  • SQLite Database (persistent state)                │   │
│  │  • ONNX Runtime (ML inference)                       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## ✨ Features

### 🧠 Multi-Tier Decision System
- **Reflex Tier**: Sub-millisecond emergency responses (dodge AoE, use potions)
- **Rules Tier**: Fast heuristic logic for common scenarios (<10ms)
- **ML Tier**: Trained models for complex pattern recognition (<100ms)
- **LLM Tier**: Natural language reasoning for novel situations (seconds)

### 🤖 Advanced AI Capabilities
- **OpenMemory Integration**: Five-sector memory system (episodic, semantic, procedural, emotional, reflective)
- **CrewAI Multi-Agent**: Strategic planner, combat tactician, resource manager, performance analyst
- **LLM Provider Chain**: Automatic failover (DeepSeek → OpenAI → Anthropic)
- **Personality System**: 8 configurable traits (chattiness, friendliness, caution, humor, etc.)

### 🎯 Specialized Coordinators
14 domain-specific coordinators for optimal decision-making:
1. **Combat Coordinator**: Target selection, skill rotation, positioning
2. **Movement Coordinator**: Pathfinding, obstacle avoidance, map exploration
3. **Resource Coordinator**: Inventory management, consumable usage
4. **Social Coordinator**: Player interactions, party dynamics, guild management
5. **Economic Coordinator**: Buying, selling, trading optimization
6. **Quest Coordinator**: Quest tracking, objective planning
7. **Survival Coordinator**: HP/SP monitoring, safety priorities
8. **Skill Coordinator**: Skill leveling, build optimization
9. **Equipment Coordinator**: Gear upgrades, enchanting decisions
10. **Grinding Coordinator**: Farming efficiency, loot optimization
11. **PvP Coordinator**: Player combat tactics, arena strategies
12. **Party Coordinator**: Group coordination, role fulfillment
13. **Exploration Coordinator**: Map discovery, hidden content
14. **Adaptive Coordinator**: Meta-learning, strategy refinement

### 🔄 PDCA Cycle
Continuous improvement through Plan-Do-Check-Act methodology:
- **Plan**: Strategic goal setting
- **Do**: Execute actions via multi-tier system
- **Check**: Performance monitoring and metrics
- **Act**: Adaptive improvements and learning

## 📁 Project Structure

```
openkore-ai/
├── ai-engine/              # C++ HTTP REST Engine (port 9901)
│   ├── src/                # Source code
│   ├── include/            # Header files
│   ├── tests/              # Unit tests
│   ├── CMakeLists.txt      # Build configuration
│   └── README.md           # C++ setup guide
│
├── ai-service/             # Python AI Service (port 9902)
│   ├── src/                # Python source code
│   ├── tests/              # Unit tests
│   ├── requirements.txt    # Dependencies
│   ├── pyproject.toml      # Project config
│   └── README.md           # Python setup guide
│
├── plugins/                # OpenKore Perl plugin
│   └── godtier-ai/
│       ├── GodTierAI.pm    # Main plugin
│       ├── Bridge.pm       # HTTP client bridge
│       ├── Config.pm       # Configuration loader
│       └── README.md       # Plugin installation guide
│
├── config/                 # Configuration templates
│   ├── ai-engine.yaml      # C++ engine config
│   ├── ai-service.yaml     # Python service config
│   ├── plugin.yaml         # Plugin config
│   └── README.md           # Configuration guide
│
├── macros/                 # Generated macro files (hot-reload)
├── logs/                   # Log files
└── plans/                  # Detailed documentation (26 files)
```

## 🚀 Quick Start

### Phase 0: Project Setup (Current)

✅ **Completed:**
- Directory structure created
- Build system configured (CMake, pip)
- Configuration templates generated
- README documentation written

### Phase 1: Core Bridge & HTTP REST API (Next)

Implement the foundational communication layer between OpenKore and the AI system.

**Estimated Time**: 1-2 weeks

See [`plans/01_IMPLEMENTATION_PHASES.md`](plans/01_IMPLEMENTATION_PHASES.md) for full roadmap.

## 📋 Prerequisites

### Required Software

**C++ AI Engine:**
- CMake 3.20+
- C++20 compiler (MSVC 2022, GCC 11+, or Clang 14+)
- OpenSSL

**Python AI Service:**
- Python 3.11+
- pip or uv

**OpenKore Plugin:**
- Perl 5.x
- LWP::UserAgent, JSON::XS, YAML::XS

**Optional:**
- Git (version control)
- Docker (containerized deployment)

### API Keys (Optional)

For LLM features, obtain at least ONE API key:

1. **DeepSeek** (Recommended, lowest cost ~$0.14/1M tokens)
   - Sign up: https://platform.deepseek.com/

2. **OpenAI** (Fallback, ~$10/1M tokens)
   - Sign up: https://platform.openai.com/

3. **Anthropic** (Final fallback, ~$15/1M tokens)
   - Sign up: https://console.anthropic.com/

Create `.env` file:
```bash
DEEPSEEK_API_KEY=sk-your-key-here
OPENAI_API_KEY=sk-your-key-here     # Optional
ANTHROPIC_API_KEY=sk-ant-your-key-here  # Optional
```

## 🔧 Installation

### 1. Build C++ AI Engine

See [`ai-engine/README.md`](ai-engine/README.md) for detailed instructions.

**Quick Start (Windows):**
```cmd
cd openkore-ai\ai-engine
cmake -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release
```

**Quick Start (Linux/macOS):**
```bash
cd openkore-ai/ai-engine
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
```

### 2. Set Up Python AI Service

See [`ai-service/README.md`](ai-service/README.md) for detailed instructions.

**Quick Start:**
```bash
cd openkore-ai/ai-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Install OpenKore Plugin

See [`plugins/godtier-ai/README.md`](plugins/godtier-ai/README.md) for detailed instructions.

**Quick Start:**
```bash
# Copy plugin to OpenKore
cp -r plugins/godtier-ai /path/to/openkore/plugins/

# Install Perl dependencies
cpan install LWP::UserAgent JSON::XS YAML::XS

# Configure OpenKore
echo "godtier-ai/GodTierAI" >> /path/to/openkore/control/plugins.txt
```

## ▶️ Running the System

### Terminal 1: Start C++ AI Engine
```bash
cd openkore-ai/ai-engine/build
./ai-engine --config ../../config/ai-engine.yaml
```

### Terminal 2: Start Python AI Service
```bash
cd openkore-ai/ai-service
source venv/bin/activate
python src/main.py
```

### Terminal 3: Start OpenKore
```bash
cd /path/to/openkore
perl openkore.pl
```

The plugin will automatically connect to the AI services and begin making intelligent decisions!

## 📊 Monitoring

### Health Checks

**C++ Engine:**
```bash
curl http://127.0.0.1:9901/api/v1/health
```

**Python Service:**
```bash
curl http://127.0.0.1:9902/api/v1/health
```

### Performance Metrics

**C++ Engine:**
```bash
curl http://127.0.0.1:9901/api/v1/metrics
```

### Logs

- C++ Engine: [`logs/ai-engine.log`](logs/)
- Python Service: [`logs/ai-service.log`](logs/)
- OpenKore: Console output

## 📖 Documentation

### Planning Documents (26 files)

Located in [`plans/`](plans/):

**Core Architecture:**
- [`00_PROJECT_OVERVIEW.md`](plans/00_PROJECT_OVERVIEW.md) - System overview and goals
- [`01_IMPLEMENTATION_PHASES.md`](plans/01_IMPLEMENTATION_PHASES.md) - Development roadmap
- [`02_THREE_PROCESS_ARCHITECTURE.md`](plans/02_THREE_PROCESS_ARCHITECTURE.md) - Technical architecture
- [`03_MULTI_TIER_DECISION_SYSTEM.md`](plans/03_MULTI_TIER_DECISION_SYSTEM.md) - Decision-making tiers

**Component Specifications:**
- [`04_CPP_AI_ENGINE.md`](plans/04_CPP_AI_ENGINE.md) - C++ engine details
- [`05_PYTHON_AI_SERVICE.md`](plans/05_PYTHON_AI_SERVICE.md) - Python service details
- [`06_OPENKORE_PLUGIN.md`](plans/06_OPENKORE_PLUGIN.md) - Plugin implementation
- [`07_HTTP_REST_API_SPEC.md`](plans/07_HTTP_REST_API_SPEC.md) - API specifications

**Advanced Features:**
- [`08_COORDINATORS_SYSTEM.md`](plans/08_COORDINATORS_SYSTEM.md) - 14 specialized coordinators
- [`09_PDCA_CYCLE.md`](plans/09_PDCA_CYCLE.md) - Continuous improvement
- [`10_OPENMEMORY_INTEGRATION.md`](plans/10_OPENMEMORY_INTEGRATION.md) - Memory system
- [`11_CREWAI_AGENTS.md`](plans/11_CREWAI_AGENTS.md) - Multi-agent system

**And 14 more detailed specifications...**

### Component READMEs

- [`ai-engine/README.md`](ai-engine/README.md) - C++ build and setup
- [`ai-service/README.md`](ai-service/README.md) - Python installation
- [`plugins/godtier-ai/README.md`](plugins/godtier-ai/README.md) - Plugin guide
- [`config/README.md`](config/README.md) - Configuration reference

## 🧪 Testing

### C++ Engine Tests
```bash
cd openkore-ai/ai-engine/build
ctest --output-on-failure
```

### Python Service Tests
```bash
cd openkore-ai/ai-service
pytest --cov=src --cov-report=html
```

### Integration Tests
```bash
# Start all services
./scripts/start-all.sh

# Run integration test suite
./scripts/test-integration.sh
```

## 🔒 Security Considerations

⚠️ **Important Security Notes:**

1. **Local Only**: Run AI services on `127.0.0.1` (localhost)
2. **Firewall**: Block external access to ports 9901-9902
3. **API Keys**: Store in `.env` file, never commit to Git
4. **Auto-Trade**: Keep `auto_trade_enabled: false` unless trusted
5. **Macro Permissions**: Generated macros should not be world-writable

## 🎮 Personality Configuration

Customize your bot's behavior in [`config/plugin.yaml`](config/plugin.yaml):

**Combat-Focused:**
```yaml
personality:
  chattiness: 0.1
  caution: 0.8
  curiosity: 0.2
```

**Social Friendly:**
```yaml
personality:
  chattiness: 0.9
  friendliness: 0.9
  helpfulness: 0.8
```

**Greedy Farmer:**
```yaml
personality:
  chattiness: 0.2
  helpfulness: 0.2
  curiosity: 0.3
```

## 🐛 Troubleshooting

### Common Issues

**"Connection refused" on port 9901:**
- Verify C++ engine is running
- Check firewall settings
- Review logs: `logs/ai-engine.log`

**"Module not found" in Python:**
- Activate virtual environment
- Reinstall: `pip install -r requirements.txt`

**OpenKore plugin not loading:**
- Check `control/plugins.txt` has correct path
- Verify Perl modules installed: `cpan LWP::UserAgent`

**LLM requests timing out:**
- Check API keys in `.env`
- Test provider: `curl http://127.0.0.1:9902/api/v1/health`
- Reduce timeout in `config/ai-service.yaml`

## 📈 Performance Tips

1. **Build Release Mode**: Always use Release for production
2. **Disable Unused Tiers**: Set `ml_enabled: false` if not using ML
3. **Local Services**: Run all processes on same machine
4. **Log Level**: Use `warning` or `error` in production
5. **Workers**: Run Python service with 4+ workers

## 🗺️ Roadmap

### ✅ Phase 0: Project Setup (COMPLETED)
- Directory structure
- Build systems
- Configuration templates

### 🔄 Phase 1: Core Bridge & HTTP REST API (Next)
- OpenKore → C++ HTTP communication
- Basic decision routing
- Health check endpoints

### 🔜 Phase 2: Multi-Tier Decision System
- Reflex tier implementation
- Rules engine
- ML inference pipeline
- LLM integration

### 🔜 Phase 3: Coordinators & PDCA
- 14 specialized coordinators
- PDCA cycle system
- Performance metrics

### 🔜 Phase 4-8: Advanced Features
- Memory system
- Multi-agent coordination
- Social AI
- Adaptive learning
- Production deployment

See [`plans/01_IMPLEMENTATION_PHASES.md`](plans/01_IMPLEMENTATION_PHASES.md) for complete timeline.

## 🤝 Contributing

This project is currently in active development (Phase 0 complete).

**Future Contribution Areas:**
- Coordinator implementations
- ML model training
- Agent behavior tuning
- Documentation improvements
- Bug reports and testing

## 📄 License

This project follows OpenKore's GPL-2.0 license.

## 🙏 Credits

**Technologies:**
- [OpenKore](https://github.com/OpenKore/openkore) - Ragnarok Online bot
- [cpp-httplib](https://github.com/yhirose/cpp-httplib) - C++ HTTP library
- [FastAPI](https://fastapi.tiangolo.com/) - Python web framework
- [OpenMemory](https://github.com/openmemoryai/openmemory) - Memory SDK
- [CrewAI](https://www.crewai.io/) - Multi-agent framework
- [DeepSeek](https://www.deepseek.com/) - LLM provider
- [OpenAI](https://openai.com/) - GPT-4 API
- [Anthropic](https://www.anthropic.com/) - Claude API

## 📞 Support

**Documentation:**
- See [`plans/`](plans/) for detailed specs
- Component READMEs for setup guides
- Configuration examples in [`config/`](config/)

**Debugging:**
- Check logs: [`logs/`](logs/)
- Enable debug mode: `logging.level: "debug"`
- Use health check endpoints

**Issues:**
- Review troubleshooting section above
- Check existing documentation
- Enable verbose logging for diagnostics

---

**Current Status**: 🏗️ Phase 0 Complete - Ready for Phase 1 Implementation

**Next Step**: Implement core HTTP bridge and decision routing (Phase 1)

**Estimated Time to MVP**: 8-12 weeks (all phases)
