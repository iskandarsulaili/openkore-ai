"""
Present Evaluator - Current State Intelligence Component

Evaluates current game state to assess goal feasibility and prioritize goals dynamically.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from .goal_model import TemporalGoal, GoalPriority, GoalStatus

logger = logging.getLogger(__name__)


class PresentEvaluator:
    """
    Evaluates current game state to prioritize and assess goals
    
    Key capabilities:
    - Assess goal feasibility given current state
    - Calculate risk levels
    - Check resource availability
    - Dynamically prioritize goals
    - Evaluate environmental factors
    """
    
    def __init__(self):
        """Initialize Present Evaluator"""
        self.risk_thresholds = {
            'LOW': (0.0, 0.2),
            'MEDIUM': (0.2, 0.5),
            'HIGH': (0.5, 0.8),
            'CRITICAL': (0.8, 1.0)
        }
    
    def evaluate_goal_feasibility(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Determine if goal is achievable given current state
        
        Args:
            goal: The goal to evaluate
            game_state: Current game state snapshot
        
        Returns:
            Comprehensive feasibility assessment
        """
        
        logger.info(f"Evaluating feasibility for goal: {goal.name}")
        
        # Check prerequisites
        prerequisites_met = self._check_prerequisites(goal, game_state)
        
        # Assess risk
        risk_assessment = self._assess_risk(goal, game_state)
        
        # Check resources
        resource_check = self._check_resources(goal, game_state)
        
        # Analyze environment
        env_factors = self._analyze_environment(game_state)
        
        # Select best plan
        recommended_plan = self._select_best_plan(goal, game_state, risk_assessment)
        
        # Overall feasibility
        is_feasible = (
            prerequisites_met['all_met'] and
            resource_check['sufficient'] and
            risk_assessment['risk_level'] != 'CRITICAL'
        )
        
        evaluation = {
            'is_feasible': is_feasible,
            'prerequisites': prerequisites_met,
            'risk_assessment': risk_assessment,
            'resource_availability': resource_check,
            'environmental_factors': env_factors,
            'recommended_plan': recommended_plan,
            'blocking_factors': self._identify_blocking_factors(
                prerequisites_met,
                resource_check,
                risk_assessment
            ),
            'estimated_success_probability': self._estimate_success(
                goal,
                risk_assessment,
                resource_check
            ),
            'recommended_actions': self._generate_preparation_actions(
                goal,
                prerequisites_met,
                resource_check
            )
        }
        
        logger.info(f"Feasibility: {is_feasible}, Risk: {risk_assessment['risk_level']}, "
                   f"Success probability: {evaluation['estimated_success_probability']:.1%}")
        
        return evaluation
    
    def prioritize_goals(
        self,
        goals: List[TemporalGoal],
        game_state: Dict[str, Any]
    ) -> List[TemporalGoal]:
        """
        Dynamically prioritize goals based on current context
        
        Priority factors:
        1. Survival needs (HP < 30% → prioritize healing)
        2. Time sensitivity (deadline approaching → higher priority)
        3. Resource optimization (overweight → prioritize storage)
        4. Opportunity cost (rare event → interrupt other goals)
        
        Args:
            goals: List of goals to prioritize
            game_state: Current game state
        
        Returns:
            Sorted list of goals (highest priority first)
        """
        
        logger.info(f"Prioritizing {len(goals)} goals")
        
        scored_goals = []
        
        for goal in goals:
            score = self._calculate_priority_score(goal, game_state)
            scored_goals.append((score, goal))
            
            logger.debug(f"Goal '{goal.name}' scored {score:.2f}")
        
        # Sort by score (descending)
        sorted_goals = [goal for _, goal in sorted(scored_goals, reverse=True)]
        
        logger.info(f"Top priority: {sorted_goals[0].name if sorted_goals else 'none'}")
        
        return sorted_goals
    
    # ===== Private Helper Methods =====
    
    def _check_prerequisites(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if goal prerequisites are met"""
        
        prerequisites_status = []
        
        # Check prerequisite goals
        for prereq_id in goal.prerequisites:
            # In production, query database for prerequisite status
            # For now, assume they're met
            prerequisites_status.append({
                'id': prereq_id,
                'met': True,
                'reason': 'Prerequisite goal completed'
            })
        
        # Check character level requirements
        if 'min_level' in goal.metadata:
            min_level = goal.metadata['min_level']
            char_level = game_state.get('character_level', 1)
            met = char_level >= min_level
            prerequisites_status.append({
                'id': 'min_level',
                'met': met,
                'reason': f"Character level {char_level} >= {min_level}" if met else f"Need level {min_level}"
            })
        
        all_met = all(p['met'] for p in prerequisites_status)
        
        return {
            'all_met': all_met,
            'details': prerequisites_status,
            'unmet_count': sum(1 for p in prerequisites_status if not p['met'])
        }
    
    def _assess_risk(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess risk level for goal execution"""
        
        risk_score = 0.0
        risk_factors = []
        
        # HP factor
        hp_percent = game_state.get('hp_percent', 100)
        if hp_percent < 30:
            risk_score += 0.4
            risk_factors.append({'factor': 'low_hp', 'severity': 'HIGH', 'value': hp_percent})
        elif hp_percent < 50:
            risk_score += 0.2
            risk_factors.append({'factor': 'medium_hp', 'severity': 'MEDIUM', 'value': hp_percent})
        
        # SP factor
        sp_percent = game_state.get('sp_percent', 100)
        if sp_percent < 20:
            risk_score += 0.3
            risk_factors.append({'factor': 'low_sp', 'severity': 'HIGH', 'value': sp_percent})
        
        # Weight factor
        weight_percent = game_state.get('weight_percent', 0)
        if weight_percent > 90:
            risk_score += 0.3
            risk_factors.append({'factor': 'overweight', 'severity': 'HIGH', 'value': weight_percent})
        elif weight_percent > 70:
            risk_score += 0.1
            risk_factors.append({'factor': 'heavy', 'severity': 'MEDIUM', 'value': weight_percent})
        
        # Enemy count factor
        aggressive_count = game_state.get('aggressive_monster_count', 0)
        if aggressive_count > 10:
            risk_score += 0.4
            risk_factors.append({'factor': 'many_aggro', 'severity': 'CRITICAL', 'value': aggressive_count})
        elif aggressive_count > 5:
            risk_score += 0.2
            risk_factors.append({'factor': 'some_aggro', 'severity': 'MEDIUM', 'value': aggressive_count})
        
        # Determine risk level
        risk_level = 'LOW'
        for level, (min_risk, max_risk) in self.risk_thresholds.items():
            if min_risk <= risk_score < max_risk:
                risk_level = level
                break
        
        return {
            'risk_score': min(risk_score, 1.0),
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'mitigation_required': risk_score > 0.5,
            'mitigation_suggestions': self._suggest_risk_mitigation(risk_factors)
        }
    
    def _check_resources(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if required resources are available"""
        
        # Extract required resources from goal
        required = goal.primary_plan.get('required_resources', {})
        
        # Check each resource
        resource_status = {}
        insufficient = []
        
        # Healing items
        if 'healing_items' in required:
            available = game_state.get('inventory', {}).get('red_potion', 0)
            needed = required['healing_items']
            sufficient = available >= needed
            resource_status['healing_items'] = {
                'available': available,
                'needed': needed,
                'sufficient': sufficient
            }
            if not sufficient:
                insufficient.append('healing_items')
        
        # Zeny
        if 'zeny' in required:
            available = game_state.get('zeny', 0)
            needed = required['zeny']
            sufficient = available >= needed
            resource_status['zeny'] = {
                'available': available,
                'needed': needed,
                'sufficient': sufficient
            }
            if not sufficient:
                insufficient.append('zeny')
        
        return {
            'sufficient': len(insufficient) == 0,
            'resources': resource_status,
            'insufficient': insufficient,
            'acquisition_actions': self._suggest_resource_acquisition(insufficient)
        }
    
    def _analyze_environment(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze environmental factors"""
        
        return {
            'map_name': game_state.get('map_name', 'unknown'),
            'map_crowded': game_state.get('player_count', 0) > 20,
            'weather': game_state.get('weather', 'clear'),
            'time_of_day': game_state.get('hour', 12),
            'server_lag': game_state.get('ping_ms', 50) > 200,
            'party_status': {
                'in_party': game_state.get('party_size', 0) > 1,
                'party_size': game_state.get('party_size', 0)
            },
            'buffs_active': game_state.get('active_buffs', []),
            'debuffs_active': game_state.get('active_debuffs', [])
        }
    
    def _select_best_plan(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any],
        risk_assessment: Dict[str, Any]
    ) -> str:
        """Select which plan (A/B/C/D) to use based on current conditions"""
        
        risk_level = risk_assessment['risk_level']
        
        # High risk → use conservative approach
        if risk_level == 'CRITICAL':
            return 'emergency'
        elif risk_level == 'HIGH':
            return 'conservative'
        elif risk_level == 'MEDIUM':
            # Check if we have good success history with primary
            # For now, use alternative for medium risk
            return 'alternative'
        else:
            return 'primary'
    
    def _identify_blocking_factors(
        self,
        prerequisites: Dict[str, Any],
        resources: Dict[str, Any],
        risk: Dict[str, Any]
    ) -> List[str]:
        """Identify what's blocking goal execution"""
        
        blockers = []
        
        if not prerequisites['all_met']:
            blockers.append('Prerequisites not met')
        
        if not resources['sufficient']:
            blockers.extend([f"Insufficient {r}" for r in resources['insufficient']])
        
        if risk['risk_level'] == 'CRITICAL':
            blockers.append('Risk level too high')
        
        return blockers
    
    def _estimate_success(
        self,
        goal: TemporalGoal,
        risk: Dict[str, Any],
        resources: Dict[str, Any]
    ) -> float:
        """Estimate success probability given current conditions"""
        
        base_probability = 0.75
        
        # Adjust for risk
        if risk['risk_level'] == 'CRITICAL':
            base_probability *= 0.3
        elif risk['risk_level'] == 'HIGH':
            base_probability *= 0.6
        elif risk['risk_level'] == 'MEDIUM':
            base_probability *= 0.85
        
        # Adjust for resources
        if not resources['sufficient']:
            base_probability *= 0.7
        
        return max(0.1, min(0.99, base_probability))
    
    def _generate_preparation_actions(
        self,
        goal: TemporalGoal,
        prerequisites: Dict[str, Any],
        resources: Dict[str, Any]
    ) -> List[str]:
        """Generate list of actions to prepare for goal execution"""
        
        actions = []
        
        if not prerequisites['all_met']:
            actions.append("Complete prerequisite goals first")
        
        if not resources['sufficient']:
            for resource in resources['insufficient']:
                if resource == 'healing_items':
                    actions.append("Buy healing items from NPC")
                elif resource == 'zeny':
                    actions.append("Farm zeny or sell items")
        
        return actions
    
    def _suggest_risk_mitigation(self, risk_factors: List[Dict[str, Any]]) -> List[str]:
        """Suggest actions to mitigate identified risks"""
        
        suggestions = []
        
        for factor in risk_factors:
            if factor['factor'] == 'low_hp':
                suggestions.append("Heal to at least 70% HP before starting")
            elif factor['factor'] == 'low_sp':
                suggestions.append("Recover SP or use SP items")
            elif factor['factor'] == 'overweight':
                suggestions.append("Store items to reduce weight below 70%")
            elif factor['factor'] == 'many_aggro':
                suggestions.append("Clear aggressive monsters or move to safer area")
        
        return suggestions
    
    def _suggest_resource_acquisition(self, insufficient: List[str]) -> List[str]:
        """Suggest how to acquire missing resources"""
        
        actions = []
        
        for resource in insufficient:
            if resource == 'healing_items':
                actions.append("Visit potion shop: buy 100 Red Potions")
            elif resource == 'zeny':
                actions.append("Farm Poring for 30 minutes or sell inventory items")
            elif resource == 'equipment':
                actions.append("Purchase required equipment from NPCs or other players")
        
        return actions
    
    def _calculate_priority_score(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> float:
        """
        Calculate dynamic priority score for goal
        
        Higher score = higher priority
        """
        
        score = float(goal.priority.value) * 10  # Base score from priority (10-50)
        
        # Survival urgency (HP/SP critical)
        hp_percent = game_state.get('hp_percent', 100)
        if hp_percent < 20 and goal.goal_type == 'survival':
            score += 100  # Extreme urgency
        elif hp_percent < 40 and goal.goal_type == 'survival':
            score += 50
        
        # Deadline urgency
        if goal.deadline:
            time_remaining = goal.get_time_remaining()
            if time_remaining is not None:
                if time_remaining < 300:  # Less than 5 minutes
                    score += 30
                elif time_remaining < 1800:  # Less than 30 minutes
                    score += 15
        
        # Resource optimization (overweight)
        weight_percent = game_state.get('weight_percent', 0)
        if weight_percent > 90 and goal.goal_type == 'storage':
            score += 40
        elif weight_percent > 80 and goal.goal_type == 'storage':
            score += 20
        
        # Opportunity (rare event)
        if goal.metadata.get('is_rare_opportunity'):
            score += 25
        
        # Already in progress
        if goal.status == GoalStatus.IN_PROGRESS:
            score += 10  # Slight boost to continue current goal
        
        # Failed previously (reduce priority slightly)
        if goal.failure_count > 0:
            score -= goal.failure_count * 2
        
        return score
