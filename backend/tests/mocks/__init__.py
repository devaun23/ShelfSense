"""
Mock infrastructure for ShelfSense testing.
Provides deterministic mocks for OpenAI and other external services.
"""

from .openai_mocks import (
    MOCK_QUESTION_RESPONSE,
    MOCK_QUALITY_SCORES,
    MOCK_EXPLANATION,
    MOCK_CHAT_RESPONSE,
    MockOpenAIClient,
    MockChatCompletion,
    mock_openai_completion,
    create_mock_question,
    create_mock_explanation,
)

__all__ = [
    "MOCK_QUESTION_RESPONSE",
    "MOCK_QUALITY_SCORES",
    "MOCK_EXPLANATION",
    "MOCK_CHAT_RESPONSE",
    "MockOpenAIClient",
    "MockChatCompletion",
    "mock_openai_completion",
    "create_mock_question",
    "create_mock_explanation",
]
