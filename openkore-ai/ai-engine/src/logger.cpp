#include "../include/logger.hpp"
#include <iostream>
#include <fstream>
#include <filesystem>
#include <chrono>
#include <iomanip>
#include <sstream>

namespace openkore_ai {
namespace logging {

// Initialize static members
std::mutex Logger::log_mutex_;
std::ofstream Logger::log_file_;
std::string Logger::log_directory_;
std::string Logger::current_date_;
LogLevel Logger::min_level_ = LogLevel::INFO;

void Logger::initialize(const std::string& log_dir, LogLevel min_level) {
    std::lock_guard<std::mutex> lock(log_mutex_);
    
    log_directory_ = log_dir;
    min_level_ = min_level;
    
    // Create logs directory if it doesn't exist
    try {
        std::filesystem::create_directories(log_directory_);
        std::cerr << "[LOGGER] Logs directory created/verified: " << log_directory_ << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "[LOGGER] FATAL: Failed to create logs directory: " << e.what() << std::endl;
        throw std::runtime_error(std::string("Logger initialization failed - cannot create directory: ") + e.what());
    }
    
    // Open log file for current date (rotate_log_file assumes mutex is already locked)
    try {
        rotate_log_file();
        if (!log_file_.is_open()) {
            throw std::runtime_error("Log file failed to open after rotation");
        }
        std::cerr << "[LOGGER] Log file opened successfully" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "[LOGGER] FATAL: Failed to open log file: " << e.what() << std::endl;
        throw std::runtime_error(std::string("Logger initialization failed - cannot open log file: ") + e.what());
    }
    
    // Write initialization message directly (avoid recursive mutex lock)
    std::string timestamp = get_timestamp();
    std::string log_line = timestamp + " | INFO  | [LOGGER] Logger initialized - Directory: " + log_directory_;
    std::cout << log_line << std::endl;
    if (log_file_.is_open()) {
        log_file_ << log_line << std::endl;
        log_file_.flush();
    }
}

void Logger::rotate_log_file() {
    // Close existing file if open
    if (log_file_.is_open()) {
        log_file_.close();
    }
    
    // Get current date
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    std::tm tm;
    
#ifdef _WIN32
    localtime_s(&tm, &time_t);
#else
    localtime_r(&time_t, &tm);
#endif
    
    std::ostringstream date_stream;
    date_stream << std::put_time(&tm, "%Y-%m-%d");
    std::string new_date = date_stream.str();
    
    // Check if date changed
    if (new_date == current_date_ && log_file_.is_open()) {
        return; // No need to rotate
    }
    
    current_date_ = new_date;
    
    // Open new log file
    std::string log_filename = log_directory_ + "/ai_engine_" + current_date_ + ".log";
    
    try {
        log_file_.open(log_filename, std::ios::app);
        
        if (!log_file_.is_open()) {
            std::cerr << "[LOGGER] ERROR: Failed to open log file: " << log_filename << std::endl;
            // Try to provide more context
            if (!std::filesystem::exists(log_directory_)) {
                std::cerr << "[LOGGER] ERROR: Log directory does not exist: " << log_directory_ << std::endl;
            }
            throw std::runtime_error("Failed to open log file: " + log_filename);
        }
        
        std::cerr << "[LOGGER] Log file opened: " << log_filename << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "[LOGGER] Exception opening log file: " << e.what() << std::endl;
        throw;
    }
}

std::string Logger::get_timestamp() {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()
    ) % 1000;
    
    std::tm tm;
#ifdef _WIN32
    localtime_s(&tm, &time_t);
#else
    localtime_r(&time_t, &tm);
#endif
    
    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y-%m-%d %H:%M:%S")
        << '.' << std::setfill('0') << std::setw(3) << ms.count();
    return oss.str();
}

std::string Logger::level_to_string(LogLevel level) {
    switch (level) {
        case LogLevel::DEBUG: return "DEBUG";
        case LogLevel::INFO: return "INFO ";
        case LogLevel::WARNING: return "WARN ";
        case LogLevel::ERROR_LEVEL: return "ERROR";
        default: return "UNKNOWN";
    }
}

void Logger::log(LogLevel level, const std::string& message, const std::string& context) {
    if (level < min_level_) {
        return; // Skip if below minimum level
    }
    
    std::lock_guard<std::mutex> lock(log_mutex_);
    
    // Check if we need to rotate (daily rotation)
    rotate_log_file();
    
    // Format log message
    std::string timestamp = get_timestamp();
    std::string level_str = level_to_string(level);
    
    std::ostringstream log_line;
    log_line << timestamp << " | " << level_str << " | ";
    
    if (!context.empty()) {
        log_line << "[" << context << "] ";
    }
    
    log_line << message;
    
    // Write to console
    if (level >= LogLevel::WARNING) {
        std::cerr << log_line.str() << std::endl;
    } else {
        std::cout << log_line.str() << std::endl;
    }
    
    // Write to file
    if (log_file_.is_open()) {
        log_file_ << log_line.str() << std::endl;
        log_file_.flush(); // Ensure immediate write
    }
}

void Logger::debug(const std::string& message, const std::string& context) {
    log(LogLevel::DEBUG, message, context);
}

void Logger::info(const std::string& message, const std::string& context) {
    log(LogLevel::INFO, message, context);
}

void Logger::warning(const std::string& message, const std::string& context) {
    log(LogLevel::WARNING, message, context);
}

void Logger::error(const std::string& message, const std::string& context) {
    log(LogLevel::ERROR_LEVEL, message, context);
}

void Logger::log_request(const std::string& method, const std::string& path,
                        const std::string& body, size_t body_size) {
    std::ostringstream msg;
    msg << ">>> " << method << " " << path;
    info(msg.str(), "REQUEST");
    
    if (!body.empty() && body_size > 0) {
        std::string truncated_body = body;
        if (body.length() > 500) {
            truncated_body = body.substr(0, 500) + "... (truncated)";
        }
        debug("Body: " + truncated_body, "REQUEST");
    }
}

void Logger::log_response(const std::string& path, int status_code,
                         double latency_ms, const std::string& body) {
    std::ostringstream msg;
    msg << "<<< " << path << " - Status: " << status_code
        << " - Time: " << std::fixed << std::setprecision(3) << latency_ms << "ms";
    info(msg.str(), "RESPONSE");
    
    if (!body.empty()) {
        std::string truncated_body = body;
        if (body.length() > 300) {
            truncated_body = body.substr(0, 300) + "... (truncated)";
        }
        debug("Body: " + truncated_body, "RESPONSE");
    }
}

void Logger::cleanup() {
    std::lock_guard<std::mutex> lock(log_mutex_);
    
    if (log_file_.is_open()) {
        info("[LOGGER] Shutting down logger");
        log_file_.close();
    }
}

} // namespace logging
} // namespace openkore_ai
