cmake_minimum_required(VERSION 3.20)
project(openkore-ai-engine VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Dependencies
find_package(Threads REQUIRED)
find_package(OpenSSL)

# Check if OpenSSL is found
if(OPENSSL_FOUND)
    message(STATUS "OpenSSL found - HTTPS support enabled")
    add_compile_definitions(CPPHTTPLIB_OPENSSL_SUPPORT)
else()
    message(WARNING "OpenSSL not found - HTTPS support disabled (HTTP only)")
endif()

# cpp-httplib (header-only, will download if not found)
include(FetchContent)
FetchContent_Declare(
    httplib
    GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
    GIT_TAG v0.15.3
)
FetchContent_MakeAvailable(httplib)

# ONNX Runtime (for ML inference)
# User must install ONNX Runtime separately
# Instructions in README.md

# nlohmann/json (header-only)
FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
)
FetchContent_MakeAvailable(json)

# yaml-cpp (for config parsing) - Phase 2
# FetchContent_Declare(
#     yaml-cpp
#     GIT_REPOSITORY https://github.com/jbeder/yaml-cpp.git
#     GIT_TAG yaml-cpp-0.7.0
# )
# FetchContent_MakeAvailable(yaml-cpp)

# Source files
file(GLOB_RECURSE SOURCES
    "src/main.cpp"
    "src/logger.cpp"
    "src/decision/*.cpp"
    "src/coordinators/*.cpp"
)
file(GLOB_RECURSE HEADERS "include/*.hpp")

# Executable
add_executable(ai-engine ${SOURCES} ${HEADERS})

target_include_directories(ai-engine PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(ai-engine PRIVATE
    Threads::Threads
    httplib::httplib
    nlohmann_json::nlohmann_json
)

# Link OpenSSL if available
if(OPENSSL_FOUND)
    target_include_directories(ai-engine PRIVATE ${OPENSSL_INCLUDE_DIR})
    target_link_libraries(ai-engine PRIVATE OpenSSL::SSL OpenSSL::Crypto)
endif()

# Compiler flags
if(MSVC)
    target_compile_options(ai-engine PRIVATE /W4 /O2)
else()
    target_compile_options(ai-engine PRIVATE -Wall -Wextra -O3)
endif()

# Install
install(TARGETS ai-engine DESTINATION bin)
