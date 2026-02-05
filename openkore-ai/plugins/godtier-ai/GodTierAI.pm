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
my $ua = LWP::UserAgent->new(timeout => 30);
my $request_counter = 0;

sub on_unload {
    Plugins::delHooks($hooks);
    message "[GodTierAI] Unloaded\n", "success";
}

# Initialize plugin
$hooks = Plugins::addHooks(
    ['AI_pre', \&on_ai_pre, undef],
    ['packet_mapChange', \&on_map_change, undef],
);

message "[GodTierAI] Loaded successfully\n", "success";
message "[GodTierAI] AI Engine URL: $ai_engine_url\n", "info";

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

# Collect game state
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
    
    # Collect nearby players
    foreach my $player (@{$playersList->getItems()}) {
        next unless $player;
        push @{$state{nearby_players}}, {
            name => $player->{name} || 'Unknown',
            level => $player->{lv} || 1,
            guild => $player->{guild}{name} || '',
            distance => int(distance($char->{pos_to}, $player->{pos_to})),
            is_party_member => exists $char->{party}{users}{$player->{ID}} ? JSON::true : JSON::false,
        };
    }
    
    return \%state;
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

# Execute action
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
    } elsif ($type eq 'none') {
        # No action needed
        debug "[GodTierAI] Action: None ($reason)\n", "ai";
    } else {
        warning "[GodTierAI] Unknown action type: $type\n";
    }
}

# AI_pre hook - called every AI cycle
sub on_ai_pre {
    return unless $net && $net->getState() == Network::IN_GAME;
    return unless $char && defined $char->{pos_to};
    
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
    message "[GodTierAI] Map changed, resetting state\n", "info";
}

1;
