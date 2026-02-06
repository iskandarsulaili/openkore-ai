"""
Conscious Goal Planner - Layer 1: Strategic Planning (CrewAI)

Uses multi-agent CrewAI system for strategic goal planning with comprehensive contingency generation.
Response time: 1-5 seconds
"""

from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from .goal_model import TemporalGoal, ContingencyPlan, PlanType

logger = logging.getLogger(__name__)


class ConsciousGoalPlanner:
    """
    CrewAI-based strategic goal planning with contingencies
    
    Uses multiple specialized agents:
    - Strategist: Creates optimal primary plan
    - Risk Analyst: Identifies potential failures
    - Contingency Specialist: Designs fallback plans B, C, D
    - Coordinator: Orchestrates multi-agent collaboration
    """
    
    def __init__(self):
        """Initialize Conscious Goal Planner with CrewAI agents"""
        self.enabled = True
        self.response_time_limit = 5.0  # seconds
        
        # In production, initialize actual CrewAI agents
        # self.crew = self._initialize_crew()
        
    async def plan_execution(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate strategic execution plan using CrewAI
        
        Args:
            goal: Goal to plan execution for
            game_state: Current game state
        
        Returns:
            Comprehensive execution plan with primary and contingencies
        """
        
        logger.info(f"Conscious planning for goal: {goal.name}")
        
        start_time = datetime.now()
        
        try:
            # Step 1: Analyze goal and context
            analysis = await self._analyze_goal_context(goal, game_state)
            
            # Step 2: Generate primary strategy
            primary_strategy = await self._generate_primary_strategy(goal, game_state, analysis)
            
            # Step 3: Identify risks
            risks = await self._identify_risks(goal, game_state, primary_strategy)
            
            # Step 4: Generate contingency plans
            contingencies = await self.generate_contingency_plans(goal, game_state)
            
            # Step 5: Validate complete plan
            validated_plan = self._validate_plan(primary_strategy, contingencies)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Conscious planning complete in {execution_time:.2f}s")
            
            return {
                'primary_plan': validated_plan['primary'],
                'contingency_plans': validated_plan['contingencies'],
                'analysis': analysis,
                'risks': risks,
                'planning_time': execution_time,
                'confidence': self._calculate_plan_confidence(validated_plan)
            }
            
        except Exception as e:
            logger.error(f"Conscious planning failed: {str(e)}")
            return self._get_fallback_plan(goal, game_state)
    
    async def generate_contingency_plans(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> List[ContingencyPlan]:
        """
        Generate 3 contingency plans (B, C, D) for any goal
        
        Plan B: Alternative approach (if A fails)
        Plan C: Conservative approach (guaranteed safe)
        Plan D: Emergency abort (last resort)
        
        Args:
            goal: Goal to generate contingencies for
            game_state: Current game state
        
        Returns:
            List of 3 contingency plans
        """
        
        logger.info(f"Generating contingency plans for: {goal.name}")
        
        contingencies = []
        
        # Plan B: Alternative Approach
        plan_b = await self._create_alternative_plan(goal, game_state)
        contingencies.append(plan_b)
        
        # Plan C: Conservative Approach
        plan_c = await self._create_conservative_plan(goal, game_state)
        contingencies.append(plan_c)
        
        # Plan D: Emergency Abort
        plan_d = await self._create_emergency_plan(goal, game_state)
        contingencies.append(plan_d)
        
        logger.info(f"Generated {len(contingencies)} contingency plans")
        
        return contingencies
    
    # ===== Private Methods =====
    
    async def _analyze_goal_context(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze goal context using CrewAI agents"""
        
        # Simulate CrewAI analysis
        # In production, this would use actual agent reasoning
        
        return {
            'goal_complexity': 'medium',
            'required_skills': ['combat', 'navigation', 'inventory_management'],
            'estimated_difficulty': 'moderate',
            'success_factors': [
                'sufficient_healing_items',
                'appropriate_character_level',
                'clear_path_to_objective'
            ],
            'challenges': [
                'potential_aggressive_monsters',
                'weight_management',
                'resource_depletion'
            ]
        }
    
    async def _generate_primary_strategy(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate optimal primary strategy"""
        
        # Use strategist agent to create optimal approach
        # This is a simulation - in production, use actual CrewAI
        
        if goal.goal_type == 'farming':
            return {
                'strategy': 'efficient_farming',
                'approach': 'aggressive',
                'actions': [
                    'teleport_to_optimal_spawn',
                    'engage_monsters_efficiently',
                    'maintain_heal_threshold_40',
                    'loot_high_value_first',
                    'return_when_overweight'
                ],
                'parameters': {
                    'attack_style': 'aoe_when_possible',
                    'heal_threshold': 40,
                    'loot_priority': 'value_over_quantity',
                    'weight_limit': 80
                }
            }
        
        elif goal.goal_type == 'survival':
            return {
                'strategy': 'immediate_safety',
                'approach': 'defensive',
                'actions': [
                    'stop_current_action',
                    'use_best_healing',
                    'assess_threats',
                    'retreat_if_necessary'
                ],
                'parameters': {
                    'heal_target': 80,
                    'threat_threshold': 3
                }
            }
        
        else:
            return {
                'strategy': 'balanced',
                'approach': 'normal',
                'actions': ['assess', 'plan', 'execute', 'verify'],
                'parameters': {}
            }
    
    async def _identify_risks(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any],
        strategy: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify potential risks using risk analyst agent"""
        
        risks = []
        
        # HP risk
        hp_percent = game_state.get('hp_percent', 100)
        if hp_percent < 50:
            risks.append({
                'risk': 'low_hp',
                'severity': 'HIGH' if hp_percent < 30 else 'MEDIUM',
                'probability': 0.7,
                'mitigation': 'Heal before starting or use conservative plan'
            })
        
        # Weight risk
        weight_percent = game_state.get('weight_percent', 0)
        if weight_percent > 70:
            risks.append({
                'risk': 'overweight',
                'severity': 'MEDIUM',
                'probability': 0.6,
                'mitigation': 'Store items before starting'
            })
        
        # Combat risk
        if goal.goal_type == 'farming':
            risks.append({
                'risk': 'multiple_aggro',
                'severity': 'MEDIUM',
                'probability': 0.4,
                'mitigation': 'Use defensive positioning, keep escape ready'
            })
        
        return risks
    
    async def _create_alternative_plan(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> ContingencyPlan:
        """Create Plan B: Alternative approach"""
        
        return ContingencyPlan(
            name=f"Plan B: Alternative {goal.goal_type.title()}",
            plan_type=PlanType.ALTERNATIVE,
            description=f"Alternative approach with better risk management",
            activation_conditions={
                'primary_failed': True,
                'failure_count': 3
            },
            actions=[
                'assess_failure_reason',
                'adjust_strategy',
                'retry_with_modifications',
                'monitor_closely'
            ],
            action_details={
                'strategy_adjustment': 'more_defensive',
                'heal_threshold': 60,  # Increase from 40
                'timeout_extension': 1.5
            },
            success_probability=0.90,
            estimated_duration=goal.estimated_duration + 120,
            risk_level="MEDIUM",
            required_resources={
                'healing_items': 50,  # More than primary
                'emergency_teleport': True
            }
        )
    
    async def _create_conservative_plan(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> ContingencyPlan:
        """Create Plan C: Conservative safe approach"""
        
        return ContingencyPlan(
            name=f"Plan C: Conservative {goal.goal_type.title()}",
            plan_type=PlanType.CONSERVATIVE,
            description=f"Maximum safety approach - guaranteed completion",
            activation_conditions={
                'alternative_failed': True,
                'high_risk_detected': True
            },
            actions=[
                'ensure_full_resources',
                'use_safest_route',
                'execute_minimal_actions',
                'constant_monitoring',
                'immediate_retreat_on_danger'
            ],
            action_details={
                'strategy': 'ultra_defensive',
                'heal_threshold': 80,
                'max_duration_per_attempt': 180,
                'safety_checks': 'every_30_seconds'
            },
            success_probability=0.98,
            estimated_duration=goal.estimated_duration * 2,
            risk_level="LOW",
            required_resources={
                'healing_items': 100,
                'emergency_teleport': True,
                'full_hp_sp': True
            },
            max_retries=3
        )
    
    async def _create_emergency_plan(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> ContingencyPlan:
        """Create Plan D: Emergency abort"""
        
        return ContingencyPlan(
            name="Plan D: Emergency Abort",
            plan_type=PlanType.EMERGENCY,
            description="Emergency abort - ensure character safety at all costs",
            activation_conditions={
                'all_plans_failed': True,
                'critical_situation': True
            },
            actions=[
                'stop_all_actions',
                'save_character_state',
                'emergency_teleport',
                'heal_to_full',
                'return_to_safe_zone',
                'log_comprehensive_failure'
            ],
            action_details={
                'teleport_method': 'fly_wing_or_skill',
                'safe_destination': 'capital_city',
                'heal_to_percent': 100,
                'generate_post_mortem': True
            },
            success_probability=0.999,
            estimated_duration=60,
            risk_level="MINIMAL",
            required_resources={
                'fly_wing': True
            },
            max_retries=0,  # No retries on emergency abort
            timeout_seconds=120
        )
    
    def _validate_plan(
        self,
        primary: Dict[str, Any],
        contingencies: List[ContingencyPlan]
    ) -> Dict[str, Any]:
        """Validate that plan has all required components"""
        
        # Ensure we have all 3 contingencies
        assert len(contingencies) >= 3, "Must have at least 3 contingency plans"
        
        # Ensure success probabilities increase
        for i in range(len(contingencies) - 1):
            assert contingencies[i+1].success_probability >= contingencies[i].success_probability, \
                "Contingency success rates must increase"
        
        return {
            'primary': primary,
            'contingencies': contingencies
        }
    
    def _calculate_plan_confidence(self, plan: Dict[str, Any]) -> float:
        """Calculate confidence in generated plan"""
        
        # Higher confidence if:
        # - More contingencies available
        # - Higher success probabilities
        # - More detailed action plans
        
        contingencies = plan['contingencies']
        avg_success = sum(c.success_probability for c in contingencies) / len(contingencies)
        
        confidence = 0.7 + (avg_success * 0.3)  # Base 0.7, up to 1.0
        
        return round(confidence, 2)
    
    def _get_fallback_plan(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get simple fallback plan if CrewAI fails"""
        
        logger.warning("Using fallback plan due to CrewAI failure")
        
        return {
            'primary_plan': {
                'strategy': 'simple',
                'actions': ['execute_goal_directly'],
                'parameters': {}
            },
            'contingency_plans': goal.fallback_plans,
            'analysis': {'mode': 'fallback'},
            'risks': [],
            'planning_time': 0,
            'confidence': 0.5
        }
