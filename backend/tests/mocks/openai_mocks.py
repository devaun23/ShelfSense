"""
Deterministic OpenAI mocks for ShelfSense testing.

These mocks provide predictable responses without API costs,
enabling fast and reliable unit tests for AI-powered features.
"""

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from unittest.mock import MagicMock


# =============================================================================
# Mock Data - Deterministic Responses
# =============================================================================

MOCK_EXPLANATION = {
    "type": "TYPE_A_STABILITY",
    "principle": "Acute cholecystitis with hemodynamic instability requires urgent surgical intervention.",
    "clinical_reasoning": "BP 82/48 (systolic <90) → septic shock from cholecystitis → source control required. Stable patients get antibiotics and elective surgery within 72 hours, but hypotension changes this to urgent.",
    "correct_answer_explanation": "Emergent cholecystectomy is indicated because the patient has signs of septic shock (hypotension, tachycardia) from an infected gallbladder. Source control takes priority over medical optimization.",
    "distractor_explanations": {
        "A": "IV antibiotics alone are insufficient when septic shock is present - source control is required.",
        "B": "ERCP is for choledocholithiasis, not primary cholecystitis management.",
        "C": "Percutaneous drainage is for patients too unstable for surgery, but this patient needs definitive source control.",
        "E": "Observation is inappropriate in septic shock - delay increases mortality."
    },
    "educational_objective": "Recognize that hemodynamic instability in cholecystitis mandates urgent surgical intervention.",
    "concept": "Acute Care Surgery"
}

MOCK_QUESTION_RESPONSE = {
    "vignette": "A 45-year-old woman presents to the emergency department with 2 days of right upper quadrant pain, fever, and nausea. She has a history of gallstones. Temperature is 38.9°C (102°F), blood pressure is 82/48 mm Hg, and pulse is 118/min. Physical examination shows right upper quadrant tenderness with a positive Murphy sign. Laboratory studies show WBC 18,000/μL with 85% neutrophils. Ultrasound shows gallbladder wall thickening to 5 mm and pericholecystic fluid. Which of the following is the most appropriate next step in management?",
    "choices": [
        "A. IV antibiotics and observation",
        "B. ERCP with sphincterotomy",
        "C. Percutaneous cholecystostomy",
        "D. Emergent cholecystectomy",
        "E. Repeat ultrasound in 24 hours"
    ],
    "answer_key": "D",
    "explanation": MOCK_EXPLANATION,
    "source": "AI Agent Generated - Internal Medicine",
    "specialty": "Internal Medicine",
    "recency_weight": 1.0,
    "metadata": {
        "topic": "Acute Cholecystitis",
        "question_type": "management",
        "clinical_setting": "Emergency Department",
        "generation_method": "multi_step_agent",
        "difficulty": "medium"
    }
}

MOCK_QUALITY_SCORES = {
    "quality_score": 85,
    "clinical_accuracy": True,
    "structure_valid": True,
    "has_distractors": True,
    "vignette_length": 180,
    "issues": [],
    "suggestions": []
}

MOCK_CHAT_RESPONSE = {
    "response": "The key to this question is recognizing the hemodynamic instability. When a patient with cholecystitis has a systolic BP <90, this indicates septic shock requiring source control. The critical threshold to remember is BP <90 systolic = unstable = urgent intervention.",
    "key_points": [
        "BP <90 indicates hemodynamic instability",
        "Septic shock requires source control",
        "Urgent surgery takes priority over medical optimization"
    ]
}

MOCK_ERROR_ANALYSIS = {
    "error_type": "premature_closure",
    "confidence": 0.85,
    "explanation": "The student selected antibiotics without recognizing the hemodynamic instability markers.",
    "missed_detail": "Blood pressure 82/48 mm Hg indicates septic shock",
    "correct_reasoning": "Low BP + infection source → septic shock → urgent source control needed",
    "coaching_question": "What vital sign finding in this patient suggests they need more than just antibiotics?"
}

MOCK_STUDY_PLAN = {
    "target_score": 250,
    "exam_date": "2025-03-15",
    "weeks_remaining": 16,
    "weekly_goals": [
        {
            "week": 1,
            "focus_areas": ["Internal Medicine - Cardiology", "Surgery - Acute Care"],
            "questions_target": 100,
            "review_target": 20
        }
    ],
    "weak_areas": ["Surgery", "Pediatrics"],
    "strong_areas": ["Internal Medicine", "Psychiatry"]
}


# =============================================================================
# Mock Classes
# =============================================================================

@dataclass
class MockMessage:
    """Mock OpenAI message object"""
    content: str
    role: str = "assistant"


@dataclass
class MockChoice:
    """Mock OpenAI choice object"""
    message: MockMessage
    index: int = 0
    finish_reason: str = "stop"


@dataclass
class MockChatCompletion:
    """Mock OpenAI chat completion response"""
    id: str = "mock-completion-123"
    object: str = "chat.completion"
    created: int = 1699999999
    model: str = "gpt-4o"
    choices: List[MockChoice] = None

    def __post_init__(self):
        if self.choices is None:
            self.choices = [MockChoice(message=MockMessage(content="{}"))]


class MockOpenAIClient:
    """
    Mock OpenAI client for testing.
    Returns deterministic responses based on the prompt content.
    """

    def __init__(self):
        self.chat = MockChatEndpoint()
        self.call_history: List[Dict[str, Any]] = []

    def get_call_count(self) -> int:
        """Get number of API calls made"""
        return len(self.call_history)

    def get_last_call(self) -> Optional[Dict[str, Any]]:
        """Get the last API call made"""
        return self.call_history[-1] if self.call_history else None

    def reset(self):
        """Reset call history"""
        self.call_history = []


class MockChatEndpoint:
    """Mock for client.chat endpoint"""

    def __init__(self):
        self.completions = MockCompletions()


class MockCompletions:
    """Mock for client.chat.completions endpoint"""

    def __init__(self):
        self.responses: Dict[str, str] = {}
        self.default_response = json.dumps(MOCK_QUESTION_RESPONSE)
        self.call_count = 0

    def set_response(self, key: str, response: Any):
        """Set a specific response for a key"""
        if isinstance(response, dict):
            self.responses[key] = json.dumps(response)
        else:
            self.responses[key] = str(response)

    def create(
        self,
        model: str = "gpt-4o",
        messages: List[Dict[str, str]] = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        **kwargs
    ) -> MockChatCompletion:
        """
        Mock chat completion create method.
        Returns deterministic responses based on message content.
        """
        self.call_count += 1

        # Analyze the prompt to determine response type
        prompt_text = ""
        if messages:
            for msg in messages:
                prompt_text += msg.get("content", "").lower()

        # Determine response based on prompt content
        response_content = self._get_response_for_prompt(prompt_text)

        return MockChatCompletion(
            choices=[
                MockChoice(
                    message=MockMessage(content=response_content)
                )
            ]
        )

    def _get_response_for_prompt(self, prompt: str) -> str:
        """Determine response based on prompt content"""

        # Check for specific response overrides
        for key, response in self.responses.items():
            if key.lower() in prompt:
                return response

        # Question generation prompts
        if "generate" in prompt and "question" in prompt:
            return json.dumps(MOCK_QUESTION_RESPONSE)

        # Quality validation prompts
        if "quality" in prompt or "validate" in prompt or "score" in prompt:
            return json.dumps(MOCK_QUALITY_SCORES)

        # Explanation prompts
        if "explanation" in prompt or "explain" in prompt:
            return json.dumps(MOCK_EXPLANATION)

        # Chat/conversation prompts
        if "chat" in prompt or "help" in prompt or "understand" in prompt:
            return json.dumps(MOCK_CHAT_RESPONSE)

        # Error analysis prompts
        if "error" in prompt or "mistake" in prompt or "wrong" in prompt:
            return json.dumps(MOCK_ERROR_ANALYSIS)

        # Study plan prompts
        if "study" in prompt and "plan" in prompt:
            return json.dumps(MOCK_STUDY_PLAN)

        # Default response
        return self.default_response


# =============================================================================
# Helper Functions
# =============================================================================

def mock_openai_completion(content: Any = None) -> MockChatCompletion:
    """
    Create a mock chat completion response.

    Args:
        content: Response content (dict will be JSON-encoded)

    Returns:
        MockChatCompletion object
    """
    if content is None:
        content = MOCK_QUESTION_RESPONSE

    if isinstance(content, dict):
        content = json.dumps(content)

    return MockChatCompletion(
        choices=[
            MockChoice(
                message=MockMessage(content=content)
            )
        ]
    )


def create_mock_question(
    specialty: str = "Internal Medicine",
    difficulty: str = "medium",
    with_explanation: bool = True
) -> Dict[str, Any]:
    """
    Create a mock question with customizable parameters.

    Args:
        specialty: Medical specialty
        difficulty: easy, medium, or hard
        with_explanation: Include structured explanation

    Returns:
        Mock question dict
    """
    question = MOCK_QUESTION_RESPONSE.copy()
    question["specialty"] = specialty
    question["source"] = f"AI Agent Generated - {specialty}"
    question["metadata"] = {
        **question.get("metadata", {}),
        "difficulty": difficulty
    }

    if not with_explanation:
        question["explanation"] = None

    return question


def create_mock_explanation(
    explanation_type: str = "TYPE_A_STABILITY",
    with_distractors: bool = True
) -> Dict[str, Any]:
    """
    Create a mock explanation with customizable parameters.

    Args:
        explanation_type: TYPE_A through TYPE_F
        with_distractors: Include distractor explanations

    Returns:
        Mock explanation dict
    """
    explanation = MOCK_EXPLANATION.copy()
    explanation["type"] = explanation_type

    if not with_distractors:
        explanation.pop("distractor_explanations", None)

    return explanation


# =============================================================================
# Pytest Fixtures (for use in conftest.py)
# =============================================================================

def get_mock_openai_fixture():
    """
    Returns a fixture function for mocking OpenAI.
    Use in conftest.py:

    from tests.mocks.openai_mocks import get_mock_openai_fixture
    mock_openai_client = get_mock_openai_fixture()
    """
    from unittest.mock import patch
    import pytest

    @pytest.fixture
    def mock_openai_client(monkeypatch):
        """Fixture that replaces OpenAI client with mock"""
        mock_client = MockOpenAIClient()

        with patch("openai.OpenAI", return_value=mock_client):
            yield mock_client

    return mock_openai_client
