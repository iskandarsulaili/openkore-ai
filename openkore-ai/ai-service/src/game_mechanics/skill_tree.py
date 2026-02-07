"""
Skill Tree System extracted from rathena-AI-world.

Source: external-references/rathena-AI-world/db/skill_tree.yml
Provides intelligent skill learning path recommendations for OpenKore AI.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
import yaml
from pathlib import Path


@dataclass
class SkillRequirement:
    """Prerequisite skill requirement."""
    skill_name: str
    level: int


@dataclass
class SkillInfo:
    """
    Complete skill information from rathena skill database.
    
    This is for AI decision-making about skill learning, not for
    simulating skill effects (that's server-side).
    """
    name: str
    skill_id: int
    max_level: int
    min_base_level: int = 0
    min_job_level: int = 0
    requires: List[SkillRequirement] = field(default_factory=list)
    description: str = ""
    skill_type: str = ""  # passive, offensive, supportive, etc.
    target_type: str = ""  # self, enemy, place, etc.
    
    def can_learn(self, current_skills: Dict[str, int], base_level: int, job_level: int) -> bool:
        """
        Check if this skill can be learned given current conditions.
        
        Args:
            current_skills: Dict of skill_name -> current_level
            base_level: Character base level
            job_level: Character job level
        
        Returns:
            True if all requirements are met
        """
        # Check level requirements
        if base_level < self.min_base_level:
            return False
        if job_level < self.min_job_level:
            return False
        
        # Check prerequisite skills
        if self.requires:
            for req in self.requires:
                current_level = current_skills.get(req.skill_name, 0)
                if current_level < req.level:
                    return False
        
        return True
    
    def get_next_level(self, current_skills: Dict[str, int]) -> int:
        """Get the next level that should be learned (0 if maxed)."""
        current = current_skills.get(self.name, 0)
        if current >= self.max_level:
            return 0
        return current + 1


class SkillTreeDatabase:
    """
    Complete skill tree database from rathena.
    
    Provides learning path optimization for OpenKore AI.
    This is purely for planning skill point allocation, not skill execution.
    """
    
    def __init__(self):
        self.trees: Dict[str, List[SkillInfo]] = {}
        self.skill_by_name: Dict[str, SkillInfo] = {}
        self.skill_by_id: Dict[int, SkillInfo] = {}
        self._load_skill_trees()
    
    def _load_skill_trees(self):
        """
        Load skill trees from rathena data.
        
        In production, this would parse:
        - external-references/rathena-AI-world/db/skill_tree.yml
        - external-references/rathena-AI-world/db/skill_db.yml
        """
        # For now, define essential skill trees manually
        # A complete implementation would parse the YAML files
        
        self._define_novice_tree()
        self._define_swordsman_tree()
        self._define_mage_tree()
        self._define_archer_tree()
        self._define_acolyte_tree()
        self._define_merchant_tree()
        self._define_thief_tree()
    
    def _add_skill(self, job: str, skill: SkillInfo):
        """Add skill to database."""
        if job not in self.trees:
            self.trees[job] = []
        self.trees[job].append(skill)
        self.skill_by_name[skill.name] = skill
        self.skill_by_id[skill.skill_id] = skill
    
    def _define_novice_tree(self):
        """Define Novice skill tree."""
        job = "novice"
        
        self._add_skill(job, SkillInfo(
            name="NV_BASIC",
            skill_id=1,
            max_level=9,
            description="Basic Skill",
            skill_type="passive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="NV_FIRSTAID",
            skill_id=142,
            max_level=1,
            min_base_level=10,
            description="First Aid",
            skill_type="supportive",
            target_type="self"
        ))
    
    def _define_swordsman_tree(self):
        """Define Swordsman/Knight skill tree."""
        job = "swordsman"
        
        # Swordsman skills
        self._add_skill(job, SkillInfo(
            name="SM_BASH",
            skill_id=5,
            max_level=10,
            description="Bash",
            skill_type="offensive",
            target_type="enemy"
        ))
        
        self._add_skill(job, SkillInfo(
            name="SM_PROVOKE",
            skill_id=6,
            max_level=10,
            description="Provoke",
            skill_type="offensive",
            target_type="enemy"
        ))
        
        self._add_skill(job, SkillInfo(
            name="SM_MAGNUM",
            skill_id=7,
            max_level=10,
            min_job_level=5,
            requires=[SkillRequirement("SM_BASH", 5)],
            description="Magnum Break",
            skill_type="offensive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="SM_ENDURE",
            skill_id=8,
            max_level=10,
            min_job_level=10,
            requires=[SkillRequirement("SM_PROVOKE", 5)],
            description="Endure",
            skill_type="supportive",
            target_type="self"
        ))
        
        # Knight skills
        self._add_skill(job, SkillInfo(
            name="KN_TWOHANDQUICKEN",
            skill_id=60,
            max_level=10,
            min_job_level=25,
            description="Two-Hand Quicken",
            skill_type="supportive",
            target_type="self"
        ))
        
        self._add_skill(job, SkillInfo(
            name="KN_AUTOCOUNTER",
            skill_id=61,
            max_level=5,
            description="Auto Counter",
            skill_type="passive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="KN_BOWLINGBASH",
            skill_id=62,
            max_level=10,
            requires=[SkillRequirement("SM_BASH", 10), SkillRequirement("SM_MAGNUM", 3)],
            description="Bowling Bash",
            skill_type="offensive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="KN_SPEARMASTERY",
            skill_id=63,
            max_level=10,
            description="Spear Mastery",
            skill_type="passive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="KN_SPEARSTAB",
            skill_id=64,
            max_level=10,
            requires=[SkillRequirement("KN_SPEARMASTERY", 1)],
            description="Spear Stab",
            skill_type="offensive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="KN_SPEARBOOMERANG",
            skill_id=65,
            max_level=5,
            requires=[SkillRequirement("KN_SPEARMASTERY", 3)],
            description="Spear Boomerang",
            skill_type="offensive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="KN_BRANDISHSPEAR",
            skill_id=57,
            max_level=10,
            min_job_level=30,
            requires=[SkillRequirement("KN_RIDING", 1), SkillRequirement("KN_SPEARMASTERY", 5)],
            description="Brandish Spear",
            skill_type="offensive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="KN_RIDING",
            skill_id=63,
            max_level=1,
            min_job_level=20,
            description="Riding",
            skill_type="passive"
        ))
    
    def _define_mage_tree(self):
        """Define Mage/Wizard skill tree."""
        job = "mage"
        
        self._add_skill(job, SkillInfo(
            name="MG_SRECOVERY",
            skill_id=9,
            max_level=10,
            description="Increase SP Recovery",
            skill_type="passive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="MG_COLDBOLT",
            skill_id=14,
            max_level=10,
            description="Cold Bolt",
            skill_type="offensive",
            target_type="enemy"
        ))
        
        self._add_skill(job, SkillInfo(
            name="MG_FIREBOLT",
            skill_id=19,
            max_level=10,
            description="Fire Bolt",
            skill_type="offensive",
            target_type="enemy"
        ))
        
        self._add_skill(job, SkillInfo(
            name="MG_LIGHTNINGBOLT",
            skill_id=20,
            max_level=10,
            description="Lightning Bolt",
            skill_type="offensive",
            target_type="enemy"
        ))
        
        self._add_skill(job, SkillInfo(
            name="WZ_FIREPILLAR",
            skill_id=80,
            max_level=10,
            requires=[SkillRequirement("MG_FIREBOLT", 5)],
            description="Fire Pillar",
            skill_type="offensive",
            target_type="place"
        ))
        
        self._add_skill(job, SkillInfo(
            name="WZ_METEOR",
            skill_id=83,
            max_level=10,
            requires=[SkillRequirement("WZ_FIREPILLAR", 5)],
            description="Meteor Storm",
            skill_type="offensive",
            target_type="place"
        ))
    
    def _define_archer_tree(self):
        """Define Archer skill tree."""
        job = "archer"
        
        self._add_skill(job, SkillInfo(
            name="AC_OWL",
            skill_id=45,
            max_level=10,
            description="Owl's Eye",
            skill_type="passive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="AC_VULTURE",
            skill_id=46,
            max_level=10,
            requires=[SkillRequirement("AC_OWL", 3)],
            description="Vulture's Eye",
            skill_type="passive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="AC_DOUBLE",
            skill_id=43,
            max_level=10,
            description="Double Strafe",
            skill_type="offensive",
            target_type="enemy"
        ))
    
    def _define_acolyte_tree(self):
        """Define Acolyte/Priest skill tree."""
        job = "acolyte"
        
        self._add_skill(job, SkillInfo(
            name="AL_HEAL",
            skill_id=28,
            max_level=10,
            description="Heal",
            skill_type="supportive",
            target_type="self_or_ally"
        ))
        
        self._add_skill(job, SkillInfo(
            name="AL_INCAGI",
            skill_id=29,
            max_level=10,
            description="Increase AGI",
            skill_type="supportive",
            target_type="self_or_ally"
        ))
        
        self._add_skill(job, SkillInfo(
            name="AL_BLESSING",
            skill_id=34,
            max_level=10,
            description="Blessing",
            skill_type="supportive",
            target_type="self_or_ally"
        ))
        
        self._add_skill(job, SkillInfo(
            name="AL_ANGELUS",
            skill_id=33,
            max_level=10,
            description="Angelus",
            skill_type="supportive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="PR_KYRIE",
            skill_id=73,
            max_level=10,
            min_job_level=25,
            requires=[SkillRequirement("AL_ANGELUS", 4)],
            description="Kyrie Eleison",
            skill_type="supportive",
            target_type="self_or_ally"
        ))
        
        self._add_skill(job, SkillInfo(
            name="PR_MAGNIFICAT",
            skill_id=74,
            max_level=5,
            description="Magnificat",
            skill_type="supportive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="PR_GLORIA",
            skill_id=75,
            max_level=5,
            description="Gloria",
            skill_type="supportive"
        ))
    
    def _define_merchant_tree(self):
        """Define Merchant/Blacksmith skill tree."""
        job = "merchant"
        
        self._add_skill(job, SkillInfo(
            name="MC_DISCOUNT",
            skill_id=38,
            max_level=10,
            description="Discount",
            skill_type="passive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="MC_OVERCHARGE",
            skill_id=39,
            max_level=10,
            requires=[SkillRequirement("MC_DISCOUNT", 3)],
            description="Overcharge",
            skill_type="passive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="MC_PUSHCART",
            skill_id=39,
            max_level=10,
            description="Pushcart",
            skill_type="passive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="MC_MAMMONITE",
            skill_id=42,
            max_level=10,
            description="Mammonite",
            skill_type="offensive",
            target_type="enemy"
        ))
        
        self._add_skill(job, SkillInfo(
            name="BS_IRON",
            skill_id=108,
            max_level=5,
            description="Iron Hand",
            skill_type="passive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="BS_OVERTHRUST",
            skill_id=114,
            max_level=5,
            description="Overthrust",
            skill_type="supportive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="BS_ADRENALINE",
            skill_id=111,
            max_level=5,
            description="Adrenaline Rush",
            skill_type="supportive"
        ))
    
    def _define_thief_tree(self):
        """Define Thief/Assassin skill tree."""
        job = "thief"
        
        self._add_skill(job, SkillInfo(
            name="TF_DOUBLE",
            skill_id=48,
            max_level=10,
            description="Double Attack",
            skill_type="passive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="TF_MISS",
            skill_id=49,
            max_level=10,
            description="Improve Dodge",
            skill_type="passive"
        ))
        
        self._add_skill(job, SkillInfo(
            name="TF_HIDING",
            skill_id=51,
            max_level=10,
            description="Hiding",
            skill_type="supportive",
            target_type="self"
        ))
        
        self._add_skill(job, SkillInfo(
            name="AS_CLOAKING",
            skill_id=135,
            max_level=10,
            requires=[SkillRequirement("TF_HIDING", 2)],
            description="Cloaking",
            skill_type="supportive",
            target_type="self"
        ))
        
        self._add_skill(job, SkillInfo(
            name="AS_ENCHANTPOISON",
            skill_id=138,
            max_level=10,
            description="Enchant Poison",
            skill_type="supportive",
            target_type="self"
        ))
        
        self._add_skill(job, SkillInfo(
            name="ASC_EDP",
            skill_id=378,
            max_level=5,
            min_job_level=40,
            requires=[SkillRequirement("AS_ENCHANTPOISON", 5)],
            description="Enchant Deadly Poison",
            skill_type="supportive",
            target_type="self"
        ))
    
    def get_skill_tree(self, job: str) -> List[SkillInfo]:
        """Get complete skill tree for a job."""
        return self.trees.get(job.lower(), [])
    
    def get_skill_by_name(self, skill_name: str) -> Optional[SkillInfo]:
        """Get skill info by name."""
        return self.skill_by_name.get(skill_name)
    
    def get_skill_by_id(self, skill_id: int) -> Optional[SkillInfo]:
        """Get skill info by ID."""
        return self.skill_by_id.get(skill_id)
    
    def get_next_skill(self, job: str, current_skills: Dict[str, int], 
                      base_level: int, job_level: int) -> Optional[SkillInfo]:
        """
        Get the next skill that should be learned.
        
        Args:
            job: Job class name
            current_skills: Dict of skill_name -> current_level
            base_level: Character base level
            job_level: Character job level
        
        Returns:
            SkillInfo for next skill to learn, or None if tree is complete
        """
        skill_tree = self.get_skill_tree(job)
        
        for skill in skill_tree:
            current_level = current_skills.get(skill.name, 0)
            
            # If not maxed and can learn next level
            if current_level < skill.max_level:
                if skill.can_learn(current_skills, base_level, job_level):
                    return skill
        
        return None
    
    def get_skill_path(self, job: str, target_skill: str) -> List[str]:
        """
        Get the learning path to reach a target skill.
        
        Args:
            job: Job class
            target_skill: Name of skill to learn
        
        Returns:
            Ordered list of skill names to learn
        """
        skill_tree = self.get_skill_tree(job)
        path = []
        visited = set()
        
        # Find target skill
        target = None
        for skill in skill_tree:
            if skill.name == target_skill:
                target = skill
                break
        
        if not target:
            return path
        
        def add_prerequisites(skill_info: SkillInfo):
            """Recursively add prerequisites."""
            if skill_info.name in visited:
                return
            
            visited.add(skill_info.name)
            
            if skill_info.requires:
                for req in skill_info.requires:
                    prereq_skill = self.get_skill_by_name(req.skill_name)
                    if prereq_skill:
                        add_prerequisites(prereq_skill)
                        if prereq_skill.name not in path:
                            path.append(prereq_skill.name)
        
        add_prerequisites(target)
        path.append(target_skill)
        
        return path
    
    def calculate_skill_points_needed(self, job: str, target_skills: Dict[str, int]) -> int:
        """
        Calculate total skill points needed to reach target skill levels.
        
        Args:
            job: Job class
            target_skills: Dict of skill_name -> target_level
        
        Returns:
            Total skill points needed
        """
        total_points = 0
        counted = set()
        
        for skill_name, target_level in target_skills.items():
            skill = self.get_skill_by_name(skill_name)
            if not skill or skill_name in counted:
                continue
            
            counted.add(skill_name)
            
            # Add points for this skill
            total_points += min(target_level, skill.max_level)
            
            # Add points for prerequisites
            path = self.get_skill_path(job, skill_name)
            for prereq_name in path[:-1]:  # Exclude target itself
                if prereq_name not in counted:
                    prereq_skill = self.get_skill_by_name(prereq_name)
                    if prereq_skill:
                        counted.add(prereq_name)
                        # Find required level from dependencies
                        for req in skill.requires:
                            if req.skill_name == prereq_name:
                                total_points += req.level
                                break
        
        return total_points
