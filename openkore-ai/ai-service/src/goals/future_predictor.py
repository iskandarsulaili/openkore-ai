"""
Future Predictor - Outcome Intelligence Component

Predicts outcomes of goal execution paths using simulation and ML models.

Enhanced with:
- Historical data-based planning (30+ days analysis)
- Resource consumption forecasting
- Pattern learning from past successes
"""

from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import logging
from datetime import datetime, timedelta
from collections import defaultdict

from .goal_model import TemporalGoal, ContingencyPlan

logger = logging.getLogger(__name__)


class FuturePredictor:
    """
    Predicts outcomes of goal execution paths
    
    Key capabilities:
    - Monte Carlo simulation of goal execution
    - Success probability prediction
    - Duration estimation
    - Risk identification
    - Outcome forecasting
    """
    
    def __init__(self, ml_model=None):
        """
        Initialize Future Predictor
        
        Args:
            ml_model: Optional ML model for predictions
        """
        self.model = ml_model
        self.simulation_runs = 1000  # Monte Carlo iterations
    
    def predict_goal_outcome(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Predict success probability and expected results
        
        Args:
            goal: Goal to predict outcomes for
            game_state: Current game state
        
        Returns:
            Comprehensive prediction including success probability, duration, rewards, risks
        """
        
        logger.info(f"Predicting outcomes for goal: {goal.name}")
        
        # Simulate primary plan
        primary_prediction = self._simulate_plan(
            goal.primary_plan,
            game_state,
            goal.goal_type
        )
        
        # Simulate fallback plans
        fallback_predictions = []
        for plan in goal.fallback_plans:
            prediction = self._simulate_plan(
                plan.dict(),
                game_state,
                goal.goal_type
            )
            fallback_predictions.append({
                'plan_name': plan.name,
                'plan_type': plan.plan_type,
                **prediction
            })
        
        # Select best alternative if primary has low success
        best_alternative = self._select_best_alternative(fallback_predictions)
        
        prediction = {
            'primary_plan': primary_prediction,
            'fallback_plans': fallback_predictions,
            'success_probability': primary_prediction['success_prob'],
            'expected_duration': primary_prediction['duration'],
            'expected_rewards': primary_prediction['rewards'],
            'risks': primary_prediction['risks'],
            'best_alternative': best_alternative,
            'confidence': self._calculate_prediction_confidence(primary_prediction),
            'recommendation': self._generate_recommendation(
                primary_prediction,
                fallback_predictions
            )
        }
        
        logger.info(f"Prediction: {prediction['success_probability']:.1%} success, "
                   f"{prediction['expected_duration']}s duration")
        
        return prediction
    
    def _simulate_plan(
        self,
        plan: Dict[str, Any],
        game_state: Dict[str, Any],
        goal_type: str
    ) -> Dict[str, Any]:
        """
        Monte Carlo simulation of plan execution
        
        Runs multiple simulations and averages results to predict outcomes.
        
        Args:
            plan: Execution plan details
            game_state: Current game state
            goal_type: Type of goal (farming, questing, etc.)
        
        Returns:
            Simulated outcome statistics
        """
        
        logger.debug(f"Running {self.simulation_runs} Monte Carlo simulations")
        
        # Run simulations
        results = []
        for _ in range(self.simulation_runs):
            result = self._single_simulation(plan, game_state, goal_type)
            results.append(result)
        
        # Aggregate results
        success_count = sum(1 for r in results if r['success'])
        success_prob = success_count / len(results)
        
        durations = [r['duration'] for r in results]
        avg_duration = int(np.mean(durations))
        duration_std = int(np.std(durations))
        
        # Extract rewards from successful runs
        successful_results = [r for r in results if r['success']]
        if successful_results:
            avg_exp = int(np.mean([r['rewards']['exp'] for r in successful_results]))
            avg_zeny = int(np.mean([r['rewards']['zeny'] for r in successful_results]))
        else:
            avg_exp = 0
            avg_zeny = 0
        
        # Identify common risks
        all_risks = []
        for r in results:
            all_risks.extend(r['risks'])
        
        risk_counts = {}
        for risk in all_risks:
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
        
        common_risks = [
            {'risk': risk, 'probability': count / len(results)}
            for risk, count in sorted(risk_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        return {
            'success_prob': success_prob,
            'duration': avg_duration,
            'duration_std': duration_std,
            'duration_range': (min(durations), max(durations)),
            'rewards': {
                'exp': avg_exp,
                'zeny': avg_zeny,
                'items': []  # Simplified for now
            },
            'risks': common_risks,
            'simulation_count': len(results)
        }
    
    def _single_simulation(
        self,
        plan: Dict[str, Any],
        game_state: Dict[str, Any],
        goal_type: str
    ) -> Dict[str, Any]:
        """
        Single simulation run
        
        Simulates one execution path with randomized outcomes based on probabilities.
        """
        
        # Base success probability from goal type
        base_success = {
            'farming': 0.80,
            'questing': 0.70,
            'storage': 0.95,
            'survival': 0.90,
            'exploration': 0.75
        }.get(goal_type, 0.75)
        
        # Adjust based on current state
        hp_percent = game_state.get('hp_percent', 100)
        sp_percent = game_state.get('sp_percent', 100)
        
        hp_factor = hp_percent / 100
        sp_factor = sp_percent / 100
        
        # Strategy factor
        strategy = plan.get('strategy', 'normal')
        strategy_factor = {
            'aggressive': 0.85,
            'normal': 1.0,
            'defensive': 1.1,
            'ultra_defensive': 1.2
        }.get(strategy, 1.0)
        
        # Calculate final success probability
        success_prob = base_success * hp_factor * sp_factor * strategy_factor
        success_prob = max(0.1, min(0.99, success_prob))
        
        # Simulate outcome
        success = np.random.random() < success_prob
        
        # Duration (with variance)
        base_duration = plan.get('estimated_duration', 300)
        duration_variance = np.random.normal(0, base_duration * 0.2)
        duration = max(30, int(base_duration + duration_variance))
        
        # Rewards (only if successful)
        if success:
            exp_reward = np.random.randint(1000, 5000)
            zeny_reward = np.random.randint(500, 2000)
        else:
            exp_reward = 0
            zeny_reward = 0
        
        # Risks encountered
        risks = []
        if hp_percent < 40:
            risks.append('low_hp')
        if sp_percent < 30:
            risks.append('low_sp')
        if np.random.random() < 0.1:
            risks.append('unexpected_aggro')
        if np.random.random() < 0.05:
            risks.append('connection_issue')
        
        return {
            'success': success,
            'duration': duration,
            'rewards': {'exp': exp_reward, 'zeny': zeny_reward},
            'risks': risks
        }
    
    def _select_best_alternative(
        self,
        fallback_predictions: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Select the best alternative plan if primary fails"""
        
        if not fallback_predictions:
            return None
        
        # Score each plan: prioritize success rate, then consider duration
        best_plan = None
        best_score = 0
        
        for pred in fallback_predictions:
            success_prob = pred['success_prob']
            duration = pred['duration']
            
            # Score: success rate is primary, efficiency is secondary
            score = success_prob - (duration / 10000)  # Normalize duration impact
            
            if score > best_score:
                best_score = score
                best_plan = pred['plan_name']
        
        return best_plan
    
    def _calculate_prediction_confidence(
        self,
        prediction: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence in prediction
        
        Confidence is based on:
        - Number of simulations run
        - Consistency of results (low std deviation)
        - Model availability
        """
        
        # Base confidence from simulation count
        sim_confidence = min(prediction['simulation_count'] / 1000, 1.0)
        
        # Consistency confidence (inverse of coefficient of variation)
        duration = prediction['duration']
        duration_std = prediction['duration_std']
        if duration > 0:
            cv = duration_std / duration  # Coefficient of variation
            consistency_confidence = max(0, 1.0 - cv)
        else:
            consistency_confidence = 0.5
        
        # Model confidence
        model_confidence = 0.8 if self.model else 0.5
        
        # Combined confidence
        confidence = (
            sim_confidence * 0.4 +
            consistency_confidence * 0.3 +
            model_confidence * 0.3
        )
        
        return round(confidence, 2)
    
    def _generate_recommendation(
        self,
        primary_prediction: Dict[str, Any],
        fallback_predictions: List[Dict[str, Any]]
    ) -> str:
        """Generate recommendation based on predictions"""
        
        primary_success = primary_prediction['success_prob']
        
        if primary_success >= 0.8:
            return "✅ Primary plan has high success probability. Proceed with Plan A."
        
        elif primary_success >= 0.6:
            return "⚠️ Primary plan has moderate success. Consider Plan B if risk-averse."
        
        elif primary_success >= 0.4:
            # Check if any fallback is significantly better
            best_fallback = max(
                fallback_predictions,
                key=lambda p: p['success_prob'],
                default=None
            )
            if best_fallback and best_fallback['success_prob'] > primary_success + 0.15:
                return f"⚠️ Low primary success. Recommend starting with {best_fallback['plan_name']} instead."
            else:
                return "⚠️ Moderate-low success rate. Prepare contingency plans."
        
        else:
            return "❌ Low success probability. Consider postponing or using Plan C conservative approach."
    
    def predict_contingency_activation(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Predict probability of needing each contingency plan
        
        Returns:
            Dict mapping plan names to activation probabilities
        """
        
        # Simulate to see which plans get activated
        activation_counts = {
            'primary': 0,
            'alternative': 0,
            'conservative': 0,
            'emergency': 0
        }
        
        # Simplified simulation
        primary_success = 0.75  # Base assumption
        
        for _ in range(1000):
            if np.random.random() < primary_success:
                activation_counts['primary'] += 1
            elif np.random.random() < 0.85:  # Plan B success rate
                activation_counts['alternative'] += 1
            elif np.random.random() < 0.95:  # Plan C success rate
                activation_counts['conservative'] += 1
            else:
                activation_counts['emergency'] += 1
        
        # Convert to probabilities
        total = sum(activation_counts.values())
        probabilities = {
            plan: count / total
            for plan, count in activation_counts.items()
        }
        
        return probabilities
    
    def forecast_timeline(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Forecast execution timeline with confidence intervals
        
        Returns:
            Timeline with estimated start, milestones, and completion times
        """
        
        now = datetime.now()
        
        # Predict duration
        prediction = self.predict_goal_outcome(goal, game_state)
        
        duration = prediction['expected_duration']
        std_dev = prediction['primary_plan']['duration_std']
        
        estimated_completion = now + timedelta(seconds=duration)
        
        # Confidence intervals (68%, 95%, 99.7%)
        ci_68 = (
            now + timedelta(seconds=duration - std_dev),
            now + timedelta(seconds=duration + std_dev)
        )
        ci_95 = (
            now + timedelta(seconds=duration - 2*std_dev),
            now + timedelta(seconds=duration + 2*std_dev)
        )
        
        return {
            'start_time': now,
            'estimated_completion': estimated_completion,
            'confidence_intervals': {
                '68%': ci_68,
                '95%': ci_95
            },
            'milestones': self._generate_milestones(goal, duration),
            'latest_acceptable_completion': goal.deadline if goal.deadline else None
        }
    
    def _generate_milestones(
        self,
        goal: TemporalGoal,
        total_duration: int
    ) -> List[Dict[str, Any]]:
        """Generate milestone predictions"""
        
        milestones = []
        
        # 25% progress
        milestones.append({
            'progress': 0.25,
            'time_offset': int(total_duration * 0.25),
            'description': "Quarter progress"
        })
        
        # 50% progress
        milestones.append({
            'progress': 0.50,
            'time_offset': int(total_duration * 0.50),
            'description': "Half progress"
        })
        
        # 75% progress
        milestones.append({
            'progress': 0.75,
            'time_offset': int(total_duration * 0.75),
            'description': "Three-quarter progress"
        })
        
        # 100% completion
        milestones.append({
            'progress': 1.0,
            'time_offset': total_duration,
            'description': "Completion"
        })
        
        return milestones
    
    # ===== NEW ENHANCED METHODS =====
    
    def plan_using_historical_data(
        self,
        goal_type: str,
        lookback_days: int = 30,
        historical_goals: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Use 30+ days of historical data to predict optimal approach
        
        Analyzes similar goals from the past to identify:
        - Best strategies (what worked)
        - Common pitfalls (what failed)
        - Optimal timing (when success rate is highest)
        - Resource patterns (what was needed)
        
        Args:
            goal_type: Type of goal to analyze (farming, questing, etc.)
            lookback_days: How far back to analyze
            historical_goals: Optional list of historical goal data
        
        Returns:
            Strategic plan based on historical patterns
        """
        
        logger.info(f"Planning using {lookback_days} days of historical data for {goal_type}")
        
        # In production, query database for historical goals
        # For now, use mock historical data
        if not historical_goals:
            historical_goals = self._get_mock_historical_data(goal_type, lookback_days)
        
        # Analyze success patterns
        success_analysis = self._analyze_success_patterns(historical_goals)
        
        # Identify best strategies
        best_strategies = self._identify_best_strategies(historical_goals)
        
        # Analyze timing patterns
        timing_analysis = self._analyze_timing_patterns(historical_goals)
        
        # Resource pattern analysis
        resource_patterns = self._analyze_resource_patterns(historical_goals)
        
        # Generate recommendations
        recommendations = self._generate_historical_recommendations(
            success_analysis,
            best_strategies,
            timing_analysis,
            resource_patterns
        )
        
        plan = {
            'goal_type': goal_type,
            'lookback_days': lookback_days,
            'historical_samples': len(historical_goals),
            'success_analysis': success_analysis,
            'best_strategies': best_strategies,
            'optimal_timing': timing_analysis,
            'resource_patterns': resource_patterns,
            'recommendations': recommendations,
            'confidence': self._calculate_historical_confidence(historical_goals)
        }
        
        logger.info(f"Historical plan generated: {recommendations[0] if recommendations else 'No recommendations'}")
        
        return plan
    
    def predict_resource_needs(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Forecast resource consumption for goal execution
        
        Predicts:
        - How many potions needed
        - How much time required
        - What skills must be ready
        - Expected zeny cost
        - API calls required
        - CPU/memory usage
        
        Args:
            goal: Goal to predict resource needs for
            game_state: Current game state
        
        Returns:
            Comprehensive resource forecast
        """
        
        logger.info(f"Predicting resource needs for: {goal.name}")
        
        # Base resource needs by goal type
        base_needs = {
            'farming': {
                'potions': 50,
                'time_minutes': 30,
                'zeny': 5000,
                'api_calls': 100,
                'cpu_percent': 15,
                'memory_mb': 256
            },
            'questing': {
                'potions': 30,
                'time_minutes': 45,
                'zeny': 10000,
                'api_calls': 150,
                'cpu_percent': 20,
                'memory_mb': 512
            },
            'storage': {
                'potions': 5,
                'time_minutes': 5,
                'zeny': 0,
                'api_calls': 10,
                'cpu_percent': 5,
                'memory_mb': 128
            },
            'survival': {
                'potions': 10,
                'time_minutes': 1,
                'zeny': 1000,
                'api_calls': 5,
                'cpu_percent': 2,
                'memory_mb': 64
            }
        }.get(goal.goal_type, {
            'potions': 20,
            'time_minutes': 20,
            'zeny': 5000,
            'api_calls': 50,
            'cpu_percent': 10,
            'memory_mb': 256
        })
        
        # Adjust for goal duration
        duration_factor = goal.estimated_duration / 1800  # Normalize to 30 min
        
        # Adjust for game state (low HP = more potions)
        hp_percent = game_state.get('hp_percent', 100)
        hp_factor = 2.0 if hp_percent < 50 else 1.0
        
        # Adjust for time scale
        scale_multipliers = {
            'short': 1.0,
            'medium': 5.0,  # 5x for medium-term
            'long': 20.0    # 20x for long-term
        }
        scale_factor = scale_multipliers.get(goal.time_scale, 1.0)
        
        # Calculate forecasted needs
        forecast = {
            'potions': {
                'hp_potions': int(base_needs['potions'] * duration_factor * hp_factor * scale_factor),
                'sp_potions': int(base_needs['potions'] * 0.5 * duration_factor * scale_factor),
                'confidence': 0.85
            },
            'time': {
                'estimated_minutes': int(base_needs['time_minutes'] * duration_factor * scale_factor),
                'min_minutes': int(base_needs['time_minutes'] * duration_factor * scale_factor * 0.7),
                'max_minutes': int(base_needs['time_minutes'] * duration_factor * scale_factor * 1.5),
                'confidence': 0.90
            },
            'zeny': {
                'estimated': int(base_needs['zeny'] * duration_factor * scale_factor),
                'buffer': int(base_needs['zeny'] * 0.2 * scale_factor),
                'confidence': 0.75
            },
            'skills': self._predict_required_skills(goal, game_state),
            'system_resources': {
                'api_calls_per_minute': int(base_needs['api_calls'] / base_needs['time_minutes']),
                'total_api_calls': int(base_needs['api_calls'] * duration_factor * scale_factor),
                'cpu_percent': base_needs['cpu_percent'],
                'memory_mb': base_needs['memory_mb'],
                'confidence': 0.95
            },
            'warnings': []
        }
        
        # Add warnings
        if forecast['potions']['hp_potions'] > game_state.get('inventory', {}).get('red_potion', 0):
            forecast['warnings'].append(f"⚠️ Need {forecast['potions']['hp_potions']} HP potions, have {game_state.get('inventory', {}).get('red_potion', 0)}")
        
        if forecast['zeny']['estimated'] > game_state.get('zeny', 0):
            forecast['warnings'].append(f"⚠️ Need {forecast['zeny']['estimated']} zeny, have {game_state.get('zeny', 0)}")
        
        logger.info(f"Resource forecast: {forecast['time']['estimated_minutes']}min, "
                   f"{forecast['potions']['hp_potions']} potions, "
                   f"{forecast['zeny']['estimated']} zeny")
        
        return forecast
    
    def _get_mock_historical_data(self, goal_type: str, lookback_days: int) -> List[Dict[str, Any]]:
        """Generate mock historical data for development"""
        
        historical_goals = []
        
        # Generate sample data
        for day in range(lookback_days):
            date = datetime.now() - timedelta(days=day)
            
            # Simulate varying success rates
            success = np.random.random() < 0.75
            
            historical_goals.append({
                'date': date.isoformat(),
                'goal_type': goal_type,
                'success': success,
                'duration': np.random.randint(600, 3600),
                'strategy': np.random.choice(['aggressive', 'normal', 'defensive']),
                'hour_of_day': date.hour,
                'resources_used': {
                    'potions': np.random.randint(20, 100),
                    'zeny': np.random.randint(1000, 10000)
                }
            })
        
        return historical_goals
    
    def _analyze_success_patterns(self, historical_goals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze what patterns lead to success"""
        
        total = len(historical_goals)
        successful = [g for g in historical_goals if g['success']]
        failed = [g for g in historical_goals if not g['success']]
        
        success_rate = len(successful) / total if total > 0 else 0
        
        # Analyze strategy success rates
        strategy_success = defaultdict(lambda: {'success': 0, 'total': 0})
        for goal in historical_goals:
            strategy = goal['strategy']
            strategy_success[strategy]['total'] += 1
            if goal['success']:
                strategy_success[strategy]['success'] += 1
        
        strategy_rates = {
            strategy: data['success'] / data['total'] if data['total'] > 0 else 0
            for strategy, data in strategy_success.items()
        }
        
        return {
            'overall_success_rate': round(success_rate, 2),
            'total_attempts': total,
            'successful_attempts': len(successful),
            'failed_attempts': len(failed),
            'strategy_success_rates': strategy_rates,
            'trend': 'improving' if len(successful[-7:]) > len(successful[:7]) else 'stable'
        }
    
    def _identify_best_strategies(self, historical_goals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify strategies with highest success rates"""
        
        strategy_analysis = defaultdict(lambda: {'successes': 0, 'attempts': 0, 'avg_duration': []})
        
        for goal in historical_goals:
            strategy = goal['strategy']
            strategy_analysis[strategy]['attempts'] += 1
            if goal['success']:
                strategy_analysis[strategy]['successes'] += 1
            strategy_analysis[strategy]['avg_duration'].append(goal['duration'])
        
        best_strategies = []
        for strategy, data in strategy_analysis.items():
            success_rate = data['successes'] / data['attempts'] if data['attempts'] > 0 else 0
            avg_duration = int(np.mean(data['avg_duration'])) if data['avg_duration'] else 0
            
            best_strategies.append({
                'strategy': strategy,
                'success_rate': round(success_rate, 2),
                'attempts': data['attempts'],
                'avg_duration_seconds': avg_duration,
                'score': success_rate - (avg_duration / 10000)  # Balance success vs speed
            })
        
        # Sort by score
        best_strategies.sort(key=lambda x: x['score'], reverse=True)
        
        return best_strategies[:3]  # Top 3
    
    def _analyze_timing_patterns(self, historical_goals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze when success rates are highest"""
        
        hour_success = defaultdict(lambda: {'success': 0, 'total': 0})
        
        for goal in historical_goals:
            hour = goal['hour_of_day']
            hour_success[hour]['total'] += 1
            if goal['success']:
                hour_success[hour]['success'] += 1
        
        hour_rates = {
            hour: data['success'] / data['total'] if data['total'] > 0 else 0
            for hour, data in hour_success.items()
        }
        
        # Find best time window
        if hour_rates:
            best_hour = max(hour_rates.items(), key=lambda x: x[1])
            worst_hour = min(hour_rates.items(), key=lambda x: x[1])
        else:
            best_hour = (12, 0.75)
            worst_hour = (3, 0.50)
        
        return {
            'hourly_success_rates': hour_rates,
            'best_time': {
                'hour': best_hour[0],
                'success_rate': round(best_hour[1], 2)
            },
            'worst_time': {
                'hour': worst_hour[0],
                'success_rate': round(worst_hour[1], 2)
            },
            'recommendation': f"Execute between {best_hour[0]}:00-{(best_hour[0]+2)%24}:00 for best results"
        }
    
    def _analyze_resource_patterns(self, historical_goals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze resource consumption patterns"""
        
        successful = [g for g in historical_goals if g['success']]
        
        if not successful:
            return {'pattern': 'insufficient_data'}
        
        potion_usage = [g['resources_used']['potions'] for g in successful]
        zeny_usage = [g['resources_used']['zeny'] for g in successful]
        
        return {
            'potions': {
                'avg': int(np.mean(potion_usage)),
                'min': int(np.min(potion_usage)),
                'max': int(np.max(potion_usage)),
                'recommended': int(np.percentile(potion_usage, 75))  # 75th percentile
            },
            'zeny': {
                'avg': int(np.mean(zeny_usage)),
                'min': int(np.min(zeny_usage)),
                'max': int(np.max(zeny_usage)),
                'recommended': int(np.percentile(zeny_usage, 75))
            }
        }
    
    def _generate_historical_recommendations(
        self,
        success_analysis: Dict,
        best_strategies: List[Dict],
        timing_analysis: Dict,
        resource_patterns: Dict
    ) -> List[str]:
        """Generate actionable recommendations from historical analysis"""
        
        recommendations = []
        
        # Success rate recommendation
        if success_analysis['overall_success_rate'] < 0.6:
            recommendations.append(f"⚠️ Low historical success rate ({success_analysis['overall_success_rate']:.0%}). Consider alternative approach.")
        else:
            recommendations.append(f"✅ Good historical success rate ({success_analysis['overall_success_rate']:.0%}).")
        
        # Strategy recommendation
        if best_strategies:
            best = best_strategies[0]
            recommendations.append(f"📊 Best strategy: {best['strategy']} ({best['success_rate']:.0%} success)")
        
        # Timing recommendation
        recommendations.append(timing_analysis['recommendation'])
        
        # Resource recommendation
        if 'potions' in resource_patterns:
            recommendations.append(f"💊 Stock {resource_patterns['potions']['recommended']} potions (historical 75th percentile)")
        
        return recommendations
    
    def _calculate_historical_confidence(self, historical_goals: List[Dict[str, Any]]) -> float:
        """Calculate confidence in historical analysis"""
        
        sample_size = len(historical_goals)
        
        # More samples = higher confidence
        if sample_size >= 30:
            return 0.95
        elif sample_size >= 20:
            return 0.85
        elif sample_size >= 10:
            return 0.75
        else:
            return 0.50
    
    def _predict_required_skills(self, goal: TemporalGoal, game_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Predict which skills will be needed"""
        
        # Simple skill predictions based on goal type
        skill_requirements = {
            'farming': [
                {'skill': 'heal', 'frequency': 'frequent', 'sp_cost': 10},
                {'skill': 'teleport', 'frequency': 'occasional', 'sp_cost': 10}
            ],
            'survival': [
                {'skill': 'emergency_heal', 'frequency': 'immediate', 'sp_cost': 20},
                {'skill': 'emergency_teleport', 'frequency': 'immediate', 'sp_cost': 10}
            ],
            'questing': [
                {'skill': 'buff', 'frequency': 'start', 'sp_cost': 30},
                {'skill': 'heal', 'frequency': 'frequent', 'sp_cost': 10},
                {'skill': 'attack_skill', 'frequency': 'frequent', 'sp_cost': 15}
            ]
        }.get(goal.goal_type, [])
        
        return skill_requirements
