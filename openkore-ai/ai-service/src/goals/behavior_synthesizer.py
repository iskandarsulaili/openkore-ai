"""
Behavior Synthesizer - Emergent Behavior Component

Synthesizes emergent behaviors from goal combinations to create more efficient
composite strategies.

Key concepts:
- Goal merging: Combine compatible goals
- Synergy detection: Find goals that amplify each other
- Behavior patterns: Learn from successful combinations
"""

from typing import List, Optional, Dict, Any, Tuple
import logging
from datetime import datetime

from .goal_model import TemporalGoal, GoalPriority

logger = logging.getLogger(__name__)


class BehaviorSynthesizer:
    """
    Synthesize emergent behaviors from goal combinations
    
    Key capabilities:
    - Merge compatible goals for efficiency
    - Detect synergies between goals
    - Generate composite behaviors
    - Learn from successful combinations
    """
    
    def __init__(self):
        """Initialize Behavior Synthesizer"""
        
        # Track successful behavior patterns
        self.learned_patterns: List[Dict[str, Any]] = []
        
        # Synergy rules
        self.synergy_rules = self._initialize_synergy_rules()
        
        logger.info("Behavior Synthesizer initialized")
    
    def combine_goals(
        self,
        goals: List[TemporalGoal]
    ) -> Optional[TemporalGoal]:
        """
        Merge compatible goals for efficiency
        
        Example merges:
        - "Farm Poring" + "Collect Jellopy" → "Farm Poring for Jellopy"
        - "Level up" + "Farm exp" → "Leveling session"
        - "Heal party" + "Buff party" → "Support party"
        
        Args:
            goals: Goals to potentially merge
        
        Returns:
            Merged goal if compatible, None otherwise
        """
        
        if len(goals) < 2:
            return None
        
        logger.info(f"Attempting to combine {len(goals)} goals")
        
        # Check if all goals have same type
        goal_types = set(g.goal_type for g in goals)
        
        if len(goal_types) == 1:
            # Same type - try type-specific merge
            goal_type = list(goal_types)[0]
            
            if goal_type == 'farming':
                return self._merge_farming_goals(goals)
            
            elif goal_type == 'support':
                return self._merge_support_goals(goals)
            
            elif goal_type == 'exploration':
                return self._merge_exploration_goals(goals)
        
        # Different types - check for synergies
        combined = self._create_synergistic_goal(goals)
        
        if combined:
            logger.info(f"Created synergistic goal: {combined.name}")
            return combined
        
        logger.info("Goals not compatible for merging")
        return None
    
    def detect_synergies(
        self,
        goals: List[TemporalGoal]
    ) -> List[Dict[str, Any]]:
        """
        Find goals that work better together
        
        Synergy types:
        - Location synergy: Both benefit from being in same area
        - Timing synergy: Sequential execution is more efficient
        - Resource synergy: Share resources/buffs
        - Action synergy: Actions complement each other
        
        Args:
            goals: Goals to analyze for synergies
        
        Returns:
            List of detected synergies with details
        """
        
        logger.info(f"Detecting synergies among {len(goals)} goals")
        
        synergies = []
        
        # Check all pairs
        for i, goal1 in enumerate(goals):
            for goal2 in goals[i+1:]:
                synergy = self._check_synergy(goal1, goal2)
                
                if synergy:
                    synergies.append(synergy)
        
        logger.info(f"Detected {len(synergies)} synergies")
        
        return synergies
    
    def learn_pattern(
        self,
        combined_goal: TemporalGoal,
        component_goals: List[TemporalGoal],
        success: bool,
        efficiency_gain: float
    ) -> None:
        """
        Learn from successful (or failed) goal combinations
        
        Args:
            combined_goal: The merged goal
            component_goals: Original goals that were combined
            success: Whether the combination was successful
            efficiency_gain: Performance improvement (1.5 = 50% better)
        """
        
        if success and efficiency_gain > 1.1:
            # Worth learning
            pattern = {
                'goal_types': [g.goal_type for g in component_goals],
                'combined_type': combined_goal.goal_type,
                'success': success,
                'efficiency_gain': efficiency_gain,
                'learned_at': datetime.now().isoformat(),
                'strategy': combined_goal.primary_plan.get('strategy'),
                'synergies': combined_goal.metadata.get('synergies', [])
            }
            
            self.learned_patterns.append(pattern)
            
            logger.info(f"Learned new behavior pattern: {efficiency_gain:.1%} efficiency gain")
    
    def get_learned_patterns(
        self,
        goal_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get learned behavior patterns
        
        Args:
            goal_type: Optional filter by goal type
        
        Returns:
            List of learned patterns
        """
        
        if goal_type:
            return [p for p in self.learned_patterns if goal_type in p['goal_types']]
        
        return self.learned_patterns
    
    # ===== Private Helper Methods =====
    
    def _merge_farming_goals(self, goals: List[TemporalGoal]) -> Optional[TemporalGoal]:
        """Merge multiple farming goals"""
        
        # Check if same location
        locations = set()
        for goal in goals:
            map_name = goal.primary_plan.get('parameters', {}).get('map')
            if map_name:
                locations.add(map_name)
        
        if len(locations) > 1:
            logger.debug("Farming goals in different locations, cannot merge")
            return None
        
        # Merge into single farming session
        total_kills = sum(g.success_conditions.get('kills', 0) for g in goals)
        monsters = [g.name.replace('farm_', '') for g in goals]
        
        map_name = list(locations)[0] if locations else 'unknown'
        
        merged = TemporalGoal(
            name=f"farm_session_{map_name}",
            description=f"Farm {', '.join(monsters)} in {map_name}",
            goal_type='farming',
            priority=max(g.priority for g in goals),
            time_scale=goals[0].time_scale,
            estimated_duration=max(g.estimated_duration for g in goals),
            primary_plan=goals[0].primary_plan.copy(),
            success_conditions={'kills': total_kills, 'monsters': monsters},
            tags=list(set(tag for g in goals for tag in g.tags)),
            metadata={
                'merged_from': [g.id for g in goals],
                'merge_type': 'farming_session',
                'efficiency_gain': 1.3  # Estimated 30% gain from not switching
            }
        )
        
        merged.add_milestone("25% kills", 0.25, f"{int(total_kills * 0.25)} kills")
        merged.add_milestone("50% kills", 0.50, f"{int(total_kills * 0.50)} kills")
        merged.add_milestone("75% kills", 0.75, f"{int(total_kills * 0.75)} kills")
        merged.add_milestone("100% kills", 1.00, f"{total_kills} kills")
        
        return merged
    
    def _merge_support_goals(self, goals: List[TemporalGoal]) -> Optional[TemporalGoal]:
        """Merge multiple support goals (healing, buffing, etc.)"""
        
        support_actions = []
        for goal in goals:
            actions = goal.primary_plan.get('actions', [])
            support_actions.extend(actions)
        
        merged = TemporalGoal(
            name="support_routine",
            description="Comprehensive party support",
            goal_type='support',
            priority=max(g.priority for g in goals),
            time_scale='short',
            estimated_duration=max(g.estimated_duration for g in goals),
            primary_plan={
                'strategy': 'reactive',
                'actions': list(set(support_actions)),  # Unique actions
                'parameters': {
                    'check_interval': 2,  # Check every 2 seconds
                    'priority_order': ['heal', 'buff', 'resurrect']
                }
            },
            success_conditions={'party_hp_above': 80, 'buffs_maintained': True},
            metadata={
                'merged_from': [g.id for g in goals],
                'merge_type': 'support_routine'
            }
        )
        
        return merged
    
    def _merge_exploration_goals(self, goals: List[TemporalGoal]) -> Optional[TemporalGoal]:
        """Merge multiple exploration goals into efficient route"""
        
        locations = []
        for goal in goals:
            location = goal.primary_plan.get('parameters', {}).get('destination')
            if location:
                locations.append(location)
        
        if not locations:
            return None
        
        merged = TemporalGoal(
            name="exploration_route",
            description=f"Explore {len(locations)} locations",
            goal_type='exploration',
            priority=max(g.priority for g in goals),
            time_scale='medium',
            estimated_duration=sum(g.estimated_duration for g in goals),
            primary_plan={
                'strategy': 'optimal_route',
                'actions': ['calculate_shortest_path', 'explore_locations', 'return_to_base'],
                'parameters': {
                    'locations': locations,
                    'route_optimization': 'traveling_salesman'
                }
            },
            success_conditions={'locations_explored': len(locations)},
            metadata={
                'merged_from': [g.id for g in goals],
                'merge_type': 'exploration_route',
                'efficiency_gain': 1.5  # 50% gain from optimized routing
            }
        )
        
        return merged
    
    def _create_synergistic_goal(self, goals: List[TemporalGoal]) -> Optional[TemporalGoal]:
        """Create a new goal that combines synergistic actions"""
        
        # Example synergy: Farming + Support → Tank while party farms
        types = [g.goal_type for g in goals]
        
        if 'farming' in types and 'support' in types:
            # Party farming synergy
            farming_goal = next(g for g in goals if g.goal_type == 'farming')
            support_goal = next(g for g in goals if g.goal_type == 'support')
            
            synergistic = TemporalGoal(
                name="party_farming_with_support",
                description="Farm while providing party support",
                goal_type='farming',
                priority=max(g.priority for g in goals),
                time_scale=farming_goal.time_scale,
                estimated_duration=farming_goal.estimated_duration,
                primary_plan={
                    'strategy': 'synergistic',
                    'actions': ['farm_monsters', 'heal_party', 'buff_party', 'loot_items'],
                    'parameters': {
                        'dual_role': True,
                        'farm_priority': 0.6,
                        'support_priority': 0.4
                    }
                },
                success_conditions={
                    'kills': farming_goal.success_conditions.get('kills', 100),
                    'party_survival': True
                },
                metadata={
                    'merged_from': [g.id for g in goals],
                    'synergy_type': 'farming_support',
                    'synergies': ['dual_role_efficiency', 'party_bonus_exp'],
                    'efficiency_gain': 1.8  # 80% gain from party bonuses
                }
            )
            
            return synergistic
        
        return None
    
    def _check_synergy(
        self,
        goal1: TemporalGoal,
        goal2: TemporalGoal
    ) -> Optional[Dict[str, Any]]:
        """Check if two goals have synergy"""
        
        # Check predefined synergy rules
        key = tuple(sorted([goal1.goal_type, goal2.goal_type]))
        
        if key in self.synergy_rules:
            rule = self.synergy_rules[key]
            
            return {
                'goal1_id': goal1.id,
                'goal2_id': goal2.id,
                'goal1_name': goal1.name,
                'goal2_name': goal2.name,
                'synergy_type': rule['type'],
                'benefit': rule['benefit'],
                'efficiency_multiplier': rule['multiplier'],
                'recommendation': rule['recommendation']
            }
        
        return None
    
    def _initialize_synergy_rules(self) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """Initialize synergy detection rules"""
        
        return {
            ('farming', 'support'): {
                'type': 'party_efficiency',
                'benefit': 'Party exp bonus + safety',
                'multiplier': 1.5,
                'recommendation': 'Execute simultaneously in party'
            },
            ('farming', 'questing'): {
                'type': 'dual_objective',
                'benefit': 'Farm mobs for quest while leveling',
                'multiplier': 1.3,
                'recommendation': 'Choose quest monsters as farm targets'
            },
            ('leveling', 'farming'): {
                'type': 'natural_synergy',
                'benefit': 'Leveling produces farming results',
                'multiplier': 1.2,
                'recommendation': 'Track both objectives simultaneously'
            },
            ('exploration', 'questing'): {
                'type': 'location_efficiency',
                'benefit': 'Explore while completing quests',
                'multiplier': 1.4,
                'recommendation': 'Plan quest route through unexplored areas'
            }
        }
