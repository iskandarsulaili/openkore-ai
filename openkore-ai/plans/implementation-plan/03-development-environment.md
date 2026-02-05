# Development Environment Setup Guide

**Version:** 1.0  
**Date:** 2026-02-05  
**Status:** Planning Phase

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Requirements](#2-system-requirements)
3. [C++ Development Environment](#3-c-development-environment)
4. [Python ML Environment](#4-python-ml-environment)
5. [Perl Development Environment](#5-perl-development-environment)
6. [Database Setup](#6-database-setup)
7. [IDE Configuration](#7-ide-configuration)
8. [Build and Deployment Tools](#8-build-and-deployment-tools)
9. [Testing Tools](#9-testing-tools)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Overview

### 1.1 Purpose

This guide provides step-by-step instructions for setting up a complete development environment for the OpenKore AI system.

### 1.2 Supported Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| **Windows 10/11** | ✅ Primary | Full support, native development |
| **Linux (Ubuntu 20.04+)** | ✅ Supported | Recommended for ML training |
| **macOS** | ⚠️ Limited | C++ development only, no game server |

### 1.3 Quick Start Checklist

- [ ] Install C++ compiler and build tools
- [ ] Install Python 3.9+ with ML libraries
- [ ] Install Perl 5.30+
- [ ] Install CMake 3.20+
- [ ] Install Git
- [ ] Clone repository
- [ ] Build C++ engine
- [ ] Run tests
- [ ] Configure IDE

---

## 2. System Requirements

### 2.1 Hardware Requirements

**Minimum:**
- CPU: Intel Core i5 / AMD Ryzen 5 (4 cores)
- RAM: 8 GB
- Storage: 20 GB SSD
- Network: Broadband internet

**Recommended:**
- CPU: Intel Core i7 / AMD Ryzen 7 (8 cores)
- RAM: 16 GB
- Storage: 50 GB NVMe SSD
- GPU: NVIDIA GTX 1060+ (for ML training)
- Network: Gigabit ethernet

### 2.2 Software Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| **C++ Compiler** | GCC 11+ / MSVC 2022+ / Clang 14+ | C++20 support |
| **CMake** | 3.20+ | Build system |
| **Python** | 3.9+ | ML training |
| **Perl** | 5.30+ | Plugin development |
| **Git** | 2.30+ | Version control |
| **SQLite** | 3.35+ | Database |

---

## 3. C++ Development Environment

### 3.1 Windows Setup

#### 3.1.1 Install Visual Studio 2022

**Option 1: Full Visual Studio (Recommended)**

1. Download [Visual Studio 2022 Community](https://visualstudio.microsoft.com/downloads/)
2. Run installer
3. Select workload: "Desktop development with C++"
4. Additional components:
   - C++ CMake tools for Windows
   - C++ AddressSanitizer
   - C++ profiling tools
   - Windows 10/11 SDK

**Option 2: Build Tools Only**

```powershell
# Download and install
choco install visualstudio2022buildtools --package-parameters "--add Microsoft.VisualStudio.Workload.VCTools"
```

#### 3.1.2 Install CMake

```powershell
# Using Chocolatey
choco install cmake --installargs 'ADD_CMAKE_TO_PATH=System'

# Or download from cmake.org
```

#### 3.1.3 Install vcpkg (Dependency Manager)

```powershell
# Clone vcpkg
cd C:\
git clone https://github.com/Microsoft/vcpkg.git
cd vcpkg

# Bootstrap
.\bootstrap-vcpkg.bat

# Add to PATH
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\vcpkg", "Machine")

# Integrate with Visual Studio
.\vcpkg integrate install
```

#### 3.1.4 Install Dependencies via vcpkg

```powershell
cd C:\vcpkg

# Install required libraries
.\vcpkg install nlohmann-json:x64-windows
.\vcpkg install sqlite3:x64-windows
.\vcpkg install protobuf:x64-windows
.\vcpkg install curl:x64-windows
.\vcpkg install gtest:x64-windows
.\vcpkg install spdlog:x64-windows
.\vcpkg install yaml-cpp:x64-windows

# Install ML libraries
.\vcpkg install onnxruntime:x64-windows
```

#### 3.1.5 Verify Installation

```powershell
# Check compiler
cl.exe /?

# Check CMake
cmake --version

# Check vcpkg
vcpkg version
```

### 3.2 Linux Setup (Ubuntu 20.04+)

#### 3.2.1 Install Build Tools

```bash
# Update package list
sudo apt update

# Install build essentials
sudo apt install -y build-essential gcc-11 g++-11 cmake git

# Set GCC 11 as default
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-11 100
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-11 100
```

#### 3.2.2 Install Dependencies

```bash
# Install libraries
sudo apt install -y \
    libsqlite3-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    libprotobuf-dev \
    protobuf-compiler \
    libyaml-cpp-dev \
    libgtest-dev \
    libgmock-dev

# Install spdlog
cd /tmp
git clone https://github.com/gabime/spdlog.git
cd spdlog
mkdir build && cd build
cmake ..
make -j4
sudo make install
```

#### 3.2.3 Install ONNX Runtime

```bash
# Download ONNX Runtime
cd /tmp
wget https://github.com/microsoft/onnxruntime/releases/download/v1.14.1/onnxruntime-linux-x64-1.14.1.tgz
tar -xzf onnxruntime-linux-x64-1.14.1.tgz

# Install
sudo cp -r onnxruntime-linux-x64-1.14.1/include/* /usr/local/include/
sudo cp -r onnxruntime-linux-x64-1.14.1/lib/* /usr/local/lib/
sudo ldconfig
```

#### 3.2.4 Verify Installation

```bash
# Check compiler
gcc --version
g++ --version

# Check CMake
cmake --version

# Check libraries
ldconfig -p | grep sqlite
ldconfig -p | grep curl
ldconfig -p | grep onnxruntime
```

### 3.3 Build C++ Project

#### 3.3.1 Clone Repository

```bash
git clone https://github.com/your-org/openkore-ai.git
cd openkore-ai
```

#### 3.3.2 Build (Windows)

```powershell
cd openkore-ai\cpp-core

# Create build directory
mkdir build
cd build

# Configure with vcpkg
cmake -G "Visual Studio 17 2022" -A x64 `
      -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake `
      -DCMAKE_BUILD_TYPE=Release `
      ..

# Build
cmake --build . --config Release --parallel

# Run tests
ctest -C Release --output-on-failure
```

#### 3.3.3 Build (Linux)

```bash
cd openkore-ai/cpp-core

# Create build directory
mkdir build && cd build

# Configure
cmake -DCMAKE_BUILD_TYPE=Release ..

# Build
make -j$(nproc)

# Run tests
ctest --output-on-failure
```

#### 3.3.4 Build Output

```
build/
├── bin/
│   └── openkore_ai_engine.exe    # Main executable
├── lib/
│   ├── libipc.a                  # IPC library
│   ├── libreflex.a               # Reflex engine
│   ├── librules.a                # Rule engine
│   └── libml.a                   # ML engine
└── tests/
    └── unit_tests.exe            # Test executable
```

---

## 4. Python ML Environment

### 4.1 Install Python

#### Windows

```powershell
# Using Chocolatey
choco install python --version=3.11.0

# Verify
python --version
pip --version
```

#### Linux

```bash
# Ubuntu 20.04+
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Set as default
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1
```

### 4.2 Create Virtual Environment

```bash
cd openkore-ai/ml-training

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux)
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### 4.3 Install ML Dependencies

```bash
# Install from requirements.txt
pip install -r requirements.txt
```

**requirements.txt:**
```txt
# Core ML libraries
numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.3.0
xgboost>=2.0.0

# Deep learning
torch>=2.0.0
torchvision>=0.15.0

# ONNX
onnx>=1.14.0
onnxruntime>=1.14.0
skl2onnx>=1.14.0
onnxmltools>=1.11.0

# Data processing
pyarrow>=12.0.0
fastparquet>=2023.0.0

# Visualization
matplotlib>=3.7.0
seaborn>=0.12.0

# Jupyter
jupyter>=1.0.0
ipykernel>=6.22.0

# Utilities
tqdm>=4.65.0
pyyaml>=6.0

# Testing
pytest>=7.3.0
pytest-cov>=4.1.0
```

### 4.4 Verify ML Environment

```python
# test_ml_environment.py
import numpy as np
import pandas as pd
import sklearn
import xgboost as xgb
import torch
import onnx
import onnxruntime as ort

print("NumPy version:", np.__version__)
print("Pandas version:", pd.__version__)
print("Scikit-learn version:", sklearn.__version__)
print("XGBoost version:", xgb.__version__)
print("PyTorch version:", torch.__version__)
print("ONNX version:", onnx.__version__)
print("ONNX Runtime version:", ort.__version__)

# Test CUDA availability
if torch.cuda.is_available():
    print("CUDA available:", torch.cuda.get_device_name(0))
else:
    print("CUDA not available (CPU only)")

print("\n✅ ML environment setup complete!")
```

```bash
python test_ml_environment.py
```

### 4.5 Configure Jupyter

```bash
# Install Jupyter kernel
python -m ipykernel install --user --name=openkore-ml --display-name="OpenKore ML"

# Start Jupyter
jupyter notebook
```

---

## 5. Perl Development Environment

### 5.1 Install Perl

#### Windows

```powershell
# Option 1: Strawberry Perl (Recommended)
choco install strawberryperl

# Option 2: ActivePerl
choco install activeperl
```

#### Linux

```bash
# Usually pre-installed
perl --version

# If not installed
sudo apt install -y perl
```

### 5.2 Install CPAN Modules

```bash
# Update CPAN
cpan App::cpanminus

# Install required modules
cpanm --notest Win32::Pipe          # Windows IPC
cpanm --notest IO::Socket::UNIX      # Linux IPC
cpanm --notest JSON::XS              # Fast JSON
cpanm --notest YAML::XS              # YAML parsing
cpanm --notest File::Monitor         # File watching
cpanm --notest Time::HiRes           # High resolution timing
cpanm --notest Test::More            # Testing
cpanm --notest Test::Deep            # Deep comparison
cpanm --notest Devel::NYTProf        # Profiling
```

### 5.3 Verify Perl Environment

```perl
# test_perl_environment.pl
use strict;
use warnings;
use feature 'say';

# Test required modules
my @modules = qw(
    JSON::XS
    YAML::XS
    Time::HiRes
    File::Monitor
    Test::More
);

foreach my $module (@modules) {
    eval "use $module";
    if ($@) {
        say "❌ $module not installed: $@";
    } else {
        say "✅ $module installed";
    }
}

say "\n✅ Perl environment setup complete!";
```

```bash
perl test_perl_environment.pl
```

---

## 6. Database Setup

### 6.1 SQLite

SQLite is typically bundled with the OS or installed with dependencies.

**Verify Installation:**

```bash
# Check SQLite
sqlite3 --version

# Create test database
sqlite3 test.db "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT);"
sqlite3 test.db "INSERT INTO test (name) VALUES ('test');"
sqlite3 test.db "SELECT * FROM test;"

# Cleanup
rm test.db
```

### 6.2 Database Schema Setup

```bash
cd openkore-ai/data/db

# Initialize databases
sqlite3 game_state.db < schema/game_state_schema.sql
sqlite3 metrics.db < schema/metrics_schema.sql
sqlite3 training_data.db < schema/training_data_schema.sql
```

### 6.3 Database Tools

**GUI Tools:**
- [DB Browser for SQLite](https://sqlitebrowser.org/)
- [DBeaver](https://dbeaver.io/)

**Command-line:**
```bash
# Install sqlite CLI tools
# Windows
choco install sqlite

# Linux
sudo apt install sqlite3
```

---

## 7. IDE Configuration

### 7.1 Visual Studio Code

#### 7.1.1 Install VSCode

```bash
# Windows
choco install vscode

# Linux
sudo snap install code --classic
```

#### 7.1.2 Install Extensions

**C++ Development:**
```json
{
  "recommendations": [
    "ms-vscode.cpptools",
    "ms-vscode.cmake-tools",
    "ms-vscode.cpptools-extension-pack",
    "twxs.cmake",
    "llvm-vs-code-extensions.vscode-clangd"
  ]
}
```

**Python Development:**
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-toolsai.jupyter",
    "ms-toolsai.vscode-jupyter-cell-tags"
  ]
}
```

**Perl Development:**
```json
{
  "recommendations": [
    "richterger.perl",
    "cfgarden.perlnavigator"
  ]
}
```

**General:**
```json
{
  "recommendations": [
    "eamodio.gitlens",
    "ms-vscode.live-server",
    "yzhang.markdown-all-in-one",
    "redhat.vscode-yaml"
  ]
}
```

#### 7.1.3 Workspace Settings

**.vscode/settings.json:**
```json
{
  // C++ settings
  "C_Cpp.default.configurationProvider": "ms-vscode.cmake-tools",
  "C_Cpp.default.cppStandard": "c++20",
  "C_Cpp.default.compilerPath": "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.35.32215/bin/Hostx64/x64/cl.exe",
  
  // Python settings
  "python.defaultInterpreterPath": "${workspaceFolder}/ml-training/venv/Scripts/python.exe",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  
  // Perl settings
  "perl.perlInc": [
    "${workspaceFolder}/openkore-ai/src"
  ],
  
  // Editor settings
  "editor.formatOnSave": true,
  "editor.rulers": [100],
  "files.trimTrailingWhitespace": true,
  
  // CMake settings
  "cmake.configureOnOpen": true,
  "cmake.buildDirectory": "${workspaceFolder}/cpp-core/build"
}
```

#### 7.1.4 Launch Configurations

**.vscode/launch.json:**
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "(Windows) Debug C++ Engine",
      "type": "cppvsdbg",
      "request": "launch",
      "program": "${workspaceFolder}/cpp-core/build/bin/Debug/openkore_ai_engine.exe",
      "args": [],
      "stopAtEntry": false,
      "cwd": "${workspaceFolder}/openkore-ai",
      "environment": [],
      "console": "integratedTerminal"
    },
    {
      "name": "(Linux) Debug C++ Engine",
      "type": "cppdbg",
      "request": "launch",
      "program": "${workspaceFolder}/cpp-core/build/bin/openkore_ai_engine",
      "args": [],
      "stopAtEntry": false,
      "cwd": "${workspaceFolder}/openkore-ai",
      "environment": [],
      "MIMode": "gdb"
    },
    {
      "name": "Python: Train Model",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/ml-training/train_model.py",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}/ml-training"
    }
  ]
}
```

#### 7.1.5 Tasks

**.vscode/tasks.json:**
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Build C++ Debug",
      "type": "shell",
      "command": "cmake",
      "args": [
        "--build",
        "${workspaceFolder}/cpp-core/build",
        "--config",
        "Debug"
      ],
      "group": {
        "kind": "build",
        "isDefault": true
      }
    },
    {
      "label": "Run Unit Tests",
      "type": "shell",
      "command": "ctest",
      "args": [
        "--output-on-failure"
      ],
      "options": {
        "cwd": "${workspaceFolder}/cpp-core/build"
      }
    },
    {
      "label": "Format C++ Code",
      "type": "shell",
      "command": "clang-format",
      "args": [
        "-i",
        "${file}"
      ]
    }
  ]
}
```

### 7.2 Visual Studio 2022

#### 7.2.1 Open CMake Project

1. Open Visual Studio 2022
2. File → Open → CMake...
3. Navigate to `openkore-ai/cpp-core/CMakeLists.txt`
4. Select configuration (x64-Debug or x64-Release)

#### 7.2.2 Configure CMake Settings

**CMakeSettings.json:**
```json
{
  "configurations": [
    {
      "name": "x64-Debug",
      "generator": "Ninja",
      "configurationType": "Debug",
      "buildRoot": "${projectDir}\\build\\${name}",
      "installRoot": "${projectDir}\\install\\${name}",
      "cmakeCommandArgs": "",
      "buildCommandArgs": "",
      "ctestCommandArgs": "",
      "inheritEnvironments": [ "msvc_x64_x64" ],
      "variables": [
        {
          "name": "CMAKE_TOOLCHAIN_FILE",
          "value": "C:/vcpkg/scripts/buildsystems/vcpkg.cmake",
          "type": "FILEPATH"
        }
      ]
    },
    {
      "name": "x64-Release",
      "generator": "Ninja",
      "configurationType": "Release",
      "buildRoot": "${projectDir}\\build\\${name}",
      "installRoot": "${projectDir}\\install\\${name}",
      "cmakeCommandArgs": "",
      "buildCommandArgs": "",
      "ctestCommandArgs": "",
      "inheritEnvironments": [ "msvc_x64_x64" ],
      "variables": [
        {
          "name": "CMAKE_TOOLCHAIN_FILE",
          "value": "C:/vcpkg/scripts/buildsystems/vcpkg.cmake",
          "type": "FILEPATH"
        }
      ]
    }
  ]
}
```

### 7.3 CLion (JetBrains)

#### 7.3.1 Import Project

1. Open CLion
2. File → Open → Select `openkore-ai/cpp-core`
3. CLion will automatically detect CMake project

#### 7.3.2 Configure Toolchain

1. File → Settings → Build, Execution, Deployment → Toolchains
2. Add new toolchain (Visual Studio or MinGW)
3. Configure CMake: Settings → Build, Execution, Deployment → CMake

---

## 8. Build and Deployment Tools

### 8.1 Build Scripts

#### Windows Build Script

**build.bat:**
```batch
@echo off
echo Building OpenKore AI Engine...

set BUILD_DIR=build
set CONFIG=Release
set PARALLEL=4

if not exist %BUILD_DIR% mkdir %BUILD_DIR%
cd %BUILD_DIR%

echo Configuring with CMake...
cmake -G "Visual Studio 17 2022" -A x64 ^
      -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake ^
      -DCMAKE_BUILD_TYPE=%CONFIG% ^
      ..

if %ERRORLEVEL% neq 0 (
    echo CMake configuration failed!
    exit /b 1
)

echo Building...
cmake --build . --config %CONFIG% --parallel %PARALLEL%

if %ERRORLEVEL% neq 0 (
    echo Build failed!
    exit /b 1
)

echo Build successful!
echo.
echo Running tests...
ctest -C %CONFIG% --output-on-failure

cd ..
```

#### Linux Build Script

**build.sh:**
```bash
#!/bin/bash
set -e

echo "Building OpenKore AI Engine..."

BUILD_DIR=build
CONFIG=Release
PARALLEL=$(nproc)

mkdir -p $BUILD_DIR
cd $BUILD_DIR

echo "Configuring with CMake..."
cmake -DCMAKE_BUILD_TYPE=$CONFIG ..

echo "Building..."
make -j$PARALLEL

echo "Build successful!"
echo
echo "Running tests..."
ctest --output-on-failure

cd ..
```

### 8.2 Docker Support (Optional)

**Dockerfile:**
```dockerfile
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc-11 g++-11 \
    cmake \
    git \
    libsqlite3-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    libprotobuf-dev \
    protobuf-compiler \
    python3.11 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Copy source code
COPY . /workspace

# Build C++ engine
RUN cd cpp-core && \
    mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release .. && \
    make -j$(nproc)

# Install Python dependencies
RUN cd ml-training && \
    pip3 install -r requirements.txt

CMD ["/bin/bash"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  dev:
    build: .
    volumes:
      - .:/workspace
      - /workspace/cpp-core/build
    environment:
      - DISPLAY=${DISPLAY}
    network_mode: host
```

### 8.3 Package Manager

#### Conan (Alternative to vcpkg)

```bash
# Install Conan
pip install conan

# Create conanfile
cat > conanfile.txt << EOF
[requires]
nlohmann_json/3.11.2
sqlite3/3.41.0
protobuf/3.21.4
libcurl/7.86.0
gtest/1.12.1
spdlog/1.11.0
yaml-cpp/0.7.0

[generators]
cmake_find_package
cmake_paths
EOF

# Install dependencies
mkdir build && cd build
conan install .. --build=missing
```

---

## 9. Testing Tools

### 9.1 Unit Testing

```bash
# Run all unit tests
cd cpp-core/build
ctest --output-on-failure

# Run specific test
./tests/unit_tests --gtest_filter=ReflexEngineTest.*

# Run with verbose output
./tests/unit_tests --gtest_verbose
```

### 9.2 Code Coverage

#### Windows (OpenCppCoverage)

```powershell
choco install opencppcoverage

# Run with coverage
OpenCppCoverage --sources cpp-core\src `
                --export_type html:coverage_report `
                -- cpp-core\build\tests\Debug\unit_tests.exe
```

#### Linux (gcov/lcov)

```bash
# Build with coverage flags
cmake -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS="--coverage" ..
make

# Run tests
./tests/unit_tests

# Generate coverage report
lcov --capture --directory . --output-file coverage.info
lcov --remove coverage.info '/usr/*' --output-file coverage.info
genhtml coverage.info --output-directory coverage_report
```

### 9.3 Memory Leak Detection

#### Valgrind (Linux)

```bash
sudo apt install valgrind

valgrind --leak-check=full \
         --show-leak-kinds=all \
         --track-origins=yes \
         --log-file=valgrind.log \
         ./build/bin/openkore_ai_engine
```

#### AddressSanitizer

```bash
# Build with ASan
cmake -DCMAKE_CXX_FLAGS="-fsanitize=address -g" ..
make

# Run
./build/bin/openkore_ai_engine
```

### 9.4 Performance Profiling

#### Google Benchmark

```bash
# Run benchmarks
./build/benchmarks/decision_latency_bench
./build/benchmarks/memory_benchmark
```

#### Perl Profiler

```bash
# Profile Perl code
perl -d:NYTProf plugins/aiCore/aiCore.pl

# Generate report
nytprofhtml
```

---

## 10. Troubleshooting

### 10.1 Common Issues

#### Issue: CMake can't find vcpkg packages

**Solution:**
```powershell
# Ensure vcpkg toolchain is specified
cmake -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake ..
```

#### Issue: Linker errors with ONNX Runtime

**Solution:**
```bash
# Ensure ONNX Runtime libraries are in library path
# Linux
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# Windows - add to PATH
set PATH=C:\onnxruntime\lib;%PATH%
```

#### Issue: Python can't find modules

**Solution:**
```bash
# Activate virtual environment
source venv/bin/activate  # Linux
venv\Scripts\activate     # Windows

# Reinstall requirements
pip install -r requirements.txt
```

#### Issue: Perl modules not found

**Solution:**
```bash
# Check installed modules
perldoc -l JSON::XS

# Reinstall
cpanm --force JSON::XS
```

#### Issue: Build fails with C++20 errors

**Solution:**
```bash
# Ensure compiler supports C++20
gcc --version  # Should be 11+
g++ --version

# Update CMake
cmake --version  # Should be 3.20+
```

### 10.2 Clean Build

```bash
# Remove build directory
rm -rf cpp-core/build

# Recreate and build
mkdir cpp-core/build && cd cpp-core/build
cmake ..
make
```

### 10.3 Dependency Issues

```bash
# Windows - Update vcpkg
cd C:\vcpkg
git pull
.\bootstrap-vcpkg.bat
.\vcpkg upgrade --no-dry-run

# Linux - Update packages
sudo apt update
sudo apt upgrade
```

### 10.4 Getting Help

**Resources:**
- Project Wiki: `docs/wiki/`
- Issue Tracker: GitHub Issues
- Discord: Development channel
- Email: dev-team@example.com

**Debug Logs:**
```
logs/
├── cmake_config.log
├── build.log
├── test_results.log
└── engine.log
```

---

## Quick Reference

### Build Commands

```bash
# Windows
build.bat

# Linux
./build.sh

# Clean build
cmake --build build --target clean
```

### Test Commands

```bash
# All tests
ctest --output-on-failure

# Specific suite
./tests/unit_tests --gtest_filter=ReflexEngine*

# With coverage
./scripts/run_with_coverage.sh
```

### Environment Variables

```bash
# Windows
set OPENAI_API_KEY=sk-...
set CMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake

# Linux
export OPENAI_API_KEY=sk-...
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
```

---

**Next Document:** [Deployment Strategy](04-deployment-strategy.md)
