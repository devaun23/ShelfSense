"""
Lazy-initialized OpenAI client to prevent import-time errors
when OPENAI_API_KEY is not set.
"""

import os
from typing import Optional
from openai import OpenAI

_client: Optional[OpenAI] = None


def get_openai_client() -> OpenAI:
    """
    Get a lazily-initialized OpenAI client.

    This prevents the OpenAI client from being initialized at module import time,
    which would cause errors if OPENAI_API_KEY is not set in the environment.

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
        _client = OpenAI(api_key=api_key)

    return _client


def reset_client() -> None:
    """
    Reset the client (useful for testing or when API key changes).
    """
    global _client
    _client = None
