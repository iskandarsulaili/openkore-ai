# GodTierAI Plugin Entry Point with Hot-Reload Support
# This file loads the GodTierAI module into OpenKore
# HOT-RELOAD: Monitors GodTierAI.pm for changes and reloads automatically

package godtier_ai;

use strict;
use warnings;

# PHASE 2: Force STDERR/STDOUT autoflush for immediate visibility
$| = 1;  # Autoflush STDOUT
select(STDERR); $| = 1; select(STDOUT);  # Autoflush STDERR

print STDERR "[godtier_ai.pl] *** PLUGIN LOADER STARTING ***\n";
print STDERR "[godtier_ai.pl] *** Timestamp: " . localtime() . "\n";
print STDERR "[godtier_ai.pl] *** Perl version: $]\n";

use FindBin qw($RealBin);
print STDERR "[godtier_ai.pl] *** Script directory: $RealBin\n";

# NO HARDCODED PATHS: Use system Perl (from PATH)
# OpenKore's start.bat ensures correct Perl is running
# @INC is automatically configured by the Perl executable
print STDERR "[godtier_ai.pl] *** Using system Perl (no hardcoded paths)\n";

# Print @INC for diagnostics
print STDERR "[godtier_ai.pl] *** Perl \@INC paths (from system):\n";
foreach my $path (@INC) {
    print STDERR "[godtier_ai.pl] ***   - $path\n";
}

use lib "$RealBin/plugins";
use Plugins;
use Log qw(message warning error);

# ============================================================================
# HOT-RELOAD STATE TRACKING
# ============================================================================
my $module_path = "$RealBin/plugins/godtier_ai/GodTierAI.pm";
my $last_mtime = 0;
my $check_interval = 60;  # Check every 60 seconds
my $last_check = 0;
my $hot_reload_hooks;

# Module path verification
my $module_dir = "$RealBin/plugins/godtier_ai";
print STDERR "[godtier_ai.pl] *** Module directory: $module_dir\n";

# Check if path exists
unless (-d $module_dir) {
    print STDERR "[godtier_ai.pl]  ERROR: Module directory not found at $module_dir\n";
    die "[godtier_ai.pl]  FATAL: Cannot continue without module directory\n";
}
print STDERR "[godtier_ai.pl]  Module directory found\n";

# Check if GodTierAI.pm exists
unless (-f $module_path) {
    print STDERR "[godtier_ai.pl]  ERROR: GodTierAI.pm not found at $module_path\n";
    die "[godtier_ai.pl]  FATAL: Cannot continue without GodTierAI.pm\n";
}
print STDERR "[godtier_ai.pl]  GodTierAI.pm found\n";

# ============================================================================
# MODULE LOADING WITH HOT-RELOAD SUPPORT
# ============================================================================
sub load_godtier_module {
    my $force_reload = shift || 0;
    
    print STDERR "[godtier_ai.pl] *** Attempting to load GodTierAI module...\n" unless $last_mtime;
    
    # Verify file exists
    unless (-e $module_path) {
        error "[godtier_ai] [HOT-RELOAD] Module not found: $module_path\n";
        print STDERR "[godtier_ai.pl]  ERROR: Module file disappeared: $module_path\n";
        return 0;
    }
    
    # Get current modification time
    my $current_mtime = (stat($module_path))[9];
    
    # Determine if reload is needed
    my $needs_reload = 0;
    if ($force_reload) {
        $needs_reload = 1;
        message "[godtier_ai] [HOT-RELOAD] Force reload requested\n", "info";
    } elsif ($last_mtime && $current_mtime > $last_mtime) {
        $needs_reload = 1;
        message "[godtier_ai] [HOT-RELOAD] File modification detected!\n", "success";
        message "[godtier_ai] [HOT-RELOAD] Old timestamp: " . localtime($last_mtime) . "\n", "info";
        message "[godtier_ai] [HOT-RELOAD] New timestamp: " . localtime($current_mtime) . "\n", "info";
    }
    
    # Perform hot-reload if needed
    if ($needs_reload && $last_mtime > 0) {
        message "[godtier_ai] [HOT-RELOAD] Initiating module reload...\n", "info";
        
        # Step 1: Call unload hook to cleanup old module
        if (defined &GodTierAI::on_unload) {
            eval {
                message "[godtier_ai] [HOT-RELOAD] Calling on_unload() to cleanup old hooks...\n", "info";
                GodTierAI::on_unload();
            };
            if ($@) {
                warning "[godtier_ai] [HOT-RELOAD] Error during on_unload: $@\n";
            } else {
                message "[godtier_ai] [HOT-RELOAD] Old module unloaded successfully\n", "success";
            }
        }
        
        # Step 2: Clear from %INC cache to force fresh load
        my $inc_key;
        for my $key (keys %INC) {
            if ($key =~ /GodTierAI\.pm$/) {
                $inc_key = $key;
                last;
            }
        }
        
        if ($inc_key) {
            delete $INC{$inc_key};
            message "[godtier_ai] [HOT-RELOAD] Cleared \%INC cache (key: $inc_key)\n", "success";
        } else {
            warning "[godtier_ai] [HOT-RELOAD] Could not find GodTierAI.pm in \%INC\n";
        }
    }
    
    # Step 3: Load/reload the module
    eval {
        if ($needs_reload && $last_mtime > 0) {
            message "[godtier_ai] [HOT-RELOAD] Loading fresh module from disk...\n", "info";
        } else {
            message "[godtier_ai] [HOT-RELOAD] Initial module load...\n", "info";
        }
        require "$RealBin/plugins/godtier_ai/GodTierAI.pm";
        $last_mtime = $current_mtime;
        print STDERR "[godtier_ai.pl]  GodTierAI module loaded successfully\n";
        message "[godtier_ai] [HOT-RELOAD]  Module loaded successfully!\n", "success";
        message "[godtier_ai] [HOT-RELOAD]  File timestamp: " . localtime($current_mtime) . "\n", "success";
    };
    
    if ($@) {
        print STDERR "[godtier_ai.pl]  FATAL: Failed to load GodTierAI: $@\n";
        error "[godtier_ai] [HOT-RELOAD]  Failed to load module: $@\n";
        return 0;
    }
    
    print STDERR "[godtier_ai.pl]  Module load completed without errors\n";
    return 1;
}

# ============================================================================
# PERIODIC HOT-RELOAD CHECK (runs every 60 seconds via AI_pre hook)
# ============================================================================
sub check_hot_reload {
    my $current_time = time();
    
    # Rate limiting: only check at specified interval
    return if ($current_time - $last_check) < $check_interval;
    
    $last_check = $current_time;
    
    # File existence check
    return unless -e $module_path;
    
    # Check modification time
    my $current_mtime = (stat($module_path))[9];
    
    if ($last_mtime && $current_mtime > $last_mtime) {
        message "[godtier_ai] [HOT-RELOAD] ========================================\n", "success";
        message "[godtier_ai] [HOT-RELOAD] FILE CHANGE DETECTED - TRIGGERING RELOAD\n", "success";
        message "[godtier_ai] [HOT-RELOAD] ========================================\n", "success";
        load_godtier_module(1);
    }
}

# ============================================================================
# LOADER CLEANUP
# ============================================================================
sub on_loader_unload {
    Plugins::delHooks($hot_reload_hooks) if $hot_reload_hooks;
    message "[godtier_ai] [HOT-RELOAD] Monitor unloaded\n", "info";
}

# ============================================================================
# INITIALIZATION
# ============================================================================

# Perform initial load
message "[godtier_ai] [HOT-RELOAD] Initializing hot-reload system...\n", "info";
message "[godtier_ai] [HOT-RELOAD] Monitoring: $module_path\n", "info";
message "[godtier_ai] [HOT-RELOAD] Check interval: ${check_interval}s\n", "info";

if (load_godtier_module()) {
    print STDERR "[godtier_ai.pl] *** Verifying module initialization...\n";
    
    # Verify the module loaded successfully
    if (defined &GodTierAI::on_load) {
        print STDERR "[godtier_ai.pl]  on_load() function found\n";
        message "[godtier_ai]  GodTierAI module loaded successfully\n", "success";
        message "[godtier_ai]  Functions available\n", "success";
    } else {
        print STDERR "[godtier_ai.pl]  ERROR: on_load() function NOT found\n";
        error "[godtier_ai]  GodTierAI module FAILED TO LOAD\n";
        error "[godtier_ai]  Check for missing Perl modules\n";
        error "[godtier_ai]  Plugin will not function\n";
    }
    
    # Check HTTP library availability
    if ($GodTierAI::HTTP_AVAILABLE) {
        print STDERR "[godtier_ai.pl]  HTTP client available: $GodTierAI::HTTP_CLIENT\n";
        message "[godtier_ai]  HTTP client available ($GodTierAI::HTTP_CLIENT)\n", "success";
    } else {
        print STDERR "[godtier_ai.pl]  WARNING: HTTP client NOT available\n";
        print STDERR "[godtier_ai.pl]  Error details: $GodTierAI::LOAD_ERROR\n" if $GodTierAI::LOAD_ERROR;
        error "[godtier_ai]  HTTP client NOT available\n";
        error "[godtier_ai]  Error: $GodTierAI::LOAD_ERROR\n";
        error "[godtier_ai]  Install LWP::UserAgent: cpanm LWP::UserAgent\n";
        error "[godtier_ai]  Or install system package: apt-get install libwww-perl (Debian/Ubuntu)\n";
    }
    
    # Register hot-reload periodic checker
    $hot_reload_hooks = Plugins::addHooks(
        ['AI_pre', \&check_hot_reload, undef]
    );
    
    print STDERR "[godtier_ai.pl]  Hot-reload monitor registered\n";
    message "[godtier_ai] [HOT-RELOAD]  Hot-reload monitor active\n", "success";
    message "[godtier_ai] [HOT-RELOAD]  Changes to GodTierAI.pm will be detected automatically\n", "success";
    
    print STDERR "[godtier_ai.pl] *** PLUGIN LOADER COMPLETE ***\n";
} else {
    print STDERR "[godtier_ai.pl]  FATAL: Failed to initialize plugin\n";
    error "[godtier_ai] [HOT-RELOAD]  Failed to initialize plugin\n";
}

# Register loader for cleanup (separate from GodTierAI plugin registration)
Plugins::register('godtier_ai_loader', 'GodTierAI hot-reload monitor', \&on_loader_unload);
print STDERR "[godtier_ai.pl]  Plugin registered with OpenKore\n";

1;
