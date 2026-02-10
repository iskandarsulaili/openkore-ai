# Intelligent Loot Prioritization System

Production-grade adaptive loot prioritization system for autonomous AI bot with risk-based tactical retrieval.

## 🎯 Overview

The Intelligent Loot Prioritization System makes smart, context-aware decisions about item pickup by:
- **Prioritizing 350+ items** by value, rarity, and importance
- **Assessing risk** for each loot situation (0-100 scale)
- **Selecting tactics** based on risk level and historical success
- **Learning from experience** to improve over time
- **Making sacrifice calculations** (is dying worth the loot?)

## 📊 System Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│              INTELLIGENT LOOT SYSTEM                     │
├─────────────────────────────────────────────────────────┤
│  1. Loot Prioritizer    → Item database & sorting       │
│  2. Risk Calculator     → Risk assessment (0-100)       │
│  3. Tactical Retrieval  → 8 tactical strategies         │
│  4. Loot Learner        → Adaptive learning & tracking  │
└─────────────────────────────────────────────────────────┘
```

### 1. Loot Prioritizer (`loot_prioritizer.py`)

**Features:**
- 350+ pre-loaded items with priorities
- Dynamic slotted equipment detection (`[1]`, `[2]`, `[3]`, `[4]`)
- Pattern matching for unknown items
- User customization support
- Category-based priority fallbacks

**Item Categories:**
- `mvp_card` (Priority 1-3): Always highest priority
- `rare_card` (Priority 5-10): Valuable cards (Ghostring, Angeling, etc.)
- `boss_card` (Priority 5): Boss monster cards
- `slotted_equipment` (Priority 15-25): Gear with card slots
- `rare_equipment` (Priority 15-20): Boss drops, event items
- `consumable` (Priority 30-50): Potions, buffs
- `crafting_material` (Priority 40-60): Oridecon, Elunium, etc.
- `collectible` (Priority 25-35): Boxes, special items
- `currency` (Priority 25-40): Tickets, coins

### 2. Risk Calculator (`risk_calculator.py`)

**Risk Formula:**
```python
risk_score = (
    (100 - hp_percent) * 0.30 +           # HP: 30%
    (nearby_enemies * 10) * 0.25 +        # Enemy count: 25%
    (distance_to_item / 20 * 100) * 0.15 + # Distance: 15%
    (distance_to_safety / 20 * 100) * 0.15 + # Safety: 15%
    (0 if escape_ready else 50) * 0.10 +  # Escape: 10%
    (0 if party_nearby else 30) * 0.05    # Party: 5%
)
```

**Risk Categories:**
- **0-30 (Safe)**: Systematic collection of all valuable items
- **31-60 (Moderate)**: Tactical approaches (kiting, hit-and-run, etc.)
- **61-100 (High)**: Sacrifice calculation, emergency grab

### 3. Tactical Retrieval (`tactical_retrieval.py`)

**8 Tactical Strategies:**

| Tactic | Risk Level | Description |
|--------|-----------|-------------|
| `systematic_collection` | 0-30 | Collect all valuable items in priority order |
| `kiting` | 31-60 | Kite enemies away, circle back to loot |
| `hit_and_run` | 31-60 | Quick dash, grab, escape (Fly Wing/Teleport) |
| `terrain` | 31-60 | Use walls/obstacles to block enemies |
| `aggro_manipulation` | 31-60 | Attack enemy, run, grab while enemy chases |
| `pet_tanking` | 31-60 | Use pet/homunculus to distract |
| `emergency_grab` | 61-100 | Grab top 1-3 items before death |
| `sacrifice` | 61-100 | Calculated death for high-value items |

**Sacrifice Logic:**
- MVP cards: **ALWAYS** worth dying for
- High priority items (≤10): Worth dying if value > 5x respawn cost
- Multiple high-value items: Calculate total value vs cost
- Otherwise: Retreat and survive

### 4. Loot Learner (`loot_learner.py`)

**Adaptive Learning:**
- Tracks success/failure for each tactic at each risk level
- Calculates success rates over rolling 7-day window
- Detects repeated failures (3+ consecutive fails)
- Recommends best tactic based on historical data
- Suggests alternatives when current approach fails

**Database Tracking:**
```sql
CREATE TABLE loot_attempts (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    item_id INTEGER,
    item_name TEXT,
    priority_level INTEGER,
    category TEXT,
    risk_level INTEGER,
    tactic_used TEXT,
    success BOOLEAN,
    hp_percent REAL,
    nearby_enemies INTEGER,
    distance_to_item REAL,
    time_taken REAL,
    died BOOLEAN,
    context_json TEXT
);
```

## 🚀 Usage

### Basic Usage

The system is automatically integrated into the main decision loop:

```python
# In main.py decision endpoint
loot_action = handle_loot_decision(
    game_state=game_state,
    loot_prioritizer=loot_prioritizer,
    risk_calculator=risk_calculator,
    tactical_retrieval=tactical_retrieval,
    loot_learner=loot_learner
)

if loot_action:
    return loot_action  # Execute loot retrieval
```

### Game State Requirements

The game state must include:
```python
{
    "character": {
        "hp": 1500,
        "max_hp": 2000,
        "hp_percent": 75.0,
        "sp": 300,
        "max_sp": 500,
        "sp_percent": 60.0,
        "position": {"x": 100, "y": 150, "map": "prt_fild08"},
        "level": 50
    },
    "ground_items": [  # ← REQUIRED for loot system
        {
            "item_id": 4047,
            "item_name": "Ghostring Card",
            "position": {"x": 105, "y": 155},
            "binID": 12345
        }
    ],
    "monsters": [...],
    "inventory": [...],
    "skills": {...}
}
```

## ⚙️ Configuration

### Default Config (`loot_config.json`)

```json
{
  "risk_tolerance": {
    "safe_threshold": 30,
    "moderate_threshold": 60,
    "sacrifice_allowed": true
  },
  "sacrifice_rules": {
    "min_priority_for_sacrifice": 10,
    "min_value_multiplier": 5.0,
    "mvp_card_always_worth": true,
    "max_deaths_per_hour": 3
  },
  "tactical_preferences": {
    "prefer_kiting": true,
    "prefer_hit_and_run": true,
    "use_terrain": true,
    "use_pet_tanking": false,
    "aggro_manipulation_enabled": true
  }
}
```

### User Customization (`loot_config_user.json`)

```json
{
  "custom_priorities": {
    "4047": {
      "priority": 1,
      "value": 50000000,
      "notes": "Ghostring Card - must have"
    }
  },
  "risk_preferences": {
    "max_acceptable_risk": 70,
    "sacrifice_for_mvp": true,
    "max_deaths_per_session": 5
  },
  "blacklist": {
    "item_names": ["Jellopy", "Sticky Mucus"]
  },
  "whitelist": {
    "item_ids": [4047, 4054, 4125]
  }
}
```

## 📈 Statistics & Monitoring

### Get Loot Statistics

```python
stats = loot_learner.get_statistics(days=7)

print(f"Total attempts: {stats['overall']['total_attempts']}")
print(f"Success rate: {stats['overall']['total_successes'] / stats['overall']['total_attempts']:.1%}")

for tactic in stats['per_tactic']:
    print(f"{tactic['tactic_used']}: {tactic['successes']}/{tactic['attempts']} ({tactic['successes']/tactic['attempts']:.1%})")
```

### Clear Old Data

```python
loot_learner.clear_old_data(days=30)  # Keep last 30 days
```

## 🔧 OpenKore Plugin Integration

### Required Modification

In `GodTierAI.pm`, add ground items to game state:

```perl
# Add ground items to game state
my @ground_items;
for my $item (@{$itemsList->getItems()}) {
    push @ground_items, {
        item_id => $item->{nameID},
        item_name => $item->{name},
        position => {
            x => $item->{pos}{x},
            y => $item->{pos}{y}
        },
        binID => $item->{binID}
    };
}
$game_state{ground_items} = \@ground_items;
```

### Action Execution

Handle `loot_tactical` action:

```perl
if ($action eq 'loot_tactical') {
    my $tactic = $params->{tactic};
    my @items_to_grab = @{$params->{items_to_grab}};
    
    # Execute tactic-specific behavior
    if ($tactic eq 'systematic_collection') {
        # Collect items in order
        for my $binID (@items_to_grab) {
            Commands::run("take $binID");
        }
    }
    elsif ($tactic eq 'hit_and_run') {
        # Quick grab + escape
        for my $binID (@items_to_grab) {
            Commands::run("take $binID");
        }
        Commands::run("use Fly Wing");
    }
    elsif ($tactic eq 'sacrifice') {
        # All-out grab, accept death
        for my $binID (@items_to_grab) {
            Commands::run("take $binID");
        }
    }
    # ... other tactics
}
```

## 📊 Examples

### Example 1: Safe Situation

```
Ground items: [White Potion, Blue Potion, Oridecon]
HP: 90%, SP: 80%, Nearby enemies: 0
Risk: 15 (Safe)
Tactic: systematic_collection
Result: Collect all 3 items in priority order
```

### Example 2: Moderate Risk

```
Ground item: [Ghostring Card]
HP: 60%, SP: 50%, Nearby enemies: 3
Risk: 45 (Moderate)
Tactic: hit_and_run (78% success rate)
Result: Dash in, grab card, use Fly Wing to escape
```

### Example 3: High Risk Sacrifice

```
Ground items: [Baphomet Card, Angeling Card]
HP: 25%, SP: 10%, Nearby enemies: 8
Risk: 85 (High)
Value: 55M zeny vs 10k respawn cost (5500x multiplier)
Tactic: sacrifice
Result: Accept death, grab both MVP cards (worth it!)
```

### Example 4: Adaptive Learning

```
Attempt 1: kiting tactic - FAILED
Attempt 2: kiting tactic - FAILED  
Attempt 3: kiting tactic - FAILED
System: "Repeated failures detected, switching to hit_and_run"
Attempt 4: hit_and_run tactic - SUCCESS
Future: hit_and_run recommended for similar situations
```

## 🎯 Success Criteria

✅ **Functional**
- Detects ground items from game state
- Prioritizes by value and importance
- Calculates risk accurately
- Selects appropriate tactics
- Learns from success/failure

✅ **Behavioral**
- Safe: Collects all valuable items
- Moderate: Uses tactical approaches
- High: Makes intelligent sacrifices
- MVP cards: Always highest priority
- Improves over time with learning

✅ **Performance**
- <50ms priority calculation
- <20ms risk assessment
- Handles 100+ ground items efficiently
- Database queries optimized with indices

## 📝 Logging

All loot decisions are logged with context:

```
[LOOT] Found 5 items on ground
[LOOT] Top priority: Ghostring Card (Priority: 3, Value: 50M zeny)
[LOOT] Risk assessment: 45/100 (moderate)
[LOOT] Recommended tactic: hit_and_run (Confidence: 78%)
[LOOT] Initiating tactical loot retrieval: hit_and_run
[LOOT] Tracked attempt: Ghostring Card - SUCCESS
```

## 🚀 Future Enhancements

Potential improvements:
- Machine learning for risk prediction
- Dynamic priority adjustment based on character needs
- Cooperative loot distribution in parties
- Market price integration for accurate value estimates
- Advanced pathfinding for terrain exploitation
- Voice alerts for MVP card drops

## 📜 License

Part of the OpenKore AI Service - Production-grade autonomous gameplay system.

---

**Version**: 1.0  
**Created**: 2026-02-09  
**Items**: 350+  
**Tactics**: 8  
**Adaptable**: Yes
