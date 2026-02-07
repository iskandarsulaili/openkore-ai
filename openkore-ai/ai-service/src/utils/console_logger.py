"""
Console Logger Utility
Centralized console output for visible, exciting AI layer activity
"""

import sys
import threading
import io
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Force UTF-8 encoding for Windows console to support emojis
if sys.platform == 'win32':
    # Reconfigure stdout to use UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    else:
        # Fallback for older Python versions
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class LayerType(Enum):
    """Three-layer architecture types"""
    CONSCIOUS = "[CONSCIOUS]"
    SUBCONSCIOUS = "[SUBCONSCIOUS]"
    REFLEX = "[REFLEX]"
    SYSTEM = "[SYSTEM]"


class ConsoleLogger:
    """
    Thread-safe console logger for three-layer AI system
    
    Provides visible, exciting console output to prove AI layers are working
    """
    
    def __init__(self):
        """Initialize console logger with thread lock"""
        self._lock = threading.Lock()
        self._conscious_last_activity = None
        self._subconscious_last_activity = None
        self._reflex_last_activity = None
    
    def print_startup_banner(self):
        """Print exciting startup banner showing three-layer system"""
        banner = """
═══════════════════════════════════════════════════════════════
[GAME] OPENKORE GODTIER AI - THREE-LAYER SYSTEM ONLINE [GAME]
═══════════════════════════════════════════════════════════════
[CONSCIOUS] Conscious Layer: CrewAI Strategic Planning
   └─ Multi-agent collaboration
   └─ Strategic macro generation
   └─ Long-term goal planning
   
[SUBCONSCIOUS] Subconscious Layer: ML Pattern Recognition
   └─ Real-time pattern prediction
   └─ Learned behavior execution
   └─ Fast response (<500ms)
   
[REFLEX] Reflex Layer: OpenKore EventMacro
   └─ Instant muscle memory
   └─ Trigger-based reactions
   └─ Ultra-fast execution (<50ms)
═══════════════════════════════════════════════════════════════
"""
        self._thread_safe_print(banner)
    
    def print_layer_initialization(self, layer: LayerType, status: str, details: Optional[str] = None):
        """
        Print layer initialization status
        
        Args:
            layer: Layer type
            status: Status message
            details: Optional details
        """
        timestamp = self._get_timestamp()
        output = f"{layer.value} {status}"
        if details:
            output += f"\n   └─ {details}"
        
        self._thread_safe_print(f"[{timestamp}] {output}")
    
    def log_conscious_decision(
        self,
        decision_type: str,
        details: Dict[str, Any],
        confidence: float
    ):
        """
        Log Conscious Layer (CrewAI) decision
        
        Args:
            decision_type: Type of decision made
            details: Decision details
            confidence: Confidence score (0-1)
        """
        timestamp = self._get_timestamp()
        self._conscious_last_activity = datetime.now()
        
        confidence_label = self._get_confidence_label(confidence)
        
        output = f"""
{LayerType.CONSCIOUS.value} Strategic Decision Made
   └─ Type: {decision_type}
   └─ Goal: {details.get('goal', 'N/A')}
   └─ Strategy: {details.get('strategy', 'N/A')}
   └─ Macros Generated: {details.get('macros_generated', 0)}
   └─ Confidence: {confidence:.2f} ({confidence_label})
"""
        self._thread_safe_print(f"[{timestamp}] {output}")
    
    def log_subconscious_prediction(
        self,
        pattern_type: str,
        prediction: Dict[str, Any],
        confidence: float
    ):
        """
        Log Subconscious Layer (ML) prediction
        
        Args:
            pattern_type: Type of pattern detected
            prediction: Prediction details
            confidence: Confidence score (0-1)
        """
        timestamp = self._get_timestamp()
        self._subconscious_last_activity = datetime.now()
        
        output = f"""
{LayerType.SUBCONSCIOUS.value} Pattern Detected
   └─ Pattern: {pattern_type}
   └─ Prediction: {prediction.get('action', 'N/A')}
   └─ Confidence: {confidence:.2f} ({'HIGH' if confidence > 0.8 else 'MEDIUM' if confidence > 0.6 else 'LOW'})
   └─ Response Time: {prediction.get('response_time_ms', 0)}ms
"""
        self._thread_safe_print(f"[{timestamp}] {output}")
    
    def log_macro_generation(
        self,
        macro_name: str,
        macro_type: str,
        generation_details: Dict[str, Any]
    ):
        """
        Log macro generation event
        
        Args:
            macro_name: Name of generated macro
            macro_type: Type of macro
            generation_details: Generation details
        """
        timestamp = self._get_timestamp()
        
        output = f"""
{LayerType.CONSCIOUS.value} Macro Generated
   └─ Name: {macro_name}
   └─ Type: {macro_type}
   └─ Triggers: {generation_details.get('trigger_count', 0)} conditions
   └─ Actions: {generation_details.get('action_count', 0)} steps
   └─ Status: {generation_details.get('status', 'Generated')} [OK]
"""
        self._thread_safe_print(f"[{timestamp}] {output}")
    
    def log_macro_deployment(
        self,
        macro_name: str,
        deployment_status: str
    ):
        """
        Log macro deployment to OpenKore
        
        Args:
            macro_name: Name of macro
            deployment_status: Deployment status
        """
        timestamp = self._get_timestamp()
        
        output = f"""
{LayerType.SYSTEM.value} Macro Deployment
   └─ Name: {macro_name}
   └─ Target: OpenKore EventMacro Engine
   └─ Status: {deployment_status}
"""
        self._thread_safe_print(f"[{timestamp}] {output}")
    
    def print_heartbeat(self):
        """Print system heartbeat showing all layers are active"""
        timestamp = self._get_timestamp()
        current_time = datetime.now()
        
        # Calculate time since last activity for each layer
        conscious_status = self._get_activity_status(
            self._conscious_last_activity,
            current_time
        )
        subconscious_status = self._get_activity_status(
            self._subconscious_last_activity,
            current_time
        )
        reflex_status = self._get_activity_status(
            self._reflex_last_activity,
            current_time
        )
        
        output = f"""
[SYSTEM HEARTBEAT - {timestamp}]
   [CONSCIOUS]: {conscious_status}
   [SUBCONSCIOUS]: {subconscious_status}
   [REFLEX]: {reflex_status}
"""
        self._thread_safe_print(output)
    
    def log_learning_progress(
        self,
        samples_collected: int,
        learning_rate: float,
        patterns_learned: int
    ):
        """
        Log ML learning progress
        
        Args:
            samples_collected: Number of samples collected
            learning_rate: Current learning rate
            patterns_learned: Number of patterns learned
        """
        timestamp = self._get_timestamp()
        
        output = f"""
{LayerType.SUBCONSCIOUS.value} Learning Progress
   └─ Samples: {samples_collected}
   └─ Learning Rate: {learning_rate:.4f}
   └─ Patterns Learned: {patterns_learned}
   └─ Status: Continuously Learning [RELOAD]
"""
        self._thread_safe_print(f"[{timestamp}] {output}")
    
    def log_crew_analysis(
        self,
        agent_name: str,
        analysis_type: str,
        insights: Dict[str, Any]
    ):
        """
        Log CrewAI agent analysis
        
        Args:
            agent_name: Name of agent
            analysis_type: Type of analysis
            insights: Analysis insights
        """
        timestamp = self._get_timestamp()
        
        output = f"""
{LayerType.CONSCIOUS.value} CrewAI Agent: {agent_name}
   └─ Analysis: {analysis_type}
   └─ Recommendations: {insights.get('recommendation_count', 0)}
   └─ Execution Time: {insights.get('execution_time_ms', 0)}ms
"""
        self._thread_safe_print(f"[{timestamp}] {output}")
    
    # ===== Private Methods =====
    
    def _thread_safe_print(self, message: str):
        """Thread-safe console print"""
        with self._lock:
            print(message, flush=True)
    
    def _get_timestamp(self) -> str:
        """Get formatted timestamp"""
        return datetime.now().strftime("%H:%M:%S")
    
    def _get_confidence_label(self, confidence: float) -> str:
        """Get confidence level label"""
        if confidence >= 0.9:
            return "VERY HIGH"
        elif confidence >= 0.8:
            return "HIGH"
        elif confidence >= 0.6:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _get_activity_status(
        self,
        last_activity: Optional[datetime],
        current_time: datetime
    ) -> str:
        """Get activity status string"""
        if last_activity is None:
            return "Standby (No activity yet)"
        
        elapsed_seconds = (current_time - last_activity).total_seconds()
        
        if elapsed_seconds < 10:
            return f"Active (Last: {int(elapsed_seconds)}s ago)"
        elif elapsed_seconds < 60:
            return f"Active (Last: {int(elapsed_seconds)}s ago)"
        elif elapsed_seconds < 300:
            minutes = int(elapsed_seconds / 60)
            return f"Idle (Last: {minutes}m ago)"
        else:
            return "Standby"


# Global singleton instance
console_logger = ConsoleLogger()
