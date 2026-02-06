# EventMacro & Macro Plugin Complete Reference

## Document Purpose
**THE definitive single-source-of-truth reference for eventMacro and macro plugin in OpenKore.**

This document is designed for CrewAI macro-generating agents to ensure 100% syntactically correct and functionally complete macro code generation with ZERO ambiguity and ZERO information loss.

**Document Version:** 1.0  
**Last Updated:** 2026-02-06  
**Sources:** OpenKore Wiki (eventMacro, macro_plugin), Plugin Source Code, Working Examples

---

## Table of Contents

1. [Architecture & Execution Model](#1-architecture--execution-model)
2. [Automacro System (eventMacro)](#2-automacro-system-eventmacro)
3. [Macro System (macro plugin)](#3-macro-system-macro-plugin)
4. [Variable System](#4-variable-system)
5. [Condition Modules Reference](#5-condition-modules-reference)
6. [Functions & Keywords Reference](#6-functions--keywords-reference)
7. [Working Patterns from Examples](#7-working-patterns-from-examples)
8. [Integration & Compatibility](#8-integration--compatibility)
9. [Debugging & Troubleshooting](#9-debugging--troubleshooting)

---

## 1. Architecture & Execution Model

### 1.1 EventMacro vs Macro Plugin

**EventMacro (New System):**
- Modern condition-based automation system
- Located in: `plugins/eventMacro/`
- Uses Condition modules (object-oriented)
- Supports complex state and event conditions
- Hook-based architecture with dynamic variable support
- Case-sensitive condition matching

**Macro Plugin (Legacy System):**
- Simpler macro execution system
- Located in: `plugins/macro/`
- Automacros for triggering + Macros for execution
- Procedural syntax with simple conditions
- Still widely used and fully functional

**KEY DISTINCTION:**
- **eventMacro** = Advanced condition evaluation system
- **macro plugin** = Command execution and flow control system
- Both systems can work together in OpenKore

### 1.2 Load Order and Initialization

```
1. OpenKore Core Initialization
2. Plugin Loading Phase
   ├── eventMacro plugin loads
   │   ├── Loads Condition modules from plugins/eventMacro/eventMacro/Condition/
   │   ├── Registers hook listeners
   │   └── Initializes variable tracking
   └── macro plugin loads
       ├── Parses control/macros.txt or control/eventMacros.txt
       ├── Compiles automacros and macros
       └── Registers to AI queue
3. Configuration Loading
4. Character Login
5. Condition Evaluation Begins
```

### 1.3 Execution Timing and Priority

**Automacro Checking:**
- Checked continuously when AI is active
- Priority: Lower number = checked first (default: 0)
- Exclusive macros block other automacros from triggering
- `timeout` setting prevents re-trigger within N seconds
- `run-once` locks automacro until manually released

**Macro Execution:**
- Runs on AI queue with configurable delay
- `macro_delay` (in timeouts.txt) controls inter-command delay
- `overrideAI` option forces macro to override normal AI
- `exclusive` flag prevents interruption by automacros
- `pause` command suspends ALL character actions

### 1.4 State Persistence Mechanisms

**Variable Persistence:**
- Macro variables ($var) are GLOBAL and persist across macros
- Special variables ($.var) are read-only and auto-updated
- Automacro `set` command creates persistent variables
- Variables survive macro execution but reset on reload

**Automacro State:**
- `run-once` automacros stay locked until `release` command
- `disabled` automacros must be released before first trigger
- `timeout` state persists per automacro instance
- Automacro variables set by conditions (e.g., $.lastMonster)

---

## 2. Automacro System (eventMacro)

### 2.1 Complete Automacro Syntax

```
automacro <automacro_name> {
    <condition_type> <condition_parameters>
    [<condition_type> <condition_parameters>]
    [...]
    
    # Special Parameters (optional)
    [exclusive <0|1>]
    [priority <number>]
    [timeout <seconds>]
    [run-once <0|1>]
    [disabled <0|1>]
    [delay <seconds>]
    [overrideAI <0|1>]
    [macro_delay <seconds>]
    [orphan <terminate|reregister|reregister_safe>]
    [set <variable> <value>]
    
    # Action Definition
    call <macro_name>
    # OR
    call {
        <macro_commands>
    }
}
```

### 2.2 Automacro Special Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `exclusive` | boolean | 0 | Prevent automacros from canceling this macro |
| `priority` | number | 0 | Lower number = checked first (0 = highest priority) |
| `timeout` | seconds | none | Minimum wait time before re-trigger |
| `run-once` | boolean | 0 | Lock automacro after one trigger (use `release` to unlock) |
| `disabled` | boolean | 0 | Start automacro in locked state |
| `delay` | seconds | none | Wait N seconds before calling macro |
| `overrideAI` | boolean | 0 | Override OpenKore's AI during macro execution |
| `macro_delay` | seconds | config | Override global macro_delay for this macro |
| `orphan` | method | terminate | Handle orphaned macros: terminate/reregister/reregister_safe |
| `set` | var value | none | Set variable when automacro triggers (can have multiple) |

### 2.3 Condition Types Overview

**State Conditions** - Always evaluating, must ALL be true:
- Can use multiple instances per automacro (AND logic)
- Examples: `hp`, `sp`, `inventory`, `location`, `status`, `monster`, `player`
- Comma-separated values within one condition = OR logic

**Event Conditions** - Trigger on specific events, max ONE per automacro:
- Examples: `console`, `pm`, `pubm`, `party`, `guild`, `mapchange`, `spell`, `areaSpell`
- Set special variables (e.g., `$.lastpm`, `$.lastpubMsg`)

### 2.4 Condition Combination Rules

```
# Multiple lines = AND logic
hp < 50%
sp > 30%
inventory "Yggdrasil Berry" > 0

# Comma-separated = OR logic
monster "Poring", "Drops" < 5
location prontera, geffen, payon

# Complex combinations
location prontera
hp < 50%
inventory "Red Potion" > 5, "Orange Potion" > 3
status not "Poisoned", not "Curse"
```

### 2.5 Case Sensitivity Rules

**CRITICAL:** eventMacro conditions are **CASE SENSITIVE** in most contexts:
- Monster names: Exact case match required ("Poring" ≠ "poring")
- Item names: Exact case match required ("Red Potion" ≠ "red potion")  
- Map names: Usually case-insensitive ("prontera" = "Prontera")
- Player names: Case-sensitive
- Config keys: Case-sensitive
- Status names: Check tables/statusnametable.txt for exact names

**Exception:** Regular expressions (`/regex/i`) with `i` flag are case-insensitive

---

## 3. Macro System (macro plugin)

### 3.1 Complete Macro Syntax

```
macro <macro_name> {
    <command>
    <command>
    [...]
}
```

**Macro Name Rules:**
- Letters and numbers only
- No spaces or special characters
- Must be unique
- Case-sensitive when calling

### 3.2 ALL Available Macro Commands

#### 3.2.1 Core Commands

**`do <console_command>`**
```
do move prontera 150 150
do sit
do c Hello world
do talknpc 147 171 r0 n
do storage get "Red Potion"
```
Executes any OpenKore console command. See Console Commands documentation.

**`log <text>`**
```
log This is a log message
log Variable value is $myvar
log Count is @invamount(Red Potion)
```
Prints text to console. Supports variable and function substitution.

**`pause [<seconds>]`**
```
pause 1
pause 2.5
pause @eval($.hp / 100)
```
Pauses macro AND character actions for N seconds. CRITICAL: Affects entire bot.

**`call <macro_name> [<times>] [-- <parameters>]`**
```
call myMacro
call myMacro 3
call myMacro -- "param1" "param2"
call myMacro 2 -- "test"
```
Calls another macro. If times=0 or undefined, runs once and doesn't return. If times>0, returns to calling macro after N executions.

**`stop`**
```
stop
```
Immediately terminates current macro execution.

**`release (<automacro_name> | all)`**
```
release myAutomacro
release all
```
Unlocks a run-once automacro or all automacros.

**`lock (<automacro_name> | all)`**
```
lock myAutomacro
lock all
```
Locks an automacro, disabling its checks.

**`set <option> <value>`**
```
set orphan terminate
set macro_delay 0.8
set overrideAI 1
set repeat 5
set exclusive 1
```
Sets macro execution features dynamically within a macro.

#### 3.2.2 Variable Assignment

```
$variable = value
$counter = 0
$name = "John Doe"
$result = @eval(2 + 2)
${$nested} = value
$counter++
$counter--
$var = unset
$var = undef
```

#### 3.2.3 List Operations

```
# Extract first element from comma-separated list
$list = apple, banana, orange
$first = [$list]
# $first = "apple", $list = "banana, orange"
```

### 3.3 Control Flow Structures

#### 3.3.1 IF Statement

**Simple IF:**
```
if (condition) goto label
if (condition) call macro
if (condition) stop
if (condition) {
    commands
}
```

**IF with ELSE:**
```
if (condition) {
    commands
} else {
    commands
}
```

**IF with ELSIF:**
```
if (condition1) {
    commands
} elsif (condition2) {
    commands
} elsif (condition3) {
    commands
} else {
    commands
}
```

**Postfix IF:**
```
do sit if ($.hp < 50%)
log Low HP! if ($.hp < 30%)
```

**Complex Conditions:**
```
if ($var1 == $var2 && ($var3 > 10 || $var4 < 5)) {
    # commands
}

if ((($a == 1) || ($a < 5)) && ($b != "" && $b > 0)) goto label
```

#### 3.3.2 SWITCH/CASE Statement

```
switch ($variable) {
    case (== value1) {
        commands
    }
    case (== value2) {
        commands
    }
    case (> 100) {
        commands  
    }
    else {
        commands
    }
}
```

**SWITCH with goto/call/stop:**
```
switch ($.map) {
    case (== prontera) goto prontera_handler
    case (== geffen) call geffen_macro
    case (== payon) stop
    else goto unknown_map
}
```

#### 3.3.3 WHILE Loop

```
while (condition) as <loop_name>
    commands
    [...]
end <loop_name>
```

**Examples:**
```
$i = 0
while ($i < 10) as counter
    log Count: $i
    $i++
end counter

while (@invamount(Red Potion) > 0) as usePotion
    do is @inventory(Red Potion)
    pause 0.5
end usePotion
```

#### 3.3.4 GOTO and Labels

```
:label_name
commands
[...]
goto label_name
```

**Example:**
```
macro checkStatus {
    if ($.hp < 50%) goto lowHp
    if ($.sp < 30%) goto lowSp
    goto done
    
    :lowHp
    log HP is low!
    do is @inventory(Red Potion)
    goto done
    
    :lowSp
    log SP is low!
    do is @inventory(Blue Potion)
    
    :done
    log Status check complete
}
```

### 3.4 Operators Reference

| Operator | Description | Example |
|----------|-------------|---------|
| `<` | Less than | `$.hp < 100` |
| `<=` | Less than or equal | `$.sp <= 50` |
| `==` or `=` | Equal to | `$var == 5` |
| `>` | Greater than | `$.zeny > 1000` |
| `>=` | Greater than or equal | `$.lvl >= 99` |
| `!=` | Not equal to | `$name != "Bob"` |
| `~` | Element of (comma-separated list) | `$item ~ $list` |
| `=~` | Matches regex | `$msg =~ /hello/i` |
| `..` | Between (range) | `$.lvl ~ 50..60` |
| `&&` | AND (logical) | `$a > 5 && $b < 10` |
| `||` | OR (logical) | `$a == 1 || $b == 2` |

### 3.5 Advanced Syntax Features

#### 3.5.1 Command Chaining

```
[
    do move prontera 150 150
    do sit
    log Sitting in prontera
]
```
Commands in `[]` execute immediately with no delay between them.

#### 3.5.2 Sub-lines (Semicolon Separator)

```
$i = 1; pause 5; log Value is $i; $i++; $ii = 2
```
Commands separated by `;` execute with no macro_delay between them (except `pause` and `log`).

#### 3.5.3 Perl Subroutines Integration

```
macro testSub {
    if (customFunction("test", 123)) goto success
    :success
    log Function returned true
}

sub customFunction {
    my ($arg1, $arg2) = @_;
    # Perl code here
    return 1; # or 0
}
```

**Accessing Macro Variables from Perl:**
```perl
$::Macro::Data::varStack{variablename}
```

**Example from Working Macros:**
```perl
sub armorEnchantList {
    my ($armor_type, $args) = @_;
    my @armorList = (
        {name => "Silk Robe", type => 0, seq => "r0 r4 r1 n"},
        {name => "Saint's Robe", type => 0, seq => "r0 r5 r1 n"},
    );
    foreach my $armor (@armorList) {
        if ($armor->{name} eq $armor_type) {
            return $armor->{$args};
        }
    }
}
```

---

## 4. Variable System

### 4.1 Variable Types and Scoping

**Macro Variables (`$variable`):**
- GLOBAL scope - persist across all macros
- No declaration needed
- Case-sensitive names
- Can contain letters and numbers only

**Special Variables (`$.variable`):**
- READ-ONLY - auto-updated by OpenKore
- Provide character/game state information
- Cannot be assigned

**Nested Variables (`${$variable}`):**
- Dynamic variable names
- Example: `$name = "hp"; ${$name} = 100` creates `$hp = 100`

### 4.2 Special Variables Reference

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `$.map` | Current map | "prontera" |
| `$.pos` | Current position | "150 150" |
| `$.time` | Unix timestamp | "1706119234" |
| `$.datetime` | Date and time | "Thu Feb 06 22:37:15 2026" |
| `$.hour` | Current hour (24h) | "22" |
| `$.minute` | Current minute | "37" |
| `$.second` | Current second | "15" |
| `$.hp` | Current HP | "1234" |
| `$.sp` | Current SP | "567" |
| `$.lvl` | Base level | "99" |
| `$.joblvl` | Job level | "50" |
| `$.spirits` | Spirit spheres | "5" |
| `$.zeny` | Current zeny | "50000" |
| `$.status` | Status list | "Blessing, Agi Up" |
| `$.param1` to `$.paramN` | Macro parameters | from `-- param1 param2` |
| `$.caller` | Last triggered automacro | "myAutomacro" |
| `$.weight` | Current weight | "1500" |
| `$.maxweight` | Maximum weight | "3000" |

**Extracting Position Coordinates:**
```
$x = @arg("$.pos", 1)
$y = @arg("$.pos", 2)
```

### 4.3 Condition-Set Variables

These are set automatically when certain conditions trigger:

**Console Condition:**
- `$.lastLogMsg` - Console text that triggered
- `$.lastMatchN` - Regex backreferences (N = 1, 2, 3...)

**PM Condition:**
- `$.lastpm` - Player name who PMed
- `$.lastpmMsg` - PM message

**Public Chat Condition:**
- `$.lastpub` - Player name
- `$.lastpubMsg` - Message

**Party Chat Condition:**
- `$.lastparty` - Player name
- `$.lastpartyMsg` - Message

**Guild Chat Condition:**
- `$.lastguild` - Player name
- `$.lastguildMsg` - Message

**System Chat Condition:**
- `$.lastsysMsg` - System message

**Monster Condition:**
- `$.lastMonster` - Monster name
- `$.lastMonsterPos` - Position "x y mapname"
- `$.lastMonsterDist` - Distance from character
- `$.lastMonsterID` - Monster index
- `$.lastMonsterBinID` - Monster binary ID
- `$.lastMonsterCount` - Count of monsters matching condition

**Player Condition:**
- `$.lastPlayerName` - Player name
- `$.lastPlayerPos` - Position "x y mapname"
- `$.lastPlayerLevel` - Base level
- `$.lastPlayerJob` - Job name
- `$.lastPlayerAccountId` - Account ID
- `$.lastPlayerBinId` - Binary ID

**Spell Condition:**
- `$.caster` - Caster actor
- `$.casterName` - Caster name
- `$.casterID` - Caster ID
- `$.casterPos` - Caster position "x y"
- `$.casterSkill` - Skill name
- `$.casterTarget` - Target location
- `$.casterTargetName` - Target party member name
- `$.casterDist` - Distance from character

**AreaSpell Condition:**
- `$.areaName` - Spell name
- `$.areaActor` - Source actor type
- `$.areaSourceName` - Actor name
- `$.areaSourceID` - Actor binary ID
- `$.areaPos` - Center position "x y mapname"
- `$.areaDist` - Distance from character

**Hook Condition:**
- `$.hooksave0`, `$.hooksave1`, ... - Saved hook values (0-indexed)

**ConfigKey Condition:**
- `$.ConfigKeyLastKey` - Config key that triggered
- `$.ConfigKeyLastValue` - Config value
- `$.ConfigKeyLastMemberIndex` - Member index

**PlayerGuild Condition:**
- `$.lastPlayerID` - Player account ID
- `$.lastGuildName` - Guild name
- `$.lastGuildNameBinID` - Player binary ID
- `$.lastGuildNameBinIDDist` - Distance
- `$.lastGuildNameBinIDName` - Player name
- `$.lastGuildNameBinIDJobName` - Job name

### 4.4 Variable Manipulation

```
# Assignment
$var = value
$var = "string value"
$var = 123

# Increment/Decrement
$counter++
$counter--

# Unset/Delete
$var = unset
$var = undef

# Nested/Dynamic
$name = "count"
${$name} = 5  # Creates $count = 5

# List extraction
$list = a, b, c
$first = [$list]  # $first="a", $list="b, c"
```

---

## 5. Condition Modules Reference

### 5.1 Complete List of Available Conditions

Based on source code analysis from `plugins/eventMacro/eventMacro/Condition/`:

#### EVENT CONDITIONS (One per automacro)

**AttackEnd**
```
AttackEnd
```
Triggers when attack sequence ends.

**AttackStart**
```
AttackStart
```
Triggers when attack sequence starts.

**AttackStartRegex**
```
AttackStartRegex /pattern/
```
Triggers when attack starts on monster matching regex pattern.

**BusMsg**
```
BusMsg "message text"
BusMsg /regex pattern/i
```
Triggers on bus message (internal message system).

**ChatRoomNear**
```
ChatRoomNear "title"
ChatRoomNear /pattern/i
```
Triggers when chat room with matching title appears nearby.

**Console**
```
Console "exact text"
Console /regex pattern/i
```
Triggers when console output matches text or regex.  
**WARNING:** Console matching is fragile. Match start/end of string. Avoid `.*` patterns.

**GuildMsg**
```
GuildMsg "message"
GuildMsg /pattern/i
```
Triggers on guild chat message.

**GuildMsgDist**
```
GuildMsgDist "message" <distance>
```
Triggers on guild message from player within distance.

**GuildMsgName**
```
GuildMsgName "player name" "message"
```
Triggers on guild message from specific player.

**GuildMsgNameDist**
```
GuildMsgNameDist "player name" <distance> "message"
```
Combined name and distance check.

**LocalMsg**
```
LocalMsg "message"
LocalMsg /pattern/i
```
Triggers on local chat message (non-public).

**MapLoaded**
```
MapLoaded
```
Triggers when map is fully loaded.

**NpcMsg**
```
NpcMsg "message"
NpcMsg /pattern/i
```
Triggers on NPC dialog message.

**NpcMsgDist / NpcMsgName / NpcMsgNameDist** - Similar patterns to GuildMsg variants

**OnCharLogIn**
```
OnCharLogIn
```
Triggers when character logs into game.

**PartyMsg / PartyMsgDist / PartyMsgName / PartyMsgNameDist** - Party chat variants

**PrivMsg / PrivMsgDist / PrivMsgName / PrivMsgNameDist** - Private message (PM) variants

**PubMsg / PubMsgDist / PubMsgName / PubMsgNameDist** - Public chat variants

**SimpleHookEvent**
```
SimpleHookEvent <hook_name>
```
Triggers on any OpenKore hook event.

**SystemMsg**
```
SystemMsg "message"
SystemMsg /pattern/i
```
Triggers on system message.

#### STATE CONDITIONS (Multiple allowed)

**BaseLevel**
```
BaseLevel > 50
BaseLevel == 99
BaseLevel >= 90, <= 99
```
Checks character base level.

**CartCurrentSize**
```
CartCurrentSize > 50
```
Number of different items in cart.

**CartCurrentWeight**
```
CartCurrentWeight > 1000
CartCurrentWeight > 50%
```
Cart weight (absolute or percentage).

**CartMaxSize / CartMaxWeight** - Similar patterns for maximum values

**CharCurrentWeight / CharMaxWeight** - Character weight variants

**ConfigKey**
```
ConfigKey lockMap prontera
ConfigKey attackAuto 2
ConfigKey $varKey $varValue
```
Checks config.txt key-value pairs. Supports variables.

**ConfigKeyDefined / ConfigKeyNotExist / ConfigKeyUndefined** - Config existence checks

**ConfigKeyDualDifferentDefinedValue / ConfigKeyDualSameDefinedValue** - Advanced config checks

**ConfigKeyNot**
```
ConfigKeyNot lockMap geffen
```
Config key does NOT match value.

**CurrentHP**
```
CurrentHP > 1000
CurrentHP > 50%
CurrentHP < 30%
```
Current HP (absolute or percentage).

**CurrentSP** - Similar to CurrentHP for SP

**Eval**
```
Eval $varA > $varB
Eval @eval($.hp + $.sp) > 2000
```
Evaluates perl expression as condition.

**EvalHook**
```
EvalHook <hook_name> <perl_expression>
```
Evaluates expression when specific hook fires.

**FreeSkillPoints**
```
FreeSkillPoints > 0
```
Number of unallocated skill points.

**FreeStatPoints** - Similar for stat points

**InCart**
```
InCart "Item Name" > 0
InCart "Item Name" >= 5, <= 10
```
Item amount in cart.

**InCartID**
```
InCartID 501 > 0
```
Item by ID in cart.

**InChatRoom**
```
InChatRoom 1
InChatRoom 0
```
Whether character is in chat room (1=yes, 0=no).

**InCity**
```
InCity 1
InCity 0
```
Whether current map is a city.

**InInventory**
```
InInventory "Red Potion" > 5
InInventory "Red Potion" >= 3, "Orange Potion" >= 2
```
Item amount in inventory. **CASE SENSITIVE!**

**InInventoryID**
```
InInventoryID 501 > 0
```
Item by ID in inventory.

**InLockMap**
```
InLockMap 1
InLockMap 0
```
Whether on lockMap.

**InMap**
```
InMap prontera
InMap geffen, prontera, payon
```
Current map check (comma-separated = OR).

**InMapRegex**
```
InMapRegex /^prt_/
```
Map name matches regex.

**InProgressBar**
```
InProgressBar 1
InProgressBar 0
```
Whether progress bar is active.

**InPvP**
```
InPvP 1
InPvP 0
```
Whether in PvP map.

**InSaveMap**
```
InSaveMap 1
InSaveMap 0
```
Whether on save map.

**InStorage**
```
InStorage "Item Name" > 0
```
Item amount in storage.

**InStorageID** - Storage by item ID

**InventoryCurrentSize** - Number of different items

**InventoryReady**
```
InventoryReady 1
```
Whether inventory data is loaded.

**IsEquippedID**
```
IsEquippedID 501
```
Whether specific item ID is equipped.

**IsInCoordinate**
```
IsInCoordinate 150 150
IsInCoordinate 145-155 145-155
```
Position check (exact or range).

**IsInMapAndCoordinate**
```
IsInMapAndCoordinate prontera 150 150
```
Combined map and position check.

**IsNotEquippedID / IsNotInCoordinate / IsNotInMapAndCoordinate** - Negated versions

**JobID**
```
JobID 4011
```
Check by job ID number.

**JobIDNot** - Negated job ID check

**JobLevel**
```
JobLevel > 50
JobLevel == 70
```
Job level check.

**MaxHP / MaxSP** - Maximum HP/SP values

**MobNear**
```
MobNear "Poring" > 0
MobNear "Poring", "Drops" >= 2
```
Monster(s) nearby. **CASE SENSITIVE!**

**MobNearCount**
```
MobNearCount > 5
```
Total nearby monster count.

**MobNearDist**
```
MobNearDist "Poring" < 7
```
Distance to specific monster.

**MobNotNear / NoMobNear** - Negated monster checks

**NoNpcNear / NoPlayerNear / NoPortalNear** - Absence checks

**NotInMap**
```
NotInMap prontera
```
NOT on specific map.

**NpcNear / NpcNearCount / NpcNearDist / NpcNotNear** - NPC proximity checks

**PlayerNear**
```
PlayerNear "PlayerName"
PlayerNear /pattern/i < 10
```
Player proximity check.

**PlayerNearCount / PlayerNearDist / PlayerNotNear** - Player variants

**PortalNearCount** - Portal count check

**QuestActive / QuestComplete / QuestHuntCompleted / QuestHuntOngoing**
```
QuestActive 12345
```
Quest status checks by quest ID.

**QuestInactive / QuestIncomplete / QuestNotComplete / QuestNotIncomplete** - Quest negations

**QuestOnTime**
```
QuestOnTime 12345
```
Quest time limit not expired.

**QuestTimeOverdue** - Quest time expired

**ShopOpened**
```
ShopOpened 1
```
Whether character's shop is open.

**SkillLevel**
```
SkillLevel "Heal" > 5
SkillLevel AL_HEAL > 5
```
Skill level check.

**Spirits**
```
Spirits > 0
Spirits == 5
```
Spirit sphere count.

**StatAdded**
```
StatAdded str > 0
```
Whether stat points added this session.

**StatusActiveHandle**
```
StatusActiveHandle EFST_BLESSING
```
Status by status handle (technical name).

**StatusInactiveHandle** - Negated status check

**StorageOpened**
```
StorageOpened 1
```
Whether storage is open.

**VarValue**
```
VarValue myVar == 5
VarValue myVar > 10
```
Custom macro variable check.

**Zeny**
```
Zeny > 50000
Zeny >= 10000, <= 100000
```
Zeny amount check.

**ZenyChanged**
```
ZenyChanged > 1000
ZenyChanged < -500
```
Zeny change delta (positive = gained, negative = lost).

### 5.2 Condition Parameter Patterns

**Numeric Comparisons:**
```
> 100      # Greater than
< 50       # Less than
>= 75      # Greater or equal
<= 25      # Less or equal
== 100     # Equal
!= 0       # Not equal
> 50, < 100  # Between (both must be true)
```

**String Comparisons:**
```
"exact match"
/regex pattern/
/regex pattern/i  # Case-insensitive
```

**Comma-Separated OR Logic:**
```
InInventory "Red Potion" > 5, "Orange Potion" > 3
# Triggers if EITHER condition is true
```

**Multiple Lines AND Logic:**
```
InInventory "Red Potion" > 5
InInventory "Blue Potion" > 3
# Triggers only if BOTH are true
```

---

## 6. Functions & Keywords Reference

### 6.1 Complete Functions List

**@npc (x y | /regexp/i | "name")**
```
@npc(150 150)
@npc(/Kafra/i)
@npc("Kafra Employee")
```
Returns NPC index or -1 if not found.

**@inventory ("item")**
```
@inventory(Red Potion)
@inventory("Red Potion")
```
Returns first inventory slot index of item or -1.

**@Inventory ("item")** (Capital I)
```
@Inventory(Red Potion)
```
Returns ALL inventory slot indexes as comma-separated list or -1.

**@invamount ("item")**
```
@invamount(Red Potion)
```
Returns total amount of item in inventory.

**@cart ("item")**
```
@cart(Red Potion)
```
Returns first cart slot index or -1.

**@Cart ("item")** (Capital C)
```
@Cart(Red Potion)
```
Returns all cart slot indexes as comma-separated list or -1.

**@cartamount ("item")**
```
@cartamount(Red Potion)
```
Returns total amount in cart.

**@storage ("item")**
```
@storage(Red Potion)
```
Returns first storage slot index or -1.

**@Storage ("item")** (Capital S)
```
@Storage(Red Potion)
```
Returns all storage slot indexes or -1.

**@storamount ("item")**
```
@storamount(Red Potion)
```
Returns total amount in storage.

**@player ("name")**
```
@player(PlayerName)
```
Returns player index or -1.

**@monster ("name|ID")**
```
@monster(Poring)
@monster(1002)
```
Returns monster index or -1.

**@vender ("name")**
```
@vender(VendorName)
```
Returns vender index or -1.

**@store ("item")**
```
@store(Red Potion)
```
Returns item index in open shop or -1.

**@shopamount ("item")**
```
@shopamount(Red Potion)
```
Returns amount in character's shop.

**@random ("arg1", "arg2", ...)**
```
@random("north", "south", "east", "west")
```
Returns one argument randomly.

**@rand (min, max)**
```
@rand(1, 100)
@rand(-10, 10)
```
Returns random integer between min and max (inclusive).

**@eval (expression)**
```
@eval(2 + 2)
@eval($.hp / $.maxhp * 100)
@eval($a + $b)
@eval(int($.weight / 10))
```
Evaluates Perl expression. **Contents are Perl, not macro syntax!**

**@arg ("string", index)**
```
@arg("word1 word2 word3", 1)  # Returns "word1"
@arg("word1 word2 word3", 2)  # Returns "word2"
@arg("$.pos", 1)  # Extract X coordinate
@arg("$.pos", 2)  # Extract Y coordinate
```
Returns Nth word from space-separated string (1-indexed).

**@config (key)**
```
@config(lockMap)
@config(attackAuto)
@config(sitAuto_hp_lower)
```
Returns value from config.txt.

**@venderitem ("item")**
```
@venderitem(Red Potion)
```
Returns item index in player vending shop or -1.

**@venderprice (indexID)**
```
@venderprice(0)
```
Returns price of item at index in vending shop.

**@nick (word)**
```
@nick($playerName)
```
Escapes regex metacharacters for safe use in patterns.

### 6.2 Function Usage Patterns

**Nested Functions:**
```
$maxCanCarry = @eval((0.9 * $.maxweight) - $.weight)
$buyAmount = @eval(int(($maxCanCarry/0.2)/500) * 500)
$result = @eval(@eval($i - 1) - @eval($i - 0))
```

**Functions in Conditions:**
```
if (@invamount(Red Potion) > 0) goto usePotion
while (@storamount($item) > 0) as loop
if (@inventory($item) != -1) call processItem
```

**Functions with Variables:**
```
$item = "Red Potion"
$amount = @invamount($item)
$index = @inventory("$item")
do is @inventory($item)
```

**Dynamic Index Access with @arg:**
```
$itemIndex = @Inventory($item)
$i = 1
while (@invamount($item) > 0) as loop
    do sell @arg("$itemIndex", $i)
    $i++
end loop
```

---

## 7. Working Patterns from Examples

### 7.1 Storage Interaction Pattern

```
# Save original storage config
do conf tempStorage_npc @config(storageAuto_npc)
do conf tempStorage_standpoint @config(storageAuto_standpoint)
do conf tempStorage_type @config(storageAuto_type)
do conf tempStorage_npc_type @config(storageAuto_npc_type)
do conf tempStorage_npc_steps @config(storageAuto_npc_steps)

# Set new storage config
do conf storageAuto_npc prontera 146 89
do conf storageAuto_standpoint prontera 146 89
do conf storageAuto_npc_type 1
do conf storageAuto_npc_steps c r1 n
do conf storageAuto_type 0
pause 1

# Use storage
do move prontera @eval(146 + @rand(-5,5)) @eval(89 + @rand(-5,5))
do talknpc 146 89 c r1 n
pause 1
if (@storage($item) > 0) {
    do storage get $item
}
do storage close

# Restore original config
do conf storageAuto_npc @config(tempStorage_npc)
do conf storageAuto_standpoint @config(tempStorage_standpoint)
do conf storageAuto_type @config(tempStorage_type)
do conf storageAuto_npc_type @config(tempStorage_npc_type)
do conf storageAuto_npc_steps @config(tempStorage_npc_steps)
```

### 7.2 NPC Dialog Handling Pattern

```
# Simple NPC interaction
do move prontera 150 150
do talknpc 147 171 r0 n

# Complex sequence with pauses
do move payon_in01 5 134
do talknpc 5 134 c r0 c r0 c r0 n
pause 2

# With variable sequence
$npcSequence = c r1 c r0 n
do talknpc 123 234 $npcSequence
```

### 7.3 Weight Management Pattern

```
# Calculate carrying capacity
$maxCanCarry = @eval((0.9 * $.maxweight) - $.weight)
$buyAmount = @eval(int(($maxCanCarry/0.2)/500) * 500)

# Check weight before action
if ($.weight >= @eval(0.9 * $.maxweight)) {
    do autostorage
}

# Loop with weight check
while ((@storamount($item) > 0) && ($.weight < @eval(0.9*$.maxweight))) as loop
    do storage get $item
end loop
```

### 7.4 Inventory Loop Pattern

```
# Sell all items of type
$itemCount = @invamount($itemToSell)
$itemIndex = @Inventory($itemToSell)
$i = 1
set macro_delay 0.7
while ((@invamount($itemToSell) > 0) && ($i <= $itemCount)) as loop
    do sell @arg("$itemIndex", $i)
    $i++
end loop
do sell done
```

### 7.5 Recursive Macro Pattern

```
macro processItems {
    if (@storage($item) > 0) {
        do storage get $item
        # Process item
        call processItems  # Recursive call
    }
    stop
}
```

### 7.6 Error Recovery Pattern

```
if (@inventory($requiredItem) == -1) goto errorNoItem
if ($.zeny < $requiredZeny) goto errorNoZeny

# Normal execution
# ...
stop

:errorNoItem
log Missing required item: $requiredItem
stop

:errorNoZeny
log Not enough zeny. Need $requiredZeny
stop
```

### 7.7 Conditional Config Change Pattern

```
$originalValue = @config(someConfig)
if ($originalValue != "desiredValue") {
    log Changing config temporarily
    do conf someConfig desiredValue
    # Do work
    do conf someConfig $originalValue
}
```

### 7.8 Perl Subroutine for Data Lookup

```
macro useEquipData {
    $equipName = $.param1
    $sequence = equipList("$equipName", "sequence")
    $zenyReq = equipList("$equipName", "zenyReq")
    
    if ($.zeny < $zenyReq) goto noZeny
    do talknpc 123 234 $sequence
    stop
    
    :noZeny
    log Need $zenyReq zeny
}

sub equipList {
    my ($equipment, $args) = @_;
    my @equipmentList = (
        {name => "Item1", sequence => "r0 n", zenyReq => 100000},
        {name => "Item2", sequence => "r1 n", zenyReq => 200000},
    );
    
    foreach my $item (@equipmentList) {
        if ($item->{name} eq $equipment) {
            return $item->{$args};
        }
    }
    return "";
}
```

### 7.9 Safe Loop with Timeout

```
$loopCount = 0
$maxLoops = 100
while ($condition && $loopCount < $maxLoops) as safeLoop
    # Do work
    $loopCount++
    pause 0.1
end safeLoop

if ($loopCount >= $maxLoops) {
    log WARNING: Loop hit maximum iterations
}
```

### 7.10 Dynamic Position Randomization

```
# Random position near target
$baseX = 150
$baseY = 150
do move prontera @eval($baseX + @rand(-5,5)) @eval($baseY + @rand(-5,5))
```

---

## 8. Integration & Compatibility

### 8.1 OpenKore Core Integration

**Plugin Loading:**
- Plugins load after core initialization
- Located in `plugins/` directory
- eventMacro: `plugins/eventMacro/`
- macro: `plugins/macro/`

**Hook System:**
- eventMacro registers hooks for game events
- Available hooks: See `Network::PacketParser`, `AI`, `Commands`
- Custom plugins can fire hooks that eventMacro catches

**AI Queue Integration:**
- Macros register as "macro" AI entry
- `overrideAI` pushes macro to front of queue
- Normal operation: macro waits for AI to be idle
- Can check AI state: `do ai clear`, `do ai manual`, `do ai on`

### 8.2 Configuration File Relationships

**config.txt:**
- Read by `@config()` function
- Modified by `do conf key value` command
- eventMacro conditions can check config values
- Temporary config changes common in macros

**macros.txt / eventMacros.txt:**
- Default macro file: `control/macros.txt`
- Configurable: `macro_file` in config.txt
- Syntax: UTF-8 encoding required
- Comments: `#` at line start or after space

**timeouts.txt:**
- `macro_delay` - delay between macro commands (default: 1.0s)
- Can override per-macro with `set macro_delay` or `macro_delay` parameter

**mon_control.txt / items_control.txt:**
- Can be dynamically modified by macros
- Requires `do reload mon_control` to take effect
- Example: Changing attack settings mid-run

### 8.3 Plugin Dependencies

**eventMacro Requirements:**
- OpenKore core modules
- Condition modules auto-load from `Condition/` directory
- No external CPAN dependencies

**macro Plugin Requirements:**
- Base eventMacro for condition evaluation (if using automacros)
- Can work standalone for simple macros

**Load Order:**
- Core → Plugins → Config → Character Select
- Plugin order doesn't matter (hooks register dynamically)

### 8.4 Compatibility Notes

**Version Compatibility:**
- eventMacro: Part of modern OpenKore (Git version)
- macro plugin: Works with OpenKore 2.0.7+
- Check wiki for version-specific features

**Server Compatibility:**
- Packet-based conditions depend on server support
- Some conditions unavailable on older servers
- Test thoroughly on target server

---

## 9. Debugging & Troubleshooting

### 9.1 Common Errors and Resolutions

**Error: "Malformed UTF-8 character"**
- **Cause:** macros.txt not in UTF-8 encoding
- **Fix:** Save macros.txt as UTF-8 (without BOM in Notepad++)

**Error: "not an automacro variable"**
- **Cause:** Using special variable in automacro condition instead of macro
- **Fix:** Move logic using `$.variable` into macro called by automacro

**Error: "Unknown command"**
- **Cause:** Using macro-only command (log, pause) as console command
- **Fix:** Use within macro, or prefix with `do` if needed

**Error: Module not found / Condition not recognized**
- **Cause:** Condition name misspelled or not loaded
- **Fix:** Check spelling, verify module exists in `Condition/` directory

**Error: Macro hangs / doesn't complete**
- **Cause:** Missing pause between commands, especially NPC interactions
- **Fix:** Add appropriate `pause` delays

**Error: Disconnected from map server**
- **Cause:** Commands sent too fast
- **Fix:** Increase `macro_delay` or add `pause` between commands

**Error: Items not found but exist in inventory**
- **Cause:** Item name case mismatch
- **Fix:** Check exact item name case (use `/ii` in console)

**Error: Automacro triggers when it shouldn't**
- **Cause:** Missing timeout or wrong condition logic
- **Fix:** Add `timeout N` and review condition combination

**Error: Variable not updating**
- **Cause:** Using `$.variable` (read-only) or scope issue
- **Fix:** Use `$variable` for mutable variables

### 9.2 Case Sensitivity Pitfalls

**Critical Case-Sensitive Elements:**
- Item names: "Red Potion" ≠ "red potion"
- Monster names: "Poring" ≠ "poring"
- Map names: Usually case-insensitive but best to match
- Player/Guild names: Case-sensitive
- Config keys: Case-sensitive
- Status names: Case-sensitive (check statusnametable.txt)
- Macro names: Case-sensitive
- Variable names: Case-sensitive

**Debugging Case Issues:**
```
# Check exact item name
do ii
# Shows: Red Potion (slot 0)

# Wrong:
InInventory "red potion" > 0

# Correct:
InInventory "Red Potion" > 0
```

### 9.3 Module Loading Issues

**Verify Module Exists:**
```
List files in: openkore-ai/plugins/eventMacro/eventMacro/Condition/
```

**Check Module Name:**
- Condition name in eventMacros.txt must match .pm filename
- Example: `BaseLevel` condition → `BaseLevel.pm` file

**Common Misspellings:**
- `InInventory` not `Ininventory` or `ininventory`
- `ConfigKey` not `configKey`
- `MobNear` not `MonsterNear`

### 9.4 Syntax Validation Techniques

**Test Incrementally:**
1. Start with simple macro
2. Add one feature at a time
3. Test after each addition
4. Use `log` statements to trace execution

**Validate Conditions:**
```
automacro testCondition {
    YourCondition parameters
    call {
        log Condition triggered!
    }
    timeout 5
}
```

**Debug Variables:**
```
log Variable value: $myvar
log Special variable: $.hp
log Function result: @invamount(Red Potion)
```

**Check Console Output:**
```
# Enable debug if needed
macro_allowDebug 1

# Watch for macro status
macro status

# View variable stack
macro varstack

# List automacros
automacro list
```

**Validate Regex Patterns:**
```
# Test regex in console
# Perl regex: /pattern/modifiers

# Common mistakes:
/pattern/  # Case-sensitive
/pattern/i # Case-insensitive
/^start/   # Anchored to beginning
/end$/     # Anchored to end
```

### 9.5 Performance Considerations

**Macro Delay Tuning:**
- Too low: Risk disconnection
- Too high: Slow execution
- Recommended: 0.5 - 1.0 seconds
- Adjust per server lag

**Heavy Loops:**
- Add `pause` in loops to prevent blocking
- Use conditions to break infinite loops
- Limit iteration count for safety

**Storage Operations:**
- Expensive: Opening/closing storage repeatedly
- Better: Batch operations in single storage session
- Cache storage state if possible

**Condition Evaluation:**
- State conditions checked continuously
- Complex conditions may impact performance
- Event conditions only check on event

### 9.6 Testing Strategies

**Unit Testing Approach:**
```
# Test one macro at a time
macro testFeature {
    log Starting test
    # Test code here
    log Test complete
}
```

**Integration Testing:**
```
# Test automacro trigger
automacro testTrigger {
    InInventory "Red Potion" > 0
    timeout 5
    call {
        log Automacro triggered
    }
}
```

**Edge Case Testing:**
- Empty inventory
- Full weight
- No zeny
- Missing items
- Map changes during execution
- Disconnection recovery

**Logging for Debug:**
```
log ===== Starting Macro =====
log Item count: @invamount($item)
log Weight: $.weight / $.maxweight
log Zeny: $.zeny
# ... operations ...
log ===== Macro Complete =====
```

---

## Appendix A: Quick Reference Card

### Automacro Template
```
automacro name {
    # Conditions (AND logic between lines)
    condition1 param
    condition2 param
    
    # Parameters
    timeout 10
    exclusive 1
    priority 0
    
    # Action
    call macroName
}
```

### Macro Template
```
macro name {
    # Variables
    $var = value
    
    # Commands
    do console_command
    log message
    pause seconds
    
    # Control flow
    if (condition) {
        commands
    }
    
    # Loop
    while (condition) as loopName
        commands
    end loopName
    
    stop
}
```

### Essential Functions
```
@inventory(item)      # Item index or -1
@invamount(item)      # Item count
@storage(item)        # Storage index
@storamount(item)     # Storage count
@eval(expression)     # Calculate
@rand(min, max)       # Random number
@config(key)          # Config value
@arg(string, N)       # Extract word
```

### Essential Special Variables
```
$.map          # Current map
$.pos          # Position "x y"
$.hp / $.sp    # Current HP/SP
$.lvl          # Base level
$.zeny         # Zeny amount
$.weight       # Current weight
$.maxweight    # Max weight
$.caller       # Last automacro
```

---

## Appendix B: Complete Condition Module List

```
AttackEnd.pm
AttackStart.pm
AttackStartRegex.pm
BaseLevel.pm
BusMsg.pm
CartCurrentSize.pm
CartCurrentWeight.pm
CartMaxSize.pm
CartMaxWeight.pm
CharCurrentWeight.pm
CharMaxWeight.pm
ChatRoomNear.pm
ConfigKey.pm
ConfigKeyDefined.pm
ConfigKeyDualDifferentDefinedValue.pm
ConfigKeyDualSameDefinedValue.pm
ConfigKeyNot.pm
ConfigKeyNotExist.pm
ConfigKeyUndefined.pm
Console.pm
CurrentHP.pm
CurrentSP.pm
Eval.pm
EvalHook.pm
FreeSkillPoints.pm
FreeStatPoints.pm
GuildMsg.pm
GuildMsgDist.pm
GuildMsgName.pm
GuildMsgNameDist.pm
InCart.pm
InCartID.pm
InChatRoom.pm
InCity.pm
InInventory.pm
InInventoryID.pm
InLockMap.pm
InMap.pm
InMapRegex.pm
InProgressBar.pm
InPvP.pm
InSaveMap.pm
InStorage.pm
InStorageID.pm
InventoryCurrentSize.pm
InventoryReady.pm
IsEquippedID.pm
IsInCoordinate.pm
IsInMapAndCoordinate.pm
IsNotEquippedID.pm
IsNotInCoordinate.pm
IsNotInMapAndCoordinate.pm
JobID.pm
JobIDNot.pm
JobLevel.pm
LocalMsg.pm
MapLoaded.pm
MaxHP.pm
MaxSP.pm
MobNear.pm
MobNearCount.pm
MobNearDist.pm
MobNotNear.pm
NoMobNear.pm
NoNpcNear.pm
NoPlayerNear.pm
NoPortalNear.pm
NotInMap.pm
NpcMsg.pm
NpcMsgDist.pm
NpcMsgName.pm
NpcMsgNameDist.pm
NpcNear.pm
NpcNearCount.pm
NpcNearDist.pm
NpcNotNear.pm
OnCharLogIn.pm
PartyMsg.pm
PartyMsgDist.pm
PartyMsgName.pm
PartyMsgNameDist.pm
PlayerNear.pm
PlayerNearCount.pm
PlayerNearDist.pm
PlayerNotNear.pm
PortalNearCount.pm
PrivMsg.pm
PrivMsgDist.pm
PrivMsgName.pm
PrivMsgNameDist.pm
PubMsg.pm
PubMsgDist.pm
PubMsgName.pm
PubMsgNameDist.pm
QuestActive.pm
QuestComplete.pm
QuestHuntCompleted.pm
QuestHuntOngoing.pm
QuestInactive.pm
QuestIncomplete.pm
QuestNotComplete.pm
QuestNotIncomplete.pm
QuestOnTime.pm
QuestTimeOverdue.pm
ShopOpened.pm
SimpleHookEvent.pm
SkillLevel.pm
Spirits.pm
StatAdded.pm
StatusActiveHandle.pm
StatusInactiveHandle.pm
StorageOpened.pm
SystemMsg.pm
VarValue.pm
Zeny.pm
ZenyChanged.pm
```

---

## Appendix C: Console Commands Available in Macros

All console commands from OpenKore can be used with `do` prefix:

```
do move <map> <x> <y>
do sit
do stand
do c <message>
do talknpc <x> <y> [<sequence>]
do take <item>
do storage get <item> [<amount>]
do storage add <item> [<amount>]
do storage close
do cart get <item> [<amount>]
do cart add <item> [<amount>]
do sell <index>
do sell done
do buy <index> <amount>
do is <index>
do deal <player>
do deal add <item>
do deal
do tele
do relog [<seconds>]
do reload <config>
do ai clear
do ai manual
do ai on
do sl <skillID> <x> <y>
do ss <skillID> [<target>]
do sp <skillID> [<target>]
do warp <memo_index>
do refineui select <index>
do refineui refine <index> <material_id>
do refineui cancel
do rodex open
do rodex write <player>
do rodex settitle <title>
do rodex setbody <body>
do rodex settarget <player>
do rodex add <index> [<amount>]
do rodex draft
do rodex send
do rodex close
```

---

## Appendix D: OpenKore Integration Points

**Events that trigger conditions:**
```
packet_pre/<packet_name>
packet/<packet_name>
packet/map_changed
packet/stat_info
packet/hp_sp_changed
Network::Receive::map_changed
in_game
configModify
pos_load_config.txt
add_monster_list
monster_disappeared
mobNameUpdate
add_player_list
player_disappeared
charNameUpdate
```

**AI Queue Integration:**
```
AI::queue("macro")    # Add macro to AI
AI::dequeue()         # Remove from AI
AI::clear("macro")    # Clear macro entries
AI::is("macro")       # Check if macro is first
AI::action()          # Get current AI action
```

---

## Document Conclusion

This reference document synthesizes information from:
- OpenKore Wiki eventMacro page
- OpenKore Wiki macro_plugin page  
- 8 working example macro files
- 100+ Condition module source files
- Plugin architecture analysis

**Critical Reminders for Code Generation:**

1. **CASE SENSITIVITY:** Item names, monster names, player names are case-sensitive
2. **PAUSES:** Always add appropriate pauses between commands, especially NPC interactions
3. **TIMEOUTS:** Every automacro should have a timeout to prevent spam
4. **WEIGHT CHECKS:** Always check weight before storage operations
5. **ERROR HANDLING:** Use goto labels or conditionals for error cases
6. **VARIABLE SCOPE:** All $variables are global
7. **SPECIAL VARIABLES:** $.variables are read-only
8. **CONDITION LOGIC:** Multiple lines = AND, comma-separated = OR
9. **PERL EXPRESSIONS:** @eval() uses Perl syntax, not macro syntax
10. **UTF-8 ENCODING:** Save all macro files in UTF-8

**For CrewAI Agents:** This document is your authoritative source. Every macro generated must conform to the syntax, patterns, and best practices documented herein. When in doubt, reference the working examples in Section 7.

**Version History:**
- v1.0 (2026-02-06): Initial complete reference based on comprehensive analysis

---
**END OF DOCUMENT**
