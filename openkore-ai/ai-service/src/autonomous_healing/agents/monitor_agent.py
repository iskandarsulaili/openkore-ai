"""
Monitor Agent - Real-time log parsing and anomaly detection
Continuously watches OpenKore logs for errors, warnings, and behavioral issues
"""

from crewai import Agent
from crewai.tools import BaseTool
from typing import Dict, List, Any, Optional
from pathlib import Path
import re
from datetime import datetime, timedelta
from pydantic import ConfigDict


class LogParsingTool(BaseTool):
    """Tool for parsing OpenKore log files and detecting patterns"""
    
    model_config = ConfigDict(
        extra='allow',
        arbitrary_types_allowed=True
    )
    
    name: str = "log_parser"
    description: str = "Parse OpenKore console logs and detect error patterns, stuck loops, and anomalies"
    
    def __init__(self, log_monitor, issue_detector):
        super().__init__()
        self.log_monitor = log_monitor
        self.issue_detector = issue_detector
    
    def _run(self, log_path: str) -> Dict[str, Any]:
        """Parse log file and return detected issues"""
        try:
            issues = self.issue_detector.scan_log_file(log_path)
            return {
                'success': True,
                'issues_found': len(issues),
                'issues': issues
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class AnomalyDetectionTool(BaseTool):
    """Tool for detecting behavioral anomalies"""
    
    model_config = ConfigDict(
        extra='allow',
        arbitrary_types_allowed=True
    )
    
    name: str = "anomaly_detector"
    description: str = "Detect behavioral anomalies like stuck loops, infinite waits, position desyncs"
    
    def _run(self, log_lines: List[str], lookback_minutes: int = 5) -> Dict[str, Any]:
        """Analyze recent log lines for behavioral anomalies"""
        try:
            anomalies = []
            
            # Detect AI stuck loops
            ai_states = {}
            for line in log_lines:
                match = re.search(r'AI: (\w+).*\| \d+', line)
                if match:
                    state = match.group(1)
                    ai_states[state] = ai_states.get(state, 0) + 1
            
            # If same AI state appears > 10 times, it's stuck
            for state, count in ai_states.items():
                if count > 10:
                    anomalies.append({
                        'type': 'ai_stuck_loop',
                        'state': state,
                        'occurrences': count,
                        'severity': 'HIGH'
                    })
            
            # Detect NPC interaction failures
            npc_failures = len([l for l in log_lines if 'Could not find an NPC' in l])
            if npc_failures > 3:
                anomalies.append({
                    'type': 'npc_interaction_failure',
                    'count': npc_failures,
                    'severity': 'HIGH'
                })
            
            # Detect route recalculation spam
            route_recalc = len([l for l in log_lines if 'recalculating' in l])
            if route_recalc > 5:
                anomalies.append({
                    'type': 'route_stuck',
                    'count': route_recalc,
                    'severity': 'MEDIUM'
                })
            
            return {
                'success': True,
                'anomalies_found': len(anomalies),
                'anomalies': anomalies
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class MonitorAgent:
    """Wrapper class for Monitor Agent functionality"""
    
    def __init__(self, agent: Agent, log_monitor, issue_detector):
        self.agent = agent
        self.log_monitor = log_monitor
        self.issue_detector = issue_detector


def create_monitor_agent(config: Dict, log_monitor, issue_detector, llm) -> Agent:
    """
    Create the Monitor Agent with log parsing and anomaly detection capabilities
    
    Args:
        config: Agent configuration from YAML
        log_monitor: LogMonitor instance
        issue_detector: IssueDetector instance
        llm: LLM instance (DeepSeek via provider chain)
        
    Returns:
        Configured CrewAI Agent
    """
    
    # Create specialized tools
    tools = [
        LogParsingTool(log_monitor=log_monitor, issue_detector=issue_detector),
        AnomalyDetectionTool()
    ]
    
    # Create agent with DeepSeek LLM
    agent = Agent(
        role=config['role'],
        goal=config['goal'],
        backstory=config['backstory'],
        tools=tools,
        verbose=config.get('verbose', True),
        allow_delegation=False,  # Monitor doesn't delegate
        max_iter=15,
        memory=True,  # Remember previous issues
        llm=llm  # Use DeepSeek LLM
    )
    
    return agent
