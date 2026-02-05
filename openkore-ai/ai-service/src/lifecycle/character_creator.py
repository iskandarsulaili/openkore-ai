"""
Character Creation Automation
Automatically creates characters with optimal job paths
"""

from typing import Dict, Any, List
from loguru import logger

class JobPath:
    """Predefined job progression paths"""
    
    PATHS = {
        "swordsman_knight": {
            "novice": "Novice",
            "first_job": "Swordsman",
            "second_job": "Knight",
            "stats_priority": ["STR", "VIT", "AGI", "DEX"],
            "recommended_skills": ["Bash", "Magnum Break", "Provoke"],
            "farming_maps": ["prt_fild08", "mjolnir_05", "clock_01"]
        },
        "mage_wizard": {
            "novice": "Novice",
            "first_job": "Magician",
            "second_job": "Wizard",
            "stats_priority": ["INT", "DEX", "VIT"],
            "recommended_skills": ["Fire Bolt", "Cold Bolt", "Lightning Bolt", "Fire Wall"],
            "farming_maps": ["gef_fild07", "moc_fild03", "clock_02"]
        },
        "archer_hunter": {
            "novice": "Novice",
            "first_job": "Archer",
            "second_job": "Hunter",
            "stats_priority": ["DEX", "AGI", "INT"],
            "recommended_skills": ["Double Strafe", "Charge Arrow", "Ankle Snare"],
            "farming_maps": ["pay_fild08", "mjolnir_03", "yuno_fild03"]
        },
        "acolyte_priest": {
            "novice": "Novice",
            "first_job": "Acolyte",
            "second_job": "Priest",
            "stats_priority": ["INT", "VIT", "DEX"],
            "recommended_skills": ["Heal", "Blessing", "Increase AGI", "Resurrect"],
            "farming_maps": ["prt_fild03", "pay_fild03", "moc_fild02"]
        },
        "merchant_blacksmith": {
            "novice": "Novice",
            "first_job": "Merchant",
            "second_job": "Blacksmith",
            "stats_priority": ["STR", "DEX", "VIT", "AGI"],
            "recommended_skills": ["Mammonite", "Cart Revolution", "Discount"],
            "farming_maps": ["prt_fild05", "ein_fild08", "ve_fild01"]
        },
        "thief_assassin": {
            "novice": "Novice",
            "first_job": "Thief",
            "second_job": "Assassin",
            "stats_priority": ["AGI", "STR", "DEX"],
            "recommended_skills": ["Sonic Blow", "Cloaking", "Poison"],
            "farming_maps": ["moc_fild17", "alde_dun03", "gl_sew04"]
        }
    }
    
    @staticmethod
    def get_random_path() -> Dict[str, Any]:
        """Get a random job path for variety"""
        import random
        path_name = random.choice(list(JobPath.PATHS.keys()))
        return {"name": path_name, **JobPath.PATHS[path_name]}
        
    @staticmethod
    def get_optimal_path_for_style(playstyle: str) -> Dict[str, Any]:
        """Get job path based on playstyle preference"""
        style_map = {
            "solo_melee": "swordsman_knight",
            "solo_magic": "mage_wizard",
            "solo_ranged": "archer_hunter",
            "support": "acolyte_priest",
            "economy": "merchant_blacksmith",
            "stealth": "thief_assassin"
        }
        path_name = style_map.get(playstyle, "swordsman_knight")
        return {"name": path_name, **JobPath.PATHS[path_name]}

class CharacterCreator:
    """Handles autonomous character creation"""
    
    def __init__(self):
        self.job_paths = JobPath.PATHS
        logger.info("Character Creator initialized with 6 job paths")
        
    async def select_job_path(self, preference: str = "random") -> Dict[str, Any]:
        """Select job path for new character"""
        if preference == "random":
            path = JobPath.get_random_path()
        else:
            path = JobPath.get_optimal_path_for_style(preference)
            
        logger.info(f"Selected job path: {path['name']}")
        return path
        
    async def generate_character_plan(self, job_path: Dict[str, Any]) -> Dict[str, Any]:
        """Generate complete leveling and equipment plan"""
        return {
            "job_path": job_path,
            "level_milestones": [
                {"level": 10, "goal": "First job change", "location": "job_change_npc"},
                {"level": 25, "goal": "Basic equipment", "zeny_target": 50000},
                {"level": 40, "goal": "Advanced skills", "skill_points_reserve": 10},
                {"level": 50, "goal": "Second job change", "location": "job_change_npc"},
                {"level": 75, "goal": "High-tier equipment", "zeny_target": 500000},
                {"level": 99, "goal": "Endgame preparation", "zeny_target": 5000000}
            ],
            "stats_per_level": self._calculate_stat_distribution(job_path),
            "skill_progression": self._generate_skill_tree(job_path)
        }
        
    def _calculate_stat_distribution(self, job_path: Dict[str, Any]) -> List[str]:
        """Calculate which stat to raise each level"""
        priority = job_path['stats_priority']
        # Distribute stats with 60% to primary, 25% to secondary, 15% to tertiary
        distribution = []
        for i in range(99):  # 99 stat points total
            if i % 5 == 0 and len(priority) > 1:
                distribution.append(priority[1])  # Secondary
            elif i % 7 == 0 and len(priority) > 2:
                distribution.append(priority[2])  # Tertiary
            else:
                distribution.append(priority[0])  # Primary
        return distribution
        
    def _generate_skill_tree(self, job_path: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate skill learning progression"""
        skills = job_path['recommended_skills']
        progression = []
        
        # Spread skills across levels 10-50 for first job
        skill_levels = [10, 15, 20, 25, 30, 35, 40, 45, 50]
        for i, skill in enumerate(skills[:len(skill_levels)]):
            progression.append({
                "level": skill_levels[i],
                "skill": skill,
                "target_level": 10 if i == 0 else 5
            })
            
        return progression

character_creator = CharacterCreator()
