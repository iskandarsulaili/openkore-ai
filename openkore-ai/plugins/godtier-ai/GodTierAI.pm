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
my $ua = LWP::UserAgent->new(timeout => 30);
my $request_counter = 0;

# Hot reload configuration monitoring
my $config_file_path = "control/config.txt";
my $last_config_mtime = 0;
my $config_check_interval = 5;  # Check every 5 seconds
my $last_config_check = 0;

sub on_unload {
    Plugins::delHooks($hooks);
    message "[GodTierAI] Unloaded\n", "success";
}

# Plugin initialization function - called explicitly by OpenKore
sub on_load {
    message "[GodTierAI] Initializing plugin...\n", "info";
    
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
        my $response = $ua->get("$ai_service_url/health");
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

# Collect game state (enhanced with equipment, quests, guild info)
sub collect_game_state {
    my %state = (
        character => {
            name => $char->{name} || 'Unknown',
            level => $char->{lv} || 1,
            base_exp => $char->{exp} || 0,
            job_exp => $char->{exp_job} || 0,
            hp => $char->{hp} || 0,
            max_hp => $char->{hp_max} || 1,
            sp => $char->{sp} || 0,
            max_sp => $char->{sp_max} || 1,
            position => {
                map => $field ? $field->name() : 'unknown',
                x => $char->{pos_to}{x} || 0,
                y => $char->{pos_to}{y} || 0,
            },
            weight => $char->{weight} || 0,
            max_weight => $char->{weight_max} || 1,
            zeny => $char->{zeny} || 0,
            job_class => $jobs_lut{$char->{jobId}} || 'Unknown',
            status_effects => [],
            # Enhanced: Equipment info
            equipment => collect_equipment(),
            # Enhanced: Guild info
            guild => {
                name => $char->{guild}{name} || '',
                id => $char->{guild}{ID} || '',
                position => $char->{guild}{title} || '',
            },
            # Enhanced: Active quests (simplified)
            active_quests => scalar(keys %questList) || 0,
        },
        monsters => [],
        inventory => [],
        nearby_players => [],
        party_members => {},
        timestamp_ms => int(time() * 1000),
    );
    
    # Collect monsters
    foreach my $monster (@{$monstersList->getItems()}) {
        next unless $monster;
        push @{$state{monsters}}, {
            id => $monster->{binID},
            name => $monster->{name} || 'Unknown',
            hp => $monster->{hp} || 0,
            max_hp => $monster->{hp_max} || 0,
            distance => int(distance($char->{pos_to}, $monster->{pos_to})),
            is_aggressive => $monster->{dmgToYou} > 0 ? JSON::true : JSON::false,
        };
    }
    
    # Collect inventory (sample - first 10 items)
    my $inv_count = 0;
    foreach my $item (@{$char->inventory->getItems()}) {
        last if $inv_count++ >= 10;
        next unless $item;
        push @{$state{inventory}}, {
            id => $item->{nameID},
            name => $item->{name} || 'Unknown',
            amount => $item->{amount} || 1,
            type => $item->{type} || 'misc',
        };
    }
    
    # Collect nearby players (enhanced)
    foreach my $player (@{$playersList->getItems()}) {
        next unless $player;
        push @{$state{nearby_players}}, {
            name => $player->{name} || 'Unknown',
            level => $player->{lv} || 1,
            guild => $player->{guild}{name} || '',
            distance => int(distance($char->{pos_to}, $player->{pos_to})),
            is_party_member => exists $char->{party}{users}{$player->{ID}} ? JSON::true : JSON::false,
            job_class => $jobs_lut{$player->{jobId}} || 'Unknown',
        };
    }
    
    return \%state;
}

# Enhanced: Collect equipment info
sub collect_equipment {
    my @equipment_list;
    
    foreach my $item (@{$char->inventory->getItems()}) {
        next unless $item && $item->{equipped};
        push @equipment_list, {
            slot => $item->{type_equip} || 'unknown',
            name => $item->{name} || 'Unknown',
            id => $item->{nameID},
        };
    }
    
    return \@equipment_list;
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
        "$ai_engine_url/api/v1/decide",
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
    
    my $action = $action_data->{action};
    my $type = $action->{type};
    my $params = $action->{parameters};
    my $reason = $action->{reason};
    
    debug "[GodTierAI] Executing action: $type ($reason)\n", "ai";
    
    if ($type eq 'attack') {
        # Attack logic (will be implemented in Phase 2)
        message "[GodTierAI] Action: Attack\n", "info";
    } elsif ($type eq 'skill') {
        # Skill logic (will be implemented in Phase 2)
        message "[GodTierAI] Action: Use skill\n", "info";
    } elsif ($type eq 'move') {
        # Move logic (will be implemented in Phase 2)
        message "[GodTierAI] Action: Move\n", "info";
    } elsif ($type eq 'item') {
        # Item usage logic
        my $item_name = $params->{item};
        message "[GodTierAI] Action: Use item '$item_name'\n", "info";
        Commands::run("is $item_name");
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
    } else {
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
        my_level => $char->{lv},
        my_job => $jobs_lut{$char->{jobId}} || 'Unknown',
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
        my_level => $char->{lv},
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
    state $last_query_time = 0;
    my $current_time = time();
    return if $current_time - $last_query_time < 2.0;
    $last_query_time = $current_time;
    
    # Request decision
    my $decision = request_decision();
    
    if ($decision) {
        my $tier = $decision->{tier_used};
        my $latency = $decision->{latency_ms};
        debug "[GodTierAI] Decision received from tier '$tier' in ${latency}ms\n", "ai";
        
        execute_action($decision);
    }
}

# Map change hook
sub on_map_change {
    my (undef, $args) = @_;
    message "[GodTierAI] Map changed, resetting state\n", "info";
    
    # Notify equipment manager about map change
    notify_equipment_map_change($field->name()) if $field;
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
        str => $char->{str} || 1,
        agi => $char->{agi} || 1,
        vit => $char->{vit} || 1,
        int => $char->{int} || 1,
        dex => $char->{dex} || 1,
        luk => $char->{luk} || 1
    );
    
    # Request stat allocation from AI Service
    eval {
        my %request = (
            current_level => $new_level,
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
                configModify('statsAddAuto', 1);
                configModify('statsAddAuto_list', $data->{config}{statsAddAuto_list});
                
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
    my $job_class = $jobs_lut{$char->{jobId}} || 'Unknown';
    message "[GodTierAI] Job Level UP! New job level: $new_job_level ($job_class)\n", "success";
    
    # Collect current skills
    my %current_skills = ();
    foreach my $skill_handle (keys %{$char->{skills}}) {
        my $skill = $char->{skills}{$skill_handle};
        $current_skills{$skill_handle} = $skill->{lv} || 0 if $skill;
    }
    
    # Request skill learning from AI Service
    eval {
        my %request = (
            current_job_level => $new_job_level,
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
                configModify('skillsAddAuto', 1);
                configModify('skillsAddAuto_list', $data->{config}{skillsAddAuto_list});
                
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
