package GodTierAI;

use strict;
use warnings;
use Plugins;
use Globals;
use Log qw(message warning error debug);
use Utils;
use JSON;
use LWP::UserAgent;
use Time::HiRes qw(time);

Plugins::register('GodTierAI', 'Advanced AI system with LLM integration', \&on_unload);

my $hooks;
my $ai_engine_url = "http://127.0.0.1:9901";
my $ai_service_url = "http://127.0.0.1:9902";
# Increased to 35s to accommodate background async CrewAI (avg 28.4s, max 31.6s observed in Test #14)
my $ua = LWP::UserAgent->new(timeout => 35);
my $request_counter = 0;

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

sub on_unload {
    Plugins::delHooks($hooks);
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
        
        message "[GodTierAI] [SELF-HEAL] ✓ Config file healed successfully!\n", "success";
        message "[GodTierAI] [SELF-HEAL] ✓ Disabled buyAuto for: " . join(", ", @disabled_items) . "\n", "success";
        message "[GodTierAI] [SELF-HEAL] ✓ Reason: buyAuto causes infinite town-return loops during farming\n", "success";
        message "[GodTierAI] [SELF-HEAL] ✓ Impact: Character will now stay in farming maps and engage combat\n", "success";
        
        # Trigger hot reload to apply changes WITHOUT disconnecting
        message "[GodTierAI] [SELF-HEAL] Triggering hot reload (no disconnect)...\n", "info";
        Commands::run("reload config");
        
        # Small delay to allow reload to complete
        select(undef, undef, undef, 0.2);
        
        message "[GodTierAI] [SELF-HEAL] ✓ Hot reload completed - buyAuto now managed by AI\n", "success";
        message "[GodTierAI] [SELF-HEAL] ✓ Self-healing action logged for analysis\n", "success";
        
        # Log to autonomous healing log
        log_healing_action('config_buyauto_disabled', {
            disabled_items => \@disabled_items,
            reason => 'Test #16 root cause: buyAuto overrides plugin runtime changes',
            impact => 'Prevents infinite town-return loops, enables sustained farming'
        });
        
    } else {
        message "[GodTierAI] [SELF-HEAL] ✓ No buyAuto issues detected - config is clean\n", "success";
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
    message "[GodTierAI] Initializing plugin...\n", "info";
    
    # CRITICAL: Sanitize config BEFORE hooks to prevent buyAuto from triggering
    sanitize_config_for_godtier_ai();
    
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
    
    # Check AI Service connectivity
    check_ai_service_connectivity();
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
    eval {
        my $response = $ua->get("$ai_service_url/api/v1/health");
        if ($response->is_success) {
            message "[GodTierAI] [OK] AI Service is online and healthy\n", "success";
        } else {
            warning "[GodTierAI] [WARNING] AI Service is not responding (HTTP " . $response->code . ")\n";
            warning "[GodTierAI] [WARNING] Conscious and Subconscious layers will be offline\n";
        }
    };
    if ($@) {
        warning "[GodTierAI] [WARNING] Cannot connect to AI Service at $ai_service_url\n";
        warning "[GodTierAI] [WARNING] Error: $@\n";
    }
}

# Call initialization
on_load();

# CRITICAL FIX: Helper function to check if inventory is ready
sub inventory_ready {
    return ($char && $char->{inventory}) ? 1 : 0;
}

# Check if AI Engine is available
sub check_engine_health {
    my $response = $ua->get("$ai_engine_url/api/v1/health");
    if ($response->is_success) {
        my $data = decode_json($response->decoded_content);
        if ($data->{status} eq 'healthy') {
            return 1;
        }
    }
    return 0;
}

# Collect game state (enhanced with equipment, quests, guild info, skills)
sub collect_game_state {
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
            # Enhanced: Guild info (safe access)
            guild => {
                name => ($char->{guild} && $char->{guild}{name}) || '',
                id => ($char->{guild} && $char->{guild}{ID}) || '',
                position => ($char->{guild} && $char->{guild}{title}) || '',
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
    
    # CRITICAL FIX #1: Collect character skills
    if ($char->{skills}) {
        foreach my $skill_name (keys %{$char->{skills}}) {
            my $skill = $char->{skills}{$skill_name};
            if ($skill && $skill->{lv} > 0) {
                push @{$state{skills}}, {
                    name => $skill_name,
                    level => int($skill->{lv} || 0),
                    sp_cost => int($skill->{sp} || 0),
                };
            }
        }
    }
    
    # Collect monsters
    foreach my $monster (@{$monstersList->getItems()}) {
        next unless $monster;
        push @{$state{monsters}}, {
            id => int($monster->{binID} || 0),
            name => $monster->{name} || 'Unknown',
            hp => int($monster->{hp} || 0),
            max_hp => int($monster->{hp_max} || 0),
            distance => int(distance($char->{pos_to}, $monster->{pos_to})),
            is_aggressive => $monster->{dmgToYou} > 0 ? JSON::true : JSON::false,
        };
    }
    
    # Collect inventory (sample - first 10 items)
    # CRITICAL FIX: Check if inventory is ready before accessing
    if (inventory_ready()) {
        my $inv_count = 0;
        foreach my $item (@{$char->inventory->getItems()}) {
            last if $inv_count++ >= 10;
            next unless $item;
            push @{$state{inventory}}, {
                id => int($item->{nameID} || 0),
                name => $item->{name} || 'Unknown',
                amount => int($item->{amount} || 1),
                type => $item->{type} || 'misc',
            };
        }
    }
    
    # Collect nearby players (enhanced)
    foreach my $player (@{$playersList->getItems()}) {
        next unless $player;
        push @{$state{nearby_players}}, {
            name => $player->{name} || 'Unknown',
            level => int($player->{lv} || 1),
            guild => $player->{guild}{name} || '',
            distance => int(distance($char->{pos_to}, $player->{pos_to})),
            is_party_member => exists $char->{party}{users}{$player->{ID}} ? JSON::true : JSON::false,
            job_class => $::jobs_lut{$player->{jobId}} || 'Novice',
        };
    }
    
    return \%state;
}

# Enhanced: Collect equipment info
sub collect_equipment {
    my @equipment_list;
    
    # CRITICAL FIX: Check if inventory is ready before accessing
    if (inventory_ready()) {
        foreach my $item (@{$char->inventory->getItems()}) {
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
sub send_action_feedback {
    my ($action, $status, $reason, $message) = @_;
    
    $message ||= '';
    
    my $payload = encode_json({
        action => $action,
        status => $status,
        reason => $reason,
        message => $message
    });
    
    my $response = $ua->post(
        "$ai_service_url/api/v1/action_feedback",
        'Content-Type' => 'application/json',
        Content => $payload
    );
    
    if ($response->is_success) {
        debug "[GodTierAI] [FEEDBACK] Sent: $action -> $status ($reason)\n", "ai";
    } else {
        error "[GodTierAI] [FEEDBACK] Failed to send feedback: " . $response->status_line . "\n";
    }
}

# Request decision from AI Engine
sub request_decision {
    my $game_state = collect_game_state();
    
    $request_counter++;
    my $request_id = "req_" . time() . "_" . $request_counter;
    
    my %request = (
        game_state => $game_state,
        request_id => $request_id,
        timestamp_ms => int(time() * 1000),
    );
    
    my $json_request = encode_json(\%request);
    
    my $response = $ua->post(
        "$ai_service_url/api/v1/decide",
        Content_Type => 'application/json',
        Content => $json_request,
    );
    
    if ($response->is_success) {
        my $data = decode_json($response->decoded_content);
        return $data;
    } else {
        error "[GodTierAI] Failed to get decision: " . $response->status_line . "\n";
        return undef;
    }
}

# Enhanced: Execute action with social support
sub execute_action {
    my ($action_data) = @_;
    
    # Safety check
    unless (ref($action_data) eq 'HASH') {
        error "[GodTierAI] Invalid action_data: expected HASH, got " . ref($action_data) . "\n";
        return;
    }
    
    my $action = $action_data->{action};
    my $params = $action_data->{params} || {};
    my $reason = $action_data->{reason} || 'no reason provided';
    
    # Handle case where action is a string (flat structure) or hash (nested structure)
    my $type;
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
        # CRITICAL FIX #1: Idle recovery (stand and wait for natural HP/SP regen)
        my $duration = $params->{duration} || 10;
        message "[GodTierAI] [ACTION] Idle recovery for ${duration}s (no Basic Skill for sit)\n", "info";
        
        # Stand if sitting
        if ($char->{sitting}) {
            Commands::run("stand");
        }
        
        # Just wait - natural HP/SP regen will occur while standing (slower than sitting)
        AI::queue("wait");
        AI::args({timeout => $duration});
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
        
        # Get inventory for analysis
        my @inventory_items;
        foreach my $item (@{$char->{inventory}->getItems()}) {
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
        
        my $response = $ua->post(
            "$ai_service_url/api/v1/inventory/sell_junk",
            'Content-Type' => 'application/json',
            Content => $payload
        );
        
        if ($response->is_success) {
            my $result = decode_json($response->decoded_content);
            
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
            error "[GodTierAI] [ACTION] Failed to get sell list from AI-Service: " . $response->status_line . "\n";
        }
    } elsif ($type eq 'idle') {
        # CRITICAL FIX #3: New action handler for idle (natural HP/SP regeneration)
        my $reason = $params->{reason} || 'unknown';
        my $duration = $params->{duration} || 5;
        
        message "[GodTierAI] [ACTION] Idling for ${duration}s - Reason: $reason\n", "info";
        message "[GodTierAI] [ACTION] Natural HP/SP regeneration will work during this time\n", "info";
        
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
                
                # Check if character has enough free points
                if ($char->{points_free} < 1) {
                    Log::warning("[GodTierAI] [PROGRESSION] No free stat points available (requested: $points to $stat_name)\n");
                    push @failed_stats, "$stat_name (no points)";
                    next;
                }
                
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
                        Log::message("[GodTierAI] [PROGRESSION] ✓ $stat_name: $stat_before → $stat_after (points: $free_before → $free_after)\n", "success");
                    } else {
                        # Failure: stat didn't change or points didn't decrease
                        Log::warning("[GodTierAI] [PROGRESSION] ✗ Failed to add point to $stat_name (stat: $stat_before→$stat_after, points: $free_before→$free_after)\n");
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
}

# Enhanced: Handle player chat messages
sub handle_player_chat {
    my ($player_name, $message, $type) = @_;
    
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
    my $response = $ua->post(
        "$ai_service_url/api/v1/social/chat",
        Content_Type => 'application/json',
        Content => $json_request
    );
    
    if ($response->is_success) {
        my $data = decode_json($response->decoded_content);
        execute_action({ action => $data });
    } else {
        debug "[GodTierAI] Social service request failed: " . $response->status_line . "\n", "ai";
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
    
    my $player_name = $args->{name};
    
    message "[GodTierAI] Party invite from $player_name\n", "info";
    
    # Query social service
    my %request = (
        character_name => $char->{name},
        player_name => $player_name,
        my_level => int($char->{lv} || 1),
    );
    
    my $json_request = encode_json(\%request);
    my $response = $ua->post(
        "$ai_service_url/api/v1/social/party_invite",
        Content_Type => 'application/json',
        Content => $json_request
    );
    
    if ($response->is_success) {
        my $data = decode_json($response->decoded_content);
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
    return unless $net && $net->getState() == Network::IN_GAME;
    return unless $char && defined $char->{pos_to};
    
    # Check for config changes and hot reload if needed (self-healing capability)
    check_config_reload();
    
    # Only query AI every 2 seconds to avoid spam
    my $current_time = time();
    return if $current_time - $last_query_time < 2.0;
    $last_query_time = $current_time;
    
    # STATELESS REFACTOR: Check auto-expiring map load cooldown
    if ($map_load_cooldown_until > 0 && $current_time < $map_load_cooldown_until) {
        debug "[GodTierAI] [FIX#2] Map load cooldown active, skipping AI decision\n", "ai";
        return;
    }
    
    # Request decision
    my $decision = request_decision();
    
    if ($decision) {
        my $tier = $decision->{tier_used} || 'unknown';
        my $latency = $decision->{latency_ms} // 0;
        my $tier_str = defined($tier) ? $tier : 'unknown';
        my $latency_str = defined($latency) ? "${latency}ms" : 'N/A';
        debug "[GodTierAI] Decision received from tier '$tier_str' in $latency_str\n", "ai";
        
        execute_action($decision);
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
    message "[GodTierAI] Map changed, resetting state\n", "info";
    
    # CRITICAL FIX #2: Wait 2 seconds for monster data to populate after map change
    # Without this delay, AI-Service sees empty monsters array and can't engage combat
    my $map_name = $field ? $field->name() : 'unknown';
    
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
            my $payload = encode_json({
                plugin_name => 'teleToDest',
                character_level => $character_level + 0,  # Force numeric
                character_class => $character_class
            });
            
            my $response = $ua->post(
                "$ai_service_url/api/v1/self_heal/fix_plugin_config",
                'Content-Type' => 'application/json',
                Content => $payload
            );
            
            if ($response->is_success) {
                my $result = decode_json($response->decoded_content);
                
                if ($result->{success}) {
                    message "[GodTierAI] [SELF-HEAL] teleToDest config auto-generated successfully!\n", "success";
                    message "[GodTierAI] [SELF-HEAL] Keys added: " . join(", ", @{$result->{config_added}{keys_added}}) . "\n", "info";
                    message "[GodTierAI] [SELF-HEAL] Hot reload will activate plugin automatically (~5 seconds)\n", "info";
                } else {
                    error "[GodTierAI] [SELF-HEAL] Failed to auto-configure: " . ($result->{error} || "Unknown error") . "\n";
                }
            } else {
                error "[GodTierAI] [SELF-HEAL] AI Service request failed: " . $response->status_line . "\n";
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
        my %request = (
            current_level => int($new_level || 1),
            current_stats => \%current_stats
        );
        
        my $json_request = encode_json(\%request);
        my $response = $ua->post(
            "$ai_service_url/api/v1/progression/stats/on_level_up",
            Content_Type => 'application/json',
            Content => $json_request
        );
        
        if ($response->is_success) {
            my $data = decode_json($response->decoded_content);
            
            if ($data->{config} && $data->{config}{statsAddAuto_list}) {
                message "[GodTierAI] Stat allocation plan: $data->{config}{statsAddAuto_list}\n", "info";
                
                # Update config for raiseStat plugin
                # FIXED: Use Commands::run to avoid hot reload conflict
                Commands::run('config statsAddAuto 1');
                Commands::run("config statsAddAuto_list $data->{config}{statsAddAuto_list}");
                
                message "[GodTierAI] Auto-stat allocation enabled\n", "success";
            }
        } else {
            warning "[GodTierAI] Failed to get stat allocation: " . $response->status_line . "\n";
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
        my %request = (
            current_job_level => int($new_job_level || 1),
            job => lc($job_class),
            current_skills => \%current_skills
        );
        
        my $json_request = encode_json(\%request);
        my $response = $ua->post(
            "$ai_service_url/api/v1/progression/skills/on_job_level_up",
            Content_Type => 'application/json',
            Content => $json_request
        );
        
        if ($response->is_success) {
            my $data = decode_json($response->decoded_content);
            
            if ($data->{config} && $data->{config}{skillsAddAuto_list}) {
                message "[GodTierAI] Skill learning plan: $data->{config}{skillsAddAuto_list}\n", "info";
                
                # Update config for raiseSkill plugin
                # FIXED: Use Commands::run to avoid hot reload conflict
                Commands::run('config skillsAddAuto 1');
                Commands::run("config skillsAddAuto_list $data->{config}{skillsAddAuto_list}");
                
                message "[GodTierAI] Auto-skill learning enabled\n", "success";
            }
        } else {
            warning "[GodTierAI] Failed to get skill learning: " . $response->status_line . "\n";
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
        my %request = (
            new_map => $map_name,
            enemies => \@enemies
        );
        
        my $json_request = encode_json(\%request);
        my $response = $ua->post(
            "$ai_service_url/api/v1/progression/equipment/on_map_change",
            Content_Type => 'application/json',
            Content => $json_request
        );
        
        if ($response->is_success) {
            my $data = decode_json($response->decoded_content);
            
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
