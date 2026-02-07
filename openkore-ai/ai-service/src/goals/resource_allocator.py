"""
Resource Allocator - Optimization Component

Optimizes resource allocation across competing goals to maximize efficiency
and prevent resource conflicts.

Resource types managed:
- Computational: API calls/min, CPU%, Memory
- In-game: Potions, Zeny, Equipment
- Location: Map areas, NPCs
- Time: Execution time slots
"""

from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime

from .goal_model import TemporalGoal, GoalPriority

logger = logging.getLogger(__name__)


class ResourceAllocator:
    """
    Optimize resource allocation across competing goals
    
    Key capabilities:
    - Fair resource distribution based on priority
    - Conflict detection (multiple goals need same resource)
    - Resource reservation system
    - Dynamic reallocation on priority changes
    - Resource usage tracking
    """
    
    def __init__(self, total_resources: Optional[Dict[str, Any]] = None):
        """
        Initialize Resource Allocator
        
        Args:
            total_resources: Total available resources
        """
        
        # Default resource limits
        self.total_resources = total_resources or {
            'api_calls_per_min': 60,
            'cpu_percent': 80,
            'memory_mb': 2048,
            'potions': 500,
            'zeny': 1000000,
            'map_slots': 1  # Can only be in one place at a time
        }
        
        # Track allocated resources
        self.allocated = {
            'api_calls_per_min': 0,
            'cpu_percent': 0,
            'memory_mb': 0,
            'potions': 0,
            'zeny': 0,
            'map_slots': 0
        }
        
        # Track which goal has which resources
        self.allocations_by_goal: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Resource Allocator initialized")
        logger.info(f"Total resources: {self.total_resources}")
    
    def allocate_resources(
        self,
        active_goals: List[TemporalGoal]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Distribute limited resources among goals
        
        Allocation strategy:
        1. Priority-weighted fair share
        2. Critical goals get guaranteed minimums
        3. Non-critical goals share remaining capacity
        4. Oversubscription handled gracefully
        
        Args:
            active_goals: List of goals needing resources
        
        Returns:
            Dict mapping goal_id to allocated resources
        """
        
        logger.info(f"Allocating resources for {len(active_goals)} active goals")
        
        if not active_goals:
            return {}
        
        # Sort by priority (CRITICAL first)
        sorted_goals = sorted(active_goals, key=lambda g: g.priority.value if hasattr(g.priority, 'value') else g.priority, reverse=True)
        
        allocation_plan = {}
        
        # Reset allocations
        self.allocated = {key: 0 for key in self.allocated}
        self.allocations_by_goal = {}
        
        # Phase 1: Allocate to CRITICAL goals (guaranteed minimum)
        for goal in sorted_goals:
            if goal.priority == GoalPriority.CRITICAL:
                allocated = self._allocate_critical(goal)
                allocation_plan[goal.id] = allocated
                self.allocations_by_goal[goal.id] = allocated
        
        # Phase 2: Allocate to other goals (fair share of remaining)
        non_critical = [g for g in sorted_goals if g.priority != GoalPriority.CRITICAL]
        
        if non_critical:
            # Calculate fair share
            remaining = self._calculate_remaining()
            
            for goal in non_critical:
                allocated = self._allocate_fair_share(goal, remaining, len(non_critical))
                allocation_plan[goal.id] = allocated
                self.allocations_by_goal[goal.id] = allocated
        
        # Log allocation summary
        logger.info(f"Allocated: API calls={self.allocated['api_calls_per_min']}/{self.total_resources['api_calls_per_min']}, "
                   f"CPU={self.allocated['cpu_percent']}/{self.total_resources['cpu_percent']}%, "
                   f"Memory={self.allocated['memory_mb']}/{self.total_resources['memory_mb']}MB")
        
        return allocation_plan
    
    def detect_resource_conflicts(
        self,
        goals: List[TemporalGoal]
    ) -> List[Tuple[str, str, str]]:
        """
        Identify goals competing for same resources
        
        Conflicts occur when:
        - Both need to be in same location (map_slots)
        - Combined resource needs exceed capacity
        - Exclusive resources (only one can use)
        
        Args:
            goals: List of goals to check
        
        Returns:
            List of conflicts: [(goal1_id, goal2_id, resource_type), ...]
        """
        
        logger.info(f"Detecting resource conflicts among {len(goals)} goals")
        
        conflicts = []
        
        # Check map location conflicts
        map_goals = {}
        for goal in goals:
            map_name = goal.primary_plan.get('parameters', {}).get('map')
            if map_name:
                if map_name not in map_goals:
                    map_goals[map_name] = []
                map_goals[map_name].append(goal)
        
        # If multiple goals need same map
        for map_name, goals_on_map in map_goals.items():
            if len(goals_on_map) > 1:
                # All pairs conflict
                for i, goal1 in enumerate(goals_on_map):
                    for goal2 in goals_on_map[i+1:]:
                        conflicts.append((goal1.id, goal2.id, f'map:{map_name}'))
                        # Update goal conflict lists
                        goal1.add_conflict(goal2.id)
                        goal2.add_conflict(goal1.id)
        
        # Check resource oversubscription
        total_needs = {
            'api_calls_per_min': 0,
            'cpu_percent': 0,
            'memory_mb': 0,
            'potions': 0,
            'zeny': 0
        }
        
        for goal in goals:
            for resource_type in total_needs:
                needed = goal.resource_allocation.get(resource_type, 0)
                total_needs[resource_type] += needed
        
        # Check if total exceeds capacity
        for resource_type, total_needed in total_needs.items():
            capacity = self.total_resources.get(resource_type, 0)
            if total_needed > capacity:
                logger.warning(f"[WARNING] Resource oversubscription: {resource_type} needs {total_needed}, have {capacity}")
                
                # Mark all goals as conflicting on this resource
                for i, goal1 in enumerate(goals):
                    for goal2 in goals[i+1:]:
                        conflicts.append((goal1.id, goal2.id, resource_type))
        
        logger.info(f"Detected {len(conflicts)} resource conflicts")
        
        return conflicts
    
    def reserve_resource(
        self,
        goal_id: str,
        resource_type: str,
        amount: Any
    ) -> bool:
        """
        Reserve a resource for a specific goal
        
        Args:
            goal_id: Goal requesting reservation
            resource_type: Type of resource
            amount: Amount to reserve
        
        Returns:
            True if reservation successful, False if insufficient resources
        """
        
        available = self.total_resources.get(resource_type, 0) - self.allocated.get(resource_type, 0)
        
        if amount <= available:
            self.allocated[resource_type] = self.allocated.get(resource_type, 0) + amount
            
            if goal_id not in self.allocations_by_goal:
                self.allocations_by_goal[goal_id] = {}
            
            self.allocations_by_goal[goal_id][resource_type] = amount
            
            logger.info(f"Reserved {amount} {resource_type} for goal {goal_id[:8]}")
            return True
        else:
            logger.warning(f"Cannot reserve {amount} {resource_type} for goal {goal_id[:8]} (only {available} available)")
            return False
    
    def release_resources(self, goal_id: str) -> None:
        """
        Release all resources allocated to a goal
        
        Args:
            goal_id: Goal to release resources from
        """
        
        if goal_id not in self.allocations_by_goal:
            return
        
        allocations = self.allocations_by_goal[goal_id]
        
        for resource_type, amount in allocations.items():
            self.allocated[resource_type] = max(0, self.allocated[resource_type] - amount)
        
        del self.allocations_by_goal[goal_id]
        
        logger.info(f"Released resources from goal {goal_id[:8]}")
    
    def get_available_resources(self) -> Dict[str, Any]:
        """Get currently available (unallocated) resources"""
        
        available = {}
        for resource_type, total in self.total_resources.items():
            allocated = self.allocated.get(resource_type, 0)
            available[resource_type] = total - allocated
        
        return available
    
    def get_utilization_stats(self) -> Dict[str, Any]:
        """Get resource utilization statistics"""
        
        utilization = {}
        
        for resource_type, total in self.total_resources.items():
            allocated = self.allocated.get(resource_type, 0)
            utilization[resource_type] = {
                'total': total,
                'allocated': allocated,
                'available': total - allocated,
                'utilization_percent': round((allocated / total * 100) if total > 0 else 0, 2)
            }
        
        return utilization
    
    # ===== Private Helper Methods =====
    
    def _allocate_critical(self, goal: TemporalGoal) -> Dict[str, Any]:
        """Allocate guaranteed minimum for critical goals"""
        
        # Critical goals get priority allocation
        allocation = {
            'api_calls_per_min': min(10, self.total_resources['api_calls_per_min']),
            'cpu_percent': min(20, self.total_resources['cpu_percent']),
            'memory_mb': min(512, self.total_resources['memory_mb']),
            'potions': min(50, self.total_resources['potions']),
            'zeny': min(10000, self.total_resources['zeny']),
            'map_slots': 1
        }
        
        # Update allocated totals
        for resource_type, amount in allocation.items():
            self.allocated[resource_type] += amount
        
        # Update goal's resource allocation
        goal.resource_allocation = allocation
        
        logger.info(f"Allocated critical resources to goal {goal.id[:8]}")
        
        return allocation
    
    def _allocate_fair_share(
        self,
        goal: TemporalGoal,
        remaining: Dict[str, Any],
        num_goals: int
    ) -> Dict[str, Any]:
        """Allocate fair share of remaining resources"""
        
        if num_goals == 0:
            return {}
        
        # Weight by priority
        priority_value = goal.priority.value if hasattr(goal.priority, 'value') else goal.priority
        priority_weight = priority_value / 3.0  # Normalize (1-5 → 0.33-1.66)
        
        allocation = {}
        for resource_type, available in remaining.items():
            # Fair share with priority weighting
            share = (available / num_goals) * priority_weight
            allocation[resource_type] = int(share)
            
            # Update allocated
            self.allocated[resource_type] += allocation[resource_type]
        
        # Update goal's resource allocation
        goal.resource_allocation = allocation
        
        return allocation
    
    def _calculate_remaining(self) -> Dict[str, Any]:
        """Calculate remaining unallocated resources"""
        
        remaining = {}
        for resource_type, total in self.total_resources.items():
            allocated = self.allocated.get(resource_type, 0)
            remaining[resource_type] = max(0, total - allocated)
        
        return remaining
