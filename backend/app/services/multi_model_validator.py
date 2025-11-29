"""
Multi-Model Question Validator

Validates Ollama-generated questions using low-cost models (Claude Haiku / GPT-3.5).
Part of the cost-optimized content pipeline:
  1. Ollama (FREE) generates bulk questions
  2. This validator (LOW COST) checks quality
  3. GPT-4/Claude Sonnet (HIGHER COST) enhances explanations for accepted questions

Usage:
    from app.services.multi_model_validator import MultiModelValidator

    validator = MultiModelValidator()
    result = await validator.validate_question(question_dict)
    # result.status = "ACCEPT" | "REVISE" | "REJECT"
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    ACCEPT = "ACCEPT"      # Question is high quality, ready for use
    REVISE = "REVISE"      # Question has issues but is salvageable
    REJECT = "REJECT"      # Question has critical flaws, discard


class ValidatorModel(Enum):
    CLAUDE_HAIKU = "claude-3-haiku-20240307"
    GPT_35_TURBO = "gpt-3.5-turbo"


@dataclass
class ValidationResult:
    """Result of question validation."""
    status: ValidationStatus
    score: float  # 0-100 overall quality score
    issues: List[str]  # List of identified issues
    suggestions: List[str]  # Improvement suggestions (for REVISE)
    medical_accuracy: float  # 0-100 medical accuracy score
    distractor_quality: float  # 0-100 distractor quality score
    vignette_quality: float  # 0-100 vignette quality score
    model_used: str  # Which validator model was used
    validation_time_ms: float
    raw_response: Optional[str] = None


VALIDATION_PROMPT = """You are a medical education quality assurance specialist reviewing USMLE Step 2 CK practice questions.

Evaluate this question on these criteria:

1. MEDICAL ACCURACY (0-100):
   - Is the clinical presentation realistic and medically accurate?
   - Is the correct answer definitively the best choice?
   - Are the findings consistent with the diagnosis?

2. DISTRACTOR QUALITY (0-100):
   - Are distractors plausible (students might reasonably choose them)?
   - Does each distractor represent a common misconception or near-correct answer?
   - Are distractors clearly wrong but not obviously so?

3. VIGNETTE QUALITY (0-100):
   - Is the patient presentation clear and complete?
   - Are vital signs, labs, and exam findings appropriate?
   - Is the question stem clear and answerable?

CRITICAL DISQUALIFIERS (automatic REJECT):
- Medically incorrect correct answer
- Missing essential clinical information
- Ambiguous question with multiple correct answers
- Offensive or inappropriate content
- Copy of known existing question

QUESTION TO EVALUATE:
{question_json}

Respond with ONLY valid JSON in this exact format:
{{
    "status": "ACCEPT" | "REVISE" | "REJECT",
    "overall_score": <0-100>,
    "medical_accuracy": <0-100>,
    "distractor_quality": <0-100>,
    "vignette_quality": <0-100>,
    "issues": ["issue 1", "issue 2"],
    "suggestions": ["suggestion 1", "suggestion 2"],
    "reasoning": "Brief explanation of decision"
}}"""


class MultiModelValidator:
    """
    Validates AI-generated questions using low-cost models.

    Cost comparison (per 1M tokens, as of 2024):
    - Claude Haiku: $0.25 input, $1.25 output
    - GPT-3.5-turbo: $0.50 input, $1.50 output
    - GPT-4o: $5.00 input, $15.00 output (10-20x more expensive)

    For 100 validations (~2K tokens each): ~$0.25 with Haiku vs $2.50 with GPT-4
    """

    def __init__(
        self,
        preferred_model: ValidatorModel = ValidatorModel.CLAUDE_HAIKU,
        fallback_model: ValidatorModel = ValidatorModel.GPT_35_TURBO,
        min_accept_score: float = 70.0,
        min_revise_score: float = 50.0
    ):
        """
        Initialize the validator.

        Args:
            preferred_model: First choice for validation
            fallback_model: Backup if preferred unavailable
            min_accept_score: Minimum score to ACCEPT (default 70)
            min_revise_score: Minimum score to REVISE vs REJECT (default 50)
        """
        self.preferred_model = preferred_model
        self.fallback_model = fallback_model
        self.min_accept_score = min_accept_score
        self.min_revise_score = min_revise_score

        self._validation_count = 0
        self._accept_count = 0
        self._revise_count = 0
        self._reject_count = 0

    async def validate_question(
        self,
        question: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate a single question.

        Args:
            question: Question dict with vignette, choices, answer_key, etc.

        Returns:
            ValidationResult with status, scores, and feedback
        """
        start_time = datetime.utcnow()

        # Try preferred model first
        model = self.preferred_model
        response = await self._call_validator(question, model)

        # Fallback if preferred failed
        if response is None and self.fallback_model != self.preferred_model:
            logger.warning(f"{model.value} failed, trying fallback {self.fallback_model.value}")
            model = self.fallback_model
            response = await self._call_validator(question, model)

        # Parse response
        if response is None:
            # All validators failed - default to REVISE (manual review needed)
            return ValidationResult(
                status=ValidationStatus.REVISE,
                score=0,
                issues=["Validation service unavailable"],
                suggestions=["Manual review required"],
                medical_accuracy=0,
                distractor_quality=0,
                vignette_quality=0,
                model_used="none",
                validation_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
            )

        result = self._parse_response(response, model.value, start_time)

        # Update stats
        self._validation_count += 1
        if result.status == ValidationStatus.ACCEPT:
            self._accept_count += 1
        elif result.status == ValidationStatus.REVISE:
            self._revise_count += 1
        else:
            self._reject_count += 1

        return result

    async def validate_batch(
        self,
        questions: List[Dict[str, Any]],
        stop_on_reject_streak: int = 5
    ) -> List[ValidationResult]:
        """
        Validate a batch of questions.

        Args:
            questions: List of question dicts
            stop_on_reject_streak: Stop if this many consecutive REJECTs (quality issue)

        Returns:
            List of ValidationResults
        """
        results = []
        reject_streak = 0

        for i, question in enumerate(questions):
            logger.info(f"Validating question {i+1}/{len(questions)}")

            result = await self.validate_question(question)
            results.append(result)

            if result.status == ValidationStatus.REJECT:
                reject_streak += 1
                if reject_streak >= stop_on_reject_streak:
                    logger.warning(
                        f"Stopping validation: {reject_streak} consecutive REJECTs. "
                        "Check generation quality."
                    )
                    break
            else:
                reject_streak = 0

        return results

    async def _call_validator(
        self,
        question: Dict[str, Any],
        model: ValidatorModel
    ) -> Optional[str]:
        """Call the validation model."""

        # Format question for evaluation
        question_json = json.dumps({
            "vignette": question.get("vignette", ""),
            "question_stem": question.get("question_stem", ""),
            "choices": question.get("choices", question.get("choices_dict", {})),
            "answer_key": question.get("answer_key", ""),
            "explanation_brief": question.get("explanation_brief", ""),
            "system": question.get("system", ""),
            "task": question.get("task", ""),
            "difficulty": question.get("difficulty", "medium")
        }, indent=2)

        prompt = VALIDATION_PROMPT.format(question_json=question_json)

        try:
            if model == ValidatorModel.CLAUDE_HAIKU:
                return await self._call_claude_haiku(prompt)
            else:
                return await self._call_gpt35(prompt)

        except Exception as e:
            logger.error(f"Validator {model.value} failed: {e}")
            return None

    async def _call_claude_haiku(self, prompt: str) -> Optional[str]:
        """Call Claude Haiku for validation (async-safe)."""
        import asyncio

        try:
            from app.utils.anthropic_client import get_anthropic_client, is_anthropic_available

            if not is_anthropic_available():
                logger.warning("Anthropic not available")
                return None

            client = get_anthropic_client()

            # Run synchronous Anthropic call in thread pool to avoid blocking event loop
            def _sync_call():
                return client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1000,
                    temperature=0.1,
                    messages=[{"role": "user", "content": prompt}]
                )

            response = await asyncio.to_thread(_sync_call)
            return response.content[0].text

        except Exception as e:
            logger.error(f"Claude Haiku error: {e}")
            return None

    async def _call_gpt35(self, prompt: str) -> Optional[str]:
        """Call GPT-3.5-turbo for validation."""
        try:
            from app.services.openai_service import openai_service, CircuitBreakerOpenError

            response = openai_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-3.5-turbo",
                temperature=0.1,
                max_tokens=1000
            )

            return response.choices[0].message.content

        except CircuitBreakerOpenError:
            logger.warning("OpenAI circuit breaker open")
            return None
        except Exception as e:
            logger.error(f"GPT-3.5 error: {e}")
            return None

    def _parse_response(
        self,
        response: str,
        model_used: str,
        start_time: datetime
    ) -> ValidationResult:
        """Parse the validation response."""

        validation_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        try:
            # Extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start < 0 or json_end <= json_start:
                raise ValueError("No JSON found in response")

            data = json.loads(response[json_start:json_end])

            # Parse status
            status_str = data.get("status", "REVISE").upper()
            if status_str == "ACCEPT":
                status = ValidationStatus.ACCEPT
            elif status_str == "REJECT":
                status = ValidationStatus.REJECT
            else:
                status = ValidationStatus.REVISE

            # Override status based on score thresholds
            overall_score = float(data.get("overall_score", 50))
            if status == ValidationStatus.ACCEPT and overall_score < self.min_accept_score:
                status = ValidationStatus.REVISE
            if status != ValidationStatus.REJECT and overall_score < self.min_revise_score:
                status = ValidationStatus.REJECT

            return ValidationResult(
                status=status,
                score=overall_score,
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                medical_accuracy=float(data.get("medical_accuracy", 50)),
                distractor_quality=float(data.get("distractor_quality", 50)),
                vignette_quality=float(data.get("vignette_quality", 50)),
                model_used=model_used,
                validation_time_ms=validation_time_ms,
                raw_response=response
            )

        except Exception as e:
            logger.warning(f"Failed to parse validation response: {e}")

            # Default to REVISE on parse failure
            return ValidationResult(
                status=ValidationStatus.REVISE,
                score=0,
                issues=["Failed to parse validation response"],
                suggestions=["Manual review required"],
                medical_accuracy=0,
                distractor_quality=0,
                vignette_quality=0,
                model_used=model_used,
                validation_time_ms=validation_time_ms,
                raw_response=response
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        total = self._validation_count

        return {
            "total_validated": total,
            "accepted": self._accept_count,
            "revised": self._revise_count,
            "rejected": self._reject_count,
            "accept_rate": f"{(self._accept_count / total * 100):.1f}%" if total > 0 else "N/A",
            "reject_rate": f"{(self._reject_count / total * 100):.1f}%" if total > 0 else "N/A",
            "preferred_model": self.preferred_model.value,
            "fallback_model": self.fallback_model.value,
            "thresholds": {
                "min_accept_score": self.min_accept_score,
                "min_revise_score": self.min_revise_score
            }
        }


# Convenience function for quick validation
async def validate_question(question: Dict[str, Any]) -> ValidationResult:
    """Quick validation using default settings."""
    validator = MultiModelValidator()
    return await validator.validate_question(question)
