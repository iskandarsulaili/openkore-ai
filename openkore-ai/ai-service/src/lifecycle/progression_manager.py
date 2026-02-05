"""
Progression Manager
Tracks character progression and manages leveling goals
"""

from typing import Dict, Any, Optional
from loguru import logger
import time

class ProgressionManager:
    """Manages character progression through game lifecycle"""
    
    def __init__(self, db_instance):
        self.db = db_instance
        self.current_stage = "novice"
        self.current_goal = None
        logger.info("Progression Manager initialized")
        
    async def update_lifecycle_state(self, session_id: str, character_state: Dict[str, Any]):
        """Update character's lifecycle stage in database"""
        level = character_state.get('level', 1)
        job_class = character_state.get('job_class', 'Novice')
        
        # Determine lifecycle stage
        if level < 10:
            stage = "novice"
            goal = "Reach level 10 for first job change"
        elif level < 50 and job_class in ['Swordsman', 'Magician', 'Archer', 'Acolyte', 'Merchant', 'Thief']:
            stage = "first_job"
            goal = "Reach level 50 for second job change"
        elif level < 99:
            stage = "second_job"
            goal = f"Reach level 99 to master {job_class}"
        else:
            stage = "endgame"
            goal = "Farm high-end content and rare equipment"
            
        self.current_stage = stage
        self.current_goal = goal
        
        # Store in database
        try:
            async with self.db.conn.execute(
                "INSERT INTO lifecycle_states (session_id, character_name, level, job_class, lifecycle_stage, current_goal, goal_progress, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (session_id, character_state.get('name', 'Unknown'), level, job_class, stage, goal, 0.0, int(time.time()))
            ) as cursor:
                await self.db.conn.commit()
        except Exception as e:
            logger.warning(f"Failed to store lifecycle state in database: {e}")
            
        logger.info(f"Lifecycle stage: {stage}, Goal: {goal}")
        
    async def get_next_milestone(self, character_level: int) -> Optional[Dict[str, Any]]:
        """Get next progression milestone"""
        milestones = {
            10: {"event": "first_job_change", "preparation": "Save skill points, complete novice quests"},
            25: {"event": "basic_equipment", "preparation": "Farm 50k zeny for weapon upgrade"},
            40: {"event": "advanced_skills", "preparation": "Allocate skill points to key skills"},
            50: {"event": "second_job_change", "preparation": "Complete job change quest requirements"},
            75: {"event": "high_tier_equipment", "preparation": "Farm 500k zeny for endgame gear"},
            99: {"event": "max_level", "preparation": "Optimize equipment and stats"}
        }
        
        # Find next milestone
        for milestone_level in sorted(milestones.keys()):
            if character_level < milestone_level:
                return {"level": milestone_level, **milestones[milestone_level]}
                
        return None

progression_manager = None  # Initialized in main.py
