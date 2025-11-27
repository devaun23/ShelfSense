"""
Lazy-initialized OpenAI client to prevent import-time errors
when OPENAI_API_KEY is not set.
"""

import os
from typing import Optional
import httpx
from openai import OpenAI

_client: Optional[OpenAI] = None

# Timeout configuration: 60s total request, 10s connect
DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


def get_openai_client() -> OpenAI:
    """
    Get a lazily-initialized OpenAI client with timeout configuration.

    This prevents the OpenAI client from being initialized at module import time,
    which would cause errors if OPENAI_API_KEY is not set in the environment.

    The client is configured with a 60-second timeout to prevent indefinite hangs.

    Returns:
        OpenAI: The OpenAI client instance

    Raises:
        ValueError: If OPENAI_API_KEY is not set
    """
    global _client

    if _client is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please set it before using AI features."
            )
        _client = OpenAI(api_key=api_key, timeout=DEFAULT_TIMEOUT)

    return _client


def reset_client() -> None:
    """
    Reset the client (useful for testing or when API key changes).
    """
    global _client
    _client = None
