"""
Performance Monitoring Middleware for ShelfSense

Tracks API endpoint latency and provides metrics for:
- Request duration by endpoint
- Slow query detection (> 3s)
- Average response times
- 95th percentile latency

Helps identify performance bottlenecks and ensures:
- AI generation < 3s target
- Database queries optimized
- Overall API responsiveness
"""

import time
from typing import Callable, Dict, List
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class PerformanceStats:
    """Store and calculate performance statistics"""

    def __init__(self, window_minutes: int = 60):
        """
        Initialize performance stats

        Args:
            window_minutes: Time window to keep stats (default 60 minutes)
        """
        # Store: {endpoint: [(timestamp, duration), ...]}
        self._requests: Dict[str, List[tuple]] = defaultdict(list)
        self._window_seconds = window_minutes * 60

    def _clean_old_requests(self, endpoint: str):
        """Remove requests outside the time window"""
        cutoff_time = time.time() - self._window_seconds

        if endpoint in self._requests:
            self._requests[endpoint] = [
                (ts, dur) for ts, dur in self._requests[endpoint]
                if ts > cutoff_time
            ]

    def record_request(self, endpoint: str, duration: float):
        """Record a request with its duration"""
        self._clean_old_requests(endpoint)
        self._requests[endpoint].append((time.time(), duration))

    def get_stats(self, endpoint: str = None) -> Dict:
        """
        Get performance statistics

        Args:
            endpoint: Specific endpoint or None for all

        Returns:
            Statistics dictionary
        """
        if endpoint:
            self._clean_old_requests(endpoint)
            durations = [dur for _, dur in self._requests.get(endpoint, [])]

            if not durations:
                return {
                    "endpoint": endpoint,
                    "count": 0,
                    "avg_ms": 0,
                    "min_ms": 0,
                    "max_ms": 0,
                    "p95_ms": 0,
                    "slow_requests": 0
                }

            sorted_durations = sorted(durations)
            p95_index = int(len(sorted_durations) * 0.95)

            return {
                "endpoint": endpoint,
                "count": len(durations),
                "avg_ms": round(sum(durations) / len(durations) * 1000, 2),
                "min_ms": round(min(durations) * 1000, 2),
                "max_ms": round(max(durations) * 1000, 2),
                "p95_ms": round(sorted_durations[p95_index] * 1000, 2) if p95_index < len(sorted_durations) else 0,
                "slow_requests": sum(1 for d in durations if d > 3.0)  # > 3s
            }

        # Get stats for all endpoints
        all_stats = {}
        for ep in self._requests.keys():
            all_stats[ep] = self.get_stats(ep)

        return all_stats

    def get_slow_requests(self, threshold_seconds: float = 3.0) -> List[Dict]:
        """
        Get list of slow requests above threshold

        Args:
            threshold_seconds: Duration threshold (default 3.0s)

        Returns:
            List of slow request details
        """
        slow = []

        for endpoint, requests in self._requests.items():
            for ts, dur in requests:
                if dur > threshold_seconds:
                    slow.append({
                        "endpoint": endpoint,
                        "duration_ms": round(dur * 1000, 2),
                        "timestamp": datetime.fromtimestamp(ts).isoformat()
                    })

        return sorted(slow, key=lambda x: x['duration_ms'], reverse=True)


# Global performance stats instance
_performance_stats = PerformanceStats(window_minutes=60)


class PerformanceMonitorMiddleware(BaseHTTPMiddleware):
    """Middleware to monitor API performance"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Monitor request performance

        Tracks:
        - Request duration
        - Endpoint path
        - Slow requests (> 3s)
        """
        # Skip monitoring for certain paths
        if request.url.path in ["/health", "/", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        # Record start time
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Record metrics
        endpoint = f"{request.method} {request.url.path}"
        _performance_stats.record_request(endpoint, duration)

        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration * 1000:.2f}ms"

        # Log slow requests
        if duration > 3.0:
            print(f"⚠️  Slow request detected: {endpoint} took {duration:.2f}s")

        return response


def get_performance_stats(endpoint: str = None) -> Dict:
    """Get performance statistics"""
    return _performance_stats.get_stats(endpoint)


def get_slow_requests(threshold_seconds: float = 3.0) -> List[Dict]:
    """Get slow requests above threshold"""
    return _performance_stats.get_slow_requests(threshold_seconds)


def reset_stats():
    """Reset all performance statistics"""
    global _performance_stats
    _performance_stats = PerformanceStats(window_minutes=60)
