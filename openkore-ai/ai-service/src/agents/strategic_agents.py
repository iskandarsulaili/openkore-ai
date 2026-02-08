"""
Strategic Planning Agents for CONSCIOUS Layer
Uses CrewAI for complex decision-making and sequential thinking

User requirement: "able to solve complex situation that might even 
need sequential thinking and sequential action"

Goal: Achieve 95% autonomous gameplay through strategic planning
"""
from crewai import Agent, Task, Crew
from typing import Dict, Any, List
from loguru import logger


class StrategicPlanner:
    """
    CONSCIOUS Layer - Strategic planning with CrewAI
    
    Enables autonomous gameplay with:
    - Long-term goal planning (quest automation, build optimization, leveling)
    - Sequential thinking (multi-step problem solving)
    - Complex situation handling (when reflex/tactical isn't enough)
    - Resource optimization (zeny management, item optimization, efficiency)
    """
    
    def __init__(self, llm_provider):
        """
        Initialize strategic planner with CrewAI agents
        
        Args:
            llm_provider: LLM instance for agents (deepseek-chat)
        """
        self.llm = llm_provider
        
        # Create specialized strategic agents
        self.goal_planner = self._create_goal_planner()
        self.resource_optimizer = self._create_resource_optimizer()
        self.quest_strategist = self._create_quest_strategist()
        self.build_advisor = self._create_build_advisor()
        
        logger.success("[STRATEGIC] Initialized StrategicPlanner with 4 specialized agents")
    
    def _create_goal_planner(self) -> Agent:
        """
        Agent that plans long-term goals and progression paths
        
        Responsibilities:
        - Plan optimal leveling paths
        - Determine next major objectives (job change, equipment upgrades)
        - Prioritize multiple goals
        - Adapt strategy based on character progress
        """
        return Agent(
            role="Strategic Goal Planner",
            goal="Plan optimal long-term goals for character progression and gameplay efficiency",
            backstory="""You are an expert Ragnarok Online strategist with deep knowledge of 
            game mechanics, optimal leveling paths, and efficient resource management. You 
            think several steps ahead and create comprehensive plans that maximize character 
            growth while minimizing risks.
            
            You understand:
            - Optimal leveling zones for each level range
            - Job change requirements and timing
            - Equipment progression paths
            - Efficient quest chains
            - Risk vs reward optimization
            
            You prioritize sustainability and long-term success over short-term gains.""",
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
    
    def _create_resource_optimizer(self) -> Agent:
        """
        Agent that optimizes resource usage and economy
        
        Responsibilities:
        - Manage zeny efficiently
        - Optimize item usage (when to use vs save)
        - Plan shopping trips
        - Decide when to sell items
        - Ensure sustainable resource flow
        """
        return Agent(
            role="Resource Optimization Specialist",
            goal="Maximize efficiency of zeny, items, and time usage",
            backstory="""You are a master of resource management in Ragnarok Online. You 
            understand market dynamics, item values, opportunity costs, and efficient 
            grinding strategies. You ensure the character never runs out of resources 
            and always maintains sustainable gameplay.
            
            You excel at:
            - Zeny budgeting and spending priorities
            - Identifying valuable vs junk drops
            - Optimizing inventory weight management
            - Planning cost-effective equipment upgrades
            - Balancing consumption with income
            
            You never let the character become resource-starved or wasteful.""",
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
    
    def _create_quest_strategist(self) -> Agent:
        """
        Agent that handles quest decisions and automation
        
        Responsibilities:
        - Identify beneficial quests
        - Plan quest completion order
        - Estimate quest rewards vs effort
        - Navigate quest chains
        - Prioritize quests based on character needs
        """
        return Agent(
            role="Quest Strategy Expert",
            goal="Identify and complete quests that provide maximum benefit",
            backstory="""You are a quest completion expert who knows all Ragnarok Online 
            quests, their requirements, rewards, and optimal completion order. You prioritize 
            quests that provide experience, equipment, or unlock new areas.
            
            You specialize in:
            - Quest reward evaluation (exp, zeny, items)
            - Prerequisite chain planning
            - Travel efficiency (group nearby quests)
            - Risk assessment (quest difficulty vs character strength)
            - Unlock priority (job change quests, area access)
            
            You ensure the character completes high-value quests at the right time.""",
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
    
    def _create_build_advisor(self) -> Agent:
        """
        Agent that advises on character build and skill allocation
        
        Responsibilities:
        - Optimize stat point allocation
        - Plan skill learning order
        - Recommend build paths (tank, DPS, support, hybrid)
        - Ensure efficient stat/skill distribution
        - Adapt build to player's playstyle
        """
        return Agent(
            role="Character Build Advisor",
            goal="Optimize stat allocation and skill learning for chosen build path",
            backstory="""You are a character build specialist with encyclopedic knowledge 
            of all Ragnarok Online job classes, skills, and stat distributions. You create 
            optimized builds based on player intent (tank, DPS, support, hybrid) and ensure 
            stat points and skill points are allocated efficiently.
            
            You master:
            - Optimal stat distributions for each class
            - Skill synergies and combos
            - Build breakpoints (AGI 90 for flee, DEX for cast time)
            - Equipment requirements (stat prerequisites)
            - Build flexibility (respec planning)
            
            You never waste stat/skill points and always build toward a coherent strategy.""",
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
    
    async def plan_next_strategic_action(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use CrewAI to plan next strategic action with sequential thinking
        
        This is called when REFLEX and TACTICAL layers don't apply:
        - Character is healthy (HP > 80%, SP > 50%)
        - Not in immediate danger
        - Time for long-term planning
        
        Args:
            game_state: Complete game state with character, inventory, monsters, etc.
            
        Returns:
            Strategic action recommendation with reasoning
        """
        logger.info("[STRATEGIC] Activating CrewAI for strategic planning...")
        
        # Extract key information for strategic decision
        character = game_state.get("character", {})
        level = character.get("level", 1)
        job_level = character.get("job_level", 1)
        current_class = character.get("job_class", "Novice")
        zeny = character.get("zeny", 0)
        current_map = character.get("position", {}).get("map", "unknown")
        
        # Get available stat/skill points
        available_stat_points = character.get("points_free", 0)
        available_skill_points = character.get("points_skill", 0)
        
        # Get inventory status
        inventory = game_state.get("inventory", [])
        weight_percent = (character.get("weight", 0) / character.get("max_weight", 1)) * 100 if character.get("max_weight", 1) > 0 else 0
        
        logger.debug(f"[STRATEGIC] Character: Lv{level} {current_class} (Job Lv{job_level}), Zeny: {zeny}z")
        logger.debug(f"[STRATEGIC] Available points: {available_stat_points} stat, {available_skill_points} skill")
        logger.debug(f"[STRATEGIC] Weight: {weight_percent:.1f}%, Inventory: {len(inventory)} items")
        
        # Create strategic planning task with sequential thinking
        task_description = f"""
        Analyze current game state and plan the NEXT strategic action for autonomous gameplay:
        
        === CHARACTER STATUS ===
        Class: {current_class}
        Level: {level} (Job Level: {job_level})
        Location: {current_map}
        Zeny: {zeny}z
        Available Points: {available_stat_points} stat, {available_skill_points} skill
        Inventory: {len(inventory)} items ({weight_percent:.1f}% weight)
        
        === CURRENT SITUATION ===
        - HP/SP are healthy (no immediate danger)
        - Not in critical combat
        - Time for strategic planning
        - Character can perform long-term actions
        
        === YOUR TASK: SEQUENTIAL THINKING ===
        Think through the following decision tree step-by-step:
        
        1. CHARACTER PROGRESSION
           - If level < 10: Focus on reaching level 10 for job change
           - If job level >= 10 and Novice: Should pursue job change quest NOW
           - If stat/skill points available: Allocate them immediately for build optimization
        
        2. RESOURCE SUSTAINABILITY
           - If zeny < 5000: Consider farming valuable drops or selling items
           - If weight > 80%: Need to sell items or store excess
           - If inventory full: Must manage items before continuing
        
        3. BUILD OPTIMIZATION
           - If stat points > 0: Allocate based on build (prioritize STR for Swordman, AGI for Thief, etc.)
           - If skill points > 0: Learn essential skills first (passive buffs, survival skills)
        
        4. QUEST OPPORTUNITIES
           - Check if any beneficial quests are available for current level
           - Prioritize quests with experience or equipment rewards
           - Consider job change quest if requirements are met
        
        5. LEVELING EFFICIENCY
           - If no urgent tasks: Continue farming monsters appropriate for level
           - Recommend optimal farming location for current level range
        
        === OUTPUT REQUIREMENTS ===
        Provide ONE specific action with clear reasoning:
        - State the action (e.g., "job_change_quest", "allocate_stats", "farm_monsters", "sell_items")
        - Explain WHY this action is optimal right now
        - Describe the expected outcome
        - Show sequential thinking (what comes after this action)
        
        Think step-by-step and choose the MOST IMPORTANT action for autonomous progression.
        """
        
        # Create task for goal planner (primary strategist)
        planning_task = Task(
            description=task_description,
            expected_output="Strategic action recommendation with reasoning and sequential plan",
            agent=self.goal_planner
        )
        
        # Execute with crew
        crew = Crew(
            agents=[self.goal_planner, self.resource_optimizer, self.build_advisor],
            tasks=[planning_task],
            verbose=True
        )
        
        try:
            logger.info("[STRATEGIC] Executing CrewAI planning...")
            result = crew.kickoff()
            
            # Extract result text
            result_text = str(result)
            logger.info(f"[STRATEGIC] CrewAI recommendation received: {result_text[:200]}...")
            
            # Parse result and convert to actionable command
            action = self._parse_crew_result(result_text, game_state)
            
            return action
            
        except Exception as e:
            logger.error(f"[STRATEGIC] CrewAI execution error: {e}")
            logger.exception(e)
            
            # Fallback to simple heuristic
            return self._fallback_strategic_action(game_state)
    
    def _parse_crew_result(self, crew_result: str, game_state: Dict) -> Dict:
        """
        Convert CrewAI text result into actionable command
        
        Parses natural language output and maps to specific game actions
        
        Args:
            crew_result: Text output from CrewAI agent
            game_state: Current game state for context
            
        Returns:
            Action dictionary with action name, params, layer, and reasoning
        """
        result_lower = crew_result.lower()
        
        # Extract character info for context
        character = game_state.get("character", {})
        level = character.get("level", 1)
        job_level = character.get("job_level", 1)
        current_class = character.get("job_class", "Novice")
        available_stat_points = character.get("points_free", 0)
        available_skill_points = character.get("points_skill", 0)
        
        # Parse common strategic recommendations
        
        # Priority 1: Job change (if Novice with job level >= 10)
        if "job change" in result_lower and current_class == "Novice" and job_level >= 10:
            logger.info("[STRATEGIC] Recommendation: Job change quest (ready for advancement)")
            return {
                "action": "job_change_quest",
                "params": {
                    "reason": "ready_for_job_advancement",
                    "priority": "high",
                    "current_class": current_class,
                    "job_level": job_level
                },
                "layer": "STRATEGIC",
                "reasoning": crew_result[:500]  # Truncate for logging
            }
        
        # Priority 2: Stat allocation (if points available)
        if ("allocate" in result_lower or "stat" in result_lower) and available_stat_points > 0:
            logger.info(f"[STRATEGIC] Recommendation: Allocate {available_stat_points} stat points")
            return {
                "action": "allocate_stats",
                "params": {
                    "reason": "build_optimization",
                    "priority": "high",
                    "available_points": available_stat_points
                },
                "layer": "STRATEGIC",
                "reasoning": crew_result[:500]
            }
        
        # Priority 3: Skill learning (if points available)
        if ("skill" in result_lower or "learn" in result_lower) and available_skill_points > 0:
            logger.info(f"[STRATEGIC] Recommendation: Learn skills ({available_skill_points} points)")
            return {
                "action": "learn_skills",
                "params": {
                    "reason": "skill_progression",
                    "priority": "high",
                    "available_points": available_skill_points
                },
                "layer": "STRATEGIC",
                "reasoning": crew_result[:500]
            }
        
        # Priority 4: Sell items (resource management)
        if "sell" in result_lower and "item" in result_lower:
            logger.info("[STRATEGIC] Recommendation: Sell items for zeny")
            return {
                "action": "sell_items",
                "params": {
                    "reason": "strategic_resource_management",
                    "priority": "medium"
                },
                "layer": "STRATEGIC",
                "reasoning": crew_result[:500]
            }
        
        # Priority 5: Buy items (restocking)
        if "buy" in result_lower or "stock up" in result_lower or "restock" in result_lower:
            logger.info("[STRATEGIC] Recommendation: Buy/restock consumables")
            return {
                "action": "auto_buy",
                "params": {
                    "items": ["Red Potion", "Fly Wing"],
                    "reason": "strategic_preparation",
                    "priority": "medium"
                },
                "layer": "STRATEGIC",
                "reasoning": crew_result[:500]
            }
        
        # Priority 6: Quest (if available and beneficial)
        if "quest" in result_lower:
            logger.info("[STRATEGIC] Recommendation: Pursue quest")
            return {
                "action": "find_quest",
                "params": {
                    "reason": "strategic_quest_completion",
                    "priority": "medium"
                },
                "layer": "STRATEGIC",
                "reasoning": crew_result[:500]
            }
        
        # Priority 7: Farm monsters (leveling/grinding)
        if "level" in result_lower or "farm" in result_lower or "grind" in result_lower or "hunt" in result_lower:
            logger.info("[STRATEGIC] Recommendation: Continue farming/leveling")
            return {
                "action": "farm_monsters",
                "params": {
                    "reason": "strategic_leveling",
                    "priority": "medium",
                    "target_level": level + 1
                },
                "layer": "STRATEGIC",
                "reasoning": crew_result[:500]
            }
        
        # Priority 8: Move to better location
        if "move" in result_lower or "location" in result_lower or "map" in result_lower:
            logger.info("[STRATEGIC] Recommendation: Move to better farming location")
            return {
                "action": "move_to_location",
                "params": {
                    "reason": "strategic_positioning",
                    "priority": "low"
                },
                "layer": "STRATEGIC",
                "reasoning": crew_result[:500]
            }
        
        # Default: Continue current behavior
        logger.info("[STRATEGIC] No specific action parsed, continuing current behavior")
        return {
            "action": "continue",
            "params": {
                "reason": "strategic_monitoring",
                "priority": "low"
            },
            "layer": "STRATEGIC",
            "reasoning": crew_result[:500]
        }
    
    def _fallback_strategic_action(self, game_state: Dict) -> Dict:
        """
        Fallback heuristic when CrewAI fails
        
        Simple rule-based strategy for reliability
        """
        logger.warning("[STRATEGIC] Using fallback heuristic (CrewAI unavailable)")
        
        character = game_state.get("character", {})
        level = character.get("level", 1)
        job_level = character.get("job_level", 1)
        current_class = character.get("job_class", "Novice")
        available_stat_points = character.get("points_free", 0)
        zeny = character.get("zeny", 0)
        
        # Simple priority heuristic
        if current_class == "Novice" and job_level >= 10:
            return {
                "action": "job_change_quest",
                "params": {"reason": "fallback_job_change", "priority": "high"},
                "layer": "STRATEGIC",
                "reasoning": "Fallback: Ready for job change"
            }
        
        if available_stat_points > 0:
            return {
                "action": "allocate_stats",
                "params": {"reason": "fallback_stat_allocation", "priority": "high"},
                "layer": "STRATEGIC",
                "reasoning": "Fallback: Allocate available stat points"
            }
        
        if zeny < 1000:
            return {
                "action": "farm_monsters",
                "params": {"reason": "fallback_earn_zeny", "priority": "medium"},
                "layer": "STRATEGIC",
                "reasoning": "Fallback: Need to earn zeny"
            }
        
        # Default: Continue farming
        return {
            "action": "farm_monsters",
            "params": {"reason": "fallback_leveling", "priority": "medium"},
            "layer": "STRATEGIC",
            "reasoning": "Fallback: Continue leveling"
        }


# Global instance - lazy initialization
_strategic_planner = None


def get_strategic_planner(llm_provider):
    """
    Get or create strategic planner singleton
    
    Args:
        llm_provider: LLM instance for agents
        
    Returns:
        StrategicPlanner instance
    """
    global _strategic_planner
    if _strategic_planner is None:
        _strategic_planner = StrategicPlanner(llm_provider)
    return _strategic_planner
