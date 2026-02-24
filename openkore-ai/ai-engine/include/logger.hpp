#pragma once

// Prevent Windows macro conflicts
#ifdef ERROR
#undef ERROR
#endif

#include <string>
#include <fstream>
#include <mutex>

namespace openkore_ai {
namespace logging {

enum class LogLevel {
    DEBUG = 0,
    INFO = 1,
    WARNING = 2,
    ERROR_LEVEL = 3
};

class Logger {
public:
    // Initialize logger with log directory and minimum level
    static void initialize(const std::string& log_dir = "logs", LogLevel min_level = LogLevel::INFO);
    
    // Log messages at different levels
    static void debug(const std::string& message, const std::string& context = "");
    static void info(const std::string& message, const std::string& context = "");
    static void warning(const std::string& message, const std::string& context = "");
    static void error(const std::string& message, const std::string& context = "");
    
    // Specialized logging for HTTP requests/responses
    static void log_request(const std::string& method, const std::string& path,
                           const std::string& body = "", size_t body_size = 0);
    static void log_response(const std::string& path, int status_code,
                            double latency_ms, const std::string& body = "");
    
    // Cleanup
    static void cleanup();
    
private:
    static void log(LogLevel level, const std::string& message, const std::string& context = "");
    static void rotate_log_file();
    static std::string get_timestamp();
    static std::string level_to_string(LogLevel level);
    
    static std::mutex log_mutex_;
    static std::ofstream log_file_;
    static std::string log_directory_;
    static std::string current_date_;
    static LogLevel min_level_;
};

} // namespace logging
} // namespace openkore_ai
