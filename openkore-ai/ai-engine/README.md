# OpenKore AI Engine (C++)

The C++ HTTP REST Engine is the core decision-making system that processes game state and returns optimal actions using a multi-tier decision architecture.

## Architecture

- **Port**: 9901
- **Protocol**: HTTP REST API
- **Language**: C++20
- **Build System**: CMake 3.20+
- **Decision Tiers**: Reflex (1ms) → Rules (10ms) → ML (100ms) → LLM (300s)

## Features

- **Multi-tier Decision System**: Four-layer decision hierarchy with progressive complexity
- **14 Specialized Coordinators**: Combat, Movement, Social, Resource Management, etc.
- **PDCA Cycle**: Plan-Do-Check-Act continuous improvement loop
- **HTTP REST API**: JSON-based communication with OpenKore plugin
- **Python Service Bridge**: Proxies complex AI queries to Python service (port 9902)
- **Low Latency**: Reflex and Rules tiers operate in <10ms

## Prerequisites

### Windows

1. **Visual Studio 2022** (or newer) with C++ Desktop Development workload
   - Download from: https://visualstudio.microsoft.com/downloads/
   - Select "Desktop development with C++" during installation

2. **CMake 3.20+**
   - Download from: https://cmake.org/download/
   - Or via Chocolatey: `choco install cmake`

3. **OpenSSL**
   - Via vcpkg (recommended):
     ```cmd
     git clone https://github.com/microsoft/vcpkg
     cd vcpkg
     bootstrap-vcpkg.bat
     vcpkg install openssl:x64-windows
     ```
   - Or download prebuilt: https://slproweb.com/products/Win32OpenSSL.html

### Linux

1. **GCC 11+** or **Clang 14+**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install build-essential g++-11
   
   # Arch Linux
   sudo pacman -S gcc cmake
   ```

2. **CMake 3.20+**
   ```bash
   # Ubuntu/Debian
   sudo apt install cmake
   
   # Arch Linux
   sudo pacman -S cmake
   ```

3. **OpenSSL**
   ```bash
   # Ubuntu/Debian
   sudo apt install libssl-dev
   
   # Arch Linux
   sudo pacman -S openssl
   ```

### macOS

1. **Xcode Command Line Tools**
   ```bash
   xcode-select --install
   ```

2. **CMake and OpenSSL**
   ```bash
   brew install cmake openssl
   ```

## Building

### Windows (Visual Studio)

```cmd
cd openkore-ai/ai-engine

:: Configure
cmake -B build -G "Visual Studio 17 2022" -A x64

:: Build Release
cmake --build build --config Release

:: Executable will be in: build\Release\ai-engine.exe
```

### Linux/macOS

```bash
cd openkore-ai/ai-engine

# Configure
cmake -B build -DCMAKE_BUILD_TYPE=Release

# Build
cmake --build build -j$(nproc)

# Executable will be in: build/ai-engine
```

## Configuration

Copy [`../config/ai-engine.yaml`](../config/ai-engine.yaml) to the build directory or specify path:

```yaml
server:
  host: "127.0.0.1"
  port: 9901

python_service:
  url: "http://127.0.0.1:9902"

decision_system:
  reflex_enabled: true
  rules_enabled: true
  ml_enabled: true
  llm_enabled: true
```

## Running

### Windows
```cmd
cd build\Release
ai-engine.exe --config ../../config/ai-engine.yaml
```

### Linux/macOS
```bash
cd build
./ai-engine --config ../config/ai-engine.yaml
```

The engine will start on `http://127.0.0.1:9901`

## API Endpoints

### `POST /api/v1/decide`
Request optimal action based on game state.

**Request Body:**
```json
{
  "game_state": {
    "player": { "hp": 1500, "max_hp": 2000, "sp": 800, "max_sp": 1000 },
    "position": { "x": 150, "y": 200, "map": "prt_fild08" },
    "monsters": [
      { "id": 1002, "name": "Poring", "distance": 5, "hp_percent": 100 }
    ],
    "inventory": { "items": [], "weight": 50, "max_weight": 2000 }
  },
  "context": {
    "mode": "auto",
    "last_action": "attack",
    "combat_state": "fighting"
  }
}
```

**Response:**
```json
{
  "action": "attack",
  "target": 1002,
  "tier": "rules",
  "latency_ms": 3.5,
  "reasoning": "Enemy within attack range, HP above threshold"
}
```

### `GET /api/v1/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "python_service": "connected"
}
```

### `GET /api/v1/metrics`
Performance metrics.

**Response:**
```json
{
  "decisions_total": 15000,
  "decisions_by_tier": {
    "reflex": 8000,
    "rules": 5000,
    "ml": 1500,
    "llm": 500
  },
  "avg_latency_ms": {
    "reflex": 0.5,
    "rules": 4.2,
    "ml": 45.0,
    "llm": 1200.0
  }
}
```

## Development

### Adding a New Coordinator

1. Create header: [`include/coordinators/my_coordinator.hpp`](include/coordinators/)
2. Create implementation: [`src/coordinators/my_coordinator.cpp`](src/coordinators/)
3. Register in [`src/main.cpp`](src/main.cpp)

### Testing

```bash
# Build tests
cmake --build build --target tests

# Run tests
cd build
ctest --output-on-failure
```

## Dependencies

All dependencies are automatically fetched by CMake:

- **cpp-httplib** (v0.15.3): HTTP server library
- **nlohmann/json** (v3.11.3): JSON parsing
- **yaml-cpp** (v0.7.0): YAML configuration parsing
- **OpenSSL**: HTTPS support (must be installed manually)

## Troubleshooting

### "Could not find OpenSSL"

**Windows (vcpkg):**
```cmd
cmake -B build -DCMAKE_TOOLCHAIN_FILE=C:/path/to/vcpkg/scripts/buildsystems/vcpkg.cmake
```

**Linux/macOS:**
```bash
cmake -B build -DOPENSSL_ROOT_DIR=/usr/local/opt/openssl
```

### Port 9901 Already in Use

Change the port in [`config/ai-engine.yaml`](../config/ai-engine.yaml):
```yaml
server:
  port: 9903  # Use a different port
```

Update the plugin configuration to match.

### Python Service Connection Failed

Ensure the Python AI Service is running on port 9902:
```bash
cd ../ai-service
python src/main.py
```

## Performance Tips

1. **Release Build**: Always use Release mode for production (`-DCMAKE_BUILD_TYPE=Release`)
2. **Disable Unused Tiers**: Set `ml_enabled: false` if not using ML models
3. **Adjust Timeouts**: Lower `timeout_ms` values in config for faster failover
4. **Log Level**: Set `logging.level: "warning"` for production

## Next Steps

- Proceed to Phase 1: Implement core HTTP server and decision system
- See [`../plans/`](../plans/) for detailed specifications
- Configure the Python AI Service (port 9902)
- Install the OpenKore plugin
