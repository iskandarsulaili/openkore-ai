"""
MacroOptimizer Agent
Reviews existing macros and suggests improvements
"""

import logging
from typing import Dict, List
from crewai import Agent, Task, Crew
from pydantic import BaseModel, Field
from llm.provider_chain import llm_chain

logger = logging.getLogger(__name__)


class OptimizationSuggestion(BaseModel):
    """Macro optimization suggestion"""
    macro_name: str = Field(..., description="Name of macro being optimized")
    current_performance: Dict = Field(..., description="Current performance metrics")
    suggested_changes: List[Dict] = Field(..., description="List of suggested improvements")
    expected_improvement: float = Field(..., description="Expected performance gain (0.0-1.0)")
    optimized_macro_text: str = Field(..., description="Optimized macro definition")


class MacroOptimizer:
    """
    MacroOptimizer Agent
    
    Role: Reviews existing macros and proposes performance improvements
    Capabilities:
    - Analyze macro execution logs
    - Identify inefficiencies and bottlenecks
    - Propose timing adjustments and condition refinements
    - A/B testing framework for variants
    """
    
    def __init__(self):
        """Initialize MacroOptimizer agent"""
        self.agent = self._create_agent()
        logger.info("MacroOptimizer agent initialized")
    
    def _create_agent(self) -> Agent:
        """Create the CrewAI agent"""
        return Agent(
            role="Macro Performance Optimizer",
            goal="Analyze and improve macro effectiveness through data-driven optimization",
            backstory="""You are an expert at performance optimization and data analysis.
            You specialize in:
            - Identifying performance bottlenecks in automated systems
            - Statistical analysis of execution patterns
            - A/B testing and iterative improvement
            - Balancing responsiveness with efficiency
            
            Your task is to review macro execution data and propose concrete improvements
            that will increase success rates, reduce execution time, or improve resource efficiency.""",
            verbose=True,
            allow_delegation=False,
            llm=llm_chain.get_crewai_llm()
        )
    
    def analyze_performance_tool(self, macro_name: str, performance_data: Dict) -> Dict:
        """
        Analyze macro performance metrics
        
        Args:
            macro_name: Name of the macro
            performance_data: Performance statistics
            
        Returns:
            Performance analysis
        """
        execution_count = performance_data.get('execution_count', 0)
        success_count = performance_data.get('success_count', 0)
        failure_count = performance_data.get('failure_count', 0)
        avg_duration = performance_data.get('avg_duration_ms', 0)
        
        success_rate = (success_count / max(execution_count, 1)) * 100
        
        # Determine performance grade
        if success_rate >= 95 and avg_duration < 2000:
            grade = 'excellent'
        elif success_rate >= 85 and avg_duration < 3000:
            grade = 'good'
        elif success_rate >= 70:
            grade = 'acceptable'
        else:
            grade = 'poor'
        
        return {
            'macro_name': macro_name,
            'success_rate': success_rate,
            'avg_duration_ms': avg_duration,
            'execution_count': execution_count,
            'performance_grade': grade,
            'needs_optimization': grade in ['acceptable', 'poor']
        }
    
    def identify_bottlenecks_tool(self, execution_log: List[Dict]) -> List[Dict]:
        """
        Identify performance bottlenecks in execution log
        
        Args:
            execution_log: List of execution records
            
        Returns:
            List of identified bottlenecks
        """
        bottlenecks = []
        
        # Analyze execution patterns
        for entry in execution_log:
            action = entry.get('action', '')
            duration = entry.get('duration_ms', 0)
            
            # Flag slow operations
            if duration > 1000:
                bottlenecks.append({
                    'type': 'slow_operation',
                    'action': action,
                    'duration_ms': duration,
                    'suggestion': 'Consider reducing wait time or optimizing action'
                })
            
            # Flag timeout issues
            if 'timeout' in str(entry.get('error', '')).lower():
                bottlenecks.append({
                    'type': 'timeout',
                    'action': action,
                    'suggestion': 'Increase timeout value or simplify condition'
                })
        
        return bottlenecks
    
    def suggest_improvements_tool(self, macro_text: str, performance_data: Dict) -> List[Dict]:
        """
        Suggest specific improvements for macro
        
        Args:
            macro_text: Current macro definition
            performance_data: Performance metrics
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        success_rate = performance_data.get('success_rate', 0)
        avg_duration = performance_data.get('avg_duration_ms', 0)
        
        # Analyze timeout settings
        if 'timeout' in macro_text:
            import re
            timeout_match = re.search(r'timeout\s+(\d+)', macro_text)
            if timeout_match:
                current_timeout = int(timeout_match.group(1))
                
                if success_rate < 80 and current_timeout > 5:
                    suggestions.append({
                        'parameter': 'timeout',
                        'current': current_timeout,
                        'suggested': max(2, current_timeout - 3),
                        'reason': 'Reduce timeout to trigger more frequently'
                    })
                elif avg_duration > 3000:
                    suggestions.append({
                        'parameter': 'timeout',
                        'current': current_timeout,
                        'suggested': current_timeout + 2,
                        'reason': 'Increase timeout to reduce excessive triggering'
                    })
        
        # Analyze pause statements
        pause_count = macro_text.count('pause')
        if pause_count > 5:
            suggestions.append({
                'parameter': 'pause_statements',
                'current': pause_count,
                'suggested': 'consolidate',
                'reason': 'Too many pause statements, consider consolidating'
            })
        
        # Analyze priority
        if 'priority' in macro_text:
            import re
            priority_match = re.search(r'priority\s+(\d+)', macro_text)
            if priority_match:
                current_priority = int(priority_match.group(1))
                
                if success_rate < 70 and current_priority < 80:
                    suggestions.append({
                        'parameter': 'priority',
                        'current': current_priority,
                        'suggested': min(100, current_priority + 10),
                        'reason': 'Increase priority for more consistent execution'
                    })
        
        return suggestions
    
    async def optimize_macro(
        self,
        macro_name: str,
        macro_text: str,
        performance_data: Dict
    ) -> OptimizationSuggestion:
        """
        Analyze macro and suggest optimizations
        
        Args:
            macro_name: Name of the macro
            macro_text: Current macro definition
            performance_data: Performance metrics
            
        Returns:
            Optimization suggestions
        """
        logger.info(f"Optimizing macro: {macro_name}")
        
        # Analyze current performance
        performance_analysis = self.analyze_performance_tool(macro_name, performance_data)
        
        # Generate suggestions
        suggestions = self.suggest_improvements_tool(macro_text, performance_data)
        
        # Calculate expected improvement
        current_success_rate = performance_analysis['success_rate'] / 100
        expected_improvement = min(0.25, (0.95 - current_success_rate) / 2)
        
        # Apply suggestions to generate optimized version
        optimized_text = self._apply_suggestions(macro_text, suggestions)
        
        result = OptimizationSuggestion(
            macro_name=macro_name,
            current_performance=performance_analysis,
            suggested_changes=suggestions,
            expected_improvement=expected_improvement,
            optimized_macro_text=optimized_text
        )
        
        logger.info(
            f"✓ Generated {len(suggestions)} optimization suggestions "
            f"(expected improvement: {expected_improvement:.1%})"
        )
        
        return result
    
    def _apply_suggestions(self, macro_text: str, suggestions: List[Dict]) -> str:
        """Apply optimization suggestions to macro text"""
        import re
        
        optimized = macro_text
        
        for suggestion in suggestions:
            param = suggestion.get('parameter')
            
            if param == 'timeout':
                current = suggestion['current']
                suggested = suggestion['suggested']
                optimized = re.sub(
                    rf'timeout\s+{current}',
                    f'timeout {suggested}',
                    optimized
                )
            
            elif param == 'priority':
                current = suggestion['current']
                suggested = suggestion['suggested']
                optimized = re.sub(
                    rf'priority\s+{current}',
                    f'priority {suggested}',
                    optimized
                )
            
            elif param == 'pause_statements':
                # Reduce pause durations
                optimized = re.sub(
                    r'pause\s+(\d+)',
                    lambda m: f'pause {max(0.5, float(m.group(1)) * 0.8)}',
                    optimized
                )
        
        return optimized
