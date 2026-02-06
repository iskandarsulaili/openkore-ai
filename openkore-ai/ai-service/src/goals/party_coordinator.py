"""
Party Goal Coordinator - Multi-Agent Coordination Component

Coordinates goals across party/guild members for collaborative objectives.

Features:
- Distribute party goals to members
- Track shared progress
- Role-based task assignment
- Synchronize state across multiple characters
"""

from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from .goal_model import TemporalGoal, GoalPriority

logger = logging.getLogger(__name__)


class PartyGoalCoordinator:
    """
    Coordinate goals across party/guild members
    
    Key capabilities:
    - Distribute party goals to individual members
    - Role-based task assignment (tank, healer, DPS)
    - Track progress across multiple characters
    - Synchronize state and handle member disconnects
    """
    
    def __init__(self):
        """Initialize Party Goal Coordinator"""
        
        # Track active party goals
        self.party_goals: Dict[str, TemporalGoal] = {}
        
        # Track member assignments
        self.member_assignments: Dict[str, List[str]] = {}  # member_id → [goal_ids]
        
        # Role capabilities
        self.role_capabilities = self._initialize_role_capabilities()
        
        logger.info("Party Goal Coordinator initialized")
    
    def coordinate_party_goal(
        self,
        party_goal: TemporalGoal,
        members: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Distribute goal across party members
        
        Example: "Clear dungeon" →
        - Tank: "Aggro and control mobs"
        - Healer: "Keep party alive"
        - DPS1: "Focus damage on marked targets"
        - DPS2: "AOE crowd control"
        
        Args:
            party_goal: Goal to distribute
            members: List of party members with roles
                     [{'member_id': '...', 'role': 'tank', 'level': 60}, ...]
        
        Returns:
            Distribution plan with member assignments
        """
        
        logger.info(f"Coordinating party goal: {party_goal.name} for {len(members)} members")
        
        # Store party goal
        self.party_goals[party_goal.id] = party_goal
        
        # Assign roles based on goal type
        assignments = self._assign_roles(party_goal, members)
        
        # Create individual goals for each member
        member_goals = {}
        for member_id, assignment in assignments.items():
            member_goal = self._create_member_goal(
                party_goal,
                member_id,
                assignment
            )
            
            member_goals[member_id] = member_goal
            
            # Track assignment
            if member_id not in self.member_assignments:
                self.member_assignments[member_id] = []
            self.member_assignments[member_id].append(member_goal.id)
        
        # Configure party coordination on main goal
        party_goal.set_party_role(
            party_id=party_goal.metadata.get('party_id', 'unknown'),
            role='coordinator',
            members=[m['member_id'] for m in members]
        )
        
        distribution_plan = {
            'party_goal_id': party_goal.id,
            'party_goal_name': party_goal.name,
            'member_count': len(members),
            'assignments': assignments,
            'member_goals': {mid: mg.dict() for mid, mg in member_goals.items()},
            'coordination_strategy': self._determine_strategy(party_goal),
            'sync_interval_seconds': 10  # Sync every 10 seconds
        }
        
        logger.info(f"Distributed goal to {len(member_goals)} members")
        
        return distribution_plan
    
    def sync_goal_progress(
        self,
        party_goal_id: str,
        member_updates: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Track progress across multiple characters
        
        Args:
            party_goal_id: Party goal ID
            member_updates: Dict of member_id → progress data
                           {'member1': {'kills': 50, 'status': 'in_progress'}, ...}
        
        Returns:
            Synchronized progress report
        """
        
        if party_goal_id not in self.party_goals:
            logger.warning(f"Party goal {party_goal_id} not found")
            return {'error': 'Party goal not found'}
        
        party_goal = self.party_goals[party_goal_id]
        
        logger.info(f"Syncing progress for party goal: {party_goal.name}")
        
        # Update shared progress
        for member_id, progress in member_updates.items():
            party_goal.update_shared_progress(member_id, progress)
        
        # Aggregate progress
        aggregated_progress = self._aggregate_progress(party_goal, member_updates)
        
        # Check if goal completed
        if self._check_party_goal_completion(party_goal, aggregated_progress):
            party_goal.complete_success()
            logger.info(f"🎉 Party goal completed: {party_goal.name}")
        
        sync_report = {
            'party_goal_id': party_goal_id,
            'party_goal_name': party_goal.name,
            'status': party_goal.status.value,
            'members_reporting': len(member_updates),
            'aggregated_progress': aggregated_progress,
            'completion_percent': self._calculate_completion_percent(party_goal, aggregated_progress),
            'next_sync_in_seconds': 10,
            'synced_at': datetime.now().isoformat()
        }
        
        return sync_report
    
    def handle_member_disconnect(
        self,
        member_id: str,
        party_goal_id: str
    ) -> Dict[str, Any]:
        """
        Handle member disconnection during party goal
        
        Args:
            member_id: Disconnected member
            party_goal_id: Affected party goal
        
        Returns:
            Rebalancing plan
        """
        
        logger.warning(f"Member {member_id[:8]} disconnected from party goal {party_goal_id[:8]}")
        
        if party_goal_id not in self.party_goals:
            return {'error': 'Party goal not found'}
        
        party_goal = self.party_goals[party_goal_id]
        
        # Get remaining members
        if not party_goal.party_coordination:
            return {'error': 'No party coordination configured'}
        
        remaining_members = [
            mid for mid in party_goal.party_coordination['members']
            if mid != member_id
        ]
        
        if len(remaining_members) == 0:
            # Everyone disconnected, abort goal
            party_goal.emergency_abort("All party members disconnected")
            
            return {
                'action': 'abort',
                'reason': 'All members disconnected'
            }
        
        # Redistribute disconnected member's tasks
        redistribution = self._redistribute_tasks(
            party_goal,
            member_id,
            remaining_members
        )
        
        return {
            'action': 'rebalance',
            'disconnected_member': member_id,
            'remaining_members': len(remaining_members),
            'redistribution': redistribution,
            'recommendation': 'Continue with remaining members' if len(remaining_members) >= 2 else 'Consider aborting'
        }
    
    def get_party_statistics(self, party_goal_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a party goal
        
        Args:
            party_goal_id: Party goal ID
        
        Returns:
            Statistics or None if not found
        """
        
        if party_goal_id not in self.party_goals:
            return None
        
        party_goal = self.party_goals[party_goal_id]
        
        if not party_goal.party_coordination:
            return None
        
        members = party_goal.party_coordination.get('members', [])
        shared_progress = party_goal.party_coordination.get('shared_progress', {})
        
        # Calculate per-member contributions
        contributions = {}
        for member_id in members:
            if member_id in shared_progress:
                progress = shared_progress[member_id]
                contributions[member_id] = {
                    'kills': progress.get('kills', 0),
                    'damage_dealt': progress.get('damage_dealt', 0),
                    'healing_done': progress.get('healing_done', 0),
                    'last_update': progress.get('updated_at')
                }
        
        return {
            'party_goal_id': party_goal_id,
            'party_goal_name': party_goal.name,
            'party_id': party_goal.party_coordination.get('party_id'),
            'member_count': len(members),
            'active_members': len(contributions),
            'contributions': contributions,
            'total_kills': sum(c.get('kills', 0) for c in contributions.values()),
            'total_damage': sum(c.get('damage_dealt', 0) for c in contributions.values()),
            'total_healing': sum(c.get('healing_done', 0) for c in contributions.values())
        }
    
    # ===== Private Helper Methods =====
    
    def _assign_roles(
        self,
        party_goal: TemporalGoal,
        members: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Assign roles based on goal type and member capabilities"""
        
        assignments = {}
        
        goal_type = party_goal.goal_type
        
        for member in members:
            member_id = member['member_id']
            role = member.get('role', 'dps')
            
            # Get role-specific tasks
            tasks = self.role_capabilities.get(goal_type, {}).get(role, ['assist'])
            
            assignments[member_id] = {
                'role': role,
                'tasks': tasks,
                'priority': self._get_role_priority(goal_type, role),
                'level': member.get('level', 1)
            }
        
        return assignments
    
    def _create_member_goal(
        self,
        party_goal: TemporalGoal,
        member_id: str,
        assignment: Dict[str, Any]
    ) -> TemporalGoal:
        """Create individual goal for party member"""
        
        member_goal = TemporalGoal(
            name=f"{party_goal.name}_{assignment['role']}",
            description=f"{assignment['role'].title()} role for {party_goal.description}",
            goal_type=party_goal.goal_type,
            priority=party_goal.priority,
            time_scale=party_goal.time_scale,
            estimated_duration=party_goal.estimated_duration,
            primary_plan={
                'strategy': f"{assignment['role']}_role",
                'actions': assignment['tasks'],
                'parameters': {
                    'party_goal_id': party_goal.id,
                    'role': assignment['role']
                }
            },
            success_conditions={
                'party_goal_completed': True,
                'role_fulfilled': True
            },
            parent_goal_id=party_goal.id,
            metadata={
                'member_id': member_id,
                'party_role': assignment['role'],
                'party_goal_id': party_goal.id
            }
        )
        
        return member_goal
    
    def _determine_strategy(self, party_goal: TemporalGoal) -> str:
        """Determine coordination strategy based on goal type"""
        
        strategies = {
            'dungeon': 'tank_and_spank',
            'farming': 'spread_and_farm',
            'boss_fight': 'coordinated_burst',
            'questing': 'sequential_completion',
            'exploration': 'divide_and_conquer'
        }
        
        return strategies.get(party_goal.goal_type, 'default')
    
    def _aggregate_progress(
        self,
        party_goal: TemporalGoal,
        member_updates: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate progress from all members"""
        
        total_kills = sum(update.get('kills', 0) for update in member_updates.values())
        total_damage = sum(update.get('damage_dealt', 0) for update in member_updates.values())
        total_healing = sum(update.get('healing_done', 0) for update in member_updates.values())
        
        return {
            'total_kills': total_kills,
            'total_damage_dealt': total_damage,
            'total_healing_done': total_healing,
            'target_kills': party_goal.success_conditions.get('kills', 0)
        }
    
    def _check_party_goal_completion(
        self,
        party_goal: TemporalGoal,
        aggregated_progress: Dict[str, Any]
    ) -> bool:
        """Check if party goal is completed"""
        
        # Check kill target
        target_kills = party_goal.success_conditions.get('kills', 0)
        actual_kills = aggregated_progress.get('total_kills', 0)
        
        if target_kills > 0 and actual_kills >= target_kills:
            return True
        
        # Check other conditions
        # ... (add more completion checks)
        
        return False
    
    def _calculate_completion_percent(
        self,
        party_goal: TemporalGoal,
        aggregated_progress: Dict[str, Any]
    ) -> float:
        """Calculate overall completion percentage"""
        
        target_kills = party_goal.success_conditions.get('kills', 0)
        actual_kills = aggregated_progress.get('total_kills', 0)
        
        if target_kills > 0:
            return min(100.0, (actual_kills / target_kills) * 100)
        
        return 0.0
    
    def _redistribute_tasks(
        self,
        party_goal: TemporalGoal,
        disconnected_member: str,
        remaining_members: List[str]
    ) -> Dict[str, Any]:
        """Redistribute tasks from disconnected member"""
        
        # Simple redistribution: split evenly among remaining
        return {
            'strategy': 'even_split',
            'remaining_members': remaining_members,
            'additional_load_per_member': 1.0 / len(remaining_members) if remaining_members else 0
        }
    
    def _get_role_priority(self, goal_type: str, role: str) -> int:
        """Get priority level for role in goal type"""
        
        priorities = {
            'dungeon': {'tank': 5, 'healer': 4, 'dps': 3},
            'farming': {'dps': 5, 'tank': 3, 'healer': 3},
            'boss_fight': {'tank': 5, 'healer': 5, 'dps': 4}
        }
        
        return priorities.get(goal_type, {}).get(role, 3)
    
    def _initialize_role_capabilities(self) -> Dict[str, Dict[str, List[str]]]:
        """Initialize role-specific tasks for different goal types"""
        
        return {
            'dungeon': {
                'tank': ['aggro_mobs', 'position_enemies', 'protect_party', 'manage_threat'],
                'healer': ['heal_party', 'buff_party', 'resurrect_fallen', 'remove_debuffs'],
                'dps': ['kill_marked_targets', 'aoe_damage', 'focus_priority', 'avoid_aggro']
            },
            'farming': {
                'tank': ['gather_mobs', 'control_spawns'],
                'healer': ['heal_as_needed', 'buff_party'],
                'dps': ['kill_monsters', 'loot_items', 'maximize_damage']
            },
            'boss_fight': {
                'tank': ['main_tank', 'boss_positioning', 'mechanic_handling'],
                'healer': ['emergency_healing', 'dispel_debuffs', 'tank_priority'],
                'dps': ['burst_windows', 'avoid_mechanics', 'interrupt_skills']
            },
            'support': {
                'support': ['heal_party', 'buff_party', 'maintain_presence'],
                'dps': ['assist_with_damage'],
                'tank': ['protect_support']
            }
        }
