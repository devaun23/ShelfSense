"""
Centralized OpenAI Service with Circuit Breaker and Retry Logic

This service wraps all OpenAI API calls with:
- Circuit breaker pattern for graceful degradation
- Exponential backoff with jitter
- Sentry error tracking
- Metrics collection

Usage:
    from app.services.openai_service import openai_service, CircuitBreakerOpenError

    try:
        response = openai_service.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o"
        )
    except CircuitBreakerOpenError:
        # Handle gracefully - serve cached content or fallback
        pass
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None

from typing import AsyncGenerator

from app.utils.api_retry import (
    OpenAIRetryHandler,
    CircuitState,
    RetryConfig
)
from app.utils.openai_client import get_openai_client

logger = logging.getLogger(__name__)


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and requests are being rejected."""
    pass


class OpenAIServiceError(Exception):
    """Base exception for OpenAI service errors."""
    pass


class OpenAIService:
    """
    Singleton wrapper for all OpenAI API calls with circuit breaker and retry logic.

    This service ensures that:
    1. All OpenAI calls go through retry logic with exponential backoff
    2. Circuit breaker prevents cascading failures
    3. Metrics are tracked for monitoring
    4. Errors are reported to Sentry
    """

    _instance: Optional['OpenAIService'] = None

    def __new__(cls) -> 'OpenAIService':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Use optimized config for OpenAI
        self.config = RetryConfig(
            max_retries=5,
            initial_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter_factor=0.5,
            retry_on_status_codes=(429, 500, 502, 503, 504, 520, 521, 522, 523, 524),
            enable_circuit_breaker=True,
            failure_threshold=5,  # Open after 5 consecutive failures
            recovery_timeout=120.0  # Try again after 2 minutes
        )

        self.retry_handler = OpenAIRetryHandler(self.config)
        self._call_history: List[Dict[str, Any]] = []
        self._initialized = True

        logger.info("OpenAI Service initialized with circuit breaker protection")

    @property
    def circuit_breaker(self):
        """Access the circuit breaker for status checks."""
        return self.retry_handler.circuit_breaker

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o",
        **kwargs
    ) -> Any:
        """
        Make a chat completion request with retry and circuit breaker protection.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: OpenAI model to use (default: gpt-4o)
            **kwargs: Additional arguments passed to OpenAI API

        Returns:
            OpenAI ChatCompletion response

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open
            Exception: If all retries exhausted
        """
        # Check circuit breaker first
        if not self.circuit_breaker.can_execute():
            self._record_call(model, success=False, circuit_open=True)

            if sentry_sdk:
                sentry_sdk.capture_message(
                    "Circuit breaker open - OpenAI requests blocked",
                    level="warning",
                    extras={
                        "circuit_state": self.circuit_breaker.state.value,
                        "failure_count": self.circuit_breaker.failure_count,
                        "model": model
                    }
                )

            logger.warning(
                f"Circuit breaker OPEN - rejecting OpenAI request. "
                f"Failures: {self.circuit_breaker.failure_count}"
            )
            raise CircuitBreakerOpenError(
                "OpenAI service temporarily unavailable due to repeated failures. "
                "Please try again later."
            )

        # Create decorated function for this specific call
        @self.retry_handler.get_decorator()
        def _make_call():
            return get_openai_client().chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )

        try:
            start_time = datetime.utcnow()
            result = _make_call()
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            self._record_call(model, success=True, latency_ms=latency_ms)
            logger.debug(f"OpenAI call succeeded in {latency_ms:.0f}ms")

            return result

        except Exception as e:
            self._record_call(model, success=False, error=str(e))

            if sentry_sdk:
                sentry_sdk.capture_exception(e, extras={
                    "model": model,
                    "message_count": len(messages),
                    "circuit_state": self.circuit_breaker.state.value,
                    "failure_count": self.circuit_breaker.failure_count
                })

            logger.error(
                f"OpenAI call failed after retries: {str(e)}. "
                f"Circuit state: {self.circuit_breaker.state.value}"
            )
            raise

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o",
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Make a streaming chat completion request with circuit breaker protection.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: OpenAI model to use (default: gpt-4o)
            **kwargs: Additional arguments passed to OpenAI API

        Yields:
            String chunks as they arrive from OpenAI

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open
            Exception: If streaming fails
        """
        # Check circuit breaker first
        if not self.circuit_breaker.can_execute():
            self._record_call(model, success=False, circuit_open=True)

            if sentry_sdk:
                sentry_sdk.capture_message(
                    "Circuit breaker open - OpenAI streaming requests blocked",
                    level="warning",
                    extras={
                        "circuit_state": self.circuit_breaker.state.value,
                        "failure_count": self.circuit_breaker.failure_count,
                        "model": model
                    }
                )

            logger.warning(
                f"Circuit breaker OPEN - rejecting OpenAI streaming request. "
                f"Failures: {self.circuit_breaker.failure_count}"
            )
            raise CircuitBreakerOpenError(
                "OpenAI service temporarily unavailable due to repeated failures. "
                "Please try again later."
            )

        try:
            start_time = datetime.utcnow()

            # Create streaming request (no retry decorator for streaming)
            stream = get_openai_client().chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                **kwargs
            )

            # Yield chunks as they arrive
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            # Record success after streaming completes
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._record_call(model, success=True, latency_ms=latency_ms)
            self.circuit_breaker.record_success()
            logger.debug(f"OpenAI streaming call succeeded in {latency_ms:.0f}ms")

        except Exception as e:
            self._record_call(model, success=False, error=str(e))
            self.circuit_breaker.record_failure()

            if sentry_sdk:
                sentry_sdk.capture_exception(e, extras={
                    "model": model,
                    "message_count": len(messages),
                    "circuit_state": self.circuit_breaker.state.value,
                    "failure_count": self.circuit_breaker.failure_count,
                    "streaming": True
                })

            logger.error(
                f"OpenAI streaming call failed: {str(e)}. "
                f"Circuit state: {self.circuit_breaker.state.value}"
            )
            raise

    def _record_call(
        self,
        model: str,
        success: bool,
        latency_ms: float = 0,
        error: str = None,
        circuit_open: bool = False
    ):
        """Record call for metrics tracking."""
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "model": model,
            "success": success,
            "latency_ms": latency_ms,
            "error": error,
            "circuit_open": circuit_open
        }
        self._call_history.append(record)

        # Keep only last 1000 calls in memory
        if len(self._call_history) > 1000:
            self._call_history = self._call_history[-1000:]

    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive service status for monitoring/admin endpoints.

        Returns:
            Dict with circuit breaker state, metrics, and recent history
        """
        circuit = self.circuit_breaker
        metrics = self.retry_handler.get_metrics()

        # Calculate recent stats from call history
        recent_calls = self._call_history[-100:] if self._call_history else []
        successful_recent = sum(1 for c in recent_calls if c.get("success"))
        failed_recent = len(recent_calls) - successful_recent
        avg_latency = (
            sum(c.get("latency_ms", 0) for c in recent_calls if c.get("success"))
            / max(successful_recent, 1)
        )

        return {
            "circuit_breaker": {
                "state": circuit.state.value,
                "failure_count": circuit.failure_count,
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout_seconds": self.config.recovery_timeout,
                "last_failure_time": (
                    circuit.last_failure_time.isoformat()
                    if circuit.last_failure_time else None
                ),
                "success_count_in_half_open": circuit.success_count
            },
            "retry_metrics": metrics,
            "recent_performance": {
                "total_calls": len(recent_calls),
                "successful_calls": successful_recent,
                "failed_calls": failed_recent,
                "success_rate": (
                    f"{(successful_recent / len(recent_calls) * 100):.1f}%"
                    if recent_calls else "N/A"
                ),
                "avg_latency_ms": round(avg_latency, 1)
            },
            "service_info": {
                "max_retries": self.config.max_retries,
                "initial_delay_seconds": self.config.initial_delay,
                "max_delay_seconds": self.config.max_delay
            }
        }

    def reset_circuit_breaker(self):
        """
        Manually reset the circuit breaker to CLOSED state.
        Use with caution - for admin/emergency recovery only.
        """
        self.circuit_breaker.state = CircuitState.CLOSED
        self.circuit_breaker.failure_count = 0
        self.circuit_breaker.success_count = 0

        logger.warning("Circuit breaker manually reset to CLOSED state")

        if sentry_sdk:
            sentry_sdk.capture_message(
                "Circuit breaker manually reset",
                level="info"
            )

    def is_healthy(self) -> bool:
        """
        Quick health check for the service.

        Returns:
            True if circuit is CLOSED or HALF_OPEN, False if OPEN
        """
        return self.circuit_breaker.state != CircuitState.OPEN


# Global singleton instance
openai_service = OpenAIService()


# Convenience function for quick status checks
def get_openai_service_status() -> Dict[str, Any]:
    """Get OpenAI service status without importing the service."""
    return openai_service.get_status()
