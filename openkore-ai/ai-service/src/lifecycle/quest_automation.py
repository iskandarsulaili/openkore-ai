"""
Quest Automation Framework
Automatically detects, accepts, and completes quests

Enhanced for Strategic Layer integration
"""

from typing import Dict, Any, List, Optional
from loguru import logger
from fastapi import APIRouter

# Create router for quest endpoints
router = APIRouter()

class QuestStep:
    """Represents a quest step"""
    def __init__(self, step_type: str, params: Dict[str, Any]):
        self.type = step_type  # "talk_npc", "kill_monster", "collect_item", "move_to"
        self.params = params
        self.completed = False

class Quest:
    """Represents a game quest"""
    def __init__(self, quest_id: str, name: str, steps: List[QuestStep]):
        self.quest_id = quest_id
        self.name = name
        self.steps = steps
        self.current_step = 0
        self.status = "available"  # available, in_progress, completed
        
class QuestAutomation:
    """Automates quest detection and completion"""
    
    def __init__(self):
        self.known_quests = self._load_quest_database()
        self.active_quests = []
        logger.info(f"Quest Automation initialized with {len(self.known_quests)} known quests")
        
    def _load_quest_database(self) -> Dict[str, Quest]:
        """Load quest database (simplified for Phase 7)"""
        quests = {}
        
        # Example: Novice Training Ground quest
        quests['novice_training'] = Quest(
            quest_id='novice_training',
            name='Novice Training',
            steps=[
                QuestStep('talk_npc', {'npc_name': 'Instructor Brutus', 'map': 'new_1-1'}),
                QuestStep('kill_monster', {'monster': 'Poring', 'count': 5}),
                QuestStep('talk_npc', {'npc_name': 'Instructor Brutus', 'map': 'new_1-1'}),
            ]
        )
        
        # Example: Job change quest
        quests['swordsman_job_change'] = Quest(
            quest_id='swordsman_job_change',
            name='Become a Swordsman',
            steps=[
                QuestStep('move_to', {'map': 'izlude_in', 'x': 74, 'y': 172}),
                QuestStep('talk_npc', {'npc_name': 'Swordsman Guildsman'}),
                QuestStep('collect_item', {'item': 'Proof of Strength', 'count': 1}),
                QuestStep('talk_npc', {'npc_name': 'Swordsman Guildsman'})
            ]
        )
        
        return quests
        
    async def detect_available_quests(self, character_state: Dict[str, Any]) -> List[Quest]:
        """Detect quests available for character"""
        level = character_state.get('level', 1)
        job_class = character_state.get('job_class', 'Novice')
        
        available = []
        
        # Novice quests
        if level < 10:
            if 'novice_training' in self.known_quests:
                available.append(self.known_quests['novice_training'])
                
        # Job change quests
        if level >= 10 and job_class == 'Novice':
            if 'swordsman_job_change' in self.known_quests:
                available.append(self.known_quests['swordsman_job_change'])
                
        logger.info(f"Detected {len(available)} available quests")
        return available
        
    async def get_next_quest_action(self, quest: Quest, game_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get next action for active quest"""
        if quest.current_step >= len(quest.steps):
            quest.status = "completed"
            return None
            
        step = quest.steps[quest.current_step]
        
        if step.type == "talk_npc":
            return {
                "type": "talk",
                "target": step.params['npc_name'],
                "map": step.params.get('map', 'current')
            }
        elif step.type == "kill_monster":
            return {
                "type": "hunt",
                "monster": step.params['monster'],
                "count": step.params['count']
            }
        elif step.type == "collect_item":
            return {
                "type": "collect",
                "item": step.params['item'],
                "count": step.params['count']
            }
        elif step.type == "move_to":
            return {
                "type": "move",
                "map": step.params['map'],
                "x": step.params.get('x', 100),
                "y": step.params.get('y', 100)
            }
            
        return None

# Initialize global instance
quest_automation = QuestAutomation()


# ============================================================================
# API ENDPOINTS for Strategic Layer Integration
# ============================================================================

from fastapi import APIRouter

# Create router for quest endpoints
router = APIRouter()

@router.post("/api/v1/quests/find_available")
async def find_available_quests(request: Dict[str, Any]):
    """
    Find quests available for character
    
    Used by Strategic Layer to identify quest opportunities
    """
    try:
        character_level = request.get("character_level", 1)
        character_class = request.get("character_class", "Novice")
        current_map = request.get("current_map", "unknown")
        completed_quests = request.get("completed_quests", [])
        
        logger.info(f"[QUEST] Finding quests for Lv{character_level} {character_class}")
        
        # Get available quests
        character_state = {
            "level": character_level,
            "job_class": character_class,
            "current_map": current_map
        }
        
        available = await quest_automation.detect_available_quests(character_state)
        available = [q for q in available if q.quest_id not in completed_quests]
        
        # Format response
        quest_list = []
        for quest in available:
            quest_list.append({
                "quest_id": quest.quest_id,
                "name": quest.name,
                "rewards": {"exp": 1000, "zeny": 500},
                "estimated_duration_minutes": 15
            })
        
        logger.success(f"[QUEST] Found {len(quest_list)} available quests")
        
        return {
            "available_quests": quest_list,
            "count": len(quest_list)
        }
        
    except Exception as e:
        logger.error(f"[QUEST] Error: {e}")
        return {"available_quests": [], "count": 0, "error": str(e)}


@router.post("/api/v1/quests/recommend")
async def recommend_quest(request: Dict[str, Any]):
    """
    Recommend best quest based on current situation
    
    Used by Strategic Layer's quest_strategist agent
    """
    try:
        character = request.get("character", {})
        available_quest_ids = request.get("available_quests", [])
        
        # Prioritize job change quest for Novice
        if character.get("job_class") == "Novice" and character.get("level", 1) >= 10:
            for quest_id in available_quest_ids:
                if "job_change" in quest_id:
                    return {
                        "recommended_quest": quest_id,
                        "reasoning": "Job advancement is critical",
                        "priority": "critical"
                    }
        
        # Otherwise recommend first available
        if available_quest_ids:
            return {
                "recommended_quest": available_quest_ids[0],
                "reasoning": "Beneficial quest available",
                "priority": "medium"
            }
        
        return {
            "recommended_quest": None,
            "reasoning": "No quests available",
            "priority": "low"
        }
        
    except Exception as e:
        logger.error(f"[QUEST] Error: {e}")
        return {"recommended_quest": None, "reasoning": f"Error: {e}", "priority": "low"}
