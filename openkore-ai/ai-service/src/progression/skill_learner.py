"""
Autonomous Skill Learning System
Integrates with existing raiseSkill.pl plugin
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger


class SkillLearner:
    """
    Autonomous skill learning based on job build and combat performance.
    Generates config for raiseSkill.pl plugin dynamically.
    """
    
    def __init__(self, user_intent_path: str, job_builds_path: str):
        """Initialize with user intent and job build definitions"""
        self.user_intent_path = Path(user_intent_path)
        self.job_builds_path = Path(job_builds_path)
        
        self.user_intent = self._load_user_intent()
        self.job_builds = self._load_job_builds()
        
        # Performance tracking for adaptive skill selection
        self.combat_stats = {
            'total_kills': 0,
            'deaths': 0,
            'avg_damage_taken': 0.0,
            'avg_kill_time': 0.0,
            'sp_efficiency': 1.0
        }
        
        logger.info(f"SkillLearner initialized for build: {self.user_intent.get('build', 'unknown')}")
    
    def _load_user_intent(self) -> Dict[str, Any]:
        """Load user intent from JSON"""
        if not self.user_intent_path.exists():
            logger.warning(f"User intent file not found: {self.user_intent_path}")
            return {}
        
        with open(self.user_intent_path, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    
    def _load_job_builds(self) -> Dict[str, Any]:
        """Load job build definitions"""
        if not self.job_builds_path.exists():
            logger.error(f"Job builds file not found: {self.job_builds_path}")
            return {}
        
        with open(self.job_builds_path, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    
    def get_current_build_config(self) -> Optional[Dict[str, Any]]:
        """Get current job build configuration"""
        current_job = self.user_intent.get('current_job', 'novice').lower()
        build_type = self.user_intent.get('build', 'default')
        
        job_data = self.job_builds.get(current_job, {})
        build_config = job_data.get(build_type, {})
        
        if not build_config:
            logger.warning(f"No build config found for {current_job}/{build_type}")
            return None
        
        return build_config
    
    def on_job_level_up(self, current_job_level: int, job: str, current_skills: Dict[str, int]) -> Dict[str, Any]:
        """
        Called when job level increases and skill points are available.
        Returns skill learning plan and config for raiseSkill.pl
        """
        build_config = self.get_current_build_config()
        if not build_config:
            return {"error": "No build configuration found"}
        
        # Get skill priority list
        skills_priority = build_config.get('skills_priority', [])
        
        # Apply adaptive adjustments
        adjusted_priority = self._apply_adaptive_skill_selection(skills_priority)
        
        # Generate skillsAddAuto_list for raiseSkill.pl
        skills_list = self._generate_skills_list(current_skills, adjusted_priority)
        
        logger.info(f"Job Level {current_job_level} - Generated skill plan: {skills_list}")
        
        return {
            "job_level": current_job_level,
            "skill_plan": skills_list,
            "config": {
                "skillsAddAuto": 1,
                "skillsAddAuto_list": skills_list
            },
            "explanation": self._explain_skill_selection(build_config, adjusted_priority),
            "next_skills": self._get_next_skills_to_learn(current_skills, adjusted_priority, count=3)
        }
    
    def _generate_skills_list(self, current_skills: Dict[str, int], priority_list: List[Dict]) -> str:
        """
        Generate comma-separated skill list for raiseSkill.pl
        Format: "NV_BASIC 9, SM_BASH 10, SM_SWORD 10, SM_PROVOKE 10"
        """
        skill_parts = []
        
        for skill_info in priority_list:
            skill_name = skill_info.get('name', '')
            max_level = skill_info.get('level', 10)
            current_level = current_skills.get(skill_name, 0)
            
            # Only add if we need to level it up
            if current_level < max_level:
                skill_parts.append(f"{skill_name} {max_level}")
        
        return ", ".join(skill_parts) if skill_parts else ""
    
    def _apply_adaptive_skill_selection(self, base_priority: List[Dict]) -> List[Dict]:
        """
        Apply adaptive adjustments to skill priority based on combat performance.
        E.g., if dying often, prioritize defensive/survival skills.
        """
        adjusted = base_priority.copy()
        
        # If high death rate, prioritize survival skills
        if self.combat_stats['deaths'] > 5:
            survival_skills = ['SM_RECOVERY', 'SM_ENDURE', 'AL_HEAL', 'TF_HIDING', 
                             'MG_SRECOVERY', 'AL_DP', 'MC_INCCARRY']
            
            # Boost priority of survival skills
            for i, skill_info in enumerate(adjusted):
                skill_name = skill_info.get('name', '')
                if any(surv in skill_name for surv in survival_skills):
                    # Move survival skill earlier in priority
                    if i > 0:
                        adjusted[i]['priority'] = max(1, adjusted[i].get('priority', 99) - 2)
            
            # Re-sort by priority
            adjusted.sort(key=lambda x: x.get('priority', 99))
            
            logger.info(f"Adaptive: Prioritizing survival skills due to {self.combat_stats['deaths']} deaths")
        
        # If low SP efficiency, deprioritize expensive skills
        if self.combat_stats['sp_efficiency'] < 0.5:
            logger.info("Adaptive: Deprioritizing SP-intensive skills due to low SP efficiency")
            # This would require SP cost data, implementing basic logic
        
        return adjusted
    
    def _explain_skill_selection(self, build_config: Dict, priority_list: List[Dict]) -> str:
        """Generate human-readable explanation of skill selection"""
        build_name = build_config.get('name', 'Unknown Build')
        
        explanation = f"Build: {build_name}\n"
        explanation += "Skill Learning Order:\n"
        
        for i, skill_info in enumerate(priority_list[:5], 1):  # Top 5
            skill_name = skill_info.get('name', 'Unknown')
            skill_level = skill_info.get('level', 10)
            description = skill_info.get('description', '')
            
            explanation += f"  {i}. {skill_name} (Level {skill_level}) - {description}\n"
        
        return explanation
    
    def _get_next_skills_to_learn(self, current_skills: Dict[str, int], 
                                  priority_list: List[Dict], count: int = 3) -> List[Dict]:
        """Get the next N skills that should be learned"""
        next_skills = []
        
        for skill_info in priority_list:
            if len(next_skills) >= count:
                break
            
            skill_name = skill_info.get('name', '')
            max_level = skill_info.get('level', 10)
            current_level = current_skills.get(skill_name, 0)
            
            if current_level < max_level:
                next_skills.append({
                    'name': skill_name,
                    'current_level': current_level,
                    'target_level': max_level,
                    'description': skill_info.get('description', ''),
                    'priority': skill_info.get('priority', 99)
                })
        
        return next_skills
    
    def should_learn_skill(self, skill_name: str, combat_stats: Dict[str, float]) -> Tuple[bool, str]:
        """
        Determine if a skill should be learned based on current performance.
        Returns: (should_learn, reason)
        """
        build_config = self.get_current_build_config()
        if not build_config:
            return False, "No build configuration"
        
        skills_priority = build_config.get('skills_priority', [])
        
        # Check if skill is in our build
        skill_in_build = any(s.get('name') == skill_name for s in skills_priority)
        if not skill_in_build:
            return False, "Skill not in current build"
        
        # Find skill info
        skill_info = next((s for s in skills_priority if s.get('name') == skill_name), None)
        if not skill_info:
            return False, "Skill info not found"
        
        # Check priority and combat stats
        priority = skill_info.get('priority', 99)
        
        # High priority skills should always be learned
        if priority <= 2:
            return True, "Essential skill for build"
        
        # Adaptive checks based on combat performance
        if 'RECOVERY' in skill_name or 'HEAL' in skill_name:
            if combat_stats.get('deaths', 0) > 3:
                return True, "Survival skill needed due to high death rate"
        
        if 'BASH' in skill_name or 'BOLT' in skill_name or 'DOUBLE' in skill_name:
            if combat_stats.get('avg_kill_time', 0) > 8.0:
                return True, "Damage skill needed to improve kill speed"
        
        # Default: learn if it's in priority list
        return True, f"Priority {priority} skill in build"
    
    def update_combat_stats(self, stats: Dict[str, Any]):
        """Update combat statistics for adaptive learning"""
        self.combat_stats.update(stats)
        logger.info(f"Combat stats updated: {self.combat_stats}")
    
    def get_skill_priority_for_job(self, job: str, build: str) -> List[Dict]:
        """Get skill priority list for a specific job/build"""
        job_data = self.job_builds.get(job.lower(), {})
        build_config = job_data.get(build, {})
        
        return build_config.get('skills_priority', [])
    
    def export_config_file(self, output_path: str) -> bool:
        """
        Export configuration to OpenKore config format.
        Updates config.txt with skillsAddAuto settings.
        """
        try:
            build_config = self.get_current_build_config()
            if not build_config:
                return False
            
            skills_priority = build_config.get('skills_priority', [])
            skills_list = self._generate_skills_list({}, skills_priority)
            
            if not skills_list:
                logger.warning("No skills to configure")
                return False
            
            config_lines = [
                f"# Auto-generated skill learning for {build_config.get('name', 'Unknown')}",
                f"skillsAddAuto 1",
                f"skillsAddAuto_list {skills_list}",
                f""
            ]
            
            # Append or update config file
            output_path_obj = Path(output_path)
            
            # Read existing config if it exists
            existing_lines = []
            if output_path_obj.exists():
                with open(output_path_obj, 'r', encoding='utf-8') as f:
                    existing_lines = f.readlines()
                
                # Remove old skillsAdd* lines
                existing_lines = [line for line in existing_lines 
                                  if not line.strip().startswith('skillsAddAuto')]
            
            # Write back with new config
            with open(output_path_obj, 'w', encoding='utf-8') as f:
                f.writelines(existing_lines)
                f.write('\n'.join(config_lines))
            
            logger.success(f"Exported skill config to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export config: {e}")
            return False
    
    def get_skill_learning_plan(self, current_job_level: int, available_points: int) -> Dict[str, Any]:
        """
        Generate a complete skill learning plan given available skill points.
        Returns detailed plan with point allocation.
        """
        build_config = self.get_current_build_config()
        if not build_config:
            return {"error": "No build configuration"}
        
        skills_priority = build_config.get('skills_priority', [])
        
        plan = {
            'total_points_available': available_points,
            'skills_to_learn': [],
            'points_remaining': available_points
        }
        
        points_used = 0
        
        for skill_info in skills_priority:
            if points_used >= available_points:
                break
            
            skill_name = skill_info.get('name', '')
            max_level = skill_info.get('level', 10)
            points_needed = max_level  # Simplified: assuming 1 point per level
            
            if points_used + points_needed <= available_points:
                plan['skills_to_learn'].append({
                    'skill': skill_name,
                    'level': max_level,
                    'points': points_needed,
                    'description': skill_info.get('description', '')
                })
                points_used += points_needed
        
        plan['points_remaining'] = available_points - points_used
        plan['points_used'] = points_used
        
        return plan
