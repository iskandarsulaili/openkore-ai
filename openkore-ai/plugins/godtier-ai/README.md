# GodTierAI Plugin for OpenKore

OpenKore Perl plugin that bridges the game client with the Advanced AI system (C++ Engine + Python Service).

## Architecture

- **Language**: Perl 5.x
- **Protocol**: HTTP REST (via LWP::UserAgent)
- **Target**: C++ AI Engine on port 9901
- **Hot-Reload**: Generates macros dynamically

## Features

- **HTTP Bridge**: Sends game state to AI Engine, receives optimal actions
- **Macro Generation**: Writes AI decisions as hot-reloadable macros
- **Personality System**: Configurable behavior traits (chattiness, caution, etc.)
- **Social AI**: Autonomous chat, party, guild interactions
- **Reputation Tracking**: Maintains player relationships and trust levels
- **Minimal Latency**: Non-blocking HTTP requests with timeout handling

## Prerequisites

### Perl Modules

The following Perl modules must be installed:

**Windows (Strawberry Perl):**
```cmd
cpan install LWP::UserAgent
cpan install HTTP::Request
cpan install JSON::XS
cpan install YAML::XS
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt install libwww-perl libjson-xs-perl libyaml-libyaml-perl

# Arch Linux
sudo pacman -S perl-libwww perl-json-xs perl-yaml-libyaml

# Or via CPAN
sudo cpan LWP::UserAgent JSON::XS YAML::XS
```

**macOS:**
```bash
sudo cpan LWP::UserAgent JSON::XS YAML::XS
```

## Installation

### 1. Copy Plugin Files

Copy the entire [`godtier-ai/`](./) directory to your OpenKore `plugins/` folder:

```
openkore/
├── plugins/
│   └── godtier-ai/
│       ├── GodTierAI.pm      # Main plugin
│       ├── Bridge.pm          # HTTP client
│       ├── Config.pm          # Configuration loader
│       └── README.md          # This file
```

### 2. Configure OpenKore

Edit `control/sys.txt` to load the plugin:

```perl
# Add to sys.txt
loadPlugins 1
```

Create `control/plugins.txt` if it doesn't exist:

```perl
# Load GodTierAI plugin
godtier-ai/GodTierAI
```

### 3. Configure Plugin

Copy [`../../config/plugin.yaml`](../../config/plugin.yaml) to `control/godtier-ai.yaml`:

```yaml
ai_engine:
  url: "http://127.0.0.1:9901"
  timeout: 30

personality:
  chattiness: 0.5      # How often to chat (0.0 = silent, 1.0 = very chatty)
  friendliness: 0.7    # Response warmth (0.0 = hostile, 1.0 = very friendly)
  helpfulness: 0.6     # Willingness to assist (0.0 = selfish, 1.0 = altruistic)
  curiosity: 0.5       # Interest in exploration (0.0 = focused, 1.0 = adventurous)
  caution: 0.6         # Risk aversion (0.0 = reckless, 1.0 = very cautious)
  formality: 0.4       # Communication style (0.0 = casual, 1.0 = formal)
  humor: 0.5           # Playfulness (0.0 = serious, 1.0 = joking)
  patience: 0.7        # Tolerance for delays (0.0 = impatient, 1.0 = very patient)

social:
  auto_chat_enabled: true
  auto_buff_enabled: true
  auto_trade_enabled: false
  auto_party_enabled: true
  auto_guild_enabled: true
  
  reputation_tiers:
    blocked: -100        # Ignored completely
    suspicious: -50      # Avoid interaction
    neutral: 0           # Default for strangers
    acquaintance: 25     # Recognize player
    friendly: 50         # Trust for party/trade
    trusted: 75          # Share resources
    whitelisted: 100     # Full cooperation
```

### 4. Start Services

**Terminal 1 - C++ AI Engine:**
```bash
cd openkore-ai/ai-engine/build
./ai-engine --config ../../config/ai-engine.yaml
```

**Terminal 2 - Python AI Service:**
```bash
cd openkore-ai/ai-service
source venv/bin/activate
python src/main.py
```

**Terminal 3 - OpenKore:**
```bash
cd openkore
perl openkore.pl
```

## How It Works

### Decision Flow

```
OpenKore Game Loop
    ↓
[1] GodTierAI Plugin Collects Game State
    - Player stats (HP, SP, position)
    - Nearby monsters
    - Inventory state
    - Party/guild info
    ↓
[2] HTTP POST to AI Engine (port 9901)
    {
      "game_state": {...},
      "context": {...}
    }
    ↓
[3] AI Engine Multi-Tier Decision
    - Reflex: Emergency responses (<1ms)
    - Rules: Heuristic logic (<10ms)
    - ML: Trained models (<100ms)
    - LLM: Complex reasoning (via Python service)
    ↓
[4] Response with Optimal Action
    {
      "action": "attack",
      "target": 1002,
      "tier": "rules",
      "reasoning": "..."
    }
    ↓
[5] Plugin Generates Macro
    macros/ai_action_XXXX.txt
    ↓
[6] OpenKore Hot-Reloads and Executes Macro
```

### Macro Generation

The plugin writes AI decisions as macro files in `macros/ai_action_*.txt`:

**Example Generated Macro:**
```perl
# macros/ai_action_1234567890.txt
automacro ai_attack_1002 {
    timeout 0
    call {
        do attack 1002
    }
}
```

OpenKore automatically reloads macros and executes the action.

### Personality System

Personality traits affect decision-making:

- **Chattiness**: Frequency of social interactions
- **Friendliness**: Tone of chat responses
- **Helpfulness**: Willingness to buff/trade with strangers
- **Curiosity**: Exploration vs. efficiency
- **Caution**: Risk-taking in combat
- **Formality**: Language style (casual vs. formal)
- **Humor**: Use of jokes/emotes
- **Patience**: Tolerance for farming/grinding

### Reputation System

Players are tracked with reputation scores (-100 to 100):

- **Blocked (-100)**: Scammers, griefers → Ignored
- **Suspicious (-50)**: Suspected bots → Avoided
- **Neutral (0)**: Unknown players → Default behavior
- **Acquaintance (25)**: Met before → Remember name
- **Friendly (50)**: Positive interactions → Party/buff
- **Trusted (75)**: Reliable ally → Share drops
- **Whitelisted (100)**: Close friend → Full cooperation

Reputation changes based on:
- Helping in combat (+5 per assist)
- Receiving buffs (+3)
- Trade success (+10)
- Dying due to player's action (-20)
- Suspected botting (-50)

## Configuration Options

### AI Engine Connection

```yaml
ai_engine:
  url: "http://127.0.0.1:9901"  # Change if using different host/port
  timeout: 30                     # HTTP request timeout (seconds)
```

### Social Behavior

```yaml
social:
  auto_chat_enabled: true         # Respond to private messages
  auto_buff_enabled: true         # Buff nearby party members
  auto_trade_enabled: false       # Accept trade requests (risky!)
  auto_party_enabled: true        # Accept party invites (with reputation check)
  auto_guild_enabled: true        # Auto guild interactions
```

### Personality Tuning

**Combat-Focused Bot:**
```yaml
personality:
  chattiness: 0.1      # Rarely talk
  caution: 0.8         # Very careful
  curiosity: 0.2       # Stick to plan
```

**Social Friendly Bot:**
```yaml
personality:
  chattiness: 0.9      # Very chatty
  friendliness: 0.9    # Warm responses
  helpfulness: 0.8     # Always help
```

**Greedy Farmer:**
```yaml
personality:
  chattiness: 0.2      # Mostly silent
  helpfulness: 0.2     # Selfish
  curiosity: 0.3       # Focus on farming
```

## Troubleshooting

### Plugin Not Loading

**Check plugins.txt:**
```perl
# Should have this line:
godtier-ai/GodTierAI
```

**Check OpenKore console:**
```
[Plugins] Loading plugin godtier-ai/GodTierAI...
[GodTierAI] Initialized successfully
```

### Connection Refused

**Verify AI Engine is running:**
```bash
curl http://127.0.0.1:9901/api/v1/health
```

Should return:
```json
{"status":"healthy","uptime_seconds":123}
```

**Check firewall:**
Windows Defender may block local ports. Add exception for ports 9901 and 9902.

### Missing Perl Modules

**Error:** `Can't locate LWP/UserAgent.pm`

**Solution:**
```bash
cpan install LWP::UserAgent
```

Repeat for any missing modules.

### Macros Not Executing

**Check macro directory:**
```bash
ls -la macros/ai_action_*.txt
```

Should see generated macro files.

**Check OpenKore macro system:**
```
reload macros
macro list
```

### High Latency

**Symptoms:** Slow responses, delayed actions

**Solutions:**
1. Reduce `timeout` in `plugin.yaml` to 10-15 seconds
2. Disable LLM tier if not needed (edit `ai-engine.yaml`)
3. Run services on same machine as OpenKore
4. Check network latency to AI services

## Performance Tips

1. **Local Services**: Run AI Engine and Python Service on same machine as OpenKore
2. **Disable Unused Features**: Set `social.auto_chat_enabled: false` if not needed
3. **Reduce Chattiness**: Lower personality values to reduce LLM calls
4. **Timeout Tuning**: Lower `timeout` for faster failover
5. **Macro Cleanup**: Periodically delete old macros: `rm macros/ai_action_*.txt`

## Advanced Usage

### Custom Decision Overrides

Add manual overrides in `config.txt`:

```perl
# Force specific behavior
attackAuto 2
route_randomWalk 0
teleportAuto_idle 1
```

The AI will respect these overrides and adapt its decisions.

### Debugging

Enable verbose logging:

```yaml
logging:
  level: "debug"
  file: "../logs/godtier-ai.log"
```

Check log file for detailed decision traces.

### Multi-Character Setup

Each character can have different personality:

```
control/
├── config.txt
├── godtier-ai-priest.yaml    # Helpful, high chattiness
├── godtier-ai-knight.yaml    # Cautious, low chattiness
└── godtier-ai-merchant.yaml  # Greedy, trade-focused
```

Load different config per character in GodTierAI.pm.

## Security Considerations

⚠️ **WARNING**: This plugin sends game state to external services.

**Risks:**
- AI Engine must be trusted (runs on port 9901)
- LLM providers see game context (sanitize sensitive data)
- Macro files are world-readable (check permissions)

**Recommendations:**
1. Run AI services on localhost only (`127.0.0.1`)
2. Use firewall to block external access to ports 9901-9902
3. Do not enable `auto_trade_enabled: true` without reputation checks
4. Review generated macros before production use

## Credits

- **OpenKore**: https://github.com/OpenKore/openkore
- **cpp-httplib**: https://github.com/yhirose/cpp-httplib
- **FastAPI**: https://fastapi.tiangolo.com/
- **CrewAI**: https://www.crewai.io/

## License

This plugin follows OpenKore's GPL-2.0 license.

## Support

For issues:
1. Check AI Engine logs: `logs/ai-engine.log`
2. Check Python Service logs: `logs/ai-service.log`
3. Check OpenKore console output
4. See full documentation: `openkore-ai/plans/`
