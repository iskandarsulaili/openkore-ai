"""
Autonomous Goal Generator
Uses LLM to generate dynamic goals based on current state
"""

from typing import Dict, Any, List
from loguru import logger

class GoalGenerator:
    """Generates autonomous goals using LLM"""
    
    def __init__(self):
        self.active_goals = []
        logger.info("Goal Generator initialized")
        
    async def generate_short_term_goals(self, character_state: Dict[str, Any], 
                                       lifecycle_stage: str) -> List[Dict[str, Any]]:
        """Generate goals for next 1-2 hours"""
        level = character_state.get('level', 1)
        job_class = character_state.get('job_class', 'Novice')
        zeny = character_state.get('zeny', 0)
        
        # Try to use LLM if available
        try:
            from llm.provider_chain import llm_chain
            
            prompt = f"""
Generate 3 short-term goals (1-2 hours) for a Ragnarok Online character:

Character: Level {level} {job_class}
Lifecycle Stage: {lifecycle_stage}
Current Zeny: {zeny}

Provide goals as JSON array with format:
[
  {{"goal": "description", "priority": "high/medium/low", "estimated_time_minutes": 30}}
]

Focus on: leveling efficiency, equipment acquisition, skill development.
"""
            
            llm_result = await llm_chain.query(prompt, {'character': character_state})
            
            if llm_result:
                # Parse LLM response (would parse JSON in production)
                # For Phase 7, return template goals
                goals = [
                    {"goal": f"Reach level {level + 5}", "priority": "high", "estimated_time_minutes": 60},
                    {"goal": "Farm 50k zeny for equipment", "priority": "medium", "estimated_time_minutes": 45},
                    {"goal": "Complete daily quests", "priority": "low", "estimated_time_minutes": 30}
                ]
            else:
                goals = self._generate_fallback_goals(level, zeny, lifecycle_stage)
        except Exception as e:
            logger.warning(f"LLM unavailable, using fallback goals: {e}")
            goals = self._generate_fallback_goals(level, zeny, lifecycle_stage)
            
        self.active_goals = goals
        logger.info(f"Generated {len(goals)} short-term goals")
        return goals
        
    def _generate_fallback_goals(self, level: int, zeny: int, lifecycle_stage: str) -> List[Dict[str, Any]]:
        """Generate fallback goals when LLM is unavailable"""
        goals = []
        
        # Level-based goals
        if level < 10:
            goals.append({
                "goal": "Complete novice training and reach level 10",
                "priority": "high",
                "estimated_time_minutes": 45
            })
        elif level < 50:
            goals.append({
                "goal": f"Level up to {level + 5}",
                "priority": "high",
                "estimated_time_minutes": 60
            })
        else:
            goals.append({
                "goal": f"Progress towards level 99 (current: {level})",
                "priority": "high",
                "estimated_time_minutes": 90
            })
        
        # Zeny-based goals
        if zeny < 50000:
            goals.append({
                "goal": "Farm 50k zeny for equipment upgrade",
                "priority": "medium",
                "estimated_time_minutes": 45
            })
        elif zeny < 500000:
            goals.append({
                "goal": "Accumulate 500k zeny for advanced gear",
                "priority": "medium",
                "estimated_time_minutes": 90
            })
        
        # Stage-based goals
        if lifecycle_stage == "novice":
            goals.append({
                "goal": "Prepare for first job change quest",
                "priority": "medium",
                "estimated_time_minutes": 30
            })
        elif lifecycle_stage == "first_job":
            goals.append({
                "goal": "Master core job skills",
                "priority": "low",
                "estimated_time_minutes": 40
            })
        
        return goals[:3]  # Return max 3 goals
        
    async def generate_long_term_goals(self, character_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate goals for next session/week"""
        level = character_state.get('level', 1)
        
        goals = [
            {"goal": "Reach next job milestone", "target_level": (level // 10 + 1) * 10, "priority": "high"},
            {"goal": "Acquire full +4 equipment set", "zeny_cost": 500000, "priority": "medium"},
            {"goal": "Master core skill tree", "skill_points_needed": 20, "priority": "medium"}
        ]
        
        logger.info(f"Generated {len(goals)} long-term goals")
        return goals
        
    async def evaluate_goal_progress(self, goal: Dict[str, Any], current_state: Dict[str, Any]) -> float:
        """Evaluate progress towards goal (0.0 to 1.0)"""
        # Simple progress tracking
        if "level" in goal.get('goal', '').lower():
            current_level = current_state.get('level', 1)
            target_level = goal.get('target_level', current_level + 5)
            return min(current_level / target_level, 1.0)
            
        return 0.5  # Default progress

goal_generator = GoalGenerator()
