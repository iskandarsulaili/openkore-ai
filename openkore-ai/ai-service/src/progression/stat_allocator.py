"""
Autonomous Stat Allocation System
Integrates with existing raiseStat.pl plugin
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger


class StatAllocator:
    """
    Autonomous stat allocation based on job build and performance metrics.
    Generates config for raiseStat.pl plugin dynamically.
    """
    
    def __init__(self, user_intent_path: str, job_builds_path: str):
        """Initialize with user intent and job build definitions"""
        self.user_intent_path = Path(user_intent_path)
        self.job_builds_path = Path(job_builds_path)
        
        self.user_intent = self._load_user_intent()
        self.job_builds = self._load_job_builds()
        
        # Performance tracking for adaptive allocation
        self.death_count = 0
        self.avg_kill_time = 0.0
        self.adaptive_adjustments = {}
        
        logger.info(f"StatAllocator initialized for build: {self.user_intent.get('build', 'unknown')}")
    
    def _load_user_intent(self) -> Dict[str, Any]:
        """Load user intent from JSON"""
        if not self.user_intent_path.exists():
            logger.warning(f"User intent file not found: {self.user_intent_path}")
            return {}
        
        with open(self.user_intent_path, 'r') as f:
            return json.load(f)
    
    def _load_job_builds(self) -> Dict[str, Any]:
        """Load job build definitions"""
        if not self.job_builds_path.exists():
            logger.error(f"Job builds file not found: {self.job_builds_path}")
            return {}
        
        with open(self.job_builds_path, 'r') as f:
            return json.load(f)
    
    def get_current_build_config(self) -> Optional[Dict[str, Any]]:
        """Get current job build configuration"""
        current_job = self.user_intent.get('current_job', 'novice').lower()
        build_type = self.user_intent.get('build', 'default')
        
        # Navigate job_builds structure
        job_data = self.job_builds.get(current_job, {})
        build_config = job_data.get(build_type, {})
        
        if not build_config:
            logger.warning(f"No build config found for {current_job}/{build_type}")
            return None
        
        return build_config
    
    def on_level_up(self, current_level: int, current_stats: Dict[str, int]) -> Dict[str, Any]:
        """
        Called when character levels up.
        Returns stat allocation plan and config for raiseStat.pl
        """
        build_config = self.get_current_build_config()
        if not build_config:
            return {"error": "No build configuration found"}
        
        # Get stat targets
        stat_targets = build_config.get('stat_targets', {})
        
        # Apply adaptive adjustments
        adjusted_targets = self._apply_adaptive_adjustments(stat_targets)
        
        # Generate statsAddAuto_list for raiseStat.pl
        stats_list = self._generate_stats_list(current_stats, adjusted_targets)
        
        logger.info(f"Level {current_level} - Generated stat plan: {stats_list}")
        
        return {
            "level": current_level,
            "stat_plan": stats_list,
            "config": {
                "statsAddAuto": 1,
                "statsAddAuto_list": stats_list,
                "statsAdd_over_99": 0
            },
            "explanation": self._explain_allocation(build_config, current_stats, adjusted_targets)
        }
    
    def _generate_stats_list(self, current_stats: Dict[str, int], targets: Dict[str, int]) -> str:
        """
        Generate comma-separated stat list for raiseStat.pl
        Format: "str 80, agi 70, vit 50, dex 40, int 10, luk 10"
        """
        stat_order = ['str', 'agi', 'vit', 'dex', 'int', 'luk']
        
        stat_parts = []
        for stat in stat_order:
            target_value = targets.get(stat, current_stats.get(stat, 1))
            current_value = current_stats.get(stat, 1)
            
            # Only add if target is higher than current
            if target_value > current_value:
                stat_parts.append(f"{stat} {target_value}")
        
        return ", ".join(stat_parts)
    
    def _apply_adaptive_adjustments(self, base_targets: Dict[str, int]) -> Dict[str, int]:
        """
        Apply adaptive adjustments based on performance.
        E.g., if dying often, increase VIT.
        """
        adjusted = base_targets.copy()
        
        # If dying too much (>5 deaths per session), prioritize VIT
        if self.death_count > 5:
            vit_boost = min(10, self.death_count)
            adjusted['vit'] = min(99, adjusted.get('vit', 1) + vit_boost)
            logger.info(f"Adaptive: Boosting VIT by {vit_boost} due to {self.death_count} deaths")
        
        # If kill time is too slow (>10 seconds avg), boost damage stats
        if self.avg_kill_time > 10.0:
            build_config = self.get_current_build_config()
            if build_config:
                primary_stat = build_config.get('stat_priority', ['str'])[0].lower()
                stat_boost = 5
                adjusted[primary_stat] = min(99, adjusted.get(primary_stat, 1) + stat_boost)
                logger.info(f"Adaptive: Boosting {primary_stat.upper()} by {stat_boost} due to slow kills")
        
        return adjusted
    
    def _explain_allocation(self, build_config: Dict, current: Dict, targets: Dict) -> str:
        """Generate human-readable explanation"""
        build_name = build_config.get('name', 'Unknown Build')
        allocation_pattern = build_config.get('stat_allocation_pattern', 'Adaptive')
        
        explanation = f"Build: {build_name}\n"
        explanation += f"Pattern: {allocation_pattern}\n"
        explanation += f"Targets: "
        
        target_parts = [f"{k.upper()}: {v}" for k, v in targets.items() if v > current.get(k, 1)]
        explanation += ", ".join(target_parts)
        
        return explanation
    
    def adjust_for_performance(self, death_count: int, avg_kill_time: float):
        """
        Update performance metrics for adaptive allocation.
        Called periodically by monitoring system.
        """
        self.death_count = death_count
        self.avg_kill_time = avg_kill_time
        
        logger.info(f"Performance update: {death_count} deaths, {avg_kill_time:.2f}s avg kill time")
    
    def get_stat_priority_for_job(self, job: str, build: str) -> List[str]:
        """Get stat priority list for a specific job/build"""
        job_data = self.job_builds.get(job.lower(), {})
        build_config = job_data.get(build, {})
        
        return build_config.get('stat_priority', ['str', 'agi', 'vit', 'dex', 'int', 'luk'])
    
    def get_allocation_recommendations(self, current_stats: Dict[str, int], free_points: int) -> Dict[str, int]:
        """
        Get immediate stat allocation recommendations for available free points.
        Returns: Dict of {stat: points_to_add}
        """
        build_config = self.get_current_build_config()
        if not build_config:
            return {}
        
        stat_targets = build_config.get('stat_targets', {})
        stat_priority = build_config.get('stat_priority', [])
        
        recommendations = {}
        remaining_points = free_points
        
        # Allocate according to priority
        for stat in stat_priority:
            stat_lower = stat.lower()
            current = current_stats.get(stat_lower, 1)
            target = stat_targets.get(stat_lower, 1)
            
            if current < target and remaining_points > 0:
                points_needed = target - current
                points_to_add = min(points_needed, remaining_points)
                
                recommendations[stat_lower] = points_to_add
                remaining_points -= points_to_add
                
                if remaining_points <= 0:
                    break
        
        return recommendations
    
    def export_config_file(self, output_path: str) -> bool:
        """
        Export configuration to OpenKore config format.
        Updates config.txt with statsAddAuto settings.
        """
        try:
            build_config = self.get_current_build_config()
            if not build_config:
                return False
            
            stat_targets = build_config.get('stat_targets', {})
            stats_list = self._generate_stats_list({}, stat_targets)
            
            config_lines = [
                f"# Auto-generated stat allocation for {build_config.get('name', 'Unknown')}",
                f"statsAddAuto 1",
                f"statsAddAuto_list {stats_list}",
                f"statsAdd_over_99 0",
                f"statsAddAuto_dontUseBonus 0",
                f""
            ]
            
            # Append or update config file
            output_path_obj = Path(output_path)
            
            # Read existing config if it exists
            existing_lines = []
            if output_path_obj.exists():
                with open(output_path_obj, 'r', encoding='utf-8') as f:
                    existing_lines = f.readlines()
                
                # Remove old statsAdd* lines
                existing_lines = [line for line in existing_lines 
                                  if not line.strip().startswith('statsAddAuto')]
            
            # Write back with new config
            with open(output_path_obj, 'w', encoding='utf-8') as f:
                f.writelines(existing_lines)
                f.write('\n'.join(config_lines))
            
            logger.success(f"Exported stat config to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export config: {e}")
            return False
