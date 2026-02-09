# GodTierAI Plugin Entry Point with Hot-Reload Support
# This file loads the GodTierAI module into OpenKore
# HOT-RELOAD: Monitors GodTierAI.pm for changes and reloads automatically

package godtier_ai;

use strict;
use warnings;
use FindBin qw($RealBin);
use lib "$RealBin/plugins";
use Plugins;
use Log qw(message warning error);

# ============================================================================
# HOT-RELOAD STATE TRACKING
# ============================================================================
my $module_path = "$RealBin/plugins/godtier-ai/GodTierAI.pm";
my $last_mtime = 0;
my $check_interval = 60;  # Check every 60 seconds
my $last_check = 0;
my $hot_reload_hooks;

# ============================================================================
# MODULE LOADING WITH HOT-RELOAD SUPPORT
# ============================================================================
sub load_godtier_module {
    my $force_reload = shift || 0;
    
    # Verify file exists
    unless (-e $module_path) {
        error "[godtier-ai] [HOT-RELOAD] Module not found: $module_path\n";
        return 0;
    }
    
    # Get current modification time
    my $current_mtime = (stat($module_path))[9];
    
    # Determine if reload is needed
    my $needs_reload = 0;
    if ($force_reload) {
        $needs_reload = 1;
        message "[godtier-ai] [HOT-RELOAD] Force reload requested\n", "info";
    } elsif ($last_mtime && $current_mtime > $last_mtime) {
        $needs_reload = 1;
        message "[godtier-ai] [HOT-RELOAD] File modification detected!\n", "success";
        message "[godtier-ai] [HOT-RELOAD] Old timestamp: " . localtime($last_mtime) . "\n", "info";
        message "[godtier-ai] [HOT-RELOAD] New timestamp: " . localtime($current_mtime) . "\n", "info";
    }
    
    # Perform hot-reload if needed
    if ($needs_reload && $last_mtime > 0) {
        message "[godtier-ai] [HOT-RELOAD] Initiating module reload...\n", "info";
        
        # Step 1: Call unload hook to cleanup old module
        if (defined &GodTierAI::on_unload) {
            eval { 
                message "[godtier-ai] [HOT-RELOAD] Calling on_unload() to cleanup old hooks...\n", "info";
                GodTierAI::on_unload(); 
            };
            if ($@) {
                warning "[godtier-ai] [HOT-RELOAD] Error during on_unload: $@\n";
            } else {
                message "[godtier-ai] [HOT-RELOAD] Old module unloaded successfully\n", "success";
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
            message "[godtier-ai] [HOT-RELOAD] Cleared \%INC cache (key: $inc_key)\n", "success";
        } else {
            warning "[godtier-ai] [HOT-RELOAD] Could not find GodTierAI.pm in \%INC\n";
        }
    }
    
    # Step 3: Load/reload the module
    eval {
        if ($needs_reload && $last_mtime > 0) {
            message "[godtier-ai] [HOT-RELOAD] Loading fresh module from disk...\n", "info";
        } else {
            message "[godtier-ai] [HOT-RELOAD] Initial module load...\n", "info";
        }
        require "$RealBin/plugins/godtier-ai/GodTierAI.pm";
        $last_mtime = $current_mtime;
        message "[godtier-ai] [HOT-RELOAD] ✓ Module loaded successfully!\n", "success";
        message "[godtier-ai] [HOT-RELOAD] ✓ File timestamp: " . localtime($current_mtime) . "\n", "success";
    };
    
    if ($@) {
        error "[godtier-ai] [HOT-RELOAD] ✗ Failed to load module: $@\n";
        return 0;
    }
    
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
        message "[godtier-ai] [HOT-RELOAD] ========================================\n", "success";
        message "[godtier-ai] [HOT-RELOAD] FILE CHANGE DETECTED - TRIGGERING RELOAD\n", "success";
        message "[godtier-ai] [HOT-RELOAD] ========================================\n", "success";
        load_godtier_module(1);
    }
}

# ============================================================================
# LOADER CLEANUP
# ============================================================================
sub on_loader_unload {
    Plugins::delHooks($hot_reload_hooks) if $hot_reload_hooks;
    message "[godtier-ai] [HOT-RELOAD] Monitor unloaded\n", "info";
}

# ============================================================================
# INITIALIZATION
# ============================================================================

# Perform initial load
message "[godtier-ai] [HOT-RELOAD] Initializing hot-reload system...\n", "info";
message "[godtier-ai] [HOT-RELOAD] Monitoring: $module_path\n", "info";
message "[godtier-ai] [HOT-RELOAD] Check interval: ${check_interval}s\n", "info";

if (load_godtier_module()) {
    # Register hot-reload periodic checker
    $hot_reload_hooks = Plugins::addHooks(
        ['AI_pre', \&check_hot_reload, undef]
    );
    
    message "[godtier-ai] [HOT-RELOAD] ✓ Hot-reload monitor active\n", "success";
    message "[godtier-ai] [HOT-RELOAD] ✓ Changes to GodTierAI.pm will be detected automatically\n", "success";
} else {
    error "[godtier-ai] [HOT-RELOAD] ✗ Failed to initialize plugin\n";
}

# Register loader for cleanup (separate from GodTierAI plugin registration)
Plugins::register('godtier_ai_loader', 'GodTierAI hot-reload monitor', \&on_loader_unload);

1;
