"""
Circuit Breaker Pattern for Failing Macros

Prevents cascading failures by temporarily disabling macros
that exhibit repeated failures.
"""

from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, Callable, Optional, Any, List
from loguru import logger
import asyncio


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Macro disabled due to failures
    HALF_OPEN = "half_open"  # Testing if macro recovered


class MacroCircuitBreaker:
    """Circuit breaker pattern for failing macros."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        half_open_max_calls: int = 3,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds before attempting reset (half-open state)
            half_open_max_calls: Max calls allowed in half-open state
            success_threshold: Successes needed in half-open to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls
        self.success_threshold = success_threshold
        
        # Circuit states per macro
        self.circuits: Dict[str, Dict] = {}
        
        # Global statistics
        self.total_failures = 0
        self.total_successes = 0
        self.total_open_circuits = 0
        
        logger.info(
            f"Initialized circuit breaker "
            f"(threshold={failure_threshold}, timeout={timeout}s)"
        )
    
    async def call(
        self,
        macro_name: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute macro with circuit breaker protection.
        
        Args:
            macro_name: Name of macro to protect
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func execution
            
        Raises:
            CircuitOpenError: If circuit is open
            Exception: Original exception from func
        """
        circuit = self._get_circuit(macro_name)
        
        # Check circuit state
        if circuit['state'] == CircuitState.OPEN:
            if self._should_attempt_reset(circuit):
                self._transition_to_half_open(circuit, macro_name)
            else:
                remaining = self._get_remaining_timeout(circuit)
                raise CircuitOpenError(
                    f"Circuit open for {macro_name} "
                    f"(retry in {remaining}s)"
                )
        
        # Check half-open call limit
        if circuit['state'] == CircuitState.HALF_OPEN:
            if circuit['half_open_calls'] >= self.half_open_max_calls:
                raise CircuitOpenError(
                    f"Half-open call limit reached for {macro_name}"
                )
            circuit['half_open_calls'] += 1
        
        # Execute function
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            self._on_success(circuit, macro_name)
            return result
            
        except Exception as e:
            self._on_failure(circuit, macro_name, e)
            raise e
    
    def call_sync(
        self,
        macro_name: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Synchronous version of call().
        
        For non-async functions.
        """
        circuit = self._get_circuit(macro_name)
        
        if circuit['state'] == CircuitState.OPEN:
            if self._should_attempt_reset(circuit):
                self._transition_to_half_open(circuit, macro_name)
            else:
                remaining = self._get_remaining_timeout(circuit)
                raise CircuitOpenError(
                    f"Circuit open for {macro_name} "
                    f"(retry in {remaining}s)"
                )
        
        if circuit['state'] == CircuitState.HALF_OPEN:
            if circuit['half_open_calls'] >= self.half_open_max_calls:
                raise CircuitOpenError(
                    f"Half-open call limit reached for {macro_name}"
                )
            circuit['half_open_calls'] += 1
        
        try:
            result = func(*args, **kwargs)
            self._on_success(circuit, macro_name)
            return result
        except Exception as e:
            self._on_failure(circuit, macro_name, e)
            raise e
    
    def _get_circuit(self, macro_name: str) -> Dict:
        """Get or create circuit for macro."""
        if macro_name not in self.circuits:
            self.circuits[macro_name] = {
                'state': CircuitState.CLOSED,
                'failures': 0,
                'successes': 0,
                'last_failure_time': None,
                'last_success_time': None,
                'last_error': None,
                'half_open_calls': 0,
                'total_calls': 0,
                'total_failures': 0,
                'total_successes': 0
            }
        return self.circuits[macro_name]
    
    def _on_success(self, circuit: Dict, macro_name: str):
        """Handle successful execution."""
        circuit['successes'] += 1
        circuit['total_successes'] += 1
        circuit['total_calls'] += 1
        circuit['last_success_time'] = datetime.now()
        
        self.total_successes += 1
        
        # Transition from half-open to closed if enough successes
        if circuit['state'] == CircuitState.HALF_OPEN:
            if circuit['successes'] >= self.success_threshold:
                self._transition_to_closed(circuit, macro_name)
        else:
            # Reset failure counter on success in closed state
            circuit['failures'] = 0
        
        logger.debug(f"Circuit success: {macro_name} (state={circuit['state'].value})")
    
    def _on_failure(self, circuit: Dict, macro_name: str, error: Exception):
        """Handle failed execution."""
        circuit['failures'] += 1
        circuit['total_failures'] += 1
        circuit['total_calls'] += 1
        circuit['last_failure_time'] = datetime.now()
        circuit['last_error'] = str(error)
        
        self.total_failures += 1
        
        # Transition to open if threshold reached
        if circuit['failures'] >= self.failure_threshold:
            self._transition_to_open(circuit, macro_name)
        
        # In half-open state, immediately reopen on failure
        elif circuit['state'] == CircuitState.HALF_OPEN:
            self._transition_to_open(circuit, macro_name)
        
        logger.warning(
            f"Circuit failure: {macro_name} "
            f"({circuit['failures']}/{self.failure_threshold}) - {error}"
        )
    
    def _transition_to_open(self, circuit: Dict, macro_name: str):
        """Transition circuit to OPEN state."""
        circuit['state'] = CircuitState.OPEN
        circuit['failures'] = 0  # Reset for next half-open attempt
        circuit['successes'] = 0
        
        self.total_open_circuits += 1
        
        logger.error(
            f"Circuit OPENED for {macro_name} "
            f"(timeout={self.timeout}s)"
        )
    
    def _transition_to_half_open(self, circuit: Dict, macro_name: str):
        """Transition circuit to HALF_OPEN state."""
        circuit['state'] = CircuitState.HALF_OPEN
        circuit['half_open_calls'] = 0
        circuit['successes'] = 0
        
        logger.info(f"Circuit HALF-OPEN for {macro_name} (testing recovery)")
    
    def _transition_to_closed(self, circuit: Dict, macro_name: str):
        """Transition circuit to CLOSED state."""
        circuit['state'] = CircuitState.CLOSED
        circuit['failures'] = 0
        circuit['successes'] = 0
        circuit['half_open_calls'] = 0
        
        logger.info(f"Circuit CLOSED for {macro_name} (recovery successful)")
    
    def _should_attempt_reset(self, circuit: Dict) -> bool:
        """Check if enough time passed to attempt reset."""
        if circuit['last_failure_time'] is None:
            return False
        
        elapsed = (datetime.now() - circuit['last_failure_time']).total_seconds()
        return elapsed >= self.timeout
    
    def _get_remaining_timeout(self, circuit: Dict) -> int:
        """Get remaining timeout in seconds."""
        if circuit['last_failure_time'] is None:
            return 0
        
        elapsed = (datetime.now() - circuit['last_failure_time']).total_seconds()
        remaining = max(0, self.timeout - elapsed)
        return int(remaining)
    
    def get_circuit_state(self, macro_name: str) -> Optional[str]:
        """Get current state of circuit."""
        if macro_name not in self.circuits:
            return None
        return self.circuits[macro_name]['state'].value
    
    def get_circuit_info(self, macro_name: str) -> Optional[Dict]:
        """Get detailed circuit information."""
        if macro_name not in self.circuits:
            return None
        
        circuit = self.circuits[macro_name]
        
        return {
            'macro_name': macro_name,
            'state': circuit['state'].value,
            'failures': circuit['failures'],
            'successes': circuit['successes'],
            'total_calls': circuit['total_calls'],
            'total_failures': circuit['total_failures'],
            'total_successes': circuit['total_successes'],
            'success_rate': (
                circuit['total_successes'] / circuit['total_calls']
                if circuit['total_calls'] > 0 else 0.0
            ),
            'last_error': circuit['last_error'],
            'last_failure_time': (
                circuit['last_failure_time'].isoformat()
                if circuit['last_failure_time'] else None
            ),
            'remaining_timeout': (
                self._get_remaining_timeout(circuit)
                if circuit['state'] == CircuitState.OPEN else 0
            )
        }
    
    def get_all_circuits(self) -> List[Dict]:
        """Get information about all circuits."""
        return [
            self.get_circuit_info(name)
            for name in self.circuits.keys()
        ]
    
    def reset_circuit(self, macro_name: str):
        """Manually reset a circuit to closed state."""
        if macro_name in self.circuits:
            circuit = self.circuits[macro_name]
            self._transition_to_closed(circuit, macro_name)
            logger.info(f"Manually reset circuit for {macro_name}")
    
    def reset_all_circuits(self):
        """Reset all circuits to closed state."""
        for macro_name in self.circuits.keys():
            self.reset_circuit(macro_name)
        logger.info("Reset all circuits")
    
    def get_statistics(self) -> Dict:
        """Get global circuit breaker statistics."""
        open_circuits = sum(
            1 for c in self.circuits.values()
            if c['state'] == CircuitState.OPEN
        )
        
        half_open_circuits = sum(
            1 for c in self.circuits.values()
            if c['state'] == CircuitState.HALF_OPEN
        )
        
        return {
            'total_circuits': len(self.circuits),
            'open_circuits': open_circuits,
            'half_open_circuits': half_open_circuits,
            'closed_circuits': len(self.circuits) - open_circuits - half_open_circuits,
            'total_failures': self.total_failures,
            'total_successes': self.total_successes,
            'total_open_events': self.total_open_circuits,
            'overall_success_rate': (
                self.total_successes / (self.total_successes + self.total_failures)
                if (self.total_successes + self.total_failures) > 0 else 0.0
            )
        }


class CircuitOpenError(Exception):
    """Exception raised when circuit is open."""
    pass


# Convenience decorator
def circuit_breaker(
    breaker: MacroCircuitBreaker,
    macro_name: str
):
    """
    Decorator for circuit breaker protection.
    
    Usage:
        breaker = MacroCircuitBreaker()
        
        @circuit_breaker(breaker, "healing_macro")
        async def execute_healing():
            ...
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            return await breaker.call(macro_name, func, *args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            return breaker.call_sync(macro_name, func, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
