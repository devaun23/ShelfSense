"""
Lazy-initialized Anthropic client for Claude API calls.

Used for one-time burst operations (PDF import, explanation enhancement).
For ongoing operations, use Ollama (ollama_service.py) which is free.
"""

import os
from typing import Optional
import httpx

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

_client: Optional["Anthropic"] = None

# Timeout configuration: 120s total for vision/long generation, 30s connect
DEFAULT_TIMEOUT = httpx.Timeout(120.0, connect=30.0)


def get_anthropic_client() -> "Anthropic":
    """
    Get a lazily-initialized Anthropic client.

    This prevents the client from being initialized at module import time,
    which would cause errors if ANTHROPIC_API_KEY is not set.

    Returns:
        Anthropic: The Anthropic client instance

    Raises:
        ImportError: If anthropic package is not installed
        ValueError: If ANTHROPIC_API_KEY is not set
    """
    global _client

    if Anthropic is None:
        raise ImportError(
            "anthropic package is not installed. "
            "Run: pip install anthropic"
        )

    if _client is None:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Get your API key from https://console.anthropic.com"
            )
        _client = Anthropic(api_key=api_key, timeout=DEFAULT_TIMEOUT)

    return _client


def reset_client() -> None:
    """
    Reset the client (useful for testing or when API key changes).
    """
    global _client
    _client = None


def is_anthropic_available() -> bool:
    """
    Check if Anthropic is available and configured.

    Returns:
        bool: True if package installed and API key set
    """
    if Anthropic is None:
        return False
    return bool(os.getenv('ANTHROPIC_API_KEY'))
