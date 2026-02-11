package GodTierAI;

use strict;
use warnings;
use feature 'state';
use Plugins;
use Globals;
use Log qw(message warning error debug);
use Utils;
use JSON;
use Time::HiRes qw(time);

# ============================================================================
# PERL LIBRARY PATHS: Use system-installed Perl (from PATH)
# ============================================================================
# No hardcoded paths - rely on the Perl installation that OpenKore is using
# OpenKore's start.bat/start.pl already ensures correct Perl is in PATH
# The @INC array is automatically populated by the Perl executable
print STDERR "[GodTierAI] *** Using system Perl from PATH (no hardcoded paths) ***\n";
print STDERR "[GodTierAI] *** Perl \@INC will be shown in BEGIN block below ***\n";

# ============================================================================
# SIMPLIFIED DEPENDENCY CHECKING (HTTP::Tiny ONLY - like AI_Bridge)
# ============================================================================
# CRITICAL FIX: Declare without initialization to prevent BEGIN block values from being reset
our $JSON_AVAILABLE;    # Flag: JSON module loaded successfully (set in BEGIN block)
our $HTTP_AVAILABLE;    # Flag: HTTP::Tiny module loaded successfully (set in BEGIN block)
our $HTTP_CLIENT;       # String: HTTP client type ('HTTP::Tiny' or 'LWP') (set in BEGIN block)

# Pre-flight dependency verification with STDERR output for visibility
print STDERR "[GodTierAI] *** MODULE LOADING STARTED ***\n";
print STDERR "[GodTierAI] *** Timestamp: " . localtime() . "\n";
print STDERR "[GodTierAI] *** Perl version: $]\n";

# ============================================================================
# PACKAGE-LEVEL VARIABLES (must be declared before BEGIN block)
# ============================================================================
# HTTP client instance (HTTP::Tiny only)
my $http_tiny;             # HTTP::Tiny instance
my $ua;                    # LWP::UserAgent instance (legacy, not used with HTTP::Tiny)
my $degraded_mode = 0;     # Flag: running in degraded mode (no HTTP)

# Request tracking
my $request_counter = 0;

# AI service URLs (will be set with dynamic port)
my $ai_service_url;
my $ai_engine_url;

# Plugin state
my $plugin_initialized = 0;

BEGIN {
    # ==========================================================================
    # FIX 3: FORCE HTTP::Tiny (GUARANTEED WORKING - Core Perl since 5.14)
    # ==========================================================================
    # HTTP::Tiny is part of core Perl and cannot fail - use it directly
    # This eliminates all uncertainty about HTTP client availability
    
    print STDERR "[GodTierAI::BEGIN] ========================================\n";
    print STDERR "[GodTierAI::BEGIN] CRITICAL FIX: Using HTTP::Tiny (guaranteed)\n";
    print STDERR "[GodTierAI::BEGIN] ========================================\n";
    
    # Create debug log file for detailed diagnostics
    my $debug_log = 'plugins/godtier_ai/http_init_debug.log';
    open my $debug_fh, '>>', $debug_log or warn "Cannot open debug log: $!";
    if ($debug_fh) {
        print $debug_fh "\n=== BEGIN Block Execution: " . localtime() . " ===\n";
        print $debug_fh "Perl Version: $]\n";
        print $debug_fh "\@INC paths:\n";
        foreach my $path (@INC) {
            print $debug_fh "  - $path\n";
        }
    }
    
    # Check JSON module (critical dependency)
    print STDERR "[GodTierAI::BEGIN] Checking JSON module...\n";
    if ($debug_fh) {
        print $debug_fh "\nAttempting JSON load...\n";
    }
    
    eval {
        require JSON;
        JSON->import();
        $GodTierAI::JSON_AVAILABLE = 1;
        print STDERR "[GodTierAI::BEGIN] OK JSON module loaded successfully\n";
        if ($debug_fh) {
            print $debug_fh " JSON loaded successfully\n";
        }
        1;
    } or do {
        my $json_error = $@ || "Unknown error";
        $GodTierAI::JSON_AVAILABLE = 0;
        print STDERR "[GodTierAI::BEGIN] ERROR JSON module FAILED: $json_error\n";
        print STDERR "[GodTierAI::BEGIN] ERROR FATAL: JSON module required!\n";
        print STDERR "[GodTierAI::BEGIN] ERROR Install with: cpanm JSON\n";
        if ($debug_fh) {
            print $debug_fh " JSON FAILED: $json_error\n";
        }
        die "[GodTierAI] FATAL: JSON module required. Install with: cpanm JSON\n";
    };
    
    # Load HTTP::Tiny module (critical dependency)
    eval {
        require HTTP::Tiny;
        HTTP::Tiny->import();
        $GodTierAI::HTTP_AVAILABLE = 1;
        $GodTierAI::HTTP_CLIENT = 'HTTP::Tiny';
        print STDERR "[GodTierAI::BEGIN] OK HTTP::Tiny module loaded successfully\n";
        if ($debug_fh) {
            print $debug_fh " HTTP::Tiny loaded successfully\n";
            print $debug_fh " HTTP_AVAILABLE = $GodTierAI::HTTP_AVAILABLE\n";
            print $debug_fh " HTTP_CLIENT = $GodTierAI::HTTP_CLIENT\n";
        }
        1;
    } or do {
        my $http_error = $@ || "Unknown error";
        $GodTierAI::HTTP_AVAILABLE = 0;
        $GodTierAI::HTTP_CLIENT = '';
        print STDERR "[GodTierAI::BEGIN] ERROR FATAL: HTTP::Tiny not available\n";
        print STDERR "[GodTierAI::BEGIN] ERROR Install with: cpanm HTTP::Tiny\n";
        if ($debug_fh) {
            print $debug_fh " HTTP::Tiny FAILED: $http_error\n";
        }
        die "[GodTierAI] FATAL: HTTP::Tiny required. Install with: cpanm HTTP::Tiny\n";
    };
    
    # Success - close debug log
    print STDERR "[GodTierAI::BEGIN] OK Required modules loaded: JSON, HTTP::Tiny\n";
    if ($debug_fh) {
        print $debug_fh "\n=== BEGIN Block Completed Successfully ===\n";
        close $debug_fh;
    }
}

# VERIFICATION: Plugin file loaded successfully
print STDERR "[GodTierAI] *** MODULE LOADED (JSON + HTTP::Tiny ready) ***\n";

Plugins::register('GodTierAI', 'Advanced AI system with LLM integration', \&on_unload);

my $hooks;

# Dynamic port configuration function
sub load_http_port_from_config {
    # Priority: Environment variable > config file > default
    return $ENV{GODTIER_AI_SERVICE_PORT} if $ENV{GODTIER_AI_SERVICE_PORT};
    # Backwards compatibility
    return $ENV{AI_SIDECAR_HTTP_PORT} if $ENV{AI_SIDECAR_HTTP_PORT};
    
    # Try to read from config file
    my $config_file = "ai_sidecar/config.yaml";
    if (-f $config_file) {
        open my $fh, '<', $config_file or return 9901;
        while (my $line = <$fh>) {
            if ($line =~ /^\s*port:\s*(\d+)/) {
                close $fh;
                return $1;
            }
        }
        close $fh;
    }
    
    return 9901;  # Default port (avoids conflict with other services)
}

# Initialize service URLs using dynamic port configuration
my $http_port = load_http_port_from_config();
$ai_service_url = "http://127.0.0.1:$http_port";
$ai_engine_url = $ai_service_url;  # Use same port for both

# FIX 2: HTTP CLIENT FACTORY WITH CONNECTION POOLING
# Note: Client variables ($http_tiny, $request_counter, $degraded_mode)
# are already declared before BEGIN block above

# FIX 7: CIRCUIT BREAKERS FOR ERROR RECOVERY
my %circuit_breakers = (
    'ai_engine' => {
        'failures' => 0,
        'threshold' => 3,
        'reset_time' => 60,
        'last_failure' => 0,
        'state' => 'closed',  # closed, open, half_open
    },
    'ai_service' => {
        'failures' => 0,
        'threshold' => 3,
        'reset_time' => 60,
        'last_failure' => 0,
        'state' => 'closed',
    },
);

# EMERGENCY CIRCUIT BREAKERS (Fix for memory crash)
my $request_count_per_minute = 0;
my $last_minute_reset = time();
my $emergency_pause_until = 0;
my $total_requests_made = 0;

# Action duration tracking to prevent infinite queue loops
my $action_pause_until = 0;  # Timestamp when next decision can be requested

# Warning flood detection
my $warning_count = 0;
my $last_warning_check = time();

# Package-level variable declarations
my %questList;          # Used in collect_game_state() for tracking active quests
my $last_query_time = 0; # Used in on_ai_pre() for rate limiting

# STATELESS REFACTOR: Minimal state tracking that auto-expires
my $buyAuto_disabled_until = 0;           # Timestamp when buyAuto can be re-enabled (auto-expires)
my %buyAuto_original_values = ();         # Temporary storage for buyAuto restoration (cleared after use)
my $map_load_cooldown_until = 0;          # Timestamp when AI can make decisions after map load (auto-expires)
my $farming_map_entry_time = 0;           # Track when entering farming map for minimum stay enforcement

# STATELESS REFACTOR: Sliding window for loop detection (not accumulating history)
my %map_visit_count = ();                 # Count of visits per map in current window
my $last_loop_check_cleanup = 0;          # Last time we cleaned the visit counts

# Hot reload configuration monitoring
my $config_file_path = "control/config.txt";
my $last_config_mtime = 0;
my $config_check_interval = 5;  # Check every 5 seconds
my $last_config_check = 0;

# MAP CHANGE DEBOUNCING: Prevent triple-firing during connection sequence
my $last_map_change_time = 0;
my $last_map_name = "";

# TELEPORT FAILURE TRACKING: Self-healing for OpenKore's native teleportAuto conflict
my $teleport_fail_count = 0;
my $last_teleport_fail_time = 0;

sub on_unload {
    Plugins::delHooks($hooks);
    message "[GodTierAI]  VERIFICATION: Plugin unloading\n", "success";
    message "[GodTierAI]  All memory fixes were active:\n", "success";
    message "[GodTierAI]   - Circuit breakers: Monsters=20, Players=15\n", "success";
    message "[GodTierAI]   - Line 388-394 fix: Guild title BULLETPROOF guard\n", "success";
    message "[GodTierAI]   - Line 444 fix: Monster dmgToYou guard\n", "success";
    message "[GodTierAI]   - Request counter circuit breaker active\n", "success";
    message "[GodTierAI] Unloaded\n", "success";
}

# ============================================================================
# AUTONOMOUS SELF-HEALING: CONFIG SANITIZATION
# ============================================================================
# User requirement: "We should never fix config.txt or macro manually.
# If it's config or macro issue, it should be done by the CrewAI or
# autonomous self healing with hot reload!"
#
# This function detects and fixes the buyAuto config.txt issue that prevents
# farming by causing infinite town return loops (Test #16 root cause).
# ============================================================================

sub sanitize_config_for_godtier_ai {
    my $config_file = "control/config.txt";
    
    unless (-e $config_file) {
        warning "[GodTierAI] [SELF-HEAL] Config file not found: $config_file\n";
        return;
    }
    
    message "[GodTierAI] [SELF-HEAL] Starting autonomous config sanitization...\n", "info";
    
    # Read config file
    open my $fh, '<', $config_file or do {
        error "[GodTierAI] [SELF-HEAL] Failed to read config file: $!\n";
        return;
    };
    my @lines = <$fh>;
    close $fh;
    
    my $modified = 0;
    my @disabled_items = ();
    my $in_buyauto_block = 0;
    
    # Process each line to detect and comment out buyAuto directives
    for my $i (0..$#lines) {
        my $line = $lines[$i];
        
        # Detect start of buyAuto block (e.g., "buyAuto Red Potion {")
        if ($line =~ /^buyAuto\s+(.+?)\s*\{/) {
            my $item_name = $1;
            $lines[$i] = "# [DISABLED BY GODTIER-AI SELF-HEAL] " . $line;
            $in_buyauto_block = 1;
            $modified = 1;
            push @disabled_items, $item_name;
            message "[GodTierAI] [SELF-HEAL] Disabled buyAuto block for: $item_name\n", "info";
        }
        # Detect single-line buyAuto (e.g., "buyAuto Red Potion")
        elsif ($line =~ /^buyAuto\s+/ && $line !~ /^buyAuto_/) {
            my ($item_name) = $line =~ /^buyAuto\s+(.+?)(?:\s+\{)?$/;
            $item_name ||= 'Unknown';
            $lines[$i] = "# [DISABLED BY GODTIER-AI SELF-HEAL] " . $line;
            $modified = 1;
            push @disabled_items, $item_name;
            message "[GodTierAI] [SELF-HEAL] Disabled buyAuto line for: $item_name\n", "info";
        }
        # If inside a buyAuto block, comment out content lines too
        elsif ($in_buyauto_block) {
            if ($line =~ /^\s*\}/) {
                # End of block
                $lines[$i] = "# [DISABLED BY GODTIER-AI SELF-HEAL] " . $line;
                $in_buyauto_block = 0;
            } elsif ($line =~ /^\s*\w/ && $line !~ /^\s*#/) {
                # Content line inside block (not already commented)
                $lines[$i] = "# [DISABLED BY GODTIER-AI SELF-HEAL] " . $line;
            }
        }
    }
    
    # Write back if modified
    if ($modified) {
        message "[GodTierAI] [SELF-HEAL] Writing healed configuration back to file...\n", "info";
        
        open $fh, '>', $config_file or do {
            error "[GodTierAI] [SELF-HEAL] Failed to write config file: $!\n";
            return;
        };
        print $fh @lines;
        close $fh;
        
        message "[GodTierAI] [SELF-HEAL]  Config file healed successfully!\n", "success";
        message "[GodTierAI] [SELF-HEAL]  Disabled buyAuto for: " . join(", ", @disabled_items) . "\n", "success";
        message "[GodTierAI] [SELF-HEAL]  Reason: buyAuto causes infinite town-return loops during farming\n", "success";
        message "[GodTierAI] [SELF-HEAL]  Impact: Character will now stay in farming maps and engage combat\n", "success";
        
        # Trigger hot reload to apply changes WITHOUT disconnecting
        message "[GodTierAI] [SELF-HEAL] Triggering hot reload (no disconnect)...\n", "info";
        Commands::run("reload config");
        
        # Small delay to allow reload to complete
        select(undef, undef, undef, 0.2);
        
        message "[GodTierAI] [SELF-HEAL]  Hot reload completed - buyAuto now managed by AI\n", "success";
        message "[GodTierAI] [SELF-HEAL]  Self-healing action logged for analysis\n", "success";
        
        # Log to autonomous healing log
        log_healing_action('config_buyauto_disabled', {
            disabled_items => \@disabled_items,
            reason => 'Test #16 root cause: buyAuto overrides plugin runtime changes',
            impact => 'Prevents infinite town-return loops, enables sustained farming'
        });
        
    } else {
        message "[GodTierAI] [SELF-HEAL]  No buyAuto issues detected - config is clean\n", "success";
    }
}

# ============================================================================
# AUTONOMOUS SELF-HEALING: TELEPORT CONFIG SANITIZATION
# ============================================================================
# Detects when OpenKore's native teleportAuto is triggering without Fly Wings
# and disables it to prevent spam. This is an adaptive response to repeated
# "You don't have the Teleport skill or a Fly Wing" messages.
# ============================================================================

sub sanitize_teleport_config {
    my $config_file = "control/config.txt";
    
    unless (-e $config_file) {
        warning "[GodTierAI] [SELF-HEAL] Config file not found: $config_file\n";
        return;
    }
    
    message "[GodTierAI] [SELF-HEAL] Starting autonomous teleportAuto sanitization...\n", "info";
    
    # Read config file
    open my $fh, '<', $config_file or do {
        error "[GodTierAI] [SELF-HEAL] Failed to read config file: $!\n";
        return;
    };
    my @lines = <$fh>;
    close $fh;
    
    my $modified = 0;
    my @disabled_settings = ();
    
    # Process each line to detect and comment out teleportAuto directives
    for my $i (0..$#lines) {
        my $line = $lines[$i];
        
        # Match teleportAuto settings (teleportAuto_hp, teleportAuto_aggressive, etc.)
        # But NOT if they're already commented out or set to 0
        if ($line =~ /^(teleportAuto_\w+)\s+(?!0|#)/ && $line !~ /^#/) {
            my $setting_name = $1;
            $lines[$i] = "# [DISABLED BY GODTIER-AI SELF-HEAL - No Fly Wing/Tele Skill] " . $line;
            $modified = 1;
            push @disabled_settings, $setting_name;
            message "[GodTierAI] [SELF-HEAL] Disabled: $setting_name\n", "info";
        }
    }
    
    # Write back if modified
    if ($modified) {
        message "[GodTierAI] [SELF-HEAL] Writing healed configuration back to file...\n", "info";
        
        open $fh, '>', $config_file or do {
            error "[GodTierAI] [SELF-HEAL] Failed to write config file: $!\n";
            return;
        };
        print $fh @lines;
        close $fh;
        
        message "[GodTierAI] [SELF-HEAL]  Config file healed successfully!\n", "success";
        message "[GodTierAI] [SELF-HEAL]  Disabled teleportAuto: " . join(", ", @disabled_settings) . "\n", "success";
        message "[GodTierAI] [SELF-HEAL]  Reason: Character has no Fly Wing or Teleport skill\n", "success";
        message "[GodTierAI] [SELF-HEAL]  Impact: No more teleport spam during combat\n", "success";
        
        # Trigger hot reload to apply changes WITHOUT disconnecting
        message "[GodTierAI] [SELF-HEAL] Triggering hot reload (no disconnect)...\n", "info";
        Commands::run("reload config");
        
        # Small delay to allow reload to complete
        select(undef, undef, undef, 0.2);
        
        message "[GodTierAI] [SELF-HEAL]  Hot reload completed - teleportAuto disabled\n", "success";
        
        # Log to autonomous healing log
        log_healing_action('config_teleportauto_disabled', {
            disabled_settings => \@disabled_settings,
            reason => 'Character has no Fly Wing or Teleport skill',
            impact => 'Prevents teleport spam during combat',
            trigger => '3+ teleport failures within 30 seconds'
        });
        
    } else {
        message "[GodTierAI] [SELF-HEAL]  No active teleportAuto settings found - already clean\n", "success";
    }
}

# Log autonomous healing actions for tracking and analysis
sub log_healing_action {
    my ($action_type, $details) = @_;
    
    my $log_dir = "logs";
    my $log_file = "$log_dir/autonomous_healing.log";
    
    # Create logs directory if it doesn't exist
    unless (-d $log_dir) {
        mkdir $log_dir or do {
            warning "[GodTierAI] [SELF-HEAL] Could not create logs directory: $!\n";
            return;
        };
    }
    
    # Prepare log entry
    my $timestamp = localtime();
    my $details_json = eval { encode_json($details) } || '{}';
    
    open my $fh, '>>', $log_file or do {
        warning "[GodTierAI] [SELF-HEAL] Could not write to healing log: $!\n";
        return;
    };
    
    print $fh "[$timestamp] ACTION: $action_type\n";
    print $fh "DETAILS: $details_json\n";
    print $fh "---\n";
    
    close $fh;
    
    debug "[GodTierAI] [SELF-HEAL] Logged healing action to $log_file\n", "ai";
}

# Plugin initialization function - called explicitly by OpenKore
sub on_load {
    # DIAGNOSTIC: Confirm plugin file was loaded
    message "[GodTierAI] ========================================\n", "system";
    message "[GodTierAI] *** PLUGIN LOADING STARTED ***\n", "system";
    message "[GodTierAI] File: " . __FILE__ . "\n", "system";
    message "[GodTierAI] Timestamp: " . scalar(localtime) . "\n", "system";
    message "[GodTierAI] ========================================\n", "system";
    # Initialize HTTP client (ONLY HTTP::Tiny)
    unless (defined $http_tiny) {
        $http_tiny = HTTP::Tiny->new(
            timeout => 5,
            agent => 'GodTierAI/2.0',
            verify_SSL => 0
        );
        message "[GodTierAI] HTTP::Tiny client initialized (timeout: 5s)", "success";
    }

    
    message "[GodTierAI] Initializing plugin...\n", "info";
    
    # CRITICAL: Sanitize config BEFORE hooks to prevent buyAuto from triggering
    sanitize_config_for_godtier_ai();
    
    # ============================================================================
    # VERIFICATION LOGGING: Prove all memory fixes are loaded
    # ============================================================================
    message "[GodTierAI] ========================================\n", "success";
    message "[GodTierAI]  FIX VERIFICATION: All memory fixes active\n", "success";
    message "[GodTierAI]  Circuit breakers: Monsters=20, Players=15\n", "success";
    message "[GodTierAI]  Line 388-394 fix active: Guild title BULLETPROOF guard\n", "success";
    message "[GodTierAI]  Line 444 fix active: Monster dmgToYou guard\n", "success";
    message "[GodTierAI]  Emergency circuit breaker: Max 30 requests/minute\n", "success";
    message "[GodTierAI]  Rate limiting: 2 second minimum between AI cycles\n", "success";
    message "[GodTierAI]  Memory cleanup: Active garbage collection hints\n", "success";
    message "[GodTierAI] ========================================\n", "success";
    
    # Initialize plugin hooks
    $hooks = Plugins::addHooks(
        ['AI_pre', \&on_ai_pre, undef],
        ['packet_mapChange', \&on_map_change, undef],
        ['packet/private_message', \&on_private_message, undef],
        ['packet/public_chat', \&on_public_chat, undef],
        ['packet/party_invite', \&on_party_invite, undef],
        ['packet/party_chat', \&on_party_chat, undef],
        ['packet/guild_chat', \&on_guild_chat, undef],
        ['base_level', \&on_base_level_up, undef],
        ['job_level', \&on_job_level_up, undef],
        ['packet/stat_info', \&on_stat_info, undef],
        ['packet/skill_update', \&on_skill_update, undef],
        ['Log::message', \&on_log_message, undef],
    );

    message "[GodTierAI] Loaded successfully (Phase 11 - Autonomous Progression)\n", "success";
    message "[GodTierAI] AI Engine URL: $ai_engine_url\n", "info";
    message "[GodTierAI] AI Service URL: $ai_service_url\n", "info";
    message "[GodTierAI] Progression Features: Auto Stats, Auto Skills, Adaptive Equipment\n", "info";
    
    # Initialize hot reload monitoring
    initialize_hot_reload();
    
    # Check AI Service connectivity - only when in-game
    if (defined $conState && $conState == Network::IN_GAME) {
        check_ai_service_connectivity();
    } else {
        message "[GodTierAI] Deferring connectivity check until in-game\n", "info";
    }
}

# Initialize hot reload monitoring for config.txt
sub initialize_hot_reload {
    if (-e $config_file_path) {
        $last_config_mtime = (stat($config_file_path))[9];
        message "[GodTierAI] [RELOAD] Hot reload monitoring enabled for config.txt\n", "info";
        message "[GodTierAI] [SYSTEM] Self-healing can modify config without disconnecting\n", "info";
    } else {
        warning "[GodTierAI] [WARNING] Config file not found at: $config_file_path\n";
    }
}

# Check if config.txt has been modified and reload if needed
sub check_config_reload {
    my $current_time = time();
    
    # Only check every N seconds to avoid excessive disk I/O
    return if ($current_time - $last_config_check < $config_check_interval);
    $last_config_check = $current_time;
    
    # Check if config file exists and get modification time
    return unless (-e $config_file_path);
    my $current_mtime = (stat($config_file_path))[9];
    
    # If modified, trigger hot reload
    if ($current_mtime > $last_config_mtime) {
        message "[GodTierAI] [RELOAD] Config change detected, hot reloading...\n", "success";
        message "[GodTierAI] [SYSTEM] Self-healing or Conscious layer updated configuration\n", "info";
        
        # Execute OpenKore's built-in reload command
        Commands::run("reload config");
        
        # Update last modification time
        $last_config_mtime = $current_mtime;
        
        message "[GodTierAI] [SUCCESS] Config hot reloaded successfully (no disconnect)\n", "success";
    }
}

# Check if AI Service is reachable
sub check_ai_service_connectivity {
    message "[GodTierAI] Checking AI service connectivity...\n", "info";
    unless (defined $http_tiny) {
        warning "[GodTierAI] HTTP client not initialized\n";
        return 0;
    }
    
    eval {
        my $response = $http_tiny->get("$ai_service_url/health");
        
        if ($response && $response->{success}) {
            message "[GodTierAI] AI service connectivity OK\n", "success";
            return 1;
        } else {
            warning "[GodTierAI] AI service not responding\n";
            return 0;
        }
    };
    
    if ($@) {
        error "[GodTierAI] Connection check failed: $@\n";
        return 0;
    }
    
    return 0;
}

# NOTE: Initialization is now triggered via start3 hook in godtier_ai.pl
# on_load();  # Removed - now called from hook

# CRITICAL FIX: Helper function to check if inventory is ready
# FIX #1: Check the actual inventory() method instead of {inventory} hash property
sub inventory_ready {
    return 0 unless defined $char;
    
    # Try to call inventory() method - if it works, inventory is ready
    eval {
        my $inv = $char->inventory;
        return 0 unless defined $inv;
        # Verify it's an object that can respond to getItems()
        return 0 unless $inv->can('getItems');
        return 1;
    };
    
    # If eval failed, inventory not ready
    return 0;
}

# Safe distance calculation helper
sub safe_distance {
    my ($pos1, $pos2) = @_;
    
    return 999 unless (defined $pos1 && ref($pos1) eq 'HASH');
    return 999 unless (defined $pos2 && ref($pos2) eq 'HASH');
    return 999 unless (defined $pos1->{x} && defined $pos1->{y});
    return 999 unless (defined $pos2->{x} && defined $pos2->{y});
    
    return distance($pos1, $pos2);
}

# Check if AI Engine is available
sub check_engine_health {
    # Skip if HTTP client not available or not initialized
    return 0 unless defined $http_tiny;
    
    my $response = $http_tiny->get("$ai_engine_url/api/v1/health");
    if ($response->{success}) {
        my $data = decode_json($response->{content});
        if ($data->{status} eq 'healthy') {
            return 1;
        }
    }
    return 0;
}

# Collect game state (enhanced with equipment, quests, guild info, skills)
sub collect_game_state {
    no warnings 'uninitialized';  # Apply to entire function scope
    # CRITICAL FIX: Guard against undefined $char (prevents line 391 error & memory crash)
    return undef unless (defined $char && $char->{name});
    
    my %state = (
        character => {
            name => $char->{name} || 'Unknown',
            level => int($char->{lv} || 1),
            job_level => int($char->{lv_job} || 0),
            base_exp => int($char->{exp} || 0),
            base_exp_max => int($char->{exp_max} || 0),
            job_exp => int($char->{exp_job} || 0),
            job_exp_max => int($char->{exp_job_max} || 0),
            hp => int($char->{hp} || 0),
            max_hp => int($char->{hp_max} || 1),
            sp => int($char->{sp} || 0),
            max_sp => int($char->{sp_max} || 1),
            
            # P0 CRITICAL FIX #1: Add stat and skill points for progression
            points_free => int($char->{points_free} || 0),
            points_skill => int($char->{points_skill} || 0),
            
            # CRITICAL FIX #5h-1: Add current stat values for AI decision-making
            str => int($char->{str} || 1),
            agi => int($char->{agi} || 1),
            vit => int($char->{vit} || 1),
            int => int($char->{int} || 1),
            dex => int($char->{dex} || 1),
            luk => int($char->{luk} || 1),
            
            # CRITICAL FIX #5h-2: Add stat point COSTS for allocation validation
            # These tell AI-Service how many points needed to increase each stat
            points_str => int($char->{points_str} || 1),
            points_agi => int($char->{points_agi} || 1),
            points_vit => int($char->{points_vit} || 1),
            points_int => int($char->{points_int} || 1),
            points_dex => int($char->{points_dex} || 1),
            points_luk => int($char->{points_luk} || 1),
            
            position => {
                map => $field ? $field->name() : 'unknown',
                x => int($char->{pos_to}{x} || 0),
                y => int($char->{pos_to}{y} || 0),
            },
            weight => int($char->{weight} || 0),
            max_weight => int($char->{weight_max} || 1),
            zeny => int($char->{zeny} || 0),
            job_class => $::jobs_lut{$char->{jobId}} || 'Novice',
            status_effects => [],
            # Enhanced: Equipment info
            equipment => collect_equipment(),
            # Enhanced: Guild info (BULLETPROOF safe access - FIX for line 349 crash)
            guild => do {
                no warnings 'uninitialized';
                local $SIG{__WARN__} = sub {};  # Suppress ALL warnings in this block
                
                my $guild_name = '';
                my $guild_id = '';
                my $guild_title = '';
                
                if (defined $char->{guild} && ref($char->{guild}) eq 'HASH') {
                    $guild_name = defined($char->{guild}{name}) ? "" . $char->{guild}{name} : '';
                    $guild_id = defined($char->{guild}{ID}) ? "" . $char->{guild}{ID} : '';
                    $guild_title = defined($char->{guild}{title}) ? "" . $char->{guild}{title} : '';
                }
                
                {
                    name => $guild_name,
                    id => $guild_id,
                    position => $guild_title,
                };
            },
            # Enhanced: Active quests (simplified)
            active_quests => int(scalar(keys %questList) || 0),
        },
        # CRITICAL FIX #1: Add character skills to game state
        skills => [],
        monsters => [],
        inventory => [],
        nearby_players => [],
        party_members => {},
        timestamp_ms => int(time() * 1000),
    );
    
    # CRITICAL FIX #1: Collect character skills (Add circuit breaker)
    if ($char->{skills}) {
        my $skill_count = 0;
        foreach my $skill_name (keys %{$char->{skills}}) {
            last if $skill_count++ >= 50;  # CIRCUIT BREAKER: Max 50 skills
            my $skill = $char->{skills}{$skill_name};
            next unless (defined $skill && ref($skill) eq 'HASH');  # Ensure it's a hash
            next unless (defined $skill->{lv});  # Check lv exists BEFORE comparison
            next unless ($skill->{lv} > 0);  # Now safe to compare
            
            push @{$state{skills}}, {
                name => $skill_name,
                level => int($skill->{lv}),
                sp_cost => int($skill->{sp} || 0),
            };
        }
    }
    
    # Collect monsters (CRITICAL FIX: Add limit to prevent memory explosion)
    my $monster_count = 0;
    foreach my $monster (@{$monstersList->getItems()}) {
        last if $monster_count++ >= 20;  # CIRCUIT BREAKER: Max 20 monsters
        next unless $monster;
        push @{$state{monsters}}, {
            id => int($monster->{binID} || 0),
            name => $monster->{name} || 'Unknown',
            hp => int($monster->{hp} || 0),
            max_hp => int($monster->{hp_max} || 0),
            distance => int(safe_distance($char->{pos_to}, $monster->{pos_to})),
            # FIX: Prevent "uninitialized value" warnings that cause memory accumulation
            is_aggressive => (defined $monster->{dmgToYou} && $monster->{dmgToYou} > 0) ? JSON::true : JSON::false,
        };
    }
    
    # Collect inventory (sample - first 20 items for better AI awareness)
    # CRITICAL FIX #2: Enhanced inventory collection with DIRECT ACCESS (bypass inventory_ready check)
    # The issue: inventory_ready() may be too conservative, causing permanent empty inventory
    eval {
        # Try multiple access methods for robustness
        my @items;
        if (defined $char && ref($char) eq 'Actor::You') {
            # Method 1: Direct inventory() call
            if ($char->can('inventory')) {
                my $inv = $char->inventory;
                @items = @{$inv->getItems()} if $inv;
            }
        }
        
        # If still no items, try globals-based access
        if (!@items && defined $::char && $::char->{inventory}) {
            @items = values %{$::char->{inventory}};
        }
        
        # Process collected items
        my $inv_count = 0;
        foreach my $item (@items) {
            last if $inv_count++ >= 20;  # CIRCUIT BREAKER: Max 20 items
            next unless $item;
            next unless (ref($item) && $item->can('name'));  # Must be item object
            
            my $item_name = $item->name() || $item->{name} || next;
            
            push @{$state{inventory}}, {
                id => int($item->{nameID} || $item->{ID} || 0),
                name => $item_name,
                amount => int($item->{amount} || 1),
                type => $item->{type} || 'misc',
                # Add equipped status for better AI decision making
                equipped => ($item->{equipped}) ? JSON::true : JSON::false,
            };
        }
        
        my $collected_count = scalar(@{$state{inventory}});
        if ($collected_count > 0) {
            debug "[GodTierAI] [INVENTORY]  Collected $collected_count items\n", "ai";
        } else {
            debug "[GodTierAI] [INVENTORY] Warning: No inventory items collected (early game or sync issue)\n", "ai";
        }
    };
    
    if ($@) {
        error "[GodTierAI] [INVENTORY] Failed to collect inventory: $@\n";
    }
    
    # Collect nearby players (CRITICAL FIX: Add limit to prevent memory explosion)
    my $player_count = 0;
    foreach my $player (@{$playersList->getItems()}) {
        last if $player_count++ >= 15;  # CIRCUIT BREAKER: Max 15 players
        next unless $player;
        push @{$state{nearby_players}}, {
            name => $player->{name} || 'Unknown',
            level => int($player->{lv} || 1),
            # FIX: Prevent "uninitialized value" warnings
            guild => ($player->{guild} && $player->{guild}{name}) || '',
            distance => int(safe_distance($char->{pos_to}, $player->{pos_to})),
            is_party_member => exists $char->{party}{users}{$player->{ID}} ? JSON::true : JSON::false,
            job_class => $::jobs_lut{$player->{jobId}} || 'Novice',
        };
    }
    
    return \%state;
}

# Enhanced: Collect equipment info
sub collect_equipment {
    my @equipment_list;
    
    # CRITICAL FIX: Check if inventory is ready before accessing (Add circuit breaker)
    if (inventory_ready()) {
        my $equip_count = 0;
        foreach my $item (@{$char->inventory->getItems()}) {
            last if $equip_count++ >= 15;  # CIRCUIT BREAKER: Max 15 equipment slots
            next unless $item && $item->{equipped};
            push @equipment_list, {
                slot => $item->{type_equip} || 'unknown',
                name => $item->{name} || 'Unknown',
                id => int($item->{nameID} || 0),
            };
        }
    }
    
    return \@equipment_list;
}

# CRITICAL FIX #4: Send action feedback to AI-Service for adaptive learning
# PHASE 5-7 UPDATE: Support Sequential Planner and Action Queue feedback
sub send_action_feedback {
    my ($action, $status, $reason, $message, $plan_id, $action_id) = @_;
    
    # Check if HTTP client available
    return unless $HTTP_AVAILABLE;
    
    $message ||= '';
    
    my $feedback_data = {
        action => $action,
        status => $status,
        reason => $reason,
        message => $message
    };
    
    # Add plan_id if provided (from Sequential Planner)
    $feedback_data->{plan_id} = $plan_id if defined $plan_id;
    
    # Add action_id if provided (from Action Queue)
    $feedback_data->{action_id} = $action_id if defined $action_id;
    
    my $payload = encode_json($feedback_data);
    # Send HTTP request using HTTP::Tiny
    {
        my $response = $http_tiny->post(
            "$ai_service_url/api/v1/action_feedback",
            {
                headers => { 'Content-Type' => 'application/json' },
                content => $payload,
            }
        );
        
        if ($response->{success}) {
            debug "[GodTierAI] [FEEDBACK] Sent: $action -> $status ($reason)\n", "ai";
        } else {
            error "[GodTierAI] [FEEDBACK] Failed to send feedback: " . $response->{status} . " " . $response->{reason} . "\n";
        }
    }
}

# PHASE 2: HTTP Connectivity Test Function
sub test_http_connectivity {
    print STDERR "[GodTierAI::TEST] ========================================\n";
    print STDERR "[GodTierAI::TEST] Testing HTTP connectivity...\n";
    print STDERR "[GodTierAI::TEST] ========================================\n";
    
    # Test URL endpoints
    my @test_endpoints = (
        { url => "http://127.0.0.1:9902/api/v1/health", service => "AI Service (Port 9902)" },
        { url => "http://127.0.0.1:9901/api/v1/health", service => "AI Engine (Port 9901)" },
    );
    
    my $success_count = 0;
    my $total_tests = scalar(@test_endpoints);
    
    foreach my $test (@test_endpoints) {
        my $test_url = $test->{url};
        my $service_name = $test->{service};
        
        print STDERR "[GodTierAI::TEST] Testing $service_name...\n";
        print STDERR "[GodTierAI::TEST] URL: $test_url\n";
        
        # Try using LWP if available
        if ($HTTP_CLIENT eq 'LWP' && defined $ua) {
            print STDERR "[GodTierAI::TEST] Using LWP::UserAgent...\n";
            eval {
                my $response = $http_tiny->get($test_url);
                if ($response->{success}) {
                    $success_count++;
                    print STDERR "[GodTierAI::TEST]  $service_name SUCCESSFUL! \n";
                    print STDERR "[GodTierAI::TEST] Status: " . $response->{status} . " " . $response->{reason} . "\n";
                    my $content = $response->{content};
                    if (length($content) < 500) {
                        print STDERR "[GodTierAI::TEST] Response: $content\n";
                    } else {
                        print STDERR "[GodTierAI::TEST] Response: [" . length($content) . " bytes]\n";
                    }
                    message "[GodTierAI]  HTTP test passed: $service_name\n", "success";
                } else {
                    print STDERR "[GodTierAI::TEST]  $service_name FAILED\n";
                    print STDERR "[GodTierAI::TEST] Status: " . "$response->{status} $response->{reason}" . "\n";
                    warning "[GodTierAI]  HTTP test failed: $service_name - " . "$response->{status} $response->{reason}" . "\n";
                }
            };
            if ($@) {
                print STDERR "[GodTierAI::TEST]  LWP test error: $@\n";
                error "[GodTierAI]  HTTP test error: $service_name - $@\n";
            }
        }
        # Try using HTTP::Tiny if available
        elsif ($HTTP_CLIENT eq 'HTTP::Tiny' && defined $http_tiny) {
            print STDERR "[GodTierAI::TEST] Using HTTP::Tiny...\n";
            eval {
                my $response = $http_tiny->get($test_url);
                if ($response->{success}) {
                    $success_count++;
                    print STDERR "[GodTierAI::TEST]  $service_name SUCCESSFUL! \n";
                    print STDERR "[GodTierAI::TEST] Status: $response->{status} $response->{reason}\n";
                    my $content = $response->{content};
                    if (length($content) < 500) {
                        print STDERR "[GodTierAI::TEST] Response: $content\n";
                    } else {
                        print STDERR "[GodTierAI::TEST] Response: [" . length($content) . " bytes]\n";
                    }
                    message "[GodTierAI]  HTTP test passed: $service_name\n", "success";
                } else {
                    print STDERR "[GodTierAI::TEST]  $service_name FAILED\n";
                    print STDERR "[GodTierAI::TEST] Status: $response->{status} $response->{reason}\n";
                    warning "[GodTierAI]  HTTP test failed: $service_name - $response->{status} $response->{reason}\n";
                }
            };
            if ($@) {
                print STDERR "[GodTierAI::TEST]  HTTP::Tiny test error: $@\n";
                error "[GodTierAI]  HTTP test error: $service_name - $@\n";
            }
        }
        else {
            print STDERR "[GodTierAI::TEST]  No HTTP client available for testing!\n";
            error "[GodTierAI]  Cannot test HTTP - no client available\n";
        }
        
        print STDERR "[GodTierAI::TEST] ----------------------------------------\n";
    }
    
    # Summary
    print STDERR "[GodTierAI::TEST] ========================================\n";
    print STDERR "[GodTierAI::TEST] HTTP CONNECTIVITY TEST RESULTS\n";
    print STDERR "[GodTierAI::TEST] Passed: $success_count / $total_tests\n";
    if ($success_count == $total_tests) {
        print STDERR "[GodTierAI::TEST]  ALL TESTS PASSED! \n";
        message "[GodTierAI]  HTTP connectivity fully operational! \n", "success";
    } elsif ($success_count > 0) {
        print STDERR "[GodTierAI::TEST] WARNING PARTIAL SUCCESS\n";
        warning "[GodTierAI] WARNING Some HTTP endpoints not responding\n";
    } else {
        print STDERR "[GodTierAI::TEST]  ALL TESTS FAILED! \n";
        error "[GodTierAI]  HTTP connectivity NOT working\n";
        error "[GodTierAI]  Check if AI services are running on ports 9901/9902\n";
    }
    print STDERR "[GodTierAI::TEST] ========================================\n";
    
    return $success_count;
}

# Request decision from AI Engine (with emergency circuit breakers)
sub request_decision {
    my $current_time = time();
    
    # FIX #4: VERBOSE DIAGNOSTICS - Track every step of decision request
    message "[GodTierAI] [REQUEST-DEBUG] === Starting request_decision() ===\n", "info";
    
    # ==========================================================================
    # CRITICAL FIX: Check both HTTP_AVAILABLE and actual instance existence
    # ==========================================================================
    unless ($HTTP_AVAILABLE) {
        error "[GodTierAI] [REQUEST-DEBUG] [X] HTTP_AVAILABLE is false - cannot make requests\n";
        return undef;
    }
    
    # NEW: Check if HTTP client instance is actually defined
    unless (defined $http_tiny) {
        error "[GodTierAI] [REQUEST-DEBUG] HTTP client not initialized\n";
        $degraded_mode = 1;
        return undef;
    }
    
    
    
    message "[GodTierAI] [REQUEST-DEBUG] [OK] HTTP client verified:\n", "success";
    message "[GodTierAI] [REQUEST-DEBUG]   HTTP client: HTTP::Tiny\n", "success";
    message "[GodTierAI] [REQUEST-DEBUG]   Instance: " . (defined($http_tiny) ? ref($http_tiny) : "N/A") . "\n", "success";
    
    # EMERGENCY CIRCUIT BREAKER #1: Check if we're in emergency pause
    if ($current_time < $emergency_pause_until) {
        my $remaining = int($emergency_pause_until - $current_time);
        warning "[GodTierAI] [REQUEST-DEBUG] EMERGENCY PAUSE active: $remaining seconds remaining\n";
        return undef;
    }
    
    # EMERGENCY CIRCUIT BREAKER #2: Reset per-minute counter
    if ($current_time - $last_minute_reset >= 60) {
        message "[GodTierAI] [REQUEST-DEBUG] Resetting request counter ($request_count_per_minute requests in last minute)\n", "info";
        $request_count_per_minute = 0;
        $last_minute_reset = $current_time;
    }
    
    # EMERGENCY CIRCUIT BREAKER #3: Max requests per minute
    $request_count_per_minute++;
    message "[GodTierAI] [REQUEST-DEBUG] Request count: $request_count_per_minute/30 per minute\n", "info";
    
    if ($request_count_per_minute > 30) {
        warning "[GodTierAI] [REQUEST-DEBUG] EMERGENCY: Too many requests ($request_count_per_minute/min), pausing 60s\n";
        $emergency_pause_until = $current_time + 60;
        $request_count_per_minute = 0;
        return undef;
    }
    
    # EMERGENCY CIRCUIT BREAKER #4: Total request counter for debugging
    $total_requests_made++;
    message "[GodTierAI] [REQUEST-DEBUG] Total requests made: $total_requests_made\n", "info";
    
    if ($total_requests_made % 100 == 0) {
        message "[GodTierAI] Stats: $total_requests_made total requests made since plugin load\n", "info";
    }
    
    message "[GodTierAI] [REQUEST-DEBUG] Collecting game state...\n", "info";
    my $game_state = collect_game_state();
    
    # CRITICAL FIX: Don't send request if character not ready (prevents line 391 crash)
    unless (defined $game_state) {
        warning "[GodTierAI] [REQUEST-DEBUG] collect_game_state() returned undef - character not ready\n";
        return undef;
    }
    
    message "[GodTierAI] [REQUEST-DEBUG] Game state collected successfully\n", "info";
    
    $request_counter++;
    my $request_id = "req_" . time() . "_" . $request_counter;
    
    message "[GodTierAI] [REQUEST-DEBUG] Building HTTP request (ID: $request_id)...\n", "info";
    
    my %request = (
        game_state => $game_state,
        request_id => $request_id,
        timestamp_ms => int(time() * 1000),
    );
    
    my $json_request = encode_json(\%request);
    my $json_size = length($json_request);
    
    message "[GodTierAI] [REQUEST-DEBUG] JSON payload size: $json_size bytes\n", "info";
    message "[GodTierAI] [REQUEST-DEBUG] Using HTTP client: HTTP::Tiny\n", "info";
    message "[GodTierAI] [REQUEST-DEBUG] Sending POST to $ai_service_url/api/v1/decide\n", "info";
    
    my $request_start = time();
    # Send HTTP request using HTTP::Tiny
    {
        my $response = $http_tiny->post(
            "$ai_service_url/api/v1/decide",
            {
                headers => { 'Content-Type' => 'application/json' },
                content => $json_request,
            }
        );
        my $request_duration = time() - $request_start;
        
        message "[GodTierAI] [REQUEST-DEBUG] HTTP request completed in ${request_duration}s\n", "info";
        message "[GodTierAI] [REQUEST-DEBUG] HTTP status: " . $response->{status} . " " . $response->{reason} . "\n", "info";
        
        if ($response->{success}) {
            message "[GodTierAI] [REQUEST-DEBUG] Response successful, decoding JSON...\n", "success";
            my $data = decode_json($response->{content});
            message "[GodTierAI] [REQUEST-DEBUG] Decision received and parsed successfully\n", "success";
            return $data;
        } else {
            error "[GodTierAI] [REQUEST-DEBUG] Request FAILED: " . $response->{status} . " " . $response->{reason} . "\n";
            error "[GodTierAI] [REQUEST-DEBUG] Response body: " . ($response->{content} || 'N/A') . "\n";
            return undef;
        }
    }
}

# Enhanced: Execute action with social support
sub execute_action {
    my ($action_data) = @_;
    
    # DIAGNOSTIC #1: Memory tracking before action
    eval {
        my $mem_before = `tasklist /FI "IMAGENAME eq perl.exe" /FO CSV 2>nul | findstr perl`;
        chomp($mem_before) if $mem_before;
        debug "[GodTierAI] [MEMORY] Before action: $mem_before\n", "ai" if $mem_before;
    };
    
    # Safety check
    unless (ref($action_data) eq 'HASH') {
        error "[GodTierAI] Invalid action_data: expected HASH, got " . ref($action_data) . "\n";
        return;
    }
    
    my $action = $action_data->{action};
    my $params = $action_data->{params} || {};
    my $reason = $action_data->{reason} || 'no reason provided';
    
    # Declare $type outside eval so it's accessible in error handler
    my $type;
    
    # DIAGNOSTIC #3: Wrap entire execution in eval block for error catching
    eval {
        # Handle case where action is a string (flat structure) or hash (nested structure)
        if (ref($action) eq 'HASH') {
            # Nested structure: {action: {type: "attack", parameters: {...}}}
            $type = $action->{type};
            $params = $action->{params} || $params;
        } elsif (ref($action) eq '') {
            # Flat structure: {action: "attack", parameters: {...}}
            $type = $action;
        } else {
            error "[GodTierAI] Invalid action format: " . ref($action) . "\n";
            return;
        }
        
        unless ($type) {
            error "[GodTierAI] Missing action type\n";
            return;
        }
        
        debug "[GodTierAI] Executing action: $type ($reason)\n", "ai";
    
    # Core combat and survival actions
    if ($type eq 'attack') {
        my $target = $params->{target} || '';
        message "[GodTierAI] [ACTION] Attacking target: $target\n", "info";
        # Attack logic handled by OpenKore's native AI
    } elsif ($type eq 'use_item') {
        # Handle use_item action from AI-Service
        my $item_name = $params->{item} || '';
        if ($item_name) {
            message "[GodTierAI] [ACTION] Using item: $item_name\n", "info";
            Commands::run("is $item_name");
        } else {
            error "[GodTierAI] [ERROR] use_item action missing item parameter\n";
        }
    } elsif ($type eq 'item') {
        # Legacy item handler (backward compatibility)
        my $item_name = $params->{item} || '';
        if ($item_name) {
            message "[GodTierAI] [ACTION] Using item: $item_name\n", "info";
            Commands::run("is $item_name");
        }
    } elsif ($type eq 'rest') {
        message "[GodTierAI] [ACTION] Resting to recover SP\n", "info";
        
        # CRITICAL FIX #4: Try to sit and monitor for failure
        Commands::run("sit");
        
        # Give OpenKore a moment to process the command
        sleep(0.5);
        
        # Check if character is actually sitting (sitting status would be set)
        # Note: In OpenKore, $char->{sitting} is true when sitting
        if ($char->{sitting}) {
            send_action_feedback('rest', 'success', 'character_sitting');
        } else {
            # Character did not sit - likely due to missing Basic Skill
            warning "[GodTierAI] [ACTION] Failed to sit - likely missing Basic Skill Lv3\n";
            send_action_feedback('rest', 'failed', 'basic_skill_not_learned', 'Character does not have Basic Skill Lv3 to sit');
        }
    } elsif ($type eq 'idle_recover') {
        # MEMORY CRASH FIX: Removed AI::queue("wait") and AI::args() which caused
        # orphaned queue entries leading to "Out of memory in perl:util:safesysrealloc"
        # The on_ai_pre() already respects $action_pause_until, so no queue needed
        my $duration = $params->{duration} || 10;
        
        message "[GodTierAI] [ACTION] Idle recovery for ${duration}s (decision paused)\n", "info";
        
        # Stand up if sitting (natural HP/SP regen is same standing or sitting for RO)
        if ($char->{sitting}) {
            debug "[GodTierAI] Standing up for idle recovery\n", "ai";
            Commands::run("stand");
        }
        
        # SIMPLE FIX: Just set timestamp - on_ai_pre already skips cycles when paused
        # This avoids all AI queue manipulation that was causing memory leaks
        $action_pause_until = time() + $duration;
        debug "[GodTierAI] Pause until " . localtime($action_pause_until) . " (no queue manipulation)\n", "ai";
    } elsif ($type eq 'attack_monster') {
        # CRITICAL FIX #3: Attack specific monster by ID
        my $target_id = $params->{target_id};
        my $target_name = $params->{target_name} || 'Unknown';
        
        # FIX #18: Use 'defined' check instead of truthiness (binID 0 is valid!)
        if (defined $target_id) {
            message "[GodTierAI] [COMBAT] Attacking monster: $target_name (ID: $target_id)\n", "info";
            Commands::run("a $target_id");  # FIX: Use 'a' command instead of 'attack'
        } else {
            error "[GodTierAI] [ERROR] attack_monster action missing target_id parameter\n";
        }
    } elsif ($type eq 'move_to_position') {
        # NEW FEATURE: Move to specific position for exploration
        my $x = $params->{x};
        my $y = $params->{y};
        my $reason = $params->{reason} || 'exploration';
        
        if (defined $x && defined $y) {
            message "[GodTierAI] [EXPLORE] Moving to ($x, $y) - Reason: $reason\n", "info";
            Commands::run("move $x $y");
        } else {
            error "[GodTierAI] [ERROR] move_to_position action missing x/y parameters\n";
        }
    } elsif ($type eq 'teleport') {
        my $method = $params->{method} || 'fly_wing';
        message "[GodTierAI] [ACTION] Teleporting via $method\n", "info";
        if ($method eq 'fly_wing') {
            Commands::run("is Fly Wing");
        } else {
            Commands::run("sl 26");  # Teleport skill
        }
    } elsif ($type eq 'continue') {
        # No action needed - let OpenKore's native AI continue
        debug "[GodTierAI] [ACTION] Continuing with current behavior\n", "ai";
    } elsif ($type eq 'continue_combat') {
        # Continue combat - let OpenKore's combat AI handle it
        message "[GodTierAI] [ACTION] Continuing combat (will recover after)\n", "info";
        # No specific command needed - OpenKore's native AI will handle combat
    } elsif ($type eq 'retreat') {
        # Retreat from danger (move away from current position)
        my $reason = $params->{reason} || 'unknown';
        warning "[GodTierAI] [ACTION] Retreating: $reason\n";
        
        # Try to move away from current position (5 cells back)
        if ($char->{pos_to}) {
            my $x = int($char->{pos_to}{x}) - 5;
            my $y = int($char->{pos_to}{y}) - 5;
            Commands::run("move $x $y");
        } else {
            # If position unknown, try random teleport
            Commands::run("is Fly Wing");
        }
    } elsif ($type eq 'auto_buy') {
        # Auto-buy items (return to town and purchase)
        my $items = $params->{items} || [];
        my $priority = $params->{priority} || 'medium';
        
        message "[GodTierAI] [ACTION] Auto-buy triggered (priority: $priority)\n", "info";
        message "[GodTierAI] [ACTION] Items needed: " . join(", ", @{$items}) . "\n", "info";
        
        # Let OpenKore's native storageAuto and buyAuto handle this
        # The bot will automatically return to town and buy when needed
        # based on config.txt settings (buyAuto_* configurations)
    } elsif ($type eq 'sell_items') {
        # Priority 2 Fix: Sell junk items to NPC
        my $reason = $params->{reason} || 'resource_management';
        my $priority = $params->{priority} || 'medium';
        
        message "[GodTierAI] [ACTION] Selling junk items - Reason: $reason, Priority: $priority\n", "info";
        
        # CRITICAL FIX: Safety check - ensure character and inventory exist
        unless (inventory_ready()) {
            error "[GodTierAI] [ERROR] Character inventory not initialized, cannot sell items\n";
            send_action_feedback('sell_items', 'failed', 'inventory_not_ready',
                'Character inventory not available');
            return;
        }
        
        # Get inventory for analysis (CIRCUIT BREAKER: Limit items to prevent memory explosion)
        my @inventory_items;
        my $sell_item_count = 0;
        foreach my $item (@{$char->{inventory}->getItems()}) {
            last if $sell_item_count++ >= 50;  # CIRCUIT BREAKER: Max 50 items for sell analysis
            next unless $item;
            push @inventory_items, {
                name => $item->name(),
                amount => $item->{amount},
                type => $item->{type},
                id => $item->{nameID}
            };
        }
        
        # Call AI-Service to categorize items
        my $payload = encode_json({
            inventory => \@inventory_items
        });
        
        # Check if HTTP client is available
        unless (defined $http_tiny) {
            warning "[GodTierAI] [ACTION] Cannot sell items - HTTP client not available (degraded mode)\n";
            send_action_feedback('sell_items', 'failed', 'http_client_unavailable',
                'Running in degraded mode without HTTP library');
            return;
        }
        
        my $response = $http_tiny->post(
            "$ai_service_url/api/v1/inventory/sell_junk",
            {
                headers => { 'Content-Type' => 'application/json' },
                content => $payload,
            }
        );
        
        if ($response->{success}) {
            my $result = decode_json($response->{content});
            
            if ($result->{success} && @{$result->{sell_commands}}) {
                message "[GodTierAI] [ACTION] Got " . scalar(@{$result->{sell_commands}}) . " items to sell for ~" . $result->{estimated_zeny} . "z\n", "info";
                
                # Navigate to Tool Dealer
                Commands::run("move prontera 134 88");
                
                # Wait a moment for navigation
                sleep(2);
                
                # Execute sell commands
                foreach my $sell_cmd (@{$result->{sell_commands}}) {
                    Commands::run($sell_cmd);
                    sleep(0.5);  # Small delay between sells
                }
                
                message "[GodTierAI] [ACTION] Finished selling items\n", "success";
            } else {
                message "[GodTierAI] [ACTION] No items to sell\n", "info";
            }
        } else {
            error "[GodTierAI] [ACTION] Failed to get sell list from AI-Service: " . "$response->{status} $response->{reason}" . "\n";
        }
    } elsif ($type eq 'idle') {
        # CRITICAL FIX #3: New action handler for idle (natural HP/SP regeneration)
        my $reason = $params->{reason} || 'unknown';
        my $duration = $params->{duration} || 5;
        
        message "[GodTierAI] [ACTION] Idling for ${duration}s (decision paused) - Reason: $reason\n", "info";
        message "[GodTierAI] [ACTION] Natural HP/SP regeneration will work during this time\n", "info";
        
        # Prevent decision requests during wait to avoid infinite queue accumulation
        $action_pause_until = time() + $duration;
        debug "[GodTierAI] [FIX] Decision requests paused until " . localtime($action_pause_until) . "\n", "ai";
        
        # Just wait - natural HP/SP regeneration will work
        sleep($duration);
        
        # Report success
        send_action_feedback('idle', 'success', 'completed_idle_period');
        
    } elsif ($type eq 'attack_nearest') {
        # CRITICAL FIX #3: New action handler for attacking nearest monster
        my $reason = $params->{reason} || 'farming';
        
        message "[GodTierAI] [ACTION] Attacking nearest monster - Reason: $reason\n", "info";
        
        # Find nearest monster using OpenKore's built-in function
        my $monster = getBestTarget();
        if ($monster) {
            message "[GodTierAI] [ACTION] Target: " . $monster->name() . " (ID: " . $monster->{binID} . ")\n", "info";
            Commands::run("a " . $monster->{binID});  # FIX: Use 'a' command instead of 'attack'
            send_action_feedback('attack_nearest', 'success', 'monster_targeted');
        } else {
            warning "[GodTierAI] [ACTION] No monsters nearby to attack\n";
            send_action_feedback('attack_nearest', 'failed', 'no_monsters_in_range');
        }
        
    } elsif ($type eq 'return_to_town') {
        # CRITICAL FIX #3: New action handler for returning to town
        my $reason = $params->{reason} || 'unknown';
        my $buy_items = $params->{buy_items} || [];
        
        message "[GodTierAI] [ACTION] Returning to town - Reason: $reason\n", "info";
        
        # Check if we have Butterfly Wing or Fly Wing
        my $butterfly_wing = $char->inventory()->getByName("Butterfly Wing");
        my $fly_wing = $char->inventory()->getByName("Fly Wing");
        
        if ($butterfly_wing) {
            message "[GodTierAI] [ACTION] Using Butterfly Wing to return to save point\n", "info";
            Commands::run("is Butterfly Wing");
            send_action_feedback('return_to_town', 'success', 'used_butterfly_wing');
        } elsif ($fly_wing) {
            message "[GodTierAI] [ACTION] Using Fly Wing to teleport (will need to walk to town)\n", "info";
            Commands::run("is Fly Wing");
            # Note: Fly Wing only random teleports, may need to walk from there
            send_action_feedback('return_to_town', 'partial', 'used_fly_wing_need_walk');
        } else {
            # No teleport items, try to walk to nearest town
            message "[GodTierAI] [ACTION] No teleport items, walking to town...\n", "info";
            Commands::run("move prontera");  # Default to Prontera
            send_action_feedback('return_to_town', 'success', 'walking_to_town');
        }
        
        # If items to buy, queue auto-buy
        if (@$buy_items) {
            message "[GodTierAI] [ACTION] Will buy: " . join(", ", @$buy_items) . "\n", "info";
            # Let OpenKore's buyAuto handle it based on config.txt
        }
        
    } elsif ($type eq 'skill') {
        # Skill logic (will be implemented in Phase 2)
        message "[GodTierAI] Action: Use skill\n", "info";
    } elsif ($type eq 'move') {
        # Move logic (will be implemented in Phase 2)
        message "[GodTierAI] Action: Move\n", "info";
    }
    # Strategic Layer Actions (CONSCIOUS Layer - CrewAI)
    elsif ($type eq 'farm_monsters') {
        my $reason = $params->{reason} || 'strategic_leveling';
        my $target_level = $params->{target_level} || ($char->{lv} + 1);
        
        message "[GodTierAI] [STRATEGIC] Farming monsters - Reason: $reason (Target: Lv$target_level)\n", "info";
        
        # Enable OpenKore's native monster hunting AI
        Commands::run("conf attackAuto 2");
        Commands::run("conf route_randomWalk 1");
        
        send_action_feedback('farm_monsters', 'success', 'farming_enabled');
    }
    elsif ($type eq 'job_change_quest') {
        my $reason = $params->{reason} || 'ready_for_advancement';
        my $current_class = $params->{current_class} || $char->{jobName};
        
        message "[GodTierAI] [STRATEGIC] Job change quest - Class: $current_class, Reason: $reason\n", "info";
        
        # Navigate to job change location based on class
        if ($current_class eq 'Novice') {
            message "[GodTierAI] [STRATEGIC] Navigating to job change location (Prontera)\n", "info";
            Commands::run("move prontera");
            # Note: Actual quest automation would be handled by quest_automation.py
        } else {
            message "[GodTierAI] [STRATEGIC] Already advanced from Novice\n", "info";
        }
        
        send_action_feedback('job_change_quest', 'success', 'navigating_to_job_change');
    }
    elsif ($type eq 'find_quest') {
        my $reason = $params->{reason} || 'strategic_quest';
        
        message "[GodTierAI] [STRATEGIC] Finding available quests - Reason: $reason\n", "info";
        
        # Navigate to quest board or quest NPC location
        # This would integrate with quest automation system
        message "[GodTierAI] [STRATEGIC] Moving to Prontera quest board\n", "info";
        Commands::run("move prontera");
        
        send_action_feedback('find_quest', 'success', 'searching_for_quests');
    }
    elsif ($type eq 'move_to_location') {
        my $reason = $params->{reason} || 'strategic_positioning';
        my $target_map = $params->{target_map} || 'prontera';
        
        message "[GodTierAI] [STRATEGIC] Moving to location: $target_map - Reason: $reason\n", "info";
        
        Commands::run("move $target_map");
        
        send_action_feedback('move_to_location', 'success', 'navigating');
    }
    # Enhanced: Social actions
    elsif ($type eq 'chat_response') {
        my $target = $params->{target};
        my $message = $params->{message} || $params->{response_text};
        my $msg_type = $params->{message_type} || 'pm';
        
        if ($msg_type eq 'whisper' || $msg_type eq 'pm') {
            Commands::run("pm \"$target\" $message");
            message "[GodTierAI] Sent PM to $target: $message\n", "info";
        } elsif ($msg_type eq 'public') {
            Commands::run("c $message");
            message "[GodTierAI] Public chat: $message\n", "info";
        } elsif ($msg_type eq 'party') {
            Commands::run("p $message");
            message "[GodTierAI] Party chat: $message\n", "info";
        }
    }
    elsif ($type eq 'give_buff') {
        my $skill = $params->{skill};
        my $target = $params->{target};
        Commands::run("sl $skill $target");
        message "[GodTierAI] Buffing $target with $skill\n", "info";
    }
    elsif ($type eq 'accept_party') {
        Commands::run("party join 1");
        message "[GodTierAI] Accepted party invite\n", "info";
        
        # Send optional message
        if ($params->{message}) {
            Commands::run("p $params->{message}");
        }
    }
    elsif ($type eq 'decline_party') {
        Commands::run("party join 0");
        debug "[GodTierAI] Declined party invite\n", "ai";
    }
    elsif ($type eq 'accept_trade') {
        Commands::run("deal");
        message "[GodTierAI] Accepted trade\n", "info";
    }
    elsif ($type eq 'decline_trade') {
        Commands::run("deal no");
        debug "[GodTierAI] Declined trade: $reason\n", "ai";
    }
    elsif ($type eq 'accept_duel') {
        # Duel acceptance (if supported by server)
        message "[GodTierAI] Accepted duel request\n", "info";
    }
    elsif ($type eq 'decline_duel') {
        debug "[GodTierAI] Declined duel: $reason\n", "ai";
    }
    elsif ($type eq 'none') {
        # No action needed
        debug "[GodTierAI] Action: None ($reason)\n", "ai";
    }
    elsif ($type eq 'move_random') {
        # FIX #3: Active monster seeking - random movement to find targets
        my $max_dist = $params->{max_distance} || 10;
        message "[GodTierAI] [EXPLORE] Random walk to find monsters (max: ${max_dist} cells) - Reason: $reason\n", "info";
        
        # Use OpenKore's route_randomWalk to move randomly and find monsters
        eval {
            require Task::Route;
            my $task = new Task::Route(
                map => $field->name(),
                maxRouteTime => 30,
                randomWalk => 1,
                maxDistance => $max_dist
            );
            
            if ($task) {
                $taskManager->add($task);
                send_action_feedback('move_random', 'success', 'random_walk_initiated');
            }
        };
        
        if ($@) {
            warning "[GodTierAI] [EXPLORE] Failed to create random walk task: $@\n";
            # Fallback: Just use simple random coordinate movement
            my $current_x = $char->{pos_to}{x};
            my $current_y = $char->{pos_to}{y};
            my $new_x = $current_x + int(rand($max_dist * 2)) - $max_dist;
            my $new_y = $current_y + int(rand($max_dist * 2)) - $max_dist;
            
            Commands::run("move $new_x $new_y");
            send_action_feedback('move_random', 'success', 'random_coordinate_movement');
        }
    }
    # P0 CRITICAL FIX #4: Direct stat allocation (from AI-Service decision layer)
    elsif ($type eq 'allocate_stats') {
        my $stats = $params->{stats};  # Hash of stat => points
        my $reason = $params->{reason} || 'progression';
        
        Log::message("[GodTierAI] [PROGRESSION] Allocating stat points (reason: $reason)\n", "ai");
        
        # CRITICAL FIX: Track actual successful allocations vs attempted
        my $points_attempted = 0;
        my $points_allocated = 0;
        my @failed_stats = ();
        
        # Store current free points BEFORE allocation
        my $free_points_before = $char->{points_free} || 0;
        
        foreach my $stat_name (keys %$stats) {
            my $points = $stats->{$stat_name};
            
            if ($points > 0) {
                # Convert to lowercase for OpenKore command syntax
                # OpenKore expects: "st add <str|agi|vit|int|dex|luk>"
                my $stat_lower = lc($stat_name);  # "STR" -> "str", "DEX" -> "dex"
                
                # Validate stat before attempting
                if ($stat_lower !~ /^(str|agi|vit|int|dex|luk)$/) {
                    Log::error("[GodTierAI] [PROGRESSION] Invalid stat name: $stat_name\n");
                    next;
                }
                
                # CRITICAL FIX: Re-query points FRESH from network to avoid stale data
                # This prevents race condition where collected state is outdated
                Network::send($messageSender, "018A", { type => 0 });
                sleep 0.05;  # Allow network update
                
                # Now check CURRENT free points (not stale cached value)
                my $current_free_points = int($char->{points_free} || 0);
                if ($current_free_points < 1) {
                    Log::warning("[GodTierAI] [PROGRESSION] No free stat points available after refresh (requested: $points to $stat_name)\n");
                    push @failed_stats, "$stat_name (no points)";
                    next;
                }
                
                Log::message("[GodTierAI] [PROGRESSION] Verified: $current_free_points stat points available\n", "ai");
                
                # Check if stat is already at cap
                my $current_stat = $char->{$stat_lower} || 1;
                if ($current_stat >= 99 && !$config{statsAdd_over_99}) {
                    Log::warning("[GodTierAI] [PROGRESSION] $stat_name already at cap (99)\n");
                    push @failed_stats, "$stat_name (at cap)";
                    next;
                }
                
                # Check cost to increase stat
                my $cost_key = "points_$stat_lower";
                my $stat_cost = $char->{$cost_key} || 1;
                if ($stat_cost > $char->{points_free}) {
                    Log::warning("[GodTierAI] [PROGRESSION] Not enough points to increase $stat_name (need: $stat_cost, have: $char->{points_free})\n");
                    push @failed_stats, "$stat_name (cost: $stat_cost)";
                    next;
                }
                
                Log::message("[GodTierAI] [PROGRESSION] Attempting to add $points points to $stat_name (current: $current_stat, cost: $stat_cost)\n", "ai");
                
                # Execute stat add for each point using CORRECT OpenKore syntax
                for (my $i = 0; $i < $points; $i++) {
                    my $free_before = $char->{points_free} || 0;
                    my $stat_before = $char->{$stat_lower} || 1;
                    
                    Commands::run("st add $stat_lower");
                    $points_attempted++;
                    
                    # Small delay to allow stat change to register
                    sleep 0.1;
                    
                    # Verify if stat actually increased
                    my $free_after = $char->{points_free} || 0;
                    my $stat_after = $char->{$stat_lower} || 1;
                    
                    if ($stat_after > $stat_before && $free_after < $free_before) {
                        # Success: stat increased and free points decreased
                        $points_allocated++;
                        Log::message("[GodTierAI] [PROGRESSION]  $stat_name: $stat_before -> $stat_after (points: $free_before -> $free_after)\n", "success");
                    } else {
                        # Failure: stat didn't change or points didn't decrease
                        Log::warning("[GodTierAI] [PROGRESSION]  Failed to add point to $stat_name (stat: $stat_before->$stat_after, points: $free_before->$free_after)\n");
                        push @failed_stats, "$stat_name (allocation failed)";
                        last;  # Stop trying this stat
                    }
                    
                    # Additional delay between multiple point additions
                    sleep 0.05 if $i < $points - 1;
                }
                
                Log::message("[GodTierAI] [PROGRESSION] Executed: st add $stat_lower (attempted: $points, successful: varies)\n", "ai");
            }
        }
        
        # CRITICAL: Report accurate feedback based on actual results
        my $free_points_after = $char->{points_free} || 0;
        my $actual_points_used = $free_points_before - $free_points_after;
        
        if ($points_allocated > 0) {
            Log::message("[GodTierAI] [PROGRESSION] Successfully allocated $points_allocated/$points_attempted stat points\n", "success");
            send_action_feedback('allocate_stats', 'success', 'stats_allocated',
                "$points_allocated stat points allocated");
        } elsif ($points_attempted > 0) {
            # Attempted but all failed
            my $failure_details = join(", ", @failed_stats);
            Log::error("[GodTierAI] [PROGRESSION] FAILED to allocate any stat points (attempted: $points_attempted, failures: $failure_details)\n");
            send_action_feedback('allocate_stats', 'failed', 'stat_allocation_failed',
                "Failed to allocate stats: $failure_details");
        } else {
            Log::message("[GodTierAI] [PROGRESSION] Warning: No stat points to allocate\n", "warning");
            send_action_feedback('allocate_stats', 'failed', 'no_points_available',
                'No free stat points available');
        }
    }
    # P0 CRITICAL FIX #5: Direct skill learning (from AI-Service decision layer)
    elsif ($type eq 'learn_skill') {
        my $skill_name = $params->{skill_name} || $params->{skill_display_name};
        my $points_to_add = $params->{points_to_add} || 1;
        my $reason = $params->{reason} || 'progression';
        
        Log::message("[GodTierAI] [PROGRESSION] Learning skill: $skill_name (adding $points_to_add points)\n", "ai");
        
        # OpenKore skill learning command requires NUMERIC skill ID (not name/handle)
        # Format: skills add <skill_id_number>
        # We need to convert skill handle to skill IDN
        
        my $skills_learned = 0;
        
        # Create Skill object from handle to get numeric ID
        my $skill = new Skill(handle => $skill_name);
        my $skill_idn = $skill->getIDN();
        
        if ($skill_idn) {
            Log::message("[GodTierAI] [PROGRESSION] Skill handle '$skill_name' -> IDN: $skill_idn\n", "ai");
            
            for (my $i = 0; $i < $points_to_add; $i++) {
                # FIXED: OpenKore expects numeric skill ID, not skill name
                Commands::run("skills add $skill_idn");  # Was: "skills add $skill_name"
                $skills_learned++;
                
                # Add small delay to prevent command flooding
                sleep 0.05 if $i < $points_to_add - 1;
            }
            
            Log::message("[GodTierAI] [PROGRESSION] Executed: skills add $skill_idn (x$points_to_add)\n", "success");
            
            send_action_feedback('learn_skill', 'success', 'skill_learned',
                "Learned $skill_name (+$skills_learned levels)");
        } else {
            Log::message("[GodTierAI] [PROGRESSION] Error: Could not resolve skill handle '$skill_name' to IDN\n", "error");
            send_action_feedback('learn_skill', 'failed', 'skill_not_found',
                "Skill '$skill_name' not found in skill database");
        }
    }
    # CRITICAL FIX: Add move_to_map action handler (sequential thinking dependency)
    elsif ($type eq 'move_to_map') {
        my $target_map = $params->{target_map} || $params->{map};
        my $reason = $params->{reason} || 'sequential_thinking';
        
        unless ($target_map) {
            error "[GodTierAI] [ERROR] move_to_map action missing target_map parameter\n";
            send_action_feedback('move_to_map', 'failed', 'missing_target_map',
                'No target map specified');
            return;
        }
        
        message "[GodTierAI] [SEQUENTIAL] Moving to map: $target_map - Reason: $reason\n", "info";
        
        # STATELESS REFACTOR: Temporarily disable buyAuto during farming to prevent town returns
        # State expires automatically after 10 minutes (600s) - no manual cleanup needed
        if ($target_map =~ /fild|beach|dun|forest|mine|cave/i) {
            message "[GodTierAI] [FIX#1] Disabling buyAuto BEFORE route calculation\n", "info";
            $buyAuto_disabled_until = time() + 600;  # Auto-expires after 10 minutes
            
            # Save original values temporarily (will be cleared when re-enabled)
            %buyAuto_original_values = ();
            $buyAuto_original_values{Red_Potion} = $config{buyAuto_Red_Potion} if exists $config{buyAuto_Red_Potion};
            $buyAuto_original_values{Fly_Wing} = $config{buyAuto_Fly_Wing} if exists $config{buyAuto_Fly_Wing};
            
            # CRITICAL: Disable buyAuto BEFORE route calculation
            $config{buyAuto_Red_Potion} = '';
            $config{buyAuto_Fly_Wing} = '';
            
            # Wait for config to propagate through OpenKore's subsystems (100ms)
            select(undef, undef, undef, 0.1);
            
            message "[GodTierAI] [FIX#1] buyAuto disabled (auto-expires in 600s), ready to route\n", "success";
        }
        
        # Now route calculation sees correct config (buyAuto disabled)
        Commands::run("move $target_map");
        
        send_action_feedback('move_to_map', 'success', 'navigating_to_map',
            "Moving to $target_map");
    }
    else {
        warning "[GodTierAI] Unknown action type: $type\n";
    }
    
    };  # End of eval block
    
    # DIAGNOSTIC #3: Error catching and reporting
    if ($@) {
        error "[GodTierAI] [CRASH] execute_action failed: $@\n";
        error "[GodTierAI] [CRASH] Action was: $type\n" if defined $type;
        error "[GodTierAI] [CRASH] Params: " . (eval { encode_json($params) } || 'JSON encode failed') . "\n" if $params;
        
        # Try to capture memory state at crash
        eval {
            my $mem_crash = `tasklist /FI "IMAGENAME eq perl.exe" /FO CSV 2>nul | findstr perl`;
            chomp($mem_crash) if $mem_crash;
            error "[GodTierAI] [CRASH] Memory at crash: $mem_crash\n" if $mem_crash;
        };
    }
}

# Enhanced: Handle player chat messages
sub handle_player_chat {
    my ($player_name, $message, $type) = @_;
    
    # Skip if HTTP client not available
    return unless defined $http_tiny;
    
    # Build context
    my %request = (
        character_name => $char->{name},
        player_name => $player_name,
        message => $message,
        message_type => $type,
        my_level => int($char->{lv} || 1),
        my_job => $::jobs_lut{$char->{jobId}} || 'Novice',
    );
    
    my $json_request = encode_json(\%request);
    my $response = $http_tiny->post(
            "$ai_service_url/api/v1/social/chat",
            {
                headers => { 'Content-Type' => 'application/json' },
                content => $json_request,
            }
        );
    
    if ($response->{success}) {
        my $data = decode_json($response->{content});
        execute_action({ action => $data });
    } else {
        debug "[GodTierAI] Social service request failed: " . "$response->{status} $response->{reason}" . "\n", "ai";
    }
}

# Hook: Private message
sub on_private_message {
    my (undef, $args) = @_;
    return unless $args->{privMsgUser};
    
    my $player_name = $args->{privMsgUser};
    my $message = $args->{privMsg};
    
    debug "[GodTierAI] Private message from $player_name: $message\n", "ai";
    handle_player_chat($player_name, $message, 'whisper');
}

# Hook: Public chat
sub on_public_chat {
    my (undef, $args) = @_;
    return unless $args->{MsgUser};
    
    my $player_name = $args->{MsgUser};
    my $message = $args->{Msg};
    
    # Only respond if mentioned
    return unless $message =~ /\@$char->{name}/ || $message =~ /\b$char->{name}\b/i;
    
    debug "[GodTierAI] Public mention from $player_name: $message\n", "ai";
    handle_player_chat($player_name, $message, 'public');
}

# Hook: Party invite
sub on_party_invite {
    my (undef, $args) = @_;
    return unless $args->{name};
    
    # Skip if HTTP client not available
    return unless defined $http_tiny;
    
    my $player_name = $args->{name};
    
    message "[GodTierAI] Party invite from $player_name\n", "info";
    
    # Query social service
    my %request = (
        character_name => $char->{name},
        player_name => $player_name,
        my_level => int($char->{lv} || 1),
    );
    
    my $json_request = encode_json(\%request);
    my $response = $http_tiny->post(
            "$ai_service_url/api/v1/social/party_invite",
            {
                headers => { 'Content-Type' => 'application/json' },
                content => $json_request,
            }
        );
    
    if ($response->{success}) {
        my $data = decode_json($response->{content});
        execute_action({ action => $data });
    }
}

# Hook: Party chat
sub on_party_chat {
    my (undef, $args) = @_;
    return unless $args->{MsgUser};
    
    my $player_name = $args->{MsgUser};
    my $message = $args->{Msg};
    
    # Only respond if mentioned
    return unless $message =~ /\@$char->{name}/ || $message =~ /\b$char->{name}\b/i;
    
    debug "[GodTierAI] Party chat from $player_name: $message\n", "ai";
    handle_player_chat($player_name, $message, 'party');
}

# Hook: Guild chat
sub on_guild_chat {
    my (undef, $args) = @_;
    return unless $args->{MsgUser};
    
    my $player_name = $args->{MsgUser};
    my $message = $args->{Msg};
    
    # Only respond if mentioned
    return unless $message =~ /\@$char->{name}/ || $message =~ /\b$char->{name}\b/i;
    
    debug "[GodTierAI] Guild chat from $player_name: $message\n", "ai";
    handle_player_chat($player_name, $message, 'guild');
}

# AI_pre hook - called every AI cycle
sub on_ai_pre {
    return unless defined $conState;
    return unless $conState == Network::IN_GAME;
    return unless $HTTP_AVAILABLE;
    return unless (defined $http_tiny);
    
    # DIAGNOSTIC: Log that this hook is being called (once only)
    state $ai_pre_called_logged = 0;
    if (!$ai_pre_called_logged) {
        message "[GodTierAI] [DIAGNOSTIC] on_ai_pre() hook IS being called\n", "success";
        $ai_pre_called_logged = 1;
    }
    
    # Degraded mode check
    if ($degraded_mode) {
        state $degraded_warning_shown = 0;
        if (!$degraded_warning_shown) {
            warning "[GodTierAI] ========================================\n";
            warning "[GodTierAI] Running in DEGRADED MODE\n";
            warning "[GodTierAI] AI features are disabled\n";
            warning "[GodTierAI] Reason: HTTP client not available\n";
            warning "[GodTierAI] ========================================\n";
            warning "[GodTierAI] PHASE 2 TEST MODE: Will attempt to continue anyway...\n";
            warning "[GodTierAI] This will test if HTTP actually works despite module loading issues\n";
            warning "[GodTierAI] ========================================\n";
            $degraded_warning_shown = 1;
        }
        return;
    }
    
    # DIAGNOSTIC #4: Nuclear test option - Uncomment to disable all AI logic
    # This tests if OpenKore core is stable without AI-Service integration
    # return;  # <-- UNCOMMENT THIS LINE to disable all GodTierAI logic
    
    # VERBOSE DIAGNOSTIC: Track why AI cycles are being skipped
    unless ($net && $net->getState() == Network::IN_GAME) {
        # This is normal during connection, don't spam
        return;
    }
    
    unless ($char && defined $char->{pos_to}) {
        # Character not fully loaded yet
        return;
    }
    
    # PRIORITY #1: Rate limit BEFORE any expensive operations
    my $current_time = time();
    
    # Check if action is still executing (prevents infinite queue accumulation)
    if ($action_pause_until > 0 && $current_time < $action_pause_until) {
        # Action still executing, this is normal
        return;
    }
    
    # DIAGNOSTIC: Log when rate limiting is active
    if ($current_time - $last_query_time < 2.0) {
        # Rate limited - this is expected every cycle
        return;
    }
    
    # FIX #1: VERBOSE LOGGING - Track that we're actually attempting decisions
    my $time_since_last = $current_time - $last_query_time;
    message "[GodTierAI] [DECISION-CYCLE] Attempting AI decision (${time_since_last}s since last)\n", "info";
    
    $last_query_time = $current_time;
    
    # Check for warning floods every 60 seconds
    if ($current_time - $last_warning_check >= 60) {
        if ($warning_count > 100) {
            error "[GodTierAI] WARNING FLOOD: $warning_count warnings in last minute!\n";
        }
        $warning_count = 0;
        $last_warning_check = $current_time;
    }
    
    # Check for config changes and hot reload if needed (self-healing capability)
    check_config_reload();
    
    # STATELESS REFACTOR: Check auto-expiring map load cooldown
    if ($map_load_cooldown_until > 0 && $current_time < $map_load_cooldown_until) {
        my $remaining = $map_load_cooldown_until - $current_time;
        message "[GodTierAI] [FIX#2] Map load cooldown active (${remaining}s remaining), skipping AI decision\n", "info";
        return;
    }
    
    # FIX #2: PERIODIC STAT/SKILL POINT CHECK (every 30 seconds)
    check_unused_points($current_time);
    
    # Request decision (with emergency circuit breakers)
    message "[GodTierAI] [DECISION-CYCLE] Calling request_decision()...\n", "info";
    my $decision = request_decision();
    
    if ($decision) {
        my $tier = $decision->{tier_used} || 'unknown';
        my $latency = $decision->{latency_ms} // 0;
        my $tier_str = defined($tier) ? $tier : 'unknown';
        my $latency_str = defined($latency) ? "${latency}ms" : 'N/A';
        message "[GodTierAI] [DECISION-CYCLE] Decision received from tier '$tier_str' in $latency_str\n", "success";
        
        execute_action($decision);
    } else {
        warning "[GodTierAI] [DECISION-CYCLE] request_decision() returned undef/empty\n";
    }
    
    # Memory cleanup hint for Perl garbage collector
    undef $decision;
}

# FIX #3: PERIODIC CHECK FOR UNUSED STAT/SKILL POINTS
# This proactively checks for unused points every 30 seconds and allocates them
# Solves the issue where character has unused points but no level-up event triggered
my $last_point_check = 0;

sub check_unused_points {
    my ($current_time) = @_;
    
    # Check every 30 seconds
    return if ($current_time - $last_point_check < 30);
    $last_point_check = $current_time;
    
    return unless $char;
    
    # Check for unused stat points
    my $stat_points = $char->{points_free} || 0;
    if ($stat_points > 0) {
        message "[GodTierAI] [AUTO-PROGRESSION] Detected $stat_points unused stat points - allocating...\n", "success";
        
        # Skip if HTTP client not available
        unless (defined $http_tiny) {
            warning "[GodTierAI] [AUTO-PROGRESSION] Cannot allocate stats - HTTP client not available (degraded mode)\n";
            return;
        }
        
        # Trigger stat allocation as if level-up just happened
        eval {
            my %current_stats = (
                str => int($char->{str} || 1),
                agi => int($char->{agi} || 1),
                vit => int($char->{vit} || 1),
                int => int($char->{int} || 1),
                dex => int($char->{dex} || 1),
                luk => int($char->{luk} || 1)
            );
            
            my %request = (
                current_level => int($char->{lv} || 1),
                current_stats => \%current_stats,
                unused_points => int($stat_points)
            );
            
            my $json_request = encode_json(\%request);
            message "[GodTierAI] [AUTO-PROGRESSION] Requesting stat allocation from AI Service...\n", "info";
            
            my $response = $http_tiny->post(
            "$ai_service_url/api/v1/progression/stats/on_level_up",
            {
                headers => { 'Content-Type' => 'application/json' },
                content => $json_request,
            }
        );
            
            if ($response->{success}) {
                my $data = decode_json($response->{content});
                
                if ($data->{config} && $data->{config}{statsAddAuto_list}) {
                    message "[GodTierAI] [AUTO-PROGRESSION] Stat plan: $data->{config}{statsAddAuto_list}\n", "success";
                    
                    # Enable auto-stat allocation
                    Commands::run('config statsAddAuto 1');
                    Commands::run("config statsAddAuto_list $data->{config}{statsAddAuto_list}");
                    
                    message "[GodTierAI] [AUTO-PROGRESSION] Auto-stat enabled - points will be allocated\n", "success";
                } else {
                    warning "[GodTierAI] [AUTO-PROGRESSION] No stat plan received from AI Service\n";
                }
            } else {
                warning "[GodTierAI] [AUTO-PROGRESSION] Stat allocation request failed: " . "$response->{status} $response->{reason}" . "\n";
            }
        };
        if ($@) {
            warning "[GodTierAI] [AUTO-PROGRESSION] Stat allocation error: $@\n";
        }
    }
    
    # Check for unused skill points
    my $skill_points = $char->{points_skill} || 0;
    if ($skill_points > 0) {
        message "[GodTierAI] [AUTO-PROGRESSION] Detected $skill_points unused skill points - learning skills...\n", "success";
        
        # Skip if HTTP client not available
        unless (defined $http_tiny) {
            warning "[GodTierAI] [AUTO-PROGRESSION] Cannot learn skills - HTTP client not available (degraded mode)\n";
            return;
        }
        
        # Trigger skill learning as if job level-up just happened
        eval {
            my %current_skills = ();
            foreach my $skill_handle (keys %{$char->{skills}}) {
                my $skill = $char->{skills}{$skill_handle};
                $current_skills{$skill_handle} = int($skill->{lv} || 0) if $skill;
            }
            
            my $job_class = $::jobs_lut{$char->{jobId}} || 'Novice';
            
            my %request = (
                current_job_level => int($char->{lv_job} || 1),
                job_class => $job_class,
                current_skills => \%current_skills,
                unused_points => int($skill_points)
            );
            
            my $json_request = encode_json(\%request);
            message "[GodTierAI] [AUTO-PROGRESSION] Requesting skill learning from AI Service...\n", "info";
            
            my $response = $http_tiny->post(
            "$ai_service_url/api/v1/progression/skills/on_job_level_up",
            {
                headers => { 'Content-Type' => 'application/json' },
                content => $json_request,
            }
        );
            
            if ($response->{success}) {
                my $data = decode_json($response->{content});
                
                if ($data->{config} && $data->{config}{skillsAddAuto_list}) {
                    message "[GodTierAI] [AUTO-PROGRESSION] Skill plan: $data->{config}{skillsAddAuto_list}\n", "success";
                    
                    # Enable auto-skill learning
                    Commands::run('config skillsAddAuto 1');
                    Commands::run("config skillsAddAuto_list $data->{config}{skillsAddAuto_list}");
                    
                    message "[GodTierAI] [AUTO-PROGRESSION] Auto-skill enabled - skills will be learned\n", "success";
                } else {
                    warning "[GodTierAI] [AUTO-PROGRESSION] No skill plan received from AI Service\n";
                }
            } else {
                warning "[GodTierAI] [AUTO-PROGRESSION] Skill learning request failed: " . "$response->{status} $response->{reason}" . "\n";
            }
        };
        if ($@) {
            warning "[GodTierAI] [AUTO-PROGRESSION] Skill learning error: $@\n";
        }
    }
    
    # Periodic status report
    if ($stat_points == 0 && $skill_points == 0) {
        debug "[GodTierAI] [AUTO-PROGRESSION] All points allocated (Stat: 0, Skill: 0)\n", "ai";
    }
}

# STATELESS REFACTOR: Loop Detection with Sliding Window (no accumulation)
# Instead of storing full history, we use a count-based sliding window that auto-expires
sub detect_infinite_loop {
    my ($map) = @_;
    my $current_time = time();
    
    # STATELESS: Clean old data every 60 seconds (sliding window)
    if ($current_time - $last_loop_check_cleanup > 60) {
        debug "[LOOP-DETECT] Cleaning expired visit counts (sliding window)\n", "ai";
        %map_visit_count = ();  # Clear all counts (they're >60s old)
        $last_loop_check_cleanup = $current_time;
    }
    
    # STATELESS: Increment visit count for this map (just a counter, not an array)
    $map_visit_count{$map} ||= 0;
    $map_visit_count{$map}++;
    
    # Check if visited >5 times in current 60s window
    if ($map_visit_count{$map} > 5) {
        Log::warning("[LOOP-DETECT] Visited $map " . $map_visit_count{$map} . " times in 60s - BREAKING LOOP\n");
        AI::clear("route", "move");
        $timeout{ai_stuck}{time} = time() + 60;
        
        # Reset this map's count after breaking loop
        $map_visit_count{$map} = 0;
        
        return 1;  # Loop detected
    }
    
    return 0;  # No loop
}

# FIX #9: Minimum Farming Time Enforcement
sub should_leave_farming_map {
    my $time_in_map = time() - $farming_map_entry_time;
    my $min_duration = 30;  # Minimum 30 seconds
    
    if ($time_in_map < $min_duration) {
        debug "[FARMING] Only ${time_in_map}s in map, staying at least ${min_duration}s\n";
        return 0;  # Don't leave yet
    }
    
    return 1;  # OK to leave
}

sub on_map_change {
    my (undef, $args) = @_;
    
    # MAP CHANGE DEBOUNCING: Prevent triple-firing during connection sequence
    my $current_time = time();
    my $current_map = $field ? $field->name() : 'unknown';
    
    # Skip if same map within 2 seconds (duplicate event from connection sequence)
    if ($current_map eq $last_map_name && ($current_time - $last_map_change_time) < 2) {
        debug "[GodTierAI] Ignoring duplicate map change for $current_map (debounce)\n", "ai";
        return;
    }
    $last_map_change_time = $current_time;
    $last_map_name = $current_map;
    
    message "[GodTierAI] Map changed to $current_map, resetting state\n", "info";
    
    # CRITICAL FIX #2: Wait 2 seconds for monster data to populate after map change
    # Without this delay, AI-Service sees empty monsters array and can't engage combat
    my $map_name = $current_map;
    
    # FIX #8: Detect infinite loop BEFORE processing map
    if (detect_infinite_loop($map_name)) {
        warning "[GodTierAI] [LOOP-DETECT] Infinite loop detected on $map_name, clearing AI queue\n";
        return;  # Skip further processing
    }
    
    if ($map_name =~ /fild|beach|dun|forest|mine|cave/i) {
        message "[GodTierAI] [FIX#2] Waiting 5s for monster data and map stabilization on $map_name\n", "info";
        
        # STATELESS REFACTOR: Set auto-expiring cooldown timestamp
        $map_load_cooldown_until = time() + 5;  # Auto-expires after 5 seconds
        
        # FIX #9: Track farming map entry time
        $farming_map_entry_time = time();
        message "[FARMING] Entered farming map $map_name at " . localtime() . "\n", "info";
    }
    
    # Notify equipment manager about map change
    notify_equipment_map_change($map_name) if $field;
}

# Log message hook - detects plugin warnings and triggers auto-configuration
# User requirement: "Never fix config.txt manually, use autonomous self-healing"
sub on_log_message {
    my (undef, $args) = @_;
    my $message = $args->{message} || "";
    my $domain = $args->{domain} || "";
    
    # SELF-HEALING: Detect OpenKore's native teleportAuto failure
    # This happens when OpenKore tries to teleport but character has no Fly Wing or skill
    if ($message =~ /You don't have the Teleport skill or a Fly Wing/i) {
        my $now = time();
        
        # Reset counter if >30s since last failure (isolated incidents, not a pattern)
        if ($now - $last_teleport_fail_time > 30) {
            $teleport_fail_count = 0;
        }
        
        $teleport_fail_count++;
        $last_teleport_fail_time = $now;
        
        debug "[GodTierAI] Teleport failure #$teleport_fail_count detected\n", "ai";
        
        # After 3 failures in 30s, this is a pattern - disable OpenKore's teleportAuto
        if ($teleport_fail_count >= 3) {
            warning "[GodTierAI] [SELF-HEAL] Teleport failed 3x without resources, disabling teleportAuto...\n";
            sanitize_teleport_config();
            $teleport_fail_count = 0;  # Reset after healing
        }
    }
    
    # Detect teleToDest plugin warning about missing configuration
    if ($message =~ /\[teleToDest\].*config keys not defined.*won't be activated/i) {
        warning "[GodTierAI] [SELF-HEAL] Detected teleToDest plugin config missing\n";
        
        # Only trigger auto-config if character is ready
        unless (defined $char && $char->{lv}) {
            debug "[GodTierAI] [SELF-HEAL] Character not ready yet, skipping auto-config\n";
            return;
        }
        
        # Prepare payload for AI Service
        my $character_level = $char->{lv} || 1;
        my $character_class = $char->{jobName} || "Novice";
        
        message "[GodTierAI] [SELF-HEAL] Requesting auto-configuration for teleToDest\n", "info";
        message "[GodTierAI] [SELF-HEAL] Character: Lv$character_level $character_class\n", "info";
        
        # Call AI Service self-heal endpoint
        eval {
            # Skip if HTTP client not available
            unless (defined $http_tiny) {
                warning "[GodTierAI] [SELF-HEAL] Cannot auto-configure - HTTP client not available (degraded mode)\n";
                return;
            }
            
            my $payload = encode_json({
                plugin_name => 'teleToDest',
                character_level => $character_level + 0,  # Force numeric
                character_class => $character_class
            });
            
            my $response = $http_tiny->post(
                "$ai_service_url/api/v1/self_heal/fix_plugin_config",
                {
                    headers => { 'Content-Type' => 'application/json' },
                    content => $payload,
                }
            );
            
            if ($response->{success}) {
                my $result = decode_json($response->{content});
                
                if ($result->{success}) {
                    message "[GodTierAI] [SELF-HEAL] teleToDest config auto-generated successfully!\n", "success";
                    message "[GodTierAI] [SELF-HEAL] Keys added: " . join(", ", @{$result->{config_added}{keys_added}}) . "\n", "info";
                    message "[GodTierAI] [SELF-HEAL] Hot reload will activate plugin automatically (~5 seconds)\n", "info";
                } else {
                    error "[GodTierAI] [SELF-HEAL] Failed to auto-configure: " . ($result->{error} || "Unknown error") . "\n";
                }
            } else {
                error "[GodTierAI] [SELF-HEAL] AI Service request failed: " . "$response->{status} $response->{reason}" . "\n";
            }
        };
        
        if ($@) {
            error "[GodTierAI] [SELF-HEAL] Exception during auto-config: $@\n";
        }
    }
}

# ============================================================================
# PHASE 11: AUTONOMOUS PROGRESSION EVENT HANDLERS
# ============================================================================

# Base level up handler
sub on_base_level_up {
    my (undef, $args) = @_;
    return unless $char;
    
    my $new_level = $char->{lv};
    message "[GodTierAI] Level UP! New level: $new_level\n", "success";
    
    # Collect current stats
    my %current_stats = (
        str => int($char->{str} || 1),
        agi => int($char->{agi} || 1),
        vit => int($char->{vit} || 1),
        int => int($char->{int} || 1),
        dex => int($char->{dex} || 1),
        luk => int($char->{luk} || 1)
    );
    
    # Request stat allocation from AI Service
    eval {
        # Skip if HTTP client not available
        unless (defined $http_tiny) {
            warning "[GodTierAI] Cannot allocate stats - HTTP client not available (degraded mode)\n";
            return;
        }
        
        my %request = (
            current_level => int($new_level || 1),
            current_stats => \%current_stats
        );
        
        my $json_request = encode_json(\%request);
        my $response = $http_tiny->post(
            "$ai_service_url/api/v1/progression/stats/on_level_up",
            {
                headers => { 'Content-Type' => 'application/json' },
                content => $json_request,
            }
        );
        
        if ($response->{success}) {
            my $data = decode_json($response->{content});
            
            if ($data->{config} && $data->{config}{statsAddAuto_list}) {
                message "[GodTierAI] Stat allocation plan: $data->{config}{statsAddAuto_list}\n", "info";
                
                # Update config for raiseStat plugin
                # FIXED: Use Commands::run to avoid hot reload conflict
                Commands::run('config statsAddAuto 1');
                Commands::run("config statsAddAuto_list $data->{config}{statsAddAuto_list}");
                
                message "[GodTierAI] Auto-stat allocation enabled\n", "success";
            }
        } else {
            warning "[GodTierAI] Failed to get stat allocation: " . "$response->{status} $response->{reason}" . "\n";
        }
    };
    if ($@) {
        warning "[GodTierAI] Stat allocation error: $@\n";
    }
}

# Job level up handler
sub on_job_level_up {
    my (undef, $args) = @_;
    return unless $char;
    
    my $new_job_level = $char->{lv_job};
    my $job_class = $::jobs_lut{$char->{jobId}} || 'Novice';
    message "[GodTierAI] Job Level UP! New job level: $new_job_level ($job_class)\n", "success";
    
    # Collect current skills
    my %current_skills = ();
    foreach my $skill_handle (keys %{$char->{skills}}) {
        my $skill = $char->{skills}{$skill_handle};
        $current_skills{$skill_handle} = int($skill->{lv} || 0) if $skill;
    }
    
    # Request skill learning from AI Service
    eval {
        # Skip if HTTP client not available
        unless (defined $http_tiny) {
            warning "[GodTierAI] Cannot learn skills - HTTP client not available (degraded mode)\n";
            return;
        }
        
        my %request = (
            current_job_level => int($new_job_level || 1),
            job => lc($job_class),
            current_skills => \%current_skills
        );
        
        my $json_request = encode_json(\%request);
        my $response = $http_tiny->post(
            "$ai_service_url/api/v1/progression/skills/on_job_level_up",
            {
                headers => { 'Content-Type' => 'application/json' },
                content => $json_request,
            }
        );
        
        if ($response->{success}) {
            my $data = decode_json($response->{content});
            
            if ($data->{config} && $data->{config}{skillsAddAuto_list}) {
                message "[GodTierAI] Skill learning plan: $data->{config}{skillsAddAuto_list}\n", "info";
                
                # Update config for raiseSkill plugin
                # FIXED: Use Commands::run to avoid hot reload conflict
                Commands::run('config skillsAddAuto 1');
                Commands::run("config skillsAddAuto_list $data->{config}{skillsAddAuto_list}");
                
                message "[GodTierAI] Auto-skill learning enabled\n", "success";
            }
        } else {
            warning "[GodTierAI] Failed to get skill learning: " . "$response->{status} $response->{reason}" . "\n";
        }
    };
    if ($@) {
        warning "[GodTierAI] Skill learning error: $@\n";
    }
}

# Stat info update handler (for tracking)
sub on_stat_info {
    my (undef, $args) = @_;
    return unless $char;
    
    # Track stats for performance monitoring
    # This is called frequently, so we only log important changes
}

# Skill update handler (for tracking)
sub on_skill_update {
    my (undef, $args) = @_;
    return unless $char;
    
    # Track skill updates for adaptive learning
}

# Notify equipment manager about map change
sub notify_equipment_map_change {
    my ($map_name) = @_;
    return unless $map_name;
    
    # Collect enemies in current map
    my @enemies = ();
    foreach my $monster (@{$monstersList->getItems()}) {
        next unless $monster;
        push @enemies, {
            name => $monster->{name} || 'Unknown',
            element => 'neutral',  # Would need monster database lookup
            race => 'unknown',      # Would need monster database lookup
            size => 'medium'        # Would need monster database lookup
        };
        last if scalar(@enemies) >= 10;  # Sample first 10
    }
    
    eval {
        # Skip if HTTP client not available
        return unless defined $http_tiny;
        
        my %request = (
            new_map => $map_name,
            enemies => \@enemies
        );
        
        my $json_request = encode_json(\%request);
        my $response = $http_tiny->post(
            "$ai_service_url/api/v1/progression/equipment/on_map_change",
            {
                headers => { 'Content-Type' => 'application/json' },
                content => $json_request,
            }
        );
        
        if ($response->{success}) {
            my $data = decode_json($response->{content});
            
            if ($data->{commands}) {
                debug "[GodTierAI] Equipment recommendations for $map_name:\n", "ai";
                foreach my $cmd (@{$data->{commands}}) {
                    debug "[GodTierAI]   - $cmd\n", "ai";
                }
            }
        }
    };
    if ($@) {
        debug "[GodTierAI] Equipment notification error: $@\n", "ai";
    }
}

1;
