package CombatIntelligence;

use strict;
use warnings;
use JSON;
use LWP::UserAgent;
use Log qw(message warning error debug);
use Time::HiRes qw(time);

=head1 NAME

CombatIntelligence - Priority 1 Combat Intelligence Integration (opkAI)

=head1 DESCRIPTION

Integrates opkAI's 4 combat intelligence systems:
1. Threat Assessment (9-factor)
2. Kiting Engine (5-state)
3. Target Selection (XP/zeny efficiency)
4. Positioning Engine (5-factor)

Flow: Game Server -> OpenKore -> AI Service -> Combat Intelligence

=cut

my $ai_service_url = "http://127.0.0.1:9902";
my $ua = LWP::UserAgent->new(timeout => 5);  # Fast timeout for combat
my $threat_cache = {};
my $last_target_id = undef;

=head2 assess_threat_before_attack

Pre-engagement threat assessment using 9-factor analysis.
Returns: {should_engage => bool, win_probability => float, threat_level => str, ...}

=cut

sub assess_threat_before_attack {
    my ($target, $character, $nearby_enemies, $consumables) = @_;
    
    eval {
        # Check cache first (valid for 5 seconds)
        my $cache_key = $target->{binID};
        if ($threat_cache->{$cache_key} && 
            time() - $threat_cache->{$cache_key}->{timestamp} < 5) {
            return $threat_cache->{$cache_key}->{result};
        }
        
        # Build request data
        my $data = {
            target => {
                id => $target->{nameID},
                name => $target->{name},
                level => int($target->{lv} || 1),
                hp => int($target->{hp} || $target->{hp_max} || 1000),
                hp_max => int($target->{hp_max} || 1000),
                element => $target->{element} || 'neutral',
                race => $target->{race} || 'unknown',
                size => $target->{size} || 'medium',
                pos => [int($target->{pos_to}{x} || 0), int($target->{pos_to}{y} || 0)]
            },
            character => {
                level => int($character->{lv} || 1),
                hp => int($character->{hp} || 0),
                sp => int($character->{sp} || 0),
                hp_max => int($character->{hp_max} || 1),
                sp_max => int($character->{sp_max} || 1),
                attack => int($character->{attack} || 0),
                matk => int($character->{attack_magic_max} || 0),
                element => $character->{element} || 'neutral',
                buffs => collect_active_buffs($character),
                skills => collect_available_skills($character),
                equipment => collect_equipment($character),
                pos => [int($character->{pos_to}{x} || 0), int($character->{pos_to}{y} || 0)]
            },
            nearby_enemies => $nearby_enemies || [],
            consumables => $consumables || {
                potions => count_potions($character),
                fly_wings => count_item_by_name('Fly Wing')
            }
        };
        
        # Call AI Service
        my $response = $ua->post(
            "$ai_service_url/api/v1/combat/threat/assess",
            Content_Type => 'application/json',
            Content => encode_json($data)
        );
        
        if ($response->is_success) {
            my $result = decode_json($response->decoded_content);
            
            # Cache result
            $threat_cache->{$cache_key} = {
                result => $result,
                timestamp => time()
            };
            
            return $result;
        } else {
            warning "[CombatIntelligence] Threat assessment failed: " . $response->status_line . "\n";
            return undef;
        }
    };
    
    if ($@) {
        error "[CombatIntelligence] Threat assessment error: $@\n";
        return undef;
    }
}

=head2 update_kiting_position

Update kiting state machine for ranged combat.
Returns: {state => str, movement_position => [x, y], reason => str}

=cut

sub update_kiting_position {
    my ($job_class, $char_pos, $enemy_pos, $hp_percent, $enemy_targeting_us) = @_;
    
    $enemy_targeting_us = 1 unless defined $enemy_targeting_us;
    
    eval {
        my $data = {
            job_class => $job_class,
            char_pos => $char_pos,
            enemy_pos => $enemy_pos,
            hp_percent => $hp_percent,
            enemy_targeting_us => $enemy_targeting_us ? JSON::true : JSON::false
        };
        
        my $response = $ua->post(
            "$ai_service_url/api/v1/combat/kiting/update",
            Content_Type => 'application/json',
            Content => encode_json($data)
        );
        
        if ($response->is_success) {
            return decode_json($response->decoded_content);
        } else {
            warning "[CombatIntelligence] Kiting update failed: " . $response->status_line . "\n";
            return undef;
        }
    };
    
    if ($@) {
        error "[CombatIntelligence] Kiting error: $@\n";
        return undef;
    }
}

=head2 select_best_target

Select optimal target using XP/zeny efficiency.
Returns: {target => {monster_id, score, xp_efficiency, zeny_efficiency, ...}}

=cut

sub select_best_target {
    my ($monsters, $character, $quest_targets) = @_;
    
    eval {
        my $data = {
            monsters => $monsters,
            character => {
                level => int($character->{lv} || 1),
                pos => [int($character->{pos_to}{x} || 0), int($character->{pos_to}{y} || 0)],
                attack => int($character->{attack} || 0),
                matk => int($character->{attack_magic_max} || 0),
                element => $character->{element} || 'neutral',
                buffs => collect_active_buffs($character),
                aspd => int($character->{attack_speed} || 150)
            },
            quest_targets => $quest_targets || []
        };
        
        my $response = $ua->post(
            "$ai_service_url/api/v1/combat/target/select",
            Content_Type => 'application/json',
            Content => encode_json($data)
        );
        
        if ($response->is_success) {
            my $result = decode_json($response->decoded_content);
            if ($result->{status} eq 'success') {
                $last_target_id = $result->{target}->{monster_id};
                return $result->{target};
            }
        }
        return undef;
    };
    
    if ($@) {
        error "[CombatIntelligence] Target selection error: $@\n";
        return undef;
    }
}

=head2 find_optimal_position

Find optimal combat position using 5-factor scoring.
Returns: {x, y, total_score, safety_score, damage_score, ...}

=cut

sub find_optimal_position {
    my ($char_pos, $target_pos, $skill_range, $enemies, $map_data, $hp_percent, $job_class, $aoe_range) = @_;
    
    $aoe_range = 0 unless defined $aoe_range;
    
    eval {
        my $data = {
            char_pos => $char_pos,
            target_pos => $target_pos,
            skill_range => $skill_range,
            enemies => $enemies,
            map_data => $map_data,
            hp_percent => $hp_percent,
            job_class => $job_class,
            aoe_range => $aoe_range
        };
        
        my $response = $ua->post(
            "$ai_service_url/api/v1/combat/positioning/optimal",
            Content_Type => 'application/json',
            Content => encode_json($data)
        );
        
        if ($response->is_success) {
            return decode_json($response->decoded_content);
        }
        return undef;
    };
    
    if ($@) {
        error "[CombatIntelligence] Positioning error: $@\n";
        return undef;
    }
}

=head2 clear_target

Clear current target (when target dies).

=cut

sub clear_target {
    eval {
        $last_target_id = undef;
        $ua->post("$ai_service_url/api/v1/combat/target/clear");
    };
}

=head2 Helper Functions

=cut

sub collect_active_buffs {
    my ($character) = @_;
    my @buffs = ();
    
    # Check status effects
    foreach my $effect (keys %{$character->{statuses}}) {
        push @buffs, $effect;
    }
    
    return \@buffs;
}

sub collect_available_skills {
    my ($character) = @_;
    my @skills = ();
    
    # Get skills from $char object
    if ($char && $char->{skills}) {
        foreach my $skill_name (keys %{$char->{skills}}) {
            my $skill = $char->{skills}{$skill_name};
            if ($skill && $skill->{lv} > 0) {
                push @skills, $skill_name;
            }
        }
    }
    
    return \@skills;
}

sub collect_equipment {
    my ($character) = @_;
    my %equipment = ();
    
    # Get equipped items
    if ($char && $char->{equipment}) {
        foreach my $slot (keys %{$char->{equipment}}) {
            my $item = $char->{equipment}{$slot};
            if ($item) {
                $equipment{$slot} = {
                    name => $item->{name},
                    refine => $item->{upgrade} || 0,
                    cards => $item->{cards} || []
                };
            }
        }
    }
    
    return \%equipment;
}

sub count_potions {
    my ($character) = @_;
    my $count = 0;
    
    # Count healing items
    $count += count_item_by_name('Red Potion');
    $count += count_item_by_name('Orange Potion');
    $count += count_item_by_name('Yellow Potion');
    $count += count_item_by_name('White Potion');
    $count += count_item_by_name('Blue Potion');
    
    return $count;
}

sub count_item_by_name {
    my ($name) = @_;
    my $count = 0;
    
    if ($char && $char->{inventory}) {
        foreach my $item (@{$char->{inventory}}) {
            if ($item && $item->{name} eq $name) {
                $count += $item->{amount} || 1;
            }
        }
    }
    
    return $count;
}

1;

__END__

=head1 INTEGRATION EXAMPLE

In GodTierAI.pm:

    use CombatIntelligence;
    
    # Before attacking
    sub on_attack_start {
        my $assessment = CombatIntelligence::assess_threat_before_attack(
            $target, $char, \@nearby_enemies, \%consumables
        );
        
        if ($assessment && !$assessment->{should_engage}) {
            # Cancel attack
            message "[ThreatAssessor] DANGER: $assessment->{threat_level} - ".
                    "Win prob: $assessment->{win_probability}%. AVOIDING.\n", "warning";
            Commands::run('move ' . $char->{pos_to}{x} . ' ' . $char->{pos_to}{y});
            return 0;  # Cancel
        }
    }
    
    # During ranged combat
    sub on_ai_pre_ranged {
        my $kiting = CombatIntelligence::update_kiting_position(
            $config{jobClass}, 
            [$char->{pos_to}{x}, $char->{pos_to}{y}],
            [$target->{pos_to}{x}, $target->{pos_to}{y}],
            $char->{hp} / $char->{hp_max},
            1
        );
        
        if ($kiting && $kiting->{movement_position}) {
            my ($x, $y) = @{$kiting->{movement_position}};
            Commands::run("move $x $y");
        }
    }

=head1 AUTHOR

GodTier AI System - Combat Intelligence Module

=cut
