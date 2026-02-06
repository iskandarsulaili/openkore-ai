"""
Temporal Goals Coordinator - Main Integration Component

Orchestrates all temporal reasoning components and intelligence layers for goal execution.

Enhanced with:
- Hierarchical goal decomposition
- Milestone tracking and validation
- Conflict resolution
- Cross-system synchronization with OpenKore bridge
"""

from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime
import asyncio
import httpx

from .goal_model import TemporalGoal, GoalStatus, GoalPriority, ContingencyPlan, PlanType
from .past_analyzer import PastAnalyzer
from .present_evaluator import PresentEvaluator
from .future_predictor import FuturePredictor
from .contingency_manager import ContingencyManager
from .conscious_planner import ConsciousGoalPlanner
from .subconscious_predictor import SubconsciousGoalPredictor
from .reflex_trigger import ReflexGoalTrigger
from .muscle_memory import MuscleMemoryExecutor

logger = logging.getLogger(__name__)


class TemporalGoalsCoordinator:
    """
    Main coordinator integrating all temporal reasoning and intelligence layers
    
    Architecture:
    - Past Analysis → Present Evaluation → Future Prediction → Goal Synthesis
    - Four-layer execution: Muscle Memory → Reflex → Subconscious → Conscious
    - Contingency management for zero-failure operation
    """
    
    def __init__(self, db_session=None, ml_model=None):
        """
        Initialize Temporal Goals Coordinator
        
        Args:
            db_session: Database session for historical data
            ml_model: Optional ML model for predictions
        """
        
        logger.info("Initializing Temporal Goals Coordinator")
        
        # Temporal reasoning components
        self.past_analyzer = PastAnalyzer(db_session)
        self.present_evaluator = PresentEvaluator()
        self.future_predictor = FuturePredictor(ml_model)
        self.contingency_manager = ContingencyManager()
        
        # Intelligence layers (fastest to slowest)
        self.muscle_memory = MuscleMemoryExecutor()
        self.reflex_layer = ReflexGoalTrigger()
        self.subconscious_layer = SubconsciousGoalPredictor(ml_model)
        self.conscious_layer = ConsciousGoalPlanner()
        
        # Coordinator state
        self.active_goals = []
        self.completed_goals = []
        self.failed_goals = []
        
        logger.info("✅ Temporal Goals Coordinator initialized")
    
    async def process_goal(
        self,
        goal_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main processing loop with temporal reasoning
        
        Flow:
        1. PAST: Analyze similar historical goals
        2. PRESENT: Evaluate current feasibility
        3. FUTURE: Predict outcomes
        4. SYNTHESIZE: Create goal with contingency plans
        5. EXECUTE: With multi-layer intelligence + contingency
        
        Args:
            goal_request: Goal request parameters
        
        Returns:
            Complete execution result
        """
        
        logger.info(f"=== Processing Goal Request: {goal_request.get('name')} ===")
        
        start_time = datetime.now()
        
        try:
            # Get current game state
            game_state = await self._get_current_game_state()
            
            # === Phase 1: PAST Analysis ===
            logger.info("Phase 1: Analyzing past...")
            past_analysis = self.past_analyzer.analyze_similar_goals(
                self._create_temp_goal(goal_request),
                lookback_days=30
            )
            
            # === Phase 2: PRESENT Evaluation ===
            logger.info("Phase 2: Evaluating present...")
            present_eval = self.present_evaluator.evaluate_goal_feasibility(
                self._create_temp_goal(goal_request),
                game_state
            )
            
            # Check if goal is feasible
            if not present_eval['is_feasible']:
                logger.warning(f"Goal not feasible: {present_eval['blocking_factors']}")
                return {
                    'status': 'blocked',
                    'reason': 'Not feasible in current state',
                    'blocking_factors': present_eval['blocking_factors'],
                    'recommended_actions': present_eval['recommended_actions']
                }
            
            # === Phase 3: FUTURE Prediction ===
            logger.info("Phase 3: Predicting future...")
            future_pred = self.future_predictor.predict_goal_outcome(
                self._create_temp_goal(goal_request),
                game_state
            )
            
            # === Phase 4: SYNTHESIZE Goal ===
            logger.info("Phase 4: Synthesizing goal...")
            goal = self._synthesize_goal(
                request=goal_request,
                past=past_analysis,
                present=present_eval,
                future=future_pred
            )
            
            # === Phase 5: EXECUTE ===
            logger.info("Phase 5: Executing with layers and contingency...")
            result = await self._execute_with_layers(goal, game_state)
            
            # Record processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            result['processing_time'] = processing_time
            
            # Store completed goal
            if result.get('status') == 'success':
                self.completed_goals.append(goal)
            else:
                self.failed_goals.append(goal)
            
            logger.info(f"=== Goal Processing Complete: {result['status']} in {processing_time:.2f}s ===")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing goal: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                'status': 'error',
                'reason': str(e),
                'processing_time': (datetime.now() - start_time).total_seconds()
            }
    
    async def _execute_with_layers(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute goal using appropriate intelligence layer with contingency
        
        Layer priority (fastest first):
        4. Muscle Memory (instant, <10ms)
        3. Reflex (emergency, <100ms)
        2. Subconscious (ML pattern, <500ms)
        1. Conscious (strategic, <5s)
        
        Args:
            goal: Goal to execute
            game_state: Current game state
        
        Returns:
            Execution result
        """
        
        logger.info(f"Selecting intelligence layer for: {goal.name}")
        
        # === Layer 4: Muscle Memory ===
        if self.muscle_memory.enabled:
            if self.muscle_memory.has_cached_sequence(goal):
                logger.info("⚡ Using Layer 4: Muscle Memory")
                muscle_result = await self.muscle_memory.try_execute(goal, game_state)
                
                if muscle_result and muscle_result.get('success'):
                    goal.complete_success()
                    return {
                        'status': 'success',
                        'layer': 'muscle_memory',
                        'result': muscle_result,
                        'response_time': '<10ms'
                    }
        
        # === Layer 3: Reflex ===
        if self.reflex_layer.enabled:
            if goal.priority == GoalPriority.CRITICAL:
                logger.info("🚨 Using Layer 3: Reflex")
                reflex_result = await self.reflex_layer.try_execute(goal, game_state)
                
                if reflex_result and reflex_result.get('success'):
                    goal.complete_success()
                    return {
                        'status': 'success',
                        'layer': 'reflex',
                        'result': reflex_result,
                        'response_time': '<100ms'
                    }
        
        # === Layer 2: Subconscious (ML) ===
        if self.subconscious_layer.enabled:
            logger.info("🧠 Trying Layer 2: Subconscious (ML)")
            ml_prediction = await self.subconscious_layer.predict_execution(goal, game_state)
            
            if ml_prediction and ml_prediction['confidence'] > 0.85:
                logger.info(f"ML confidence: {ml_prediction['confidence']:.2f}")
                
                # Execute with contingency management
                result = await self.contingency_manager.execute_with_contingency(
                    goal,
                    game_state,
                    execution_plan=ml_prediction['plan']
                )
                
                if result['status'] == 'success':
                    # Learn from successful execution
                    self.subconscious_layer.learn_from_execution(goal, result, game_state)
                    
                    return {
                        'status': 'success',
                        'layer': 'subconscious',
                        'result': result,
                        'response_time': '<500ms'
                    }
                
                logger.warning("ML execution failed, falling through to Conscious layer")
        
        # === Layer 1: Conscious (CrewAI Strategic Planning) ===
        logger.info("🎯 Using Layer 1: Conscious (CrewAI)")
        conscious_plan = await self.conscious_layer.plan_execution(goal, game_state)
        
        # Execute with full contingency management
        result = await self.contingency_manager.execute_with_contingency(
            goal,
            game_state,
            execution_plan=conscious_plan['primary_plan']
        )
        
        return {
            'status': result['status'],
            'layer': 'conscious',
            'result': result,
            'response_time': f"{conscious_plan.get('planning_time', 0):.2f}s",
            'contingency_plans_used': result.get('plan_used', 'primary')
        }
    
    def _synthesize_goal(
        self,
        request: Dict[str, Any],
        past: Dict[str, Any],
        present: Dict[str, Any],
        future: Dict[str, Any]
    ) -> TemporalGoal:
        """
        Synthesize goal from temporal analysis
        
        Combines insights from past, present, and future to create
        an optimally configured goal with appropriate contingencies.
        
        Args:
            request: Original goal request
            past: Past analysis results
            present: Present evaluation results
            future: Future prediction results
        
        Returns:
            Fully configured TemporalGoal
        """
        
        logger.debug("Synthesizing goal from temporal analysis")
        
        # Extract primary plan from request or use defaults
        primary_plan = request.get('primary_plan', {
            'strategy': 'balanced',
            'actions': ['execute_goal'],
            'parameters': {}
        })
        
        # Adjust plan based on temporal analysis
        if past['success_rate'] < 0.5:
            # Low historical success → use conservative approach
            primary_plan['strategy'] = 'conservative'
            primary_plan['parameters']['caution_level'] = 'high'
        
        # Create contingency plans if not provided
        fallback_plans = request.get('fallback_plans', [])
        
        if len(fallback_plans) < 3:
            # Generate missing contingency plans
            logger.info("Generating missing contingency plans")
            # Use conscious planner to generate them
            # For now, use placeholders
        
        # Create goal
        goal = TemporalGoal(
            name=request.get('name', 'unnamed_goal'),
            description=request.get('description', ''),
            goal_type=request.get('goal_type', 'general'),
            priority=request.get('priority', GoalPriority.MEDIUM),
            estimated_duration=request.get('estimated_duration', future['expected_duration']),
            primary_plan=primary_plan,
            fallback_plans=fallback_plans,
            success_conditions=request.get('success_conditions', {}),
            past_context=past,
            present_state=present,
            future_predictions=future
        )
        
        logger.debug(f"Goal synthesized: {goal.id}")
        
        return goal
    
    def _create_temp_goal(self, request: Dict[str, Any]) -> TemporalGoal:
        """Create temporary goal for analysis"""
        
        return TemporalGoal(
            name=request.get('name', 'temp'),
            description=request.get('description', ''),
            goal_type=request.get('goal_type', 'general'),
            priority=request.get('priority', GoalPriority.MEDIUM),
            primary_plan=request.get('primary_plan', {}),
            success_conditions=request.get('success_conditions', {})
        )
    
    async def _get_current_game_state(self) -> Dict[str, Any]:
        """
        Get current game state snapshot
        
        In production, this would query actual game client state.
        """
        
        # Mock game state for development
        return {
            'hp_percent': 85,
            'sp_percent': 70,
            'weight_percent': 45,
            'character_level': 50,
            'party_size': 0,
            'map_name': 'prontera',
            'position': {'x': 150, 'y': 180},
            'hour': datetime.now().hour,
            'aggressive_monster_count': 2,
            'inventory': {
                'red_potion': 50,
                'fly_wing': 10
            },
            'zeny': 50000,
            'active_buffs': [],
            'active_debuffs': [],
            'in_safe_zone': False,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get coordinator statistics"""
        
        return {
            'active_goals': len(self.active_goals),
            'completed_goals': len(self.completed_goals),
            'failed_goals': len(self.failed_goals),
            'total_processed': len(self.completed_goals) + len(self.failed_goals),
            'success_rate': (
                len(self.completed_goals) / (len(self.completed_goals) + len(self.failed_goals))
                if (len(self.completed_goals) + len(self.failed_goals)) > 0
                else 0.0
            ),
            'layer_stats': {
                'muscle_memory': self.muscle_memory.get_statistics(),
                'reflex': {'enabled': self.reflex_layer.enabled},
                'subconscious': {'enabled': self.subconscious_layer.enabled},
                'conscious': {'enabled': self.conscious_layer.enabled}
            }
        }
    
    async def process_multiple_goals(
        self,
        goal_requests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process multiple goals with priority ordering
        
        Args:
            goal_requests: List of goal requests
        
        Returns:
            List of execution results
        """
        
        logger.info(f"Processing {len(goal_requests)} goals")
        
        # Get current game state
        game_state = await self._get_current_game_state()
        
        # Create temporary goals for prioritization
        temp_goals = [self._create_temp_goal(req) for req in goal_requests]
        
        # Prioritize goals
        prioritized = self.present_evaluator.prioritize_goals(temp_goals, game_state)
        
        # Execute in priority order
        results = []
        for goal in prioritized:
            # Find original request
            original_request = next(
                (req for req in goal_requests if req.get('name') == goal.name),
                None
            )
            
            if original_request:
                result = await self.process_goal(original_request)
                results.append(result)
        
        return results
    
    # ===== NEW ENHANCED METHODS =====
    
    def decompose_goal(self, parent_goal: TemporalGoal) -> List[TemporalGoal]:
        """
        Break complex goal into sub-goals hierarchically
        
        Decomposes goals based on time_scale:
        - Short (hours): Direct execution
        - Medium (days): Break into daily sub-goals
        - Long (endgame): Break into milestone-based sub-goals
        
        Args:
            parent_goal: Complex goal to decompose
        
        Returns:
            List of sub-goals in execution order
        """
        
        logger.info(f"Decomposing goal: {parent_goal.name} (time_scale: {parent_goal.time_scale})")
        
        sub_goals = []
        
        if parent_goal.time_scale == 'short':
            # Short goals don't need decomposition
            logger.debug("Short-term goal, no decomposition needed")
            return [parent_goal]
        
        elif parent_goal.time_scale == 'medium':
            # Medium: Break into daily chunks
            # Example: "Level up 5 times this week" → 5 daily sub-goals
            
            logger.info("Decomposing medium-term goal into daily sub-goals")
            
            if parent_goal.goal_type == 'farming':
                # Example: Farm 1000 mobs → 5 days × 200 mobs
                total_target = parent_goal.success_conditions.get('kills', 1000)
                days = parent_goal.estimated_duration // 86400 or 5  # Default 5 days
                daily_target = total_target // days
                
                for day in range(1, days + 1):
                    sub_goal = TemporalGoal(
                        name=f"{parent_goal.name}_day{day}",
                        description=f"Day {day} of {parent_goal.description}",
                        goal_type=parent_goal.goal_type,
                        priority=parent_goal.priority,
                        time_scale='short',
                        estimated_duration=86400,  # 1 day
                        primary_plan=parent_goal.primary_plan.copy(),
                        success_conditions={'kills': daily_target},
                        parent_goal_id=parent_goal.id
                    )
                    sub_goal.add_milestone(f"Day {day} completion", 1.0, f"Complete {daily_target} kills")
                    sub_goals.append(sub_goal)
                    parent_goal.sub_goals.append(sub_goal.id)
            
            elif parent_goal.goal_type == 'leveling':
                # Example: Level 50→60 → 10 level sub-goals
                current_level = parent_goal.metadata.get('current_level', 50)
                target_level = parent_goal.metadata.get('target_level', 60)
                
                for level in range(current_level + 1, target_level + 1):
                    sub_goal = TemporalGoal(
                        name=f"{parent_goal.name}_lv{level}",
                        description=f"Reach level {level}",
                        goal_type='leveling',
                        priority=parent_goal.priority,
                        time_scale='short',
                        estimated_duration=86400,
                        primary_plan=parent_goal.primary_plan.copy(),
                        success_conditions={'level': level},
                        parent_goal_id=parent_goal.id
                    )
                    sub_goals.append(sub_goal)
                    parent_goal.sub_goals.append(sub_goal.id)
        
        elif parent_goal.time_scale == 'long':
            # Long: Break into milestone-based phases
            # Example: "Reach Level 99" → Multiple milestone sub-goals
            
            logger.info("Decomposing long-term goal into milestone sub-goals")
            
            if parent_goal.goal_type == 'leveling':
                # Milestone-based: 50→60→70→80→90→99
                milestones = [60, 70, 80, 90, 99]
                current_level = parent_goal.metadata.get('current_level', 50)
                
                for milestone_level in milestones:
                    if milestone_level > current_level:
                        sub_goal = TemporalGoal(
                            name=f"{parent_goal.name}_milestone_lv{milestone_level}",
                            description=f"Reach milestone: Level {milestone_level}",
                            goal_type='leveling',
                            priority=parent_goal.priority,
                            time_scale='medium',
                            estimated_duration=604800,  # 1 week
                            primary_plan=parent_goal.primary_plan.copy(),
                            success_conditions={'level': milestone_level},
                            parent_goal_id=parent_goal.id
                        )
                        sub_goals.append(sub_goal)
                        parent_goal.sub_goals.append(sub_goal.id)
            
            elif parent_goal.goal_type == 'farming':
                # Continuous farming: Break into renewable short sessions
                sub_goal = TemporalGoal(
                    name=f"{parent_goal.name}_session",
                    description=f"Farming session from {parent_goal.description}",
                    goal_type='farming',
                    priority=parent_goal.priority,
                    time_scale='short',
                    estimated_duration=7200,  # 2 hours
                    primary_plan=parent_goal.primary_plan.copy(),
                    success_conditions={'kills': 200, 'duration': 7200},
                    parent_goal_id=parent_goal.id,
                    metadata={'renewable': True}  # Can be recreated
                )
                sub_goals.append(sub_goal)
                parent_goal.sub_goals.append(sub_goal.id)
        
        logger.info(f"Decomposed into {len(sub_goals)} sub-goals")
        
        return sub_goals if sub_goals else [parent_goal]
    
    def track_milestones(self, goal: TemporalGoal) -> Dict[str, Any]:
        """
        Validate milestone completion and update progress
        
        Args:
            goal: Goal with milestones to track
        
        Returns:
            Milestone tracking report
        """
        
        logger.info(f"Tracking milestones for goal: {goal.name}")
        
        if not goal.milestones:
            logger.debug("No milestones defined for this goal")
            return {
                'total_milestones': 0,
                'completed_milestones': 0,
                'progress_percent': 0.0,
                'next_milestone': None
            }
        
        completed_count = sum(1 for m in goal.milestones if m['completed'])
        total_count = len(goal.milestones)
        progress_percent = (completed_count / total_count) * 100 if total_count > 0 else 0
        
        # Find next uncompleted milestone
        next_milestone = None
        for milestone in goal.milestones:
            if not milestone['completed']:
                next_milestone = milestone
                break
        
        # Check if we should celebrate
        celebrations = []
        if progress_percent == 25:
            celebrations.append("🎯 25% Complete - Quarter Progress!")
        elif progress_percent == 50:
            celebrations.append("🔥 50% Complete - Halfway There!")
        elif progress_percent == 75:
            celebrations.append("⚡ 75% Complete - Final Stretch!")
        elif progress_percent == 100:
            celebrations.append("🎉 100% Complete - Goal Achieved!")
        
        report = {
            'total_milestones': total_count,
            'completed_milestones': completed_count,
            'pending_milestones': total_count - completed_count,
            'progress_percent': round(progress_percent, 2),
            'next_milestone': next_milestone,
            'celebrations': celebrations,
            'milestone_details': goal.milestones
        }
        
        logger.info(f"Progress: {progress_percent:.1f}% ({completed_count}/{total_count} milestones)")
        
        if celebrations:
            for celebration in celebrations:
                logger.info(celebration)
        
        return report
    
    def resolve_conflicts(self, goals: List[TemporalGoal]) -> List[TemporalGoal]:
        """
        Resolve conflicting goals intelligently
        
        Conflict types:
        1. Location conflict: Both need same map area
        2. Resource conflict: Both need same items/resources
        3. Time conflict: Both scheduled at same time
        4. Dependency conflict: Circular dependencies
        
        Resolution strategies:
        - Merge compatible goals
        - Sequence conflicting goals
        - Split resources
        - Escalate to user if unresolvable
        
        Args:
            goals: List of potentially conflicting goals
        
        Returns:
            List of resolved goals (may be merged/reordered)
        """
        
        logger.info(f"Resolving conflicts among {len(goals)} goals")
        
        # Build conflict map
        conflict_map: Dict[str, List[str]] = {}
        for goal in goals:
            if goal.has_conflicts():
                conflict_map[goal.id] = goal.conflicts
        
        if not conflict_map:
            logger.info("No conflicts detected")
            return goals
        
        logger.info(f"Detected {len(conflict_map)} goals with conflicts")
        
        resolved_goals = []
        merged_ids = set()
        
        for goal in goals:
            if goal.id in merged_ids:
                continue
            
            # Find conflicting goals
            conflicting = [g for g in goals if g.id in goal.conflicts and g.id not in merged_ids]
            
            if not conflicting:
                resolved_goals.append(goal)
                continue
            
            # Attempt to merge if compatible
            merged = self._attempt_merge(goal, conflicting)
            
            if merged:
                logger.info(f"Merged {len(conflicting) + 1} conflicting goals into: {merged.name}")
                resolved_goals.append(merged)
                merged_ids.add(goal.id)
                for c in conflicting:
                    merged_ids.add(c.id)
            else:
                # Cannot merge - sequence them instead
                logger.info(f"Cannot merge, sequencing conflicting goals")
                resolved_goals.append(goal)
                
                # Add dependencies to force sequencing
                for i, conflicting_goal in enumerate(conflicting):
                    if i == 0:
                        conflicting_goal.prerequisites.append(goal.id)
                    else:
                        conflicting_goal.prerequisites.append(conflicting[i-1].id)
                    resolved_goals.append(conflicting_goal)
                    merged_ids.add(conflicting_goal.id)
        
        logger.info(f"Resolved to {len(resolved_goals)} goals")
        
        return resolved_goals
    
    def _attempt_merge(self, goal1: TemporalGoal, conflicting: List[TemporalGoal]) -> Optional[TemporalGoal]:
        """
        Attempt to merge conflicting goals if they're compatible
        
        Compatible criteria:
        - Same goal_type
        - Same map/location
        - Similar time_scale
        - Non-exclusive resources
        """
        
        # For now, only merge farming goals in same location
        if goal1.goal_type != 'farming':
            return None
        
        compatible = [g for g in conflicting if g.goal_type == 'farming']
        
        if not compatible:
            return None
        
        # Check if same location
        map1 = goal1.primary_plan.get('parameters', {}).get('map')
        
        mergeable = [g for g in compatible
                     if g.primary_plan.get('parameters', {}).get('map') == map1]
        
        if not mergeable:
            return None
        
        # Merge goals
        logger.info(f"Merging farming goals in same location: {map1}")
        
        # Combine targets
        total_kills = goal1.success_conditions.get('kills', 0)
        monsters = [goal1.name.replace('farm_', '')]
        
        for g in mergeable:
            total_kills += g.success_conditions.get('kills', 0)
            monsters.append(g.name.replace('farm_', ''))
        
        merged_name = f"farm_{'_'.join(monsters)}"
        merged_description = f"Farm {', '.join(monsters)} in {map1}"
        
        merged_goal = TemporalGoal(
            name=merged_name,
            description=merged_description,
            goal_type='farming',
            priority=max(goal1.priority, max(g.priority for g in mergeable)),
            time_scale=goal1.time_scale,
            estimated_duration=goal1.estimated_duration,  # Keep original estimate
            primary_plan=goal1.primary_plan.copy(),
            success_conditions={'kills': total_kills, 'monsters': monsters},
            tags=list(set(goal1.tags + [tag for g in mergeable for tag in g.tags])),
            metadata={'merged_from': [goal1.id] + [g.id for g in mergeable]}
        )
        
        # Clear conflicts
        merged_goal.conflicts = []
        
        return merged_goal
    
    async def sync_with_openkore(self, goal: TemporalGoal) -> Dict[str, Any]:
        """
        Synchronize goal state with OpenKore Perl bridge
        
        Sends goal to OpenKore for execution and receives status updates.
        
        Args:
            goal: Goal to synchronize
        
        Returns:
            Synchronization result with execution status
        """
        
        logger.info(f"Syncing goal with OpenKore bridge: {goal.name}")
        
        try:
            # Send goal to bridge API
            bridge_url = "http://localhost:8765/api/v1/goals"
            
            goal_payload = {
                'goal_id': goal.id,
                'name': goal.name,
                'type': goal.goal_type,
                'priority': goal.priority.value,
                'actions': goal.get_active_plan_details().get('actions', []),
                'parameters': goal.get_active_plan_details().get('parameters', {}),
                'success_conditions': goal.success_conditions
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(bridge_url, json=goal_payload)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    logger.info(f"OpenKore bridge accepted goal: {result.get('status')}")
                    
                    return {
                        'synced': True,
                        'bridge_response': result,
                        'execution_id': result.get('execution_id'),
                        'estimated_completion': result.get('estimated_completion')
                    }
                else:
                    logger.warning(f"Bridge rejected goal: {response.status_code}")
                    return {
                        'synced': False,
                        'error': f"HTTP {response.status_code}",
                        'details': response.text
                    }
        
        except httpx.ConnectError:
            logger.warning("OpenKore bridge not available (connection refused)")
            return {
                'synced': False,
                'error': 'Bridge not available',
                'fallback': 'Will execute locally'
            }
        
        except Exception as e:
            logger.error(f"Error syncing with bridge: {str(e)}")
            return {
                'synced': False,
                'error': str(e)
            }
    
    async def request_game_state_from_bridge(self) -> Dict[str, Any]:
        """
        Get current game state from OpenKore Perl bridge
        
        Queries bridge API for real-time game state.
        
        Returns:
            Current game state or mock state if bridge unavailable
        """
        
        logger.debug("Requesting game state from OpenKore bridge")
        
        try:
            bridge_url = "http://localhost:8765/api/v1/state"
            
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(bridge_url)
                
                if response.status_code == 200:
                    state = response.json()
                    logger.debug(f"Received game state: HP={state.get('hp_percent')}%")
                    return state
                else:
                    logger.warning(f"Bridge returned error: {response.status_code}")
                    return await self._get_current_game_state()  # Fallback to mock
        
        except httpx.ConnectError:
            logger.debug("Bridge not available, using mock state")
            return await self._get_current_game_state()  # Fallback to mock
        
        except Exception as e:
            logger.error(f"Error requesting game state: {str(e)}")
            return await self._get_current_game_state()  # Fallback to mock
