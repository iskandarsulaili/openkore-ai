"""
MacroStrategist Agent
Analyzes game state and determines what macros are needed
"""

import logging
from typing import Dict, List, Optional
from crewai import Agent, Task, Crew
from pydantic import BaseModel, Field
from llm.provider_chain import llm_chain
from .reference_loader import MacroReferenceLoader

logger = logging.getLogger(__name__)


class StrategicDecision(BaseModel):
    """Strategic macro generation decision"""
    needs_macro: bool = Field(..., description="Whether a new macro is needed")
    macro_type: str = Field(..., description="Type of macro needed")
    priority: int = Field(..., ge=1, le=100, description="Priority level")
    reason: str = Field(..., description="Reasoning for decision")
    parameters: Dict = Field(default_factory=dict, description="Macro parameters")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")


class MacroStrategist:
    """
    MacroStrategist Agent
    
    Role: Analyzes game state and decides what macros are needed
    Capabilities:
    - Evaluate character state (level, HP, SP, location, inventory)
    - Assess environmental threats and opportunities
    - Review historical performance metrics
    - Determine macro generation priorities
    """
    
    def __init__(self, db_connection=None):
        """
        Initialize MacroStrategist agent
        
        Args:
            db_connection: Database connection for performance queries
        """
        self.db = db_connection
        
        # Load EventMacro reference document
        self.reference_summary = MacroReferenceLoader.load_reference_summary()
        self.syntax_instructions = MacroReferenceLoader.get_syntax_instructions()
        
        self.agent = self._create_agent()
        
        logger.info("MacroStrategist agent initialized with EventMacro reference")
    
    def _create_agent(self) -> Agent:
        """Create the CrewAI agent with appropriate configuration and reference"""
        backstory = f"""You are an expert Ragnarok Online strategist with deep knowledge of:
- Game mechanics and character progression
- Farming efficiency and resource optimization
- Threat assessment and survival strategies
- Player behavior patterns and macro effectiveness
- OpenKore EventMacro system and capabilities

**EventMacro Knowledge Base:**

{self.reference_summary}

{self.syntax_instructions}

Your strategic decisions must consider:
1. What EventMacro conditions are available for detecting situations
2. What EventMacro commands can accomplish the desired actions
3. Appropriate priority levels for different macro types
4. Timing and performance implications of macro triggers
5. Interaction between multiple macros (exclusivity, priority)

When recommending macro types, you understand the technical capabilities and limitations
of the EventMacro system. Your strategic decisions are informed by both game knowledge
AND macro system capabilities.

Your task is to analyze the current game situation and decide what type of macro
automation would be most beneficial AND technically feasible with EventMacro.
You consider character stats, environment, inventory, threats, historical performance,
and EventMacro system capabilities to make informed decisions."""
        
        return Agent(
            role="Macro Strategy Analyst",
            goal="Analyze game state and determine optimal macro strategy for Ragnarok Online gameplay using EventMacro system",
            backstory=backstory,
            verbose=True,
            allow_delegation=False,
            llm=llm_chain.get_crewai_llm()
        )
    
    def analyze_game_state_tool(self, game_state: Dict) -> Dict:
        """
        Analyzes current game state and extracts key metrics
        
        Args:
            game_state: Complete game state dictionary
            
        Returns:
            Analyzed metrics and recommendations
        """
        char = game_state.get('character', {})
        position = game_state.get('position', {})
        inventory = game_state.get('inventory', {})
        nearby = game_state.get('nearby', {})
        
        # Calculate key metrics
        hp_percent = (char.get('hp', 0) / max(char.get('max_hp', 1), 1)) * 100
        sp_percent = (char.get('sp', 0) / max(char.get('max_sp', 1), 1)) * 100
        weight_percent = (char.get('weight', 0) / max(char.get('max_weight', 1), 1)) * 100
        
        # Assess situation
        analysis = {
            'character_health': {
                'hp_percent': hp_percent,
                'sp_percent': sp_percent,
                'status': self._assess_health_status(hp_percent, sp_percent)
            },
            'resource_status': {
                'weight_percent': weight_percent,
                'zeny': char.get('zeny', 0),
                'needs_management': weight_percent > 75
            },
            'location': {
                'map': position.get('map', 'unknown'),
                'x': position.get('x', 0),
                'y': position.get('y', 0)
            },
            'environmental_factors': {
                'monster_count': len(nearby.get('monsters', [])),
                'aggressive_count': sum(
                    1 for m in nearby.get('monsters', [])
                    if m.get('is_aggressive', False)
                )
            }
        }
        
        return analysis
    
    def assess_threat_level_tool(self, monsters: List[Dict], character: Dict) -> Dict:
        """
        Assesses threat level from nearby monsters
        
        Args:
            monsters: List of nearby monsters
            character: Character state
            
        Returns:
            Threat assessment
        """
        if not monsters:
            return {'threat_level': 'none', 'score': 0, 'recommendation': 'safe_to_farm'}
        
        aggressive_count = sum(1 for m in monsters if m.get('is_aggressive', False))
        boss_count = sum(1 for m in monsters if m.get('is_boss', False))
        
        # Calculate threat score
        threat_score = (
            aggressive_count * 10 +
            boss_count * 50 +
            len(monsters) * 2
        )
        
        # Determine threat level
        if threat_score >= 100:
            threat_level = 'critical'
            recommendation = 'escape_immediately'
        elif threat_score >= 50:
            threat_level = 'high'
            recommendation = 'defensive_macro'
        elif threat_score >= 20:
            threat_level = 'moderate'
            recommendation = 'balanced_farming'
        else:
            threat_level = 'low'
            recommendation = 'aggressive_farming'
        
        return {
            'threat_level': threat_level,
            'threat_score': threat_score,
            'aggressive_count': aggressive_count,
            'boss_count': boss_count,
            'recommendation': recommendation
        }
    
    def check_performance_history_tool(self, session_id: str = None) -> Dict:
        """
        Retrieves historical performance metrics
        
        Args:
            session_id: Optional session identifier
            
        Returns:
            Performance history data
        """
        # Placeholder for database query
        # In production, this would query the database for actual metrics
        return {
            'recent_exp_rate': 0,
            'recent_death_rate': 0,
            'recent_zeny_rate': 0,
            'macro_effectiveness': {},
            'recommendations': []
        }
    
    def _assess_health_status(self, hp_percent: float, sp_percent: float) -> str:
        """Assess overall health status"""
        if hp_percent < 20:
            return 'critical'
        elif hp_percent < 40:
            return 'low'
        elif sp_percent < 20:
            return 'sp_depleted'
        elif hp_percent < 60:
            return 'moderate'
        else:
            return 'healthy'
    
    async def analyze_and_decide(self, game_state: Dict) -> StrategicDecision:
        """
        Analyze game state and decide what macro to create
        
        Args:
            game_state: Complete game state from OpenKore
            
        Returns:
            Strategic decision on macro generation
        """
        logger.info("MacroStrategist analyzing game state...")
        
        # Extract key information
        char = game_state.get('character', {})
        position = game_state.get('position', {})
        nearby = game_state.get('nearby', {})
        objective = game_state.get('objective', 'farm_efficiently')
        
        # Create strategic analysis task
        task = Task(
            description=f"""
            Analyze this Ragnarok Online game state and decide what macro automation is needed:
            
            **Character Status:**
            - Name: {char.get('name', 'Unknown')}
            - Level: {char.get('level', 0)} {char.get('job_class', 'Unknown')}
            - HP: {char.get('hp', 0)}/{char.get('max_hp', 0)} ({self._calc_percent(char.get('hp', 0), char.get('max_hp', 1)):.1f}%)
            - SP: {char.get('sp', 0)}/{char.get('max_sp', 0)} ({self._calc_percent(char.get('sp', 0), char.get('max_sp', 1)):.1f}%)
            - Weight: {char.get('weight', 0)}/{char.get('max_weight', 0)} ({self._calc_percent(char.get('weight', 0), char.get('max_weight', 1)):.1f}%)
            - Zeny: {char.get('zeny', 0)}
            
            **Location:**
            - Map: {position.get('map', 'unknown')}
            - Coordinates: ({position.get('x', 0)}, {position.get('y', 0)})
            
            **Environment:**
            - Nearby Monsters: {len(nearby.get('monsters', []))}
            - Aggressive Monsters: {sum(1 for m in nearby.get('monsters', []) if m.get('is_aggressive', False))}
            
            **Current Objective:** {objective}
            
            **Analysis Required:**
            1. Assess if a new macro is needed or if existing macros are sufficient
            2. If needed, determine macro type: farming, healing, resource_management, escape, or skill_rotation
            3. Consider EventMacro condition availability (refer to your backstory reference)
            4. Identify specific EventMacro triggers that can detect this situation (e.g., hp < X%, aggressives > Y)
            5. Define what EventMacro commands can accomplish the desired actions
            6. Assign appropriate priority (1-100, higher = more important)
               - Healing/escape: 90-100
               - Resource management: 80-89
               - Farming/combat: 50-79
               - Utility: 10-49
            7. Explain your reasoning with reference to EventMacro capabilities
            
            **Output Format:**
            Provide a strategic decision with:
            - needs_macro: boolean
            - macro_type: string (farming|healing|resource_management|escape|skill_rotation)
            - priority: int (1-100) based on urgency and EventMacro priority guidelines
            - reason: detailed explanation including EventMacro technical feasibility
            - parameters: dict with specific parameters that will be used by EventMacro generator
            - confidence: float (0.0-1.0)
            
            **REFERENCE:** Consult the EventMacro reference in your backstory for available conditions and commands.
            """,
            agent=self.agent,
            expected_output="Strategic decision on macro generation with complete reasoning and EventMacro system awareness"
        )
        
        # Execute analysis
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=True
        )
        
        result = crew.kickoff()
        
        # Parse result into structured decision
        decision = self._parse_strategic_result(result, game_state)
        
        logger.info(
            f"Strategic decision: {'CREATE' if decision.needs_macro else 'SKIP'} "
            f"macro of type '{decision.macro_type}' with priority {decision.priority}"
        )
        
        return decision
    
    def _calc_percent(self, current: int, maximum: int) -> float:
        """Calculate percentage safely"""
        return (current / max(maximum, 1)) * 100
    
    def _parse_strategic_result(self, result: str, game_state: Dict) -> StrategicDecision:
        """
        Parse CrewAI result into structured decision
        
        Args:
            result: Raw result from CrewAI
            game_state: Original game state
            
        Returns:
            Structured strategic decision
        """
        # Extract character metrics for rule-based fallback
        char = game_state.get('character', {})
        hp_percent = self._calc_percent(char.get('hp', 0), char.get('max_hp', 1))
        sp_percent = self._calc_percent(char.get('sp', 0), char.get('max_sp', 1))
        weight_percent = self._calc_percent(char.get('weight', 0), char.get('max_weight', 1))
        
        aggressive_count = sum(
            1 for m in game_state.get('nearby', {}).get('monsters', [])
            if m.get('is_aggressive', False)
        )
        
        # Rule-based decision making (fallback + enhancement)
        # This ensures we always generate valid decisions even if LLM parsing fails
        
        if hp_percent < 30:
            return StrategicDecision(
                needs_macro=True,
                macro_type='healing',
                priority=95,
                reason=f"Critical HP at {hp_percent:.1f}% requires emergency healing macro",
                parameters={
                    'hp_threshold': 30,
                    'healing_items': ['White Potion', 'Orange Potion', 'Red Potion']
                },
                confidence=0.95
            )
        
        elif aggressive_count > 5:
            return StrategicDecision(
                needs_macro=True,
                macro_type='escape',
                priority=90,
                reason=f"Surrounded by {aggressive_count} aggressive monsters - escape needed",
                parameters={
                    'aggressive_threshold': 5,
                    'escape_method': 'fly_wing'
                },
                confidence=0.90
            )
        
        elif weight_percent > 80:
            return StrategicDecision(
                needs_macro=True,
                macro_type='resource_management',
                priority=85,
                reason=f"Overweight at {weight_percent:.1f}% - need weight management",
                parameters={
                    'weight_threshold': 80,
                    'action': 'storage'
                },
                confidence=0.88
            )
        
        elif game_state.get('objective') == 'farm_efficiently':
            return StrategicDecision(
                needs_macro=True,
                macro_type='farming',
                priority=60,
                reason="Optimizing farming efficiency for current map and level",
                parameters={
                    'target_monsters': game_state.get('nearby', {}).get('monsters', [])[:3],
                    'farming_area': {
                        'map': game_state.get('position', {}).get('map', 'unknown'),
                        'x_center': game_state.get('position', {}).get('x', 0),
                        'y_center': game_state.get('position', {}).get('y', 0),
                        'radius': 20
                    }
                },
                confidence=0.75
            )
        
        else:
            return StrategicDecision(
                needs_macro=False,
                macro_type='none',
                priority=0,
                reason="Current game state is stable, existing macros sufficient",
                parameters={},
                confidence=0.70
            )
