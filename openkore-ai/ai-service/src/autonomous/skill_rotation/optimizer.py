"""
Skill Rotation Optimizer
Optimizes skill usage order for maximum efficiency
Context-aware: opener → DPS → finisher patterns
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from loguru import logger
import threading
from datetime import datetime, timedelta


class SkillRotationOptimizer:
    """
    Optimizes skill rotation based on combat context
    - Single target: focused DPS rotation
    - AOE: area damage skills
    - Boss: high damage combo
    - SP management: preserve for emergency
    """
    
    def __init__(self, data_dir: Path, openkore_client):
        """
        Initialize skill rotation optimizer
        
        Args:
            data_dir: Directory containing skill_rotations.json
            openkore_client: OpenKore IPC client
        """
        self.data_dir = data_dir
        self.openkore = openkore_client
        self.skill_rotations: Dict[str, Any] = {}
        self.skill_cooldowns: Dict[str, datetime] = {}
        self.rotation_history: List[Dict] = []
        self._lock = threading.RLock()
        self._load_skill_rotations()
        
        logger.info("SkillRotationOptimizer initialized")
    
    def _load_skill_rotations(self):
        """Load skill rotation configurations"""
        try:
            rotation_file = self.data_dir / "skill_rotations.json"
            
            if rotation_file.exists():
                with open(rotation_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.skill_rotations = data.get('rotations', {})
                logger.success(f"Loaded skill rotations for {len(self.skill_rotations)} job classes")
            else:
                logger.warning("Skill rotation file not found, using defaults")
                self._create_default_rotations()
                
        except Exception as e:
            logger.error(f"Failed to load skill rotations: {e}")
            self._create_default_rotations()
    
    def _create_default_rotations(self):
        """Create default skill rotations"""
        self.skill_rotations = {
            "Swordman": {
                "single_target": ["Bash", "Magnum Break"],
                "aoe": ["Magnum Break"],
                "opener": ["Provoke"],
                "priority": "damage"
            },
            "Mage": {
                "single_target": ["Fire Bolt", "Cold Bolt", "Lightning Bolt"],
                "aoe": ["Fire Wall", "Thunderstorm"],
                "opener": ["Stone Curse"],
                "priority": "efficiency"
            },
            "Archer": {
                "single_target": ["Double Strafe", "Arrow Shower"],
                "aoe": ["Arrow Shower"],
                "opener": ["Improve Concentration"],
                "priority": "damage"
            }
        }
    
    async def execute_optimal_rotation(
        self,
        combat_context: Dict[str, Any],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute optimal skill rotation for combat context
        
        Args:
            combat_context: Combat situation (single, aoe, boss)
            game_state: Current game state
            
        Returns:
            Dictionary with execution result
        """
        with self._lock:
            try:
                character = game_state.get('character', {})
                job_class = character.get('job_class', 'Novice')
                current_sp = character.get('sp', 0)
                max_sp = character.get('max_sp', 1)
                sp_percent = (current_sp / max_sp) * 100 if max_sp > 0 else 0
                
                logger.info(f"Executing rotation for {job_class} (SP: {sp_percent:.1f}%)")
                
                # Get rotation for job and context
                rotation = self._get_optimal_rotation(job_class, combat_context, sp_percent)
                
                if not rotation:
                    return {
                        'success': False,
                        'reason': 'No rotation available'
                    }
                
                # Execute rotation
                executed_skills = await self._execute_rotation(rotation, game_state)
                
                # Record performance
                self.rotation_history.append({
                    'timestamp': datetime.now(),
                    'job_class': job_class,
                    'context': combat_context.get('type'),
                    'skills_used': executed_skills,
                    'sp_used': sum(skill.get('sp_cost', 0) for skill in executed_skills)
                })
                
                return {
                    'success': True,
                    'rotation_type': combat_context.get('type'),
                    'skills_executed': len(executed_skills),
                    'skills': [s.get('name') for s in executed_skills]
                }
                
            except Exception as e:
                logger.error(f"Rotation execution error: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
    
    def _get_optimal_rotation(
        self,
        job_class: str,
        combat_context: Dict[str, Any],
        sp_percent: float
    ) -> Optional[List[Dict]]:
        """
        Get optimal skill rotation for context
        
        Args:
            job_class: Character job class
            combat_context: Combat situation
            sp_percent: Current SP percentage
            
        Returns:
            List of skills in rotation order
        """
        job_rotations = self.skill_rotations.get(job_class, {})
        
        if not job_rotations:
            logger.warning(f"No rotations defined for {job_class}")
            return None
        
        context_type = combat_context.get('type', 'single_target')
        enemy_count = combat_context.get('enemy_count', 1)
        is_boss = combat_context.get('is_boss', False)
        
        # Determine rotation type
        if is_boss:
            rotation_key = 'boss'
        elif enemy_count > 3:
            rotation_key = 'aoe'
        else:
            rotation_key = 'single_target'
        
        # Get rotation
        rotation_skills = job_rotations.get(rotation_key, [])
        
        if not rotation_skills:
            rotation_skills = job_rotations.get('single_target', [])
        
        # Add opener if available and not in combat yet
        if not combat_context.get('in_combat', True):
            opener = job_rotations.get('opener', [])
            if opener:
                rotation_skills = opener + rotation_skills
        
        # Filter by SP availability
        if sp_percent < 30:
            # Low SP - use only efficient skills
            rotation_skills = [
                skill for skill in rotation_skills
                if self._get_skill_sp_cost(skill) < 20
            ]
        
        # Build rotation with skill data
        rotation = []
        for skill_name in rotation_skills:
            rotation.append({
                'name': skill_name,
                'sp_cost': self._get_skill_sp_cost(skill_name),
                'priority': self._get_skill_priority(skill_name, context_type)
            })
        
        # Sort by priority
        rotation.sort(key=lambda s: s['priority'], reverse=True)
        
        return rotation if rotation else None
    
    def _get_skill_sp_cost(self, skill_name: str) -> int:
        """Get SP cost for skill (simplified)"""
        # This would lookup from skill database
        # Simplified costs for now
        high_cost_skills = ['Magnum Break', 'Thunderstorm', 'Fire Wall']
        medium_cost_skills = ['Bash', 'Fire Bolt', 'Double Strafe']
        
        if skill_name in high_cost_skills:
            return 30
        elif skill_name in medium_cost_skills:
            return 15
        else:
            return 10
    
    def _get_skill_priority(self, skill_name: str, context: str) -> int:
        """Get skill priority for context"""
        # Higher priority = execute first
        # Context-specific priorities
        
        if context == 'aoe':
            aoe_skills = ['Arrow Shower', 'Magnum Break', 'Thunderstorm', 'Fire Wall']
            if skill_name in aoe_skills:
                return 10
        
        if context == 'boss':
            high_damage = ['Fire Bolt', 'Cold Bolt', 'Double Strafe', 'Bash']
            if skill_name in high_damage:
                return 10
        
        # Default priority
        return 5
    
    async def _execute_rotation(
        self,
        rotation: List[Dict],
        game_state: Dict[str, Any]
    ) -> List[Dict]:
        """
        Execute skill rotation
        
        Args:
            rotation: List of skills to execute
            game_state: Current game state
            
        Returns:
            List of executed skills
        """
        executed = []
        
        for skill in rotation:
            skill_name = skill['name']
            
            # Check if skill is on cooldown
            if self._is_skill_on_cooldown(skill_name):
                logger.debug(f"Skill on cooldown: {skill_name}")
                continue
            
            # Check SP availability
            current_sp = game_state.get('character', {}).get('sp', 0)
            if current_sp < skill['sp_cost']:
                logger.warning(f"Insufficient SP for {skill_name}")
                break
            
            # Execute skill
            success = await self._execute_skill(skill_name)
            
            if success:
                executed.append(skill)
                self._set_skill_cooldown(skill_name, self._get_skill_cooldown(skill_name))
                
                # Delay between skills
                await asyncio.sleep(0.5)
            else:
                logger.warning(f"Failed to execute skill: {skill_name}")
        
        return executed
    
    async def _execute_skill(self, skill_name: str) -> bool:
        """
        Execute a single skill
        
        Args:
            skill_name: Name of skill to use
            
        Returns:
            True if execution successful
        """
        try:
            # Send skill command to OpenKore
            command = f"ss {skill_name}"
            await self.openkore.send_command(command)
            
            logger.debug(f"Executed skill: {skill_name}")
            return True
            
        except Exception as e:
            logger.error(f"Skill execution error: {e}")
            return False
    
    def _is_skill_on_cooldown(self, skill_name: str) -> bool:
        """Check if skill is on cooldown"""
        with self._lock:
            if skill_name not in self.skill_cooldowns:
                return False
            
            cooldown_end = self.skill_cooldowns[skill_name]
            return datetime.now() < cooldown_end
    
    def _set_skill_cooldown(self, skill_name: str, duration: float) -> None:
        """Set skill cooldown"""
        with self._lock:
            self.skill_cooldowns[skill_name] = datetime.now() + timedelta(seconds=duration)
    
    def _get_skill_cooldown(self, skill_name: str) -> float:
        """Get skill cooldown duration in seconds"""
        # Simplified cooldowns
        instant_skills = ['Bash', 'Fire Bolt', 'Double Strafe']
        
        if skill_name in instant_skills:
            return 0.5
        else:
            return 2.0
    
    def optimize_for_efficiency(
        self,
        job_class: str,
        target_type: str
    ) -> Dict[str, Any]:
        """
        Analyze and optimize rotation for SP efficiency
        
        Args:
            job_class: Character job class
            target_type: Target type (single, aoe, boss)
            
        Returns:
            Optimized rotation configuration
        """
        with self._lock:
            # Analyze historical performance
            relevant_history = [
                record for record in self.rotation_history
                if record['job_class'] == job_class and record['context'] == target_type
            ]
            
            if not relevant_history:
                return {
                    'optimized': False,
                    'reason': 'Insufficient data'
                }
            
            # Calculate efficiency metrics
            avg_sp_used = sum(r['sp_used'] for r in relevant_history) / len(relevant_history)
            avg_skills = sum(len(r['skills_used']) for r in relevant_history) / len(relevant_history)
            
            # Find most efficient skill combinations
            skill_usage = {}
            for record in relevant_history:
                for skill in record['skills_used']:
                    skill_name = skill.get('name')
                    if skill_name not in skill_usage:
                        skill_usage[skill_name] = 0
                    skill_usage[skill_name] += 1
            
            # Most used skills = likely most effective
            top_skills = sorted(skill_usage.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                'optimized': True,
                'average_sp_per_rotation': round(avg_sp_used, 2),
                'average_skills_per_rotation': round(avg_skills, 2),
                'most_effective_skills': [skill[0] for skill in top_skills],
                'usage_data': dict(top_skills)
            }
    
    def get_rotation_statistics(self) -> Dict:
        """Get skill rotation statistics"""
        with self._lock:
            if not self.rotation_history:
                return {
                    'total_rotations': 0
                }
            
            total_sp = sum(r['sp_used'] for r in self.rotation_history)
            total_skills = sum(len(r['skills_used']) for r in self.rotation_history)
            
            return {
                'total_rotations': len(self.rotation_history),
                'total_skills_used': total_skills,
                'total_sp_used': total_sp,
                'average_sp_per_rotation': round(total_sp / len(self.rotation_history), 2),
                'recent_rotations': self.rotation_history[-10:]
            }
