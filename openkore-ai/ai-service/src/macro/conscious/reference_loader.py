"""
Reference Document Loader
Loads the EVENTMACRO_COMPLETE_REFERENCE.md for agent consumption
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class MacroReferenceLoader:
    """
    Utility class to load and manage the EventMacro Complete Reference document
    """
    
    _cached_reference: Optional[str] = None
    _cached_summary: Optional[str] = None
    
    @classmethod
    def load_complete_reference(cls) -> str:
        """
        Load the complete EVENTMACRO_COMPLETE_REFERENCE.md document
        
        Returns:
            Complete reference document content
        """
        if cls._cached_reference is not None:
            return cls._cached_reference
        
        try:
            # Navigate from src/macro/conscious/ to docs/
            # Path: src/macro/conscious/ -> src/macro/ -> src/ -> ai-service/ -> docs/
            ref_path = Path(__file__).parent.parent.parent.parent / "docs" / "EVENTMACRO_COMPLETE_REFERENCE.md"
            
            if not ref_path.exists():
                logger.error(f"Reference document not found at: {ref_path}")
                return cls._get_fallback_reference()
            
            with open(ref_path, 'r', encoding='utf-8') as f:
                cls._cached_reference = f.read()
            
            logger.info(f"✓ Loaded EventMacro reference document ({len(cls._cached_reference)} chars)")
            return cls._cached_reference
            
        except Exception as e:
            logger.error(f"Failed to load reference document: {e}")
            return cls._get_fallback_reference()
    
    @classmethod
    def load_reference_summary(cls) -> str:
        """
        Load a condensed summary of the reference for agent backstory
        Extracts key sections for efficient token usage
        
        Returns:
            Condensed reference summary
        """
        if cls._cached_summary is not None:
            return cls._cached_summary
        
        full_reference = cls.load_complete_reference()
        
        # Extract key sections for summary
        # This provides agents with critical syntax rules without overwhelming them
        summary_sections = [
            "# EventMacro & Macro Plugin Complete Reference",
            "",
            "## CRITICAL SYNTAX RULES:",
            "",
            "### Automacro Structure:",
            "```",
            "automacro <name> {",
            "    <condition> <value>",
            "    [exclusive 0|1]",
            "    [priority <number>]",
            "    [timeout <seconds>]",
            "    [run-once 0|1]",
            "    call <macro_name>",
            "}",
            "```",
            "",
            "### Macro Structure:",
            "```",
            "macro <name> {",
            "    <command> [parameters]",
            "    ...",
            "}",
            "```",
            "",
            "### Common Conditions:",
            "- hp < 50% | hp > 80%",
            "- sp < 30% | sp > 60%",
            "- weight > 80%",
            "- aggressives > 3",
            "- map <map_name>",
            "- monster <monster_name>",
            "- status <status_name>",
            "",
            "### Common Commands:",
            "- do <command> - Execute OpenKore console command",
            "- pause <seconds> - Wait for specified time",
            "- log <message> - Write to log",
            "- call <macro_name> - Call another macro",
            "- stop - Stop macro execution",
            "- release <automacro_name> - Release run-once automacro",
            "",
            "### Priority Rules:",
            "- Higher priority = checked first (1-100)",
            "- Healing/escape: 90-100",
            "- Resource management: 80-89",
            "- Farming/combat: 50-79",
            "- Utility: 10-49",
            "",
            "### Best Practices:",
            "1. Always include logging for debugging",
            "2. Use appropriate timeouts to prevent spam",
            "3. Set exclusive=1 for critical macros",
            "4. Use run-once for one-time triggers",
            "5. Add pause between commands for stability",
            "6. Match automacro name with called macro name pattern",
            "",
            "**REFERENCE:** Full documentation available in EVENTMACRO_COMPLETE_REFERENCE.md"
        ]
        
        cls._cached_summary = "\n".join(summary_sections)
        return cls._cached_summary
    
    @classmethod
    def get_syntax_instructions(cls) -> str:
        """
        Get explicit syntax instructions for agents
        
        Returns:
            Syntax instruction text
        """
        return """
**MANDATORY SYNTAX REQUIREMENTS:**

You MUST strictly follow the OpenKore EventMacro syntax defined in EVENTMACRO_COMPLETE_REFERENCE.md:

1. **Automacro blocks** define WHEN to trigger:
   - Start with: automacro <name> {
   - Include conditions (hp, sp, weight, map, monster, etc.)
   - End with: call <macro_name>
   - Close with: }

2. **Macro blocks** define WHAT to do:
   - Start with: macro <name> {
   - Include commands (do, pause, log, call, stop, release)
   - Close with: }

3. **Indentation:** Use 4 spaces or 1 tab for block contents

4. **Conditions:** Follow exact syntax (e.g., "hp < 30%", "weight > 80%")

5. **Commands:** Use OpenKore command syntax (e.g., "do is White Potion", "do attack Monster")

6. **Logging:** Always include log statements for debugging

7. **Timing:** Add pause commands between actions for stability

**VIOLATION OF THESE RULES WILL RESULT IN NON-FUNCTIONAL MACROS.**

Consult the complete reference document for advanced features, conditions, and examples.
"""
    
    @classmethod
    def _get_fallback_reference(cls) -> str:
        """
        Fallback reference content if file cannot be loaded
        
        Returns:
            Minimal reference content
        """
        return """
# EventMacro Reference (Fallback)

## Basic Automacro Structure:
```
automacro <name> {
    <condition> <value>
    priority <number>
    exclusive 1
    timeout <seconds>
    call <macro_name>
}
```

## Basic Macro Structure:
```
macro <name> {
    log <message>
    do <command>
    pause <seconds>
}
```

## Common Conditions:
- hp < X% / hp > X%
- sp < X% / sp > X%
- weight > X%
- aggressives > X
- map <map_name>
- monster <monster_name>

## Common Commands:
- do <command> - Execute OpenKore command
- pause <seconds> - Wait
- log <message> - Logging
- call <macro> - Call macro
- stop - Stop execution

**WARNING:** Complete reference document not found. Using minimal fallback.
"""
    
    @classmethod
    def clear_cache(cls):
        """Clear cached reference content (useful for testing/updates)"""
        cls._cached_reference = None
        cls._cached_summary = None
        logger.info("Reference cache cleared")
