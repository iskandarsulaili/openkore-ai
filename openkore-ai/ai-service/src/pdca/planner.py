"""
PDCA Plan Phase: LLM-powered strategy and macro generation
Enhanced with optional CrewAI multi-agent analysis
"""

from typing import Dict, Any, List, Optional
from loguru import logger
from llm.provider_chain import llm_chain
from database.schema import db

class PDCAPlanner:
    """Plans strategy and generates macros using LLM"""
    
    def __init__(self):
        self.macro_templates = self._load_macro_templates()
        logger.info("PDCA Planner initialized")
        
    def _load_macro_templates(self) -> Dict[str, str]:
        """Load macro templates for different scenarios"""
        return {
            "farming": """
# Auto-generated farming macro (PDCA Plan Phase)
# Character: {character_name} (Lv {level} {job_class})
# Target: {target_monster} at {target_map}
# Strategy: {strategy}

automacro farm_{target_monster} {{
    exclusive 1
    map {target_map}
    timeout 5
    run-once 0
    call {{
        # Move to farming area
        do move {farming_x} {farming_y}
        do ai manual
        
        # Attack sequence
        do attack "{target_monster}"
        pause 0.5
        
        # Loot drops
        do take
        
        # Return to auto mode
        do ai auto
    }}
}}
""",
            "healing": """
# Auto-generated healing macro (PDCA Plan Phase)
# HP threshold: {hp_threshold}%
# Healing item: {healing_item}

automacro emergency_heal {{
    exclusive 1
    hp < {hp_threshold}%
    timeout 2
    call {{
        do is {healing_item}
        pause 1
    }}
}}
""",
            "resource_management": """
# Auto-generated resource management macro (PDCA Plan Phase)
# Weight threshold: {weight_threshold}%

automacro manage_weight {{
    exclusive 1
    weight > {weight_threshold}%
    timeout 30
    call {{
        do storage
        pause 2
        do storage close
    }}
}}
"""
        }
        
    async def analyze_performance(self, session_id: str) -> Dict[str, Any]:
        """Analyze recent performance metrics from database"""
        # Query recent decisions and metrics
        async with db.conn.execute(
            "SELECT tier_used, outcome, confidence FROM decisions WHERE session_id = ? ORDER BY timestamp DESC LIMIT 100",
            (session_id,)
        ) as cursor:
            decisions = await cursor.fetchall()
            
        # Calculate statistics
        total = len(decisions)
        if total == 0:
            return {"error": "No performance data available"}
            
        success_count = sum(1 for d in decisions if d[1] == 'success')
        success_rate = success_count / total if total > 0 else 0
        
        tier_distribution = {}
        for decision in decisions:
            tier = decision[0]
            tier_distribution[tier] = tier_distribution.get(tier, 0) + 1
            
        return {
            "total_decisions": total,
            "success_rate": success_rate,
            "tier_distribution": tier_distribution,
            "avg_confidence": sum(d[2] or 0 for d in decisions) / total
        }
        
    async def generate_strategy(
        self,
        session_id: str,
        character_state: Dict[str, Any],
        performance_data: Dict[str, Any],
        use_crew: bool = False
    ) -> Dict[str, Any]:
        """
        Use LLM to generate strategic plan
        
        Args:
            session_id: Session identifier
            character_state: Current character state
            performance_data: Performance metrics
            use_crew: Use CrewAI multi-agent analysis (enhanced)
        """
        logger.info(f"Generating strategy (crew={'enabled' if use_crew else 'disabled'})...")
        
        # Optional: Use CrewAI for multi-agent strategy generation
        if use_crew:
            try:
                from agents.crew_manager import crew_manager
                
                # Build context for crew
                crew_context = {
                    'character': character_state,
                    'monsters': [],
                    'inventory': [],
                    'session_duration': 30,
                    'recent_decisions': performance_data
                }
                
                logger.info("Consulting CrewAI agents for strategic insights...")
                crew_result = await crew_manager.consult_agents(crew_context)
                
                # Extract strategic recommendations from crew
                crew_strategy = "\n".join([
                    f"- {rec.get('output', '')}"
                    for rec in crew_result.get('aggregated_recommendations', [])
                ])
                
                return {
                    "strategy": crew_strategy,
                    "provider": "crewai_multi_agent",
                    "character_level": character_state.get('level', 1),
                    "crew_confidence": crew_result.get('consensus_confidence', 0.85)
                }
            except Exception as e:
                logger.warning(f"CrewAI strategy generation failed: {e}, falling back to LLM")
                # Fall through to LLM
        
        # Build context-rich prompt
        prompt = f"""
Analyze this Ragnarok Online character's performance and generate an optimized strategy:

CHARACTER STATUS:
- Name: {character_state.get('name', 'Unknown')}
- Level: {character_state.get('level', 1)}
- Job: {character_state.get('job_class', 'Novice')}
- HP: {character_state.get('hp', 0)}/{character_state.get('max_hp', 1)}
- Current Map: {character_state.get('position', {}).get('map', 'unknown')}

PERFORMANCE DATA:
- Total Decisions: {performance_data.get('total_decisions', 0)}
- Success Rate: {performance_data.get('success_rate', 0)*100:.1f}%
- Decision Distribution: {performance_data.get('tier_distribution', {})}

TASK: Generate a strategic plan with:
1. Immediate priorities (next 10 minutes)
2. Short-term goals (next hour)
3. Long-term objectives (next session)
4. Recommended farming location and target monsters
5. Equipment/skill priorities

Format as structured JSON.
"""
        
        llm_result = await llm_chain.query(prompt, {
            'session_id': session_id,
            'character': character_state
        })
        
        if not llm_result:
            logger.error("LLM strategy generation failed")
            return {"error": "LLM unavailable"}
            
        return {
            "strategy": llm_result['response'],
            "provider": llm_result['provider'],
            "character_level": character_state.get('level', 1)
        }
        
    async def generate_macros(self, strategy: Dict[str, Any], character_state: Dict[str, Any]) -> List[tuple]:
        """Generate macro files from strategy"""
        logger.info("Generating macros from strategy...")
        
        macros = []
        
        # Generate farming macro
        farming_macro = self.macro_templates["farming"].format(
            character_name=character_state.get('name', 'Unknown'),
            level=character_state.get('level', 1),
            job_class=character_state.get('job_class', 'Novice'),
            target_monster="Poring",  # Would be extracted from strategy in production
            target_map="prt_fild08",
            strategy="Efficient leveling",
            farming_x=150,
            farming_y=200
        )
        macros.append(("farming.txt", farming_macro))
        
        # Generate healing macro
        healing_macro = self.macro_templates["healing"].format(
            hp_threshold=30,
            healing_item="White Potion"
        )
        macros.append(("healing.txt", healing_macro))
        
        # Generate resource management macro
        resource_macro = self.macro_templates["resource_management"].format(
            weight_threshold=80
        )
        macros.append(("resource_management.txt", resource_macro))
        
        logger.success(f"Generated {len(macros)} macro files")
        return macros

planner = PDCAPlanner()
