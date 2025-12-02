"""
Circuit Breaker implementation for vendor API calls.

Implements Requirement 13: Circuit Breaker Pattern
- Opens after 3 consecutive failures
- Skips vendor calls for 30 seconds while open
- After cooldown, enters half-open mode
- One successful call closes the circuit
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Circuit is open, rejecting calls
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for vendor API calls.
    
    Prevents cascading failures by temporarily blocking calls to failing vendors.
    """
    
    def __init__(
        self,
        vendor_name: str,
        failure_threshold: int = 3,
        cooldown_seconds: int = 30
    ):
        """
        Initialize circuit breaker.
        
        Args:
            vendor_name: Name of the vendor (for logging)
            failure_threshold: Number of consecutive failures before opening (default: 3)
            cooldown_seconds: Cooldown period in seconds (default: 30)
        """
        self.vendor_name = vendor_name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.opened_at: Optional[datetime] = None
        
        logger.info(
            f"Circuit breaker initialized for {vendor_name}: "
            f"threshold={failure_threshold}, cooldown={cooldown_seconds}s"
        )
    
    def _should_attempt_reset(self) -> bool:
        """
        Check if circuit should transition from OPEN to HALF_OPEN.
        
        Returns:
            True if cooldown period has elapsed
        """
        if self.state != CircuitState.OPEN or self.opened_at is None:
            return False
        
        elapsed = datetime.utcnow() - self.opened_at
        return elapsed.total_seconds() >= self.cooldown_seconds
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from func or None if circuit is open
            
        Raises:
            Exception: If func raises and circuit should remain closed
        """
        # Check if we should attempt reset
        if self._should_attempt_reset():
            logger.info(f"{self.vendor_name}: Circuit entering HALF_OPEN state (cooldown elapsed)")
            self.state = CircuitState.HALF_OPEN
        
        # If circuit is OPEN, reject the call
        if self.state == CircuitState.OPEN:
            logger.warning(
                f"{self.vendor_name}: Circuit is OPEN, skipping call "
                f"(opened {(datetime.utcnow() - self.opened_at).total_seconds():.1f}s ago)"
            )
            return None
        
        try:
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Success - reset failure count and close circuit
            if self.state == CircuitState.HALF_OPEN:
                logger.info(f"{self.vendor_name}: Circuit CLOSED (successful call in HALF_OPEN state)")
            
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
            self.opened_at = None
            
            return result
            
        except Exception as e:
            # Failure - increment counter
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            logger.warning(
                f"{self.vendor_name}: Call failed ({self.failure_count}/{self.failure_threshold}): {str(e)}"
            )
            
            # Check if we should open the circuit
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = datetime.utcnow()
                logger.error(
                    f"{self.vendor_name}: Circuit OPENED after {self.failure_count} consecutive failures. "
                    f"Will retry after {self.cooldown_seconds}s cooldown."
                )
            
            # Re-raise the exception
            raise
    
    def get_state(self) -> dict:
        """
        Get current circuit breaker state for monitoring.
        
        Returns:
            Dictionary with state information
        """
        state_info = {
            "vendor": self.vendor_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "cooldown_seconds": self.cooldown_seconds
        }
        
        if self.opened_at:
            elapsed = (datetime.utcnow() - self.opened_at).total_seconds()
            state_info["opened_seconds_ago"] = round(elapsed, 1)
            state_info["cooldown_remaining"] = max(0, self.cooldown_seconds - elapsed)
        
        return state_info
    
    def reset(self):
        """Manually reset the circuit breaker to CLOSED state."""
        logger.info(f"{self.vendor_name}: Circuit breaker manually reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.opened_at = None
