"""
PerformanceAnalyst Agent
Tracks and reports macro effectiveness metrics
"""

import logging
from typing import Dict, List
from datetime import datetime
from crewai import Agent, Task, Crew
from pydantic import BaseModel, Field
from llm.provider_chain import llm_chain

logger = logging.getLogger(__name__)


class PerformanceReport(BaseModel):
    """Comprehensive performance report"""
    session_id: str = Field(..., description="Session identifier")
    time_window: Dict = Field(..., description="Analysis time window")
    overall_metrics: Dict = Field(..., description="Aggregate metrics")
    macro_effectiveness: Dict = Field(..., description="Per-macro effectiveness")
    recommendations: List[str] = Field(..., description="Strategic recommendations")
    trends: Dict = Field(default_factory=dict, description="Performance trends")


class PerformanceAnalyst:
    """
    PerformanceAnalyst Agent
    
    Role: Track macro effectiveness and provide feedback loop data
    Capabilities:
    - Monitor macro execution metrics in real-time
    - Calculate performance KPIs (EXP/hour, death rate, efficiency)
    - Detect performance degradation
    - Generate reports for conscious layer feedback
    """
    
    def __init__(self, db_connection=None):
        """Initialize PerformanceAnalyst agent"""
        self.db = db_connection
        self.agent = self._create_agent()
        self._metric_history = []
        
        logger.info("PerformanceAnalyst agent initialized")
    
    def _create_agent(self) -> Agent:
        """Create the CrewAI agent"""
        return Agent(
            role="Macro Performance Analyst",
            goal="Track and analyze macro system effectiveness through comprehensive metrics",
            backstory="""You are a data analyst specializing in automation system performance.
            You excel at:
            - Real-time performance monitoring
            - Statistical analysis and trend detection
            - KPI calculation and reporting
            - Identifying correlations between actions and outcomes
            
            Your task is to continuously monitor the macro system, calculate key performance
            indicators, and provide actionable insights for system improvement.""",
            verbose=True,
            allow_delegation=False,
            llm=llm_chain.get_crewai_llm()
        )
    
    def calculate_exp_rate_tool(self, session_data: Dict) -> Dict:
        """
        Calculate experience gain rate
        
        Args:
            session_data: Session metrics
            
        Returns:
            EXP rate analysis
        """
        start_exp = session_data.get('start_exp', 0)
        current_exp = session_data.get('current_exp', 0)
        duration_seconds = session_data.get('duration_seconds', 1)
        
        exp_gained = current_exp - start_exp
        exp_per_second = exp_gained / max(duration_seconds, 1)
        exp_per_hour = exp_per_second * 3600
        
        return {
            'exp_gained': exp_gained,
            'exp_per_hour': int(exp_per_hour),
            'duration_minutes': duration_seconds / 60,
            'efficiency': 'high' if exp_per_hour > 40000 else 'moderate' if exp_per_hour > 20000 else 'low'
        }
    
    def track_death_rate_tool(self, session_data: Dict) -> Dict:
        """
        Track character death rate
        
        Args:
            session_data: Session metrics
            
        Returns:
            Death rate analysis
        """
        deaths = session_data.get('deaths', 0)
        duration_hours = session_data.get('duration_seconds', 3600) / 3600
        
        deaths_per_hour = deaths / max(duration_hours, 0.1)
        
        safety_rating = 'excellent' if deaths_per_hour == 0 else \
                       'good' if deaths_per_hour < 0.5 else \
                       'acceptable' if deaths_per_hour < 1.0 else \
                       'poor'
        
        return {
            'total_deaths': deaths,
            'deaths_per_hour': deaths_per_hour,
            'safety_rating': safety_rating,
            'needs_defensive_macro': deaths_per_hour > 0.5
        }
    
    def measure_efficiency_tool(self, session_data: Dict) -> Dict:
        """
        Measure overall farming efficiency
        
        Args:
            session_data: Session metrics
            
        Returns:
            Efficiency analysis
        """
        zeny_gained = session_data.get('zeny_gained', 0)
        items_collected = session_data.get('items_collected', 0)
        duration_hours = session_data.get('duration_seconds', 3600) / 3600
        
        zeny_per_hour = zeny_gained / max(duration_hours, 0.1)
        items_per_hour = items_collected / max(duration_hours, 0.1)
        
        # Calculate composite efficiency score
        efficiency_score = min(1.0, (
            (zeny_per_hour / 50000) * 0.4 +  # Zeny weight: 40%
            (items_per_hour / 100) * 0.3 +    # Items weight: 30%
            0.3  # Base efficiency: 30%
        ))
        
        return {
            'zeny_per_hour': int(zeny_per_hour),
            'items_per_hour': int(items_per_hour),
            'efficiency_score': efficiency_score,
            'rating': 'excellent' if efficiency_score > 0.8 else \
                     'good' if efficiency_score > 0.6 else \
                     'acceptable' if efficiency_score > 0.4 else \
                     'poor'
        }
    
    async def analyze_performance(
        self,
        session_id: str,
        session_data: Dict,
        macro_stats: Dict
    ) -> PerformanceReport:
        """
        Generate comprehensive performance report
        
        Args:
            session_id: Session identifier
            session_data: Overall session metrics
            macro_stats: Per-macro statistics
            
        Returns:
            Performance report with recommendations
        """
        logger.info(f"Analyzing performance for session: {session_id}")
        
        # Calculate metrics
        exp_analysis = self.calculate_exp_rate_tool(session_data)
        death_analysis = self.track_death_rate_tool(session_data)
        efficiency_analysis = self.measure_efficiency_tool(session_data)
        
        # Analyze macro effectiveness
        macro_effectiveness = {}
        for macro_name, stats in macro_stats.items():
            success_rate = (stats.get('success_count', 0) / 
                          max(stats.get('execution_count', 1), 1)) * 100
            
            macro_effectiveness[macro_name] = {
                'execution_count': stats.get('execution_count', 0),
                'success_rate': success_rate,
                'impact_score': self._calculate_impact_score(stats, session_data),
                'performance': 'excellent' if success_rate > 95 else \
                              'good' if success_rate > 85 else \
                              'acceptable' if success_rate > 70 else \
                              'poor'
            }
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            exp_analysis,
            death_analysis,
            efficiency_analysis,
            macro_effectiveness
        )
        
        # Record metric history
        self._metric_history.append({
            'timestamp': datetime.now().isoformat(),
            'exp_per_hour': exp_analysis['exp_per_hour'],
            'deaths_per_hour': death_analysis['deaths_per_hour'],
            'efficiency_score': efficiency_analysis['efficiency_score']
        })
        
        report = PerformanceReport(
            session_id=session_id,
            time_window={
                'start': session_data.get('start_time', ''),
                'end': datetime.now().isoformat(),
                'duration_minutes': session_data.get('duration_seconds', 0) / 60
            },
            overall_metrics={
                'exp_rate': exp_analysis,
                'death_rate': death_analysis,
                'efficiency': efficiency_analysis
            },
            macro_effectiveness=macro_effectiveness,
            recommendations=recommendations,
            trends=self._calculate_trends()
        )
        
        logger.info(
            f"✓ Performance report generated: "
            f"{len(macro_effectiveness)} macros analyzed, "
            f"{len(recommendations)} recommendations"
        )
        
        return report
    
    def _calculate_impact_score(self, macro_stats: Dict, session_data: Dict) -> float:
        """Calculate macro's impact on overall performance"""
        execution_count = macro_stats.get('execution_count', 0)
        success_rate = (macro_stats.get('success_count', 0) / 
                       max(execution_count, 1))
        
        # Weight by execution frequency and success rate
        frequency_weight = min(1.0, execution_count / 100)
        impact = frequency_weight * success_rate
        
        return round(impact, 2)
    
    def _generate_recommendations(
        self,
        exp_analysis: Dict,
        death_analysis: Dict,
        efficiency_analysis: Dict,
        macro_effectiveness: Dict
    ) -> List[str]:
        """Generate strategic recommendations"""
        recommendations = []
        
        # EXP rate recommendations
        if exp_analysis['efficiency'] == 'low':
            recommendations.append(
                f"EXP rate is low ({exp_analysis['exp_per_hour']}/hour). "
                "Consider optimizing farming macros or targeting higher-level monsters."
            )
        
        # Safety recommendations
        if death_analysis['needs_defensive_macro']:
            recommendations.append(
                f"Death rate is high ({death_analysis['deaths_per_hour']:.1f}/hour). "
                "Implement emergency healing macros or reduce farming aggressiveness."
            )
        
        # Efficiency recommendations
        if efficiency_analysis['rating'] in ['acceptable', 'poor']:
            recommendations.append(
                f"Overall efficiency is {efficiency_analysis['rating']} "
                f"(score: {efficiency_analysis['efficiency_score']:.2f}). "
                "Review resource management macros and optimize looting strategy."
            )
        
        # Macro-specific recommendations
        poor_macros = [
            name for name, stats in macro_effectiveness.items()
            if stats['performance'] == 'poor'
        ]
        
        if poor_macros:
            recommendations.append(
                f"The following macros have poor performance: {', '.join(poor_macros)}. "
                "Consider re-generating or optimizing these macros."
            )
        
        # If no issues, provide positive feedback
        if not recommendations:
            recommendations.append(
                "System is performing well. Continue monitoring for potential improvements."
            )
        
        return recommendations
    
    def _calculate_trends(self) -> Dict:
        """Calculate performance trends from history"""
        if len(self._metric_history) < 2:
            return {'status': 'insufficient_data'}
        
        recent = self._metric_history[-5:]  # Last 5 measurements
        
        # Calculate trends
        exp_rates = [m['exp_per_hour'] for m in recent]
        death_rates = [m['deaths_per_hour'] for m in recent]
        efficiency_scores = [m['efficiency_score'] for m in recent]
        
        return {
            'exp_trend': self._calculate_trend(exp_rates),
            'death_trend': self._calculate_trend(death_rates),
            'efficiency_trend': self._calculate_trend(efficiency_scores),
            'overall_trend': 'improving' if self._calculate_trend(efficiency_scores) == 'increasing' else 'declining'
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from values"""
        if len(values) < 2:
            return 'stable'
        
        diffs = [values[i] - values[i-1] for i in range(1, len(values))]
        avg_diff = sum(diffs) / len(diffs)
        
        if avg_diff > values[0] * 0.05:  # 5% increase
            return 'increasing'
        elif avg_diff < -values[0] * 0.05:  # 5% decrease
            return 'decreasing'
        else:
            return 'stable'
    
    def get_metric_history(self) -> List[Dict]:
        """Get historical metrics"""
        return self._metric_history.copy()
