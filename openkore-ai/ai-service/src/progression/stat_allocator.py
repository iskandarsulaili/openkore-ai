"""
Autonomous Stat Allocation System with Playstyle-Based Ratios
Integrates with existing raiseStat.pl plugin
Version 3.0 - Extended support for ALL 55 build variants across 11 job paths
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger
import threading


class StatAllocator:
    """
    Autonomous stat allocation based on playstyle ratios and performance metrics.
    Supports dynamic adjustment and all job/build/playstyle combinations.
    Thread-safe with mutex locks to prevent race conditions.
    
    Version 3.0 Changes:
    - Integrated with job_build_variants.json (55 build variants)
    - Support for all 11 job paths including extended classes
    - Enhanced build config lookup with job_path support
    """
    
    def __init__(self, user_intent_path: str, job_builds_path: str = None, playstyles_path: str = None):
        """
        Initialize with user intent, job builds, and playstyles
        
        Args:
            user_intent_path: Path to user intent configuration
            job_builds_path: Path to job builds (defaults to job_build_variants.json)
            playstyles_path: Path to playstyles configuration
        """
        self.user_intent_path = Path(user_intent_path)
        
        # Default to job_build_variants.json if not specified
        if job_builds_path:
            self.job_builds_path = Path(job_builds_path)
        else:
            self.job_builds_path = Path(user_intent_path).parent / "job_build_variants.json"
        
        self.playstyles_path = Path(playstyles_path) if playstyles_path else \
            Path(user_intent_path).parent / "playstyles.json"
        
        # Thread safety
        self._lock = threading.RLock()
        self._allocation_in_progress = False
        
        # Load configurations
        self.user_intent = self._load_user_intent()
        self.job_builds = self._load_job_builds()
        self.playstyles = self._load_playstyles()
        
        # Performance tracking for adaptive allocation
        self.death_count = 0
        self.avg_kill_time = 0.0
        self.hit_rate = 1.0
        self.sp_depletion_rate = 0.0
        self.adaptive_adjustments = {}
        
        logger.info(f"StatAllocator v2.0 initialized for job: {self.user_intent.get('current_job', 'unknown')}, "
                   f"build: {self.user_intent.get('build', 'unknown')}, "
                   f"playstyle: {self.user_intent.get('playstyle', 'balanced')}")
    
    def _load_user_intent(self) -> Dict[str, Any]:
        """Load user intent from JSON"""
        with self._lock:
            if not self.user_intent_path.exists():
                logger.warning(f"User intent file not found: {self.user_intent_path}")
                return {"current_job": "novice", "build": "default", "playstyle": "balanced"}
            
            with open(self.user_intent_path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
    
    def _load_job_builds(self) -> Dict[str, Any]:
        """Load job build definitions"""
        with self._lock:
            if not self.job_builds_path.exists():
                logger.error(f"Job builds file not found: {self.job_builds_path}")
                return {}
            
            with open(self.job_builds_path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
    
    def _load_playstyles(self) -> Dict[str, Any]:
        """Load playstyle definitions with ratios"""
        with self._lock:
            if not self.playstyles_path.exists():
                logger.warning(f"Playstyles file not found: {self.playstyles_path}, using defaults")
                return {"playstyles": {}, "job_playstyle_mapping": {}}
            
            with open(self.playstyles_path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
    
    def get_current_build_config(self) -> Optional[Dict[str, Any]]:
        """
        Get current job build configuration with fallback logic.
        Version 3.0: Enhanced to support job_path lookup in job_build_variants.json
        
        Lookup Strategy:
        1. Check if job_builds has 'build_variants' structure (new format)
        2. If so, lookup by job_path identifier (e.g., 'swordman_knight_rune_knight')
        3. Then lookup build within that path
        4. Fallback to legacy lookup by current_job
        """
        with self._lock:
            current_job = self.user_intent.get('current_job', 'novice').lower()
            build_type = self.user_intent.get('build', 'balanced')
            job_path = self.user_intent.get('job_path', '')
            
            # Strategy 1: New format - lookup by job_path in build_variants
            build_variants = self.job_builds.get('build_variants', {})
            if build_variants and job_path:
                path_data = build_variants.get(job_path, {})
                if path_data:
                    builds = path_data.get('builds', {})
                    build_config = builds.get(build_type, {})
                    
                    if build_config:
                        logger.debug(f"Found build config (new format): {job_path}/{build_type}")
                        return build_config
                    
                    # Try balanced as fallback within this path
                    balanced_config = builds.get('balanced', {})
                    if balanced_config:
                        logger.warning(f"Using balanced build for {job_path} (requested: {build_type})")
                        return balanced_config
            
            # Strategy 2: Legacy format - lookup by current_job
            job_data = self.job_builds.get(current_job, {})
            build_config = job_data.get(build_type, {})
            
            if build_config:
                logger.debug(f"Found build config (legacy format): {current_job}/{build_type}")
                return build_config
            
            # Strategy 3: If build_type suggests future job (e.g., dex_hunter for novice)
            # Look for the target job in job_path
            if not build_config and 'job_path' in self.user_intent:
                job_path_list = self.user_intent.get('job_path', [])
                for target_job in job_path_list:
                    target_job_lower = target_job.lower()
                    if target_job_lower == current_job:
                        continue
                    
                    target_job_data = self.job_builds.get(target_job_lower, {})
                    build_config = target_job_data.get(build_type, {})
                    
                    if build_config:
                        logger.info(f"Found future job build: {target_job_lower}/{build_type} "
                                   f"(current job: {current_job})")
                        return build_config
            
            # Strategy 4: Try balanced/default build for current job
            default_config = job_data.get('balanced', {}) or job_data.get('default', {})
            if default_config:
                logger.warning(f"Using balanced/default build for {current_job} (requested: {build_type})")
                return default_config
            
            # Strategy 5: Fallback to first available build in job_path (new format)
            if build_variants and job_path:
                path_data = build_variants.get(job_path, {})
                builds = path_data.get('builds', {})
                if builds:
                    first_build = next(iter(builds.values()), None)
                    if first_build:
                        logger.warning(f"Fallback to first build in {job_path}")
                        return first_build
            
            logger.error(f"No build config found anywhere for {current_job}/{build_type} (job_path: {job_path})")
            return None
    
    def calculate_stat_distribution_from_ratios(self, 
                                                 total_points: int, 
                                                 current_stats: Dict[str, int]) -> Dict[str, int]:
        """
        Calculate stat distribution using playstyle ratios dynamically.
        This is the CORE of the ratio-based system.
        """
        with self._lock:
            playstyle = self.user_intent.get('playstyle', 'balanced')
            current_job = self.user_intent.get('current_job', 'novice').lower()
            
            # Get playstyle ratios
            playstyle_data = self.playstyles.get('playstyles', {}).get(playstyle, {})
            if not playstyle_data:
                logger.warning(f"Unknown playstyle: {playstyle}, using balanced")
                playstyle_data = self.playstyles.get('playstyles', {}).get('balanced', {})
            
            # Determine stat type (physical/magical/ranged/critical)
            stat_type = self._determine_stat_type(current_job)
            
            # Get ratios for this stat type
            ratios = playstyle_data.get('stat_ratios', {}).get(stat_type, {})
            if not ratios:
                # Fallback to first available ratio type
                stat_ratios_all = playstyle_data.get('stat_ratios', {})
                if stat_ratios_all:
                    ratios = list(stat_ratios_all.values())[0]
                else:
                    logger.error(f"No ratios found for {playstyle}/{stat_type}")
                    return {}
            
            # Apply dynamic adjustments
            adjusted_ratios = self._apply_performance_adjustments(ratios.copy())
            
            # Apply level-based multipliers
            current_level = current_stats.get('level', 1)
            adjusted_ratios = self._apply_level_multipliers(adjusted_ratios, current_level)
            
            # Calculate actual point distribution
            distribution = self._distribute_points(total_points, adjusted_ratios, current_stats)
            
            logger.debug(f"Stat distribution: {distribution} (ratios: {adjusted_ratios})")
            return distribution
    
    def _determine_stat_type(self, job: str) -> str:
        """Determine primary stat type for job"""
        physical_jobs = ['swordsman', 'knight', 'crusader', 'merchant', 'blacksmith']
        magical_jobs = ['mage', 'wizard', 'sage', 'acolyte', 'priest']
        ranged_jobs = ['archer', 'hunter', 'bard', 'dancer']
        critical_jobs = ['thief', 'assassin', 'rogue']
        
        if job in physical_jobs:
            return 'physical'
        elif job in magical_jobs:
            return 'magical'
        elif job in ranged_jobs:
            return 'ranged'
        elif job in critical_jobs:
            return 'critical'
        else:
            # Novice or unknown - check build intent
            build = self.user_intent.get('build', 'default')
            if 'hunter' in build or 'archer' in build:
                return 'ranged'
            elif 'mage' in build or 'wizard' in build or 'priest' in build:
                return 'magical'
            elif 'assassin' in build or 'crit' in build:
                return 'critical'
            else:
                return 'physical'
    
    def _apply_performance_adjustments(self, ratios: Dict[str, int]) -> Dict[str, int]:
        """Apply dynamic adjustments based on performance metrics"""
        adjusted = ratios.copy()
        
        dynamic_rules = self.playstyles.get('dynamic_adjustments', {})
        
        # High death rate adjustment
        if self.death_count > 0:
            death_rule = dynamic_rules.get('high_death_rate', {})
            threshold = death_rule.get('threshold', 5)
            if self.death_count >= threshold:
                vit_boost = min(10, self.death_count)
                adjusted['vit'] = adjusted.get('vit', 0) + vit_boost
                logger.info(f"Performance: Boosted VIT ratio by {vit_boost} (deaths: {self.death_count})")
        
        # Slow kill speed adjustment
        if self.avg_kill_time > 10.0:
            primary_stat = self._get_primary_damage_stat(ratios)
            if primary_stat:
                boost = 3
                adjusted[primary_stat] = adjusted.get(primary_stat, 0) + boost
                logger.info(f"Performance: Boosted {primary_stat.upper()} ratio by {boost} "
                          f"(slow kills: {self.avg_kill_time:.1f}s)")
        
        # Low hit rate adjustment
        if self.hit_rate < 0.70:
            dex_boost = 3
            adjusted['dex'] = adjusted.get('dex', 0) + dex_boost
            logger.info(f"Performance: Boosted DEX ratio by {dex_boost} (hit rate: {self.hit_rate:.1%})")
        
        return adjusted
    
    def _get_primary_damage_stat(self, ratios: Dict[str, int]) -> Optional[str]:
        """Get the primary damage stat from ratios"""
        damage_stats = ['str', 'int', 'dex', 'luk']
        max_ratio = 0
        primary = None
        
        for stat in damage_stats:
            if stat in ratios and ratios[stat] > max_ratio:
                max_ratio = ratios[stat]
                primary = stat
        
        return primary
    
    def _apply_level_multipliers(self, ratios: Dict[str, int], level: int) -> Dict[str, int]:
        """Apply level-based progression multipliers"""
        adjusted = ratios.copy()
        progressions = self.playstyles.get('level_progression_multipliers', {})
        
        for stage, config in progressions.items():
            level_range = config.get('level_range', [1, 99])
            if level_range[0] <= level <= level_range[1]:
                # Early game boost to VIT
                if 'vit_multiplier' in config:
                    multiplier = config['vit_multiplier']
                    adjusted['vit'] = int(adjusted.get('vit', 0) * multiplier)
                
                # Mid game boost to primary stat
                if 'primary_stat_multiplier' in config:
                    primary = self._get_primary_damage_stat(ratios)
                    if primary:
                        multiplier = config['primary_stat_multiplier']
                        adjusted[primary] = int(adjusted.get(primary, 0) * multiplier)
                
                break
        
        return adjusted
    
    def _distribute_points(self, total_points: int, ratios: Dict[str, int], 
                          current_stats: Dict[str, int]) -> Dict[str, int]:
        """Distribute points according to ratios"""
        if not ratios:
            return {}
        
        # Calculate total ratio sum
        ratio_sum = sum(ratios.values())
        if ratio_sum == 0:
            return {}
        
        # Calculate points per stat
        distribution = {}
        remaining_points = total_points
        
        # Sort stats by ratio (highest first)
        sorted_stats = sorted(ratios.items(), key=lambda x: x[1], reverse=True)
        
        for stat, ratio in sorted_stats:
            if remaining_points <= 0:
                break
            
            # Calculate proportional points
            points = max(1, int((ratio / ratio_sum) * total_points))
            points = min(points, remaining_points)
            
            # Check if we're already at cap
            current = current_stats.get(stat, 1)
            if current >= 99:
                continue
            
            # Don't exceed cap
            points = min(points, 99 - current)
            
            if points > 0:
                distribution[stat] = points
                remaining_points -= points
        
        # Distribute any remaining points to highest priority stat not at cap
        if remaining_points > 0:
            for stat, _ in sorted_stats:
                current = current_stats.get(stat, 1)
                if current < 99:
                    can_add = min(remaining_points, 99 - current)
                    distribution[stat] = distribution.get(stat, 0) + can_add
                    remaining_points -= can_add
                    if remaining_points <= 0:
                        break
        
        return distribution
    
    def get_allocation_recommendations(self, current_stats: Dict[str, int], 
                                      free_points: int) -> Dict[str, int]:
        """
        Get immediate stat allocation recommendations for available free points.
        Thread-safe with race condition protection.
        Returns: Dict of {stat: points_to_add}
        """
        with self._lock:
            # Prevent concurrent allocations
            if self._allocation_in_progress:
                logger.warning("Allocation already in progress, queuing request")
                return {}
            
            self._allocation_in_progress = True
            
            try:
                if free_points <= 0:
                    return {}
                
                # Try playstyle ratio-based allocation first
                distribution = self.calculate_stat_distribution_from_ratios(
                    free_points, current_stats
                )
                
                if distribution:
                    logger.info(f"Ratio-based allocation: {distribution} ({free_points} points)")
                    return distribution
                
                # Fallback: Use build config targets
                build_config = self.get_current_build_config()
                if not build_config:
                    logger.error("No build config and no playstyle ratios available")
                    return {}
                
                stat_targets = build_config.get('stat_targets', {})
                stat_priority = build_config.get('stat_priority', [])
                
                recommendations = {}
                remaining_points = free_points
                
                # Allocate according to priority 1-by-1
                for stat in stat_priority:
                    if remaining_points <= 0:
                        break
                    
                    stat_lower = stat.lower()
                    current = current_stats.get(stat_lower, 1)
                    target = stat_targets.get(stat_lower, 1)
                    
                    if current < target:
                        # Allocate ONE point at a time (user requirement)
                        points_to_add = 1
                        recommendations[stat_lower] = points_to_add
                        remaining_points -= points_to_add
                        break  # Only one stat per call for 1-by-1 allocation
                
                logger.info(f"Target-based allocation: {recommendations} (1-by-1 mode)")
                return recommendations
            
            finally:
                self._allocation_in_progress = False
    
    def on_level_up(self, current_level: int, current_stats: Dict[str, int]) -> Dict[str, Any]:
        """
        Called when character levels up.
        Returns stat allocation plan and config for raiseStat.pl
        """
        with self._lock:
            build_config = self.get_current_build_config()
            if not build_config:
                return {"error": "No build configuration found"}
            
            # Get stat targets
            stat_targets = build_config.get('stat_targets', {})
            
            # Apply adaptive adjustments
            adjusted_targets = self._apply_adaptive_adjustments_legacy(stat_targets)
            
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
        
        return ", ".join(stat_parts) if stat_parts else ""
    
    def _apply_adaptive_adjustments_legacy(self, base_targets: Dict[str, int]) -> Dict[str, int]:
        """Legacy adaptive adjustments for backwards compatibility"""
        adjusted = base_targets.copy()
        
        if self.death_count > 5:
            vit_boost = min(10, self.death_count)
            adjusted['vit'] = min(99, adjusted.get('vit', 1) + vit_boost)
        
        if self.avg_kill_time > 10.0:
            build_config = self.get_current_build_config()
            if build_config:
                primary_stat = build_config.get('stat_priority', ['str'])[0].lower()
                stat_boost = 5
                adjusted[primary_stat] = min(99, adjusted.get(primary_stat, 1) + stat_boost)
        
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
    
    def adjust_for_performance(self, death_count: int = 0, avg_kill_time: float = 0.0, 
                              hit_rate: float = 1.0, sp_depletion_rate: float = 0.0):
        """
        Update performance metrics for adaptive allocation.
        Called periodically by monitoring system.
        """
        with self._lock:
            self.death_count = death_count
            self.avg_kill_time = avg_kill_time
            self.hit_rate = hit_rate
            self.sp_depletion_rate = sp_depletion_rate
            
            logger.info(f"Performance metrics updated: deaths={death_count}, "
                       f"kill_time={avg_kill_time:.2f}s, hit_rate={hit_rate:.1%}")
    
    def get_stat_priority_for_job(self, job: str, build: str) -> List[str]:
        """Get stat priority list for a specific job/build"""
        job_data = self.job_builds.get(job.lower(), {})
        build_config = job_data.get(build, {})
        
        return build_config.get('stat_priority', ['str', 'agi', 'vit', 'dex', 'int', 'luk'])
    
    def export_config_file(self, output_path: str) -> bool:
        """
        Export configuration to OpenKore config format.
        Updates config.txt with statsAddAuto settings.
        """
        with self._lock:
            try:
                build_config = self.get_current_build_config()
                if not build_config:
                    logger.error("Cannot export: no build config")
                    return False
                
                stat_targets = build_config.get('stat_targets', {})
                stats_list = self._generate_stats_list({}, stat_targets)
                
                if not stats_list:
                    logger.warning("No stats to allocate in config")
                    return False
                
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
