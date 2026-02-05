# Configuration Templates

This directory contains YAML configuration templates for the OpenKore Advanced AI system.

## Files

### [`ai-engine.yaml`](ai-engine.yaml)
Configuration for the C++ AI Engine (HTTP REST server on port 9901):
- Server settings (host, port, connections)
- Python service connection URL
- Decision system tiers and thresholds
- Logging configuration

### [`ai-service.yaml`](ai-service.yaml)
Configuration for the Python AI Service (HTTP REST server on port 9902):
- Server settings
- Database path and settings
- LLM provider chain (DeepSeek → OpenAI → Anthropic)
- OpenMemory SDK configuration
- CrewAI agent settings
- Logging configuration

### [`plugin.yaml`](plugin.yaml)
Configuration for the OpenKore Perl plugin (GodTierAI):
- AI Engine connection URL
- Personality parameters (chattiness, friendliness, etc.)
- Social interaction settings
- Reputation tier thresholds

## Usage

1. Copy the template files to your OpenKore `control/` directory
2. Rename them if needed (e.g., `ai-engine.yaml` → `godtier-ai-engine.yaml`)
3. Edit the values to match your setup
4. Set environment variables for API keys:
   - `DEEPSEEK_API_KEY` (optional, priority 1)
   - `OPENAI_API_KEY` (optional, priority 2)
   - `ANTHROPIC_API_KEY` (optional, priority 3)

## Environment Variables

Create a `.env` file in your project root:

```bash
# LLM Provider API Keys (optional, at least one required for LLM features)
DEEPSEEK_API_KEY=your_deepseek_key_here
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

The system will fallback through the provider chain if one fails.
