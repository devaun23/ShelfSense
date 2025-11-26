"""
API Retry Utility with Exponential Backoff

Provides robust retry mechanisms for external API calls, specifically
optimized for OpenAI API interactions.

Features:
- Exponential backoff with jitter
- Configurable retry limits and delays
- Specific handling for rate limit errors (HTTP 429)
- Circuit breaker pattern for failing services
- Logging and metrics
"""

import asyncio
import random
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable, Optional, Type, Tuple, Any, Dict
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    # Retry attempts
    max_retries: int = 5

    # Backoff timing (in seconds)
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0

    # Jitter to prevent thundering herd
    jitter_factor: float = 0.5  # Random factor 0-0.5x of delay

    # Specific error handling
    retry_on_status_codes: Tuple[int, ...] = (429, 500, 502, 503, 504)
    retry_on_exceptions: Tuple[Type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
    )

    # Rate limit specific
    rate_limit_header: str = "Retry-After"
    respect_retry_after: bool = True

    # Circuit breaker
    enable_circuit_breaker: bool = True
    failure_threshold: int = 5  # Failures before circuit opens
    recovery_timeout: float = 60.0  # Seconds before trying again


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


# ============================================================================
# CIRCUIT BREAKER
# ============================================================================

class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by stopping requests to a failing service.
    """

    def __init__(self, config: RetryConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count = 0

    def can_execute(self) -> bool:
        """Check if a request should be allowed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.config.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info("Circuit breaker entering HALF_OPEN state")
                    return True
            return False

        # HALF_OPEN state - allow one request to test
        return True

    def record_success(self):
        """Record a successful request."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 3:  # 3 successes to close
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker CLOSED - service recovered")
        else:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record a failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.state == CircuitState.HALF_OPEN:
            # Immediately open on failure during half-open
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker OPEN - service still failing")
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker OPEN after {self.failure_count} failures"
            )


# ============================================================================
# RETRY DECORATOR
# ============================================================================

def calculate_delay(
    attempt: int,
    config: RetryConfig,
    retry_after: Optional[float] = None
) -> float:
    """
    Calculate delay before next retry using exponential backoff with jitter.

    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration
        retry_after: Server-specified delay (from Retry-After header)

    Returns:
        Delay in seconds
    """
    if retry_after and config.respect_retry_after:
        # Use server-specified delay with some jitter
        jitter = random.uniform(0, config.jitter_factor * retry_after)
        return min(retry_after + jitter, config.max_delay)

    # Calculate exponential backoff
    base_delay = config.initial_delay * (config.exponential_base ** attempt)

    # Add jitter
    jitter = random.uniform(0, config.jitter_factor * base_delay)

    # Cap at max delay
    return min(base_delay + jitter, config.max_delay)


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        config: Retry configuration (uses defaults if None)
        on_retry: Callback function(attempt, exception, delay) called before each retry

    Usage:
        @retry_with_backoff()
        def call_openai_api():
            ...

        @retry_with_backoff(RetryConfig(max_retries=3))
        async def call_openai_api_async():
            ...
    """
    if config is None:
        config = RetryConfig()

    circuit_breaker = CircuitBreaker(config) if config.enable_circuit_breaker else None

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await _retry_async(
                func, args, kwargs, config, circuit_breaker, on_retry
            )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return _retry_sync(
                func, args, kwargs, config, circuit_breaker, on_retry
            )

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


async def _retry_async(
    func: Callable,
    args: tuple,
    kwargs: dict,
    config: RetryConfig,
    circuit_breaker: Optional[CircuitBreaker],
    on_retry: Optional[Callable]
):
    """Async retry implementation."""
    last_exception = None

    for attempt in range(config.max_retries + 1):
        # Check circuit breaker
        if circuit_breaker and not circuit_breaker.can_execute():
            raise Exception(
                "Circuit breaker is open - service temporarily unavailable"
            )

        try:
            result = await func(*args, **kwargs)
            if circuit_breaker:
                circuit_breaker.record_success()
            return result

        except Exception as e:
            last_exception = e
            should_retry, retry_after = _should_retry(e, config)

            if circuit_breaker:
                circuit_breaker.record_failure()

            if not should_retry or attempt >= config.max_retries:
                logger.error(
                    f"Request failed after {attempt + 1} attempts: {str(e)}"
                )
                raise

            delay = calculate_delay(attempt, config, retry_after)

            logger.warning(
                f"Attempt {attempt + 1}/{config.max_retries + 1} failed: {str(e)}. "
                f"Retrying in {delay:.2f}s..."
            )

            if on_retry:
                on_retry(attempt, e, delay)

            await asyncio.sleep(delay)

    raise last_exception


def _retry_sync(
    func: Callable,
    args: tuple,
    kwargs: dict,
    config: RetryConfig,
    circuit_breaker: Optional[CircuitBreaker],
    on_retry: Optional[Callable]
):
    """Synchronous retry implementation."""
    last_exception = None

    for attempt in range(config.max_retries + 1):
        # Check circuit breaker
        if circuit_breaker and not circuit_breaker.can_execute():
            raise Exception(
                "Circuit breaker is open - service temporarily unavailable"
            )

        try:
            result = func(*args, **kwargs)
            if circuit_breaker:
                circuit_breaker.record_success()
            return result

        except Exception as e:
            last_exception = e
            should_retry, retry_after = _should_retry(e, config)

            if circuit_breaker:
                circuit_breaker.record_failure()

            if not should_retry or attempt >= config.max_retries:
                logger.error(
                    f"Request failed after {attempt + 1} attempts: {str(e)}"
                )
                raise

            delay = calculate_delay(attempt, config, retry_after)

            logger.warning(
                f"Attempt {attempt + 1}/{config.max_retries + 1} failed: {str(e)}. "
                f"Retrying in {delay:.2f}s..."
            )

            if on_retry:
                on_retry(attempt, e, delay)

            time.sleep(delay)

    raise last_exception


def _should_retry(exception: Exception, config: RetryConfig) -> Tuple[bool, Optional[float]]:
    """
    Determine if an exception should trigger a retry.

    Returns:
        (should_retry, retry_after_seconds)
    """
    retry_after = None

    # Check for OpenAI-specific rate limit error
    if hasattr(exception, 'status_code'):
        status_code = exception.status_code
        if status_code in config.retry_on_status_codes:
            # Try to extract Retry-After from response
            if hasattr(exception, 'response') and exception.response:
                retry_after_header = exception.response.headers.get(
                    config.rate_limit_header
                )
                if retry_after_header:
                    try:
                        retry_after = float(retry_after_header)
                    except ValueError:
                        pass
            return True, retry_after

    # Check for HTTPStatusError (httpx)
    if hasattr(exception, 'response'):
        response = exception.response
        if hasattr(response, 'status_code'):
            if response.status_code in config.retry_on_status_codes:
                retry_after_header = response.headers.get(config.rate_limit_header)
                if retry_after_header:
                    try:
                        retry_after = float(retry_after_header)
                    except ValueError:
                        pass
                return True, retry_after

    # Check exception types
    for exc_type in config.retry_on_exceptions:
        if isinstance(exception, exc_type):
            return True, None

    # Check for common API error patterns in message
    error_msg = str(exception).lower()
    retryable_patterns = [
        "rate limit",
        "too many requests",
        "timeout",
        "connection",
        "temporarily unavailable",
        "service unavailable",
        "server error",
        "internal error"
    ]

    for pattern in retryable_patterns:
        if pattern in error_msg:
            return True, retry_after

    return False, None


# ============================================================================
# OPENAI-SPECIFIC RETRY HANDLER
# ============================================================================

class OpenAIRetryHandler:
    """
    Specialized retry handler for OpenAI API calls.

    Provides preconfigured retry settings optimized for OpenAI's rate limits
    and error patterns.
    """

    # Default config optimized for OpenAI
    DEFAULT_CONFIG = RetryConfig(
        max_retries=5,
        initial_delay=1.0,
        max_delay=60.0,
        exponential_base=2.0,
        jitter_factor=0.5,
        retry_on_status_codes=(429, 500, 502, 503, 504, 520, 521, 522, 523, 524),
        retry_on_exceptions=(
            ConnectionError,
            TimeoutError,
        ),
        respect_retry_after=True,
        enable_circuit_breaker=True,
        failure_threshold=10,
        recovery_timeout=120.0
    )

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or self.DEFAULT_CONFIG
        self.circuit_breaker = CircuitBreaker(self.config)
        self._metrics: Dict[str, int] = {
            "total_calls": 0,
            "successful_calls": 0,
            "retried_calls": 0,
            "failed_calls": 0
        }

    def get_decorator(self):
        """Get a retry decorator with this handler's configuration."""
        def on_retry(attempt, exception, delay):
            self._metrics["retried_calls"] += 1
            logger.info(
                f"OpenAI API retry #{attempt + 1}: {type(exception).__name__}"
            )

        return retry_with_backoff(
            config=self.config,
            on_retry=on_retry
        )

    async def call_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic.

        Args:
            func: The function to call (can be sync or async)
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The function's return value

        Raises:
            Exception: If all retries are exhausted
        """
        self._metrics["total_calls"] += 1

        decorated_func = self.get_decorator()(func)

        try:
            if asyncio.iscoroutinefunction(func):
                result = await decorated_func(*args, **kwargs)
            else:
                result = decorated_func(*args, **kwargs)

            self._metrics["successful_calls"] += 1
            return result

        except Exception as e:
            self._metrics["failed_calls"] += 1
            raise

    def get_metrics(self) -> Dict[str, int]:
        """Get retry metrics."""
        return self._metrics.copy()

    def reset_metrics(self):
        """Reset metrics counters."""
        self._metrics = {
            "total_calls": 0,
            "successful_calls": 0,
            "retried_calls": 0,
            "failed_calls": 0
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Global OpenAI retry handler instance
_openai_handler: Optional[OpenAIRetryHandler] = None


def get_openai_retry_handler() -> OpenAIRetryHandler:
    """Get or create the global OpenAI retry handler."""
    global _openai_handler
    if _openai_handler is None:
        _openai_handler = OpenAIRetryHandler()
    return _openai_handler


def openai_retry():
    """
    Decorator specifically for OpenAI API calls.

    Usage:
        @openai_retry()
        def generate_completion(prompt: str):
            return client.chat.completions.create(...)
    """
    return get_openai_retry_handler().get_decorator()


# ============================================================================
# UTILITY: RATE LIMIT AWARE SLEEP
# ============================================================================

async def rate_limit_sleep(
    requests_per_minute: int,
    last_request_time: Optional[datetime] = None
) -> datetime:
    """
    Sleep if necessary to stay within rate limits.

    Args:
        requests_per_minute: Maximum allowed requests per minute
        last_request_time: Time of the last request

    Returns:
        Current time (to use as next last_request_time)
    """
    if last_request_time is None:
        return datetime.utcnow()

    min_interval = 60.0 / requests_per_minute
    elapsed = (datetime.utcnow() - last_request_time).total_seconds()

    if elapsed < min_interval:
        sleep_time = min_interval - elapsed
        logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
        await asyncio.sleep(sleep_time)

    return datetime.utcnow()
