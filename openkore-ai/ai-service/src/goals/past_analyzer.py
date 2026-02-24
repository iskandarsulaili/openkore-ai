"""
Past Analyzer - Historical Intelligence Component

Analyzes historical goal execution data to inform current decision-making.
Learns from past successes and failures to improve future goal planning.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from .goal_model import TemporalGoal, GoalStatus
import logging

logger = logging.getLogger(__name__)


class PastAnalyzer:
    """
    Analyzes historical data to inform current goals
    
    Key capabilities:
    - Find similar past goals based on context
    - Calculate success rates for goal types
    - Identify failure patterns
    - Learn optimal approaches
    - Analyze temporal patterns (time of day, etc.)
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize Past Analyzer
        
        Args:
            db_session: Database session for querying historical data
        """
        self.db = db_session
        self.similarity_threshold = 0.7  # Threshold for "similar" goals
    
    def analyze_similar_goals(
        self,
        current_goal: TemporalGoal,
        lookback_days: int = 30,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Find similar past goals and analyze their outcomes
        
        Args:
            current_goal: The goal to find similar historical examples for
            lookback_days: How far back to look in history
            limit: Maximum number of historical goals to analyze
        
        Returns:
            Comprehensive analysis including success rates, patterns, and recommendations
        """
        
        logger.info(f"Analyzing similar goals for: {current_goal.name}")
        
        # Query database for similar goals
        similar_goals = self._query_similar_goals(
            goal_type=current_goal.goal_type,
            present_state=current_goal.present_state,
            lookback_days=lookback_days,
            limit=limit
        )
        
        if not similar_goals:
            logger.warning(f"No similar historical goals found for type: {current_goal.goal_type}")
            return self._get_default_analysis()
        
        # Perform comprehensive analysis
        analysis = {
            'total_attempts': len(similar_goals),
            'success_rate': self._calc_success_rate(similar_goals),
            'avg_duration': self._calc_avg_duration(similar_goals),
            'duration_std_dev': self._calc_duration_std_dev(similar_goals),
            'common_failures': self._identify_failure_patterns(similar_goals),
            'best_approach': self._identify_best_approach(similar_goals),
            'worst_approach': self._identify_worst_approach(similar_goals),
            'time_patterns': self._analyze_time_patterns(similar_goals),
            'plan_effectiveness': self._analyze_plan_effectiveness(similar_goals),
            'risk_factors': self._identify_risk_factors(similar_goals),
            'recommended_adjustments': self._generate_recommendations(similar_goals, current_goal),
            'confidence': self._calculate_confidence(similar_goals)
        }
        
        logger.info(f"Analysis complete: {analysis['total_attempts']} similar goals, "
                   f"{analysis['success_rate']:.1%} success rate")
        
        return analysis
    
    def learn_from_failures(
        self,
        failed_goal: TemporalGoal
    ) -> Dict[str, Any]:
        """
        Extract lessons from a failed goal
        
        Args:
            failed_goal: The goal that failed
        
        Returns:
            Lessons learned including root cause and avoidance strategies
        """
        
        logger.info(f"Learning from failed goal: {failed_goal.id}")
        
        # Get similar failures
        similar_failures = self._query_similar_goals(
            goal_type=failed_goal.goal_type,
            present_state=failed_goal.present_state,
            status_filter=GoalStatus.FAILED,
            lookback_days=90,
            limit=50
        )
        
        # Identify root cause
        root_cause = self._identify_root_cause(failed_goal, similar_failures)
        
        # Generate avoidance strategy
        avoidance_strategy = self._generate_avoidance_strategy(failed_goal, root_cause)
        
        # Suggest parameter adjustments
        adjusted_params = self._suggest_parameter_adjustments(failed_goal, similar_failures)
        
        return {
            'root_cause': root_cause,
            'avoidance_strategy': avoidance_strategy,
            'adjusted_parameters': adjusted_params,
            'similar_failure_count': len(similar_failures),
            'failure_cluster_detected': len(similar_failures) > 5,
            'recommended_actions': self._generate_failure_actions(root_cause)
        }
    
    def get_success_probability(
        self,
        goal: TemporalGoal,
        plan_type: str = "primary"
    ) -> float:
        """
        Calculate expected success probability based on historical data
        
        Args:
            goal: Goal to calculate probability for
            plan_type: Which plan to calculate for (primary, alternative, etc.)
        
        Returns:
            Success probability (0.0 to 1.0)
        """
        
        similar_goals = self._query_similar_goals(
            goal_type=goal.goal_type,
            present_state=goal.present_state,
            lookback_days=30,
            limit=100
        )
        
        if not similar_goals:
            return 0.75  # Default moderate probability
        
        # Filter by plan type
        plan_goals = [g for g in similar_goals if g.get('active_plan') == plan_type]
        
        if not plan_goals:
            plan_goals = similar_goals  # Fallback to all similar goals
        
        success_count = sum(1 for g in plan_goals if g['status'] == GoalStatus.COMPLETED)
        probability = success_count / len(plan_goals) if plan_goals else 0.75
        
        # Apply confidence adjustment
        confidence = min(len(plan_goals) / 20, 1.0)  # More data = higher confidence
        baseline = 0.75
        adjusted_probability = baseline + (probability - baseline) * confidence
        
        return max(0.1, min(0.99, adjusted_probability))
    
    # ===== Private Helper Methods =====
    
    def _query_similar_goals(
        self,
        goal_type: str,
        present_state: Dict[str, Any],
        lookback_days: int = 30,
        limit: int = 100,
        status_filter: Optional[GoalStatus] = None
    ) -> List[Dict[str, Any]]:
        """
        Query database for similar historical goals
        
        Similarity is based on:
        - Goal type (exact match)
        - Character level (within 10 levels)
        - Map (same or similar)
        - Time of day (similar hour)
        - Party status (solo/party)
        """
        
        # Extract context for similarity matching
        char_level = present_state.get('character_level', 50)
        map_name = present_state.get('map_name', 'unknown')
        hour = present_state.get('hour', 12)
        party_size = present_state.get('party_size', 0)
        
        logger.debug(f"Querying similar goals: type={goal_type}, level≈{char_level}, "
                    f"map={map_name}, lookback={lookback_days}d")
        
        try:
            # Calculate time window for lookback
            from datetime import datetime, timedelta
            lookback_timestamp = int((datetime.now() - timedelta(days=lookback_days)).timestamp())
            
            # Build query with similarity criteria
            # We'll use lifecycle_states table which tracks goal progression
            query = """
                SELECT
                    ls.state_id,
                    ls.session_id,
                    ls.character_name,
                    ls.level,
                    ls.job_class,
                    ls.lifecycle_stage,
                    ls.current_goal,
                    ls.goal_progress,
                    ls.timestamp,
                    s.total_exp_gained,
                    s.total_zeny_gained,
                    s.total_deaths,
                    s.status as session_status
                FROM lifecycle_states ls
                JOIN sessions s ON ls.session_id = s.session_id
                WHERE ls.timestamp >= ?
                    AND json_extract(ls.current_goal, '$.goal_type') = ?
                    AND ls.level BETWEEN ? AND ?
            """
            
            params = [
                lookback_timestamp,
                goal_type,
                max(1, char_level - 10),  # Level range: ±10 levels
                char_level + 10
            ]
            
            # Add status filter if specified
            if status_filter:
                query += " AND json_extract(ls.current_goal, '$.status') = ?"
                params.append(status_filter.value)
            
            # Add ordering and limit
            query += " ORDER BY ls.timestamp DESC LIMIT ?"
            params.append(limit)
            
            # Execute query
            cursor = self.db.execute(query, tuple(params))
            rows = cursor.fetchall()
            
            # Transform results into goal-like dictionaries
            results = []
            for row in rows:
                import json
                
                # Parse the current_goal JSON
                try:
                    current_goal = json.loads(row[6]) if row[6] else {}
                except (json.JSONDecodeError, TypeError):
                    current_goal = {}
                
                # Calculate duration if available
                duration_seconds = None
                if 'started_at' in current_goal and 'completed_at' in current_goal:
                    try:
                        started = datetime.fromisoformat(current_goal['started_at'])
                        completed = datetime.fromisoformat(current_goal['completed_at'])
                        duration_seconds = int((completed - started).total_seconds())
                    except (ValueError, TypeError):
                        pass
                
                # Extract present state from goal
                present_state_data = current_goal.get('present_state', {})
                
                # Build result dictionary
                result = {
                    'state_id': row[0],
                    'session_id': row[1],
                    'character_name': row[2],
                    'character_level': row[3],
                    'job_class': row[4],
                    'lifecycle_stage': row[5],
                    'goal_type': goal_type,
                    'goal_progress': row[7],
                    'timestamp': row[8],
                    'created_at': datetime.fromtimestamp(row[8]),
                    'exp_gained': row[9] or 0,
                    'zeny_gained': row[10] or 0,
                    'deaths': row[11] or 0,
                    'session_status': row[12],
                    'status': GoalStatus(current_goal.get('status', 'unknown')) if current_goal.get('status') in [s.value for s in GoalStatus] else GoalStatus.PENDING,
                    'duration_seconds': duration_seconds,
                    'present_state': present_state_data,
                    'primary_plan': current_goal.get('primary_plan', {}),
                    'active_plan': current_goal.get('active_plan', 'primary'),
                    'failure_reason': current_goal.get('metadata', {}).get('failure_reason', 'unknown')
                }
                
                results.append(result)
            
            logger.info(f"Found {len(results)} similar historical goals")
            return results
            
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            logger.exception(e)
            # Return empty list on error - allows system to continue with defaults
            return []
    
    def _calc_success_rate(self, goals: List[Dict[str, Any]]) -> float:
        """Calculate success rate from goal list"""
        if not goals:
            return 0.0
        
        success_count = sum(1 for g in goals if g.get('status') == GoalStatus.COMPLETED)
        return success_count / len(goals)
    
    def _calc_avg_duration(self, goals: List[Dict[str, Any]]) -> int:
        """Calculate average execution duration in seconds"""
        durations = [g.get('duration_seconds', 0) for g in goals if g.get('duration_seconds')]
        return int(np.mean(durations)) if durations else 300
    
    def _calc_duration_std_dev(self, goals: List[Dict[str, Any]]) -> int:
        """Calculate standard deviation of duration"""
        durations = [g.get('duration_seconds', 0) for g in goals if g.get('duration_seconds')]
        return int(np.std(durations)) if len(durations) > 1 else 60
    
    def _identify_failure_patterns(self, goals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify common failure patterns"""
        
        failures = [g for g in goals if g.get('status') != GoalStatus.COMPLETED]
        
        if not failures:
            return []
        
        # Group by failure reason
        failure_reasons = defaultdict(int)
        for failure in failures:
            reason = failure.get('failure_reason', 'unknown')
            failure_reasons[reason] += 1
        
        # Sort by frequency
        patterns = [
            {
                'reason': reason,
                'count': count,
                'percentage': count / len(failures) * 100
            }
            for reason, count in sorted(
                failure_reasons.items(),
                key=lambda x: x[1],
                reverse=True
            )
        ]
        
        return patterns[:5]  # Top 5 failure patterns
    
    def _identify_best_approach(self, goals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify the most successful approach"""
        
        successful = [g for g in goals if g.get('status') == GoalStatus.COMPLETED]
        
        if not successful:
            return {'approach': 'unknown', 'success_rate': 0.0}
        
        # Group by primary plan strategy
        approaches = defaultdict(lambda: {'count': 0, 'success': 0, 'durations': []})
        
        for goal in goals:
            strategy = goal.get('primary_plan', {}).get('strategy', 'default')
            approaches[strategy]['count'] += 1
            if goal.get('status') == GoalStatus.COMPLETED:
                approaches[strategy]['success'] += 1
            if goal.get('duration_seconds'):
                approaches[strategy]['durations'].append(goal['duration_seconds'])
        
        # Calculate success rates
        best_approach = None
        best_score = 0
        
        for strategy, data in approaches.items():
            if data['count'] < 3:  # Need at least 3 samples
                continue
            
            success_rate = data['success'] / data['count']
            avg_duration = np.mean(data['durations']) if data['durations'] else 999999
            
            # Score: prioritize success rate, with duration as tiebreaker
            score = success_rate - (avg_duration / 10000)  # Normalize duration impact
            
            if score > best_score:
                best_score = score
                best_approach = {
                    'strategy': strategy,
                    'success_rate': success_rate,
                    'avg_duration': int(avg_duration) if data['durations'] else None,
                    'sample_count': data['count']
                }
        
        return best_approach or {'approach': 'unknown', 'success_rate': 0.0}
    
    def _identify_worst_approach(self, goals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify approaches to avoid"""
        
        # Similar to best approach, but looking for lowest success rate
        approaches = defaultdict(lambda: {'count': 0, 'success': 0})
        
        for goal in goals:
            strategy = goal.get('primary_plan', {}).get('strategy', 'default')
            approaches[strategy]['count'] += 1
            if goal.get('status') == GoalStatus.COMPLETED:
                approaches[strategy]['success'] += 1
        
        worst_approach = None
        worst_rate = 1.0
        
        for strategy, data in approaches.items():
            if data['count'] < 3:
                continue
            
            success_rate = data['success'] / data['count']
            if success_rate < worst_rate:
                worst_rate = success_rate
                worst_approach = {
                    'strategy': strategy,
                    'success_rate': success_rate,
                    'sample_count': data['count']
                }
        
        return worst_approach or {'approach': 'none', 'success_rate': 1.0}
    
    def _analyze_time_patterns(self, goals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze success rates by time of day, day of week, etc."""
        
        time_buckets = defaultdict(lambda: {'count': 0, 'success': 0})
        
        for goal in goals:
            if 'created_at' not in goal:
                continue
            
            created_at = goal['created_at']
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            
            hour = created_at.hour
            time_period = self._get_time_period(hour)
            
            time_buckets[time_period]['count'] += 1
            if goal.get('status') == GoalStatus.COMPLETED:
                time_buckets[time_period]['success'] += 1
        
        patterns = {}
        for period, data in time_buckets.items():
            if data['count'] > 0:
                patterns[period] = {
                    'success_rate': data['success'] / data['count'],
                    'sample_count': data['count']
                }
        
        return patterns
    
    def _get_time_period(self, hour: int) -> str:
        """Convert hour to time period"""
        if 6 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 18:
            return 'afternoon'
        elif 18 <= hour < 24:
            return 'evening'
        else:
            return 'night'
    
    def _analyze_plan_effectiveness(self, goals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze which plans (A/B/C/D) are most effective"""
        
        plan_stats = defaultdict(lambda: {'used': 0, 'success': 0})
        
        for goal in goals:
            active_plan = goal.get('active_plan', 'primary')
            plan_stats[active_plan]['used'] += 1
            if goal.get('status') == GoalStatus.COMPLETED:
                plan_stats[active_plan]['success'] += 1
        
        effectiveness = {}
        for plan, stats in plan_stats.items():
            if stats['used'] > 0:
                effectiveness[plan] = {
                    'success_rate': stats['success'] / stats['used'],
                    'usage_count': stats['used']
                }
        
        return effectiveness
    
    def _identify_risk_factors(self, goals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify conditions that increase failure risk"""
        
        # Analyze what conditions correlate with failure
        risk_factors = []
        
        # Example: Low HP correlates with failure
        low_hp_goals = [g for g in goals if g.get('present_state', {}).get('hp_percent', 100) < 30]
        if low_hp_goals:
            low_hp_failures = sum(1 for g in low_hp_goals if g.get('status') != GoalStatus.COMPLETED)
            if len(low_hp_goals) > 5:
                risk_factors.append({
                    'factor': 'low_hp',
                    'condition': 'hp_percent < 30',
                    'failure_rate': low_hp_failures / len(low_hp_goals),
                    'sample_count': len(low_hp_goals)
                })
        
        return risk_factors
    
    def _identify_root_cause(
        self,
        failed_goal: TemporalGoal,
        similar_failures: List[Dict[str, Any]]
    ) -> str:
        """Identify root cause of failure"""
        
        # Check goal metadata for explicit failure reason
        if 'failure_reason' in failed_goal.metadata:
            return failed_goal.metadata['failure_reason']
        
        # Analyze similar failures for common patterns
        if similar_failures:
            patterns = self._identify_failure_patterns(similar_failures)
            if patterns:
                return patterns[0]['reason']
        
        return "unknown - requires manual investigation"
    
    def _generate_avoidance_strategy(
        self,
        failed_goal: TemporalGoal,
        root_cause: str
    ) -> Dict[str, Any]:
        """Generate strategy to avoid similar failures"""
        
        strategies = {
            'insufficient_healing': {
                'strategy': 'Increase healing item stock by 50%',
                'adjustments': {'heal_threshold': 70, 'emergency_heal_threshold': 40}
            },
            'overweight': {
                'strategy': 'Store items more frequently',
                'adjustments': {'weight_threshold': 80, 'storage_frequency': 'every_30_min'}
            },
            'surrounded_by_mobs': {
                'strategy': 'Use more conservative positioning',
                'adjustments': {'max_aggro_count': 3, 'retreat_threshold': 2}
            },
            'timeout': {
                'strategy': 'Break goal into smaller sub-goals',
                'adjustments': {'timeout_multiplier': 1.5, 'enable_checkpoints': True}
            }
        }
        
        return strategies.get(root_cause, {
            'strategy': 'Use more conservative Plan C approach',
            'adjustments': {'default_plan': 'conservative'}
        })
    
    def _suggest_parameter_adjustments(
        self,
        failed_goal: TemporalGoal,
        similar_failures: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Suggest parameter adjustments to improve success"""
        
        adjustments = {}
        
        # Increase timeout if many timeouts
        timeout_failures = sum(
            1 for f in similar_failures
            if 'timeout' in f.get('failure_reason', '').lower()
        )
        if timeout_failures > len(similar_failures) * 0.3:
            adjustments['estimated_duration'] = int(failed_goal.estimated_duration * 1.5)
        
        # Increase failure threshold if many quick failures
        quick_failures = sum(
            1 for f in similar_failures
            if f.get('duration_seconds', 999) < 60
        )
        if quick_failures > len(similar_failures) * 0.3:
            adjustments['failure_threshold'] = failed_goal.failure_threshold + 1
        
        return adjustments
    
    def _generate_recommendations(
        self,
        similar_goals: List[Dict[str, Any]],
        current_goal: TemporalGoal
    ) -> List[str]:
        """Generate actionable recommendations"""
        
        recommendations = []
        
        success_rate = self._calc_success_rate(similar_goals)
        
        if success_rate < 0.5:
            recommendations.append(
                "[WARNING] Low success rate detected. Consider using conservative Plan C approach."
            )
        
        best_approach = self._identify_best_approach(similar_goals)
        if best_approach and best_approach.get('success_rate', 0) > 0.8:
            recommendations.append(
                f"[SUCCESS] Use '{best_approach['strategy']}' strategy "
                f"(success rate: {best_approach['success_rate']:.1%})"
            )
        
        worst_approach = self._identify_worst_approach(similar_goals)
        if worst_approach and worst_approach.get('success_rate', 1) < 0.3:
            recommendations.append(
                f"[ERROR] Avoid '{worst_approach['strategy']}' strategy "
                f"(failure rate: {1-worst_approach['success_rate']:.1%})"
            )
        
        return recommendations
    
    def _generate_failure_actions(self, root_cause: str) -> List[str]:
        """Generate specific actions to take based on failure root cause"""
        
        actions_map = {
            'insufficient_healing': [
                'Buy more healing items',
                'Increase healing threshold to 70%',
                'Enable emergency healing at 40%'
            ],
            'timeout': [
                'Break goal into smaller sub-goals',
                'Increase timeout by 50%',
                'Add progress checkpoints'
            ],
            'overweight': [
                'Store items before starting',
                'Set weight limit to 80%',
                'Enable auto-storage'
            ]
        }
        
        return actions_map.get(root_cause, [
            'Review goal parameters',
            'Use more conservative approach',
            'Monitor execution closely'
        ])
    
    def _calculate_confidence(self, similar_goals: List[Dict[str, Any]]) -> float:
        """
        Calculate confidence level in the analysis
        
        Confidence is based on:
        - Number of similar goals (more = higher confidence)
        - Consistency of outcomes (consistent = higher confidence)
        - Recency of data (recent = higher confidence)
        """
        
        if not similar_goals:
            return 0.0
        
        # Sample size factor (0.0 to 1.0)
        sample_factor = min(len(similar_goals) / 50, 1.0)
        
        # Consistency factor (variance in success rates)
        success_count = sum(1 for g in similar_goals if g.get('status') == GoalStatus.COMPLETED)
        success_rate = success_count / len(similar_goals)
        consistency_factor = 1.0 - abs(success_rate - 0.5) * 2  # Higher if close to extremes
        
        # Recency factor (recent data is more valuable)
        now = datetime.now()
        ages = []
        for goal in similar_goals:
            if 'created_at' in goal:
                created_at = goal['created_at']
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
                age_days = (now - created_at).days
                ages.append(age_days)
        
        if ages:
            avg_age = np.mean(ages)
            recency_factor = max(0, 1.0 - (avg_age / 90))  # Decay over 90 days
        else:
            recency_factor = 0.5
        
        # Combined confidence
        confidence = (sample_factor * 0.5 + consistency_factor * 0.3 + recency_factor * 0.2)
        
        return round(confidence, 2)
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """Return default analysis when no historical data available"""
        return {
            'total_attempts': 0,
            'success_rate': 0.75,  # Optimistic default
            'avg_duration': 300,
            'duration_std_dev': 60,
            'common_failures': [],
            'best_approach': {'approach': 'unknown', 'success_rate': 0.75},
            'worst_approach': {'approach': 'none', 'success_rate': 1.0},
            'time_patterns': {},
            'plan_effectiveness': {},
            'risk_factors': [],
            'recommended_adjustments': {},
            'confidence': 0.0,
            'note': 'No historical data available - using defaults'
        }
