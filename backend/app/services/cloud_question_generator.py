"""
Cloud-based Question Generator

Uses OpenAI GPT-4o-mini or Claude Haiku for question generation.
Faster than local Ollama but costs ~$0.01-0.02 per question.

Usage:
    from app.services.cloud_question_generator import CloudQuestionGenerator

    generator = CloudQuestionGenerator(db)
    questions = await generator.generate_for_gap("cardiovascular", "diagnosis", count=5)
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Reuse prompts from ollama generator
from app.services.ollama_question_generator import SYSTEM_CONTEXTS, TASK_STEMS


def get_available_providers() -> List[str]:
    """
    Check which cloud providers are available.

    Returns:
        List of available provider names in priority order.
    """
    available = []

    # Check OpenAI
    if os.getenv('OPENAI_API_KEY'):
        available.append('openai')

    # Check Anthropic
    if os.getenv('ANTHROPIC_API_KEY'):
        available.append('anthropic')

    return available


class CloudQuestionGenerator:
    """
    Generates USMLE Step 2 CK questions using cloud APIs.

    Cost: ~$0.01-0.02 per question (GPT-4o-mini)
    Quality: High
    Speed: 5-15 seconds per question

    Auto-detects available providers. Set one of:
    - OPENAI_API_KEY for GPT-4o-mini
    - ANTHROPIC_API_KEY for Claude Haiku
    """

    def __init__(self, db: Session, provider: str = "auto"):
        """
        Initialize the generator.

        Args:
            db: Database session
            provider: "openai", "anthropic", or "auto" (auto-detect)
        """
        self.db = db
        self._generation_count = 0

        # Auto-detect provider if not specified
        if provider == "auto":
            available = get_available_providers()
            if not available:
                raise ValueError(
                    "No cloud provider API keys found. Set one of:\n"
                    "  - OPENAI_API_KEY (for GPT-4o-mini)\n"
                    "  - ANTHROPIC_API_KEY (for Claude Haiku)\n"
                    "Or use local Ollama without --use-cloud flag."
                )
            self.provider = available[0]
            logger.info(f"Auto-selected provider: {self.provider}")
        else:
            self.provider = provider
            # Validate the requested provider
            if provider == "openai" and not os.getenv('OPENAI_API_KEY'):
                raise ValueError("OPENAI_API_KEY not set. Get one at https://platform.openai.com/api-keys")
            if provider == "anthropic" and not os.getenv('ANTHROPIC_API_KEY'):
                raise ValueError("ANTHROPIC_API_KEY not set. Get one at https://console.anthropic.com")

    async def generate_for_gap(
        self,
        system: str,
        task: str,
        discipline: str = "internal_medicine",
        count: int = 5,
        difficulty: str = "medium"
    ) -> List[Dict[str, Any]]:
        """Generate questions for a specific curriculum gap."""
        logger.info(f"[CLOUD] Generating {count} questions: {system} x {task}")

        questions = []
        for i in range(count):
            try:
                question = await self._generate_single_question(
                    system=system,
                    task=task,
                    discipline=discipline,
                    difficulty=difficulty,
                    attempt=i + 1
                )
                if question:
                    questions.append(question)
                    self._generation_count += 1

            except Exception as e:
                logger.warning(f"Cloud generation failed (attempt {i+1}): {e}")
                continue

        logger.info(f"[CLOUD] Generated {len(questions)}/{count} questions")
        return questions

    async def _generate_single_question(
        self,
        system: str,
        task: str,
        discipline: str,
        difficulty: str,
        attempt: int
    ) -> Optional[Dict[str, Any]]:
        """Generate a single question using cloud API."""

        system_context = SYSTEM_CONTEXTS.get(system, SYSTEM_CONTEXTS["multisystem"])
        task_stems = TASK_STEMS.get(task, TASK_STEMS["diagnosis"])
        question_stem = task_stems[attempt % len(task_stems)]

        prompt = self._build_prompt(
            system=system,
            task=task,
            discipline=discipline,
            difficulty=difficulty,
            system_context=system_context,
            question_stem=question_stem
        )

        try:
            if self.provider == "openai":
                response = await self._call_openai(prompt)
            else:
                response = await self._call_anthropic(prompt)

            question = self._parse_response(response, system, task, discipline)

            if question:
                question["generated_at"] = datetime.utcnow().isoformat()
                question["generator"] = f"cloud_{self.provider}"
                question["needs_validation"] = True

            return question

        except Exception as e:
            logger.error(f"Cloud generation error: {e}")
            return None

    def _build_prompt(
        self,
        system: str,
        task: str,
        discipline: str,
        difficulty: str,
        system_context: str,
        question_stem: str
    ) -> str:
        """Build the generation prompt."""

        difficulty_guidance = {
            "easy": "straightforward presentation with classic findings",
            "medium": "typical presentation requiring integration of multiple findings",
            "hard": "atypical presentation or complex patient with comorbidities"
        }

        return f"""Create a USMLE Step 2 CK practice question.

REQUIREMENTS:
- Body System: {system.replace("_", " ").title()}
- Physician Task: {task.replace("_", " ").title()}
- Discipline: {discipline.replace("_", " ").title()}
- Difficulty: {difficulty.title()} ({difficulty_guidance.get(difficulty, difficulty_guidance["medium"])})

CLINICAL CONTEXT:
{system_context}

QUESTION STEM TO USE:
{question_stem}

Write a clinical vignette (150-250 words) with:
- Patient demographics, chief complaint with duration
- Relevant history and physical exam with vital signs
- Relevant labs/imaging

Create 5 answer choices (A-E) with one clearly correct best answer and four plausible distractors.

Return ONLY valid JSON:
{{
    "vignette": "A 45-year-old woman presents...",
    "question_stem": "{question_stem}",
    "choices": {{
        "A": "Answer A",
        "B": "Answer B",
        "C": "Answer C",
        "D": "Answer D",
        "E": "Answer E"
    }},
    "answer_key": "B",
    "explanation_brief": "Brief explanation...",
    "difficulty": "{difficulty}"
}}"""

    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        from app.services.openai_service import openai_service

        response = openai_service.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            temperature=0.8,
            max_tokens=2000
        )

        return response.choices[0].message.content

    async def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API."""
        import asyncio
        from app.utils.anthropic_client import get_anthropic_client

        client = get_anthropic_client()

        def _sync_call():
            return client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                temperature=0.8,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await asyncio.to_thread(_sync_call)
        return response.content[0].text

    def _parse_response(
        self,
        response: str,
        system: str,
        task: str,
        discipline: str
    ) -> Optional[Dict[str, Any]]:
        """Parse the response into a question dict."""

        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start < 0 or json_end <= json_start:
                logger.warning("No JSON found in response")
                return None

            json_str = response[json_start:json_end]
            question = json.loads(json_str)

            # Validate required fields
            required = ["vignette", "choices", "answer_key"]
            for field in required:
                if field not in question:
                    logger.warning(f"Missing required field: {field}")
                    return None

            # Normalize choices to list format
            if isinstance(question["choices"], dict):
                question["choices_dict"] = question["choices"]
                question["choices"] = [
                    f"{k}. {v}" for k, v in sorted(question["choices"].items())
                ]

            # Add metadata
            question["system"] = system
            question["task"] = task
            question["discipline"] = discipline
            question["specialty"] = discipline
            question["source_type"] = f"ai_generated_cloud"

            return question

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            return None
        except Exception as e:
            logger.warning(f"Parse error: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return {
            "total_generated": self._generation_count,
            "provider": self.provider
        }

    def save_questions_to_db(
        self,
        questions: List[Dict[str, Any]],
        status: str = "pending_review"
    ) -> int:
        """
        Save generated questions to database.

        Args:
            questions: List of question dicts
            status: Initial status for the questions

        Returns:
            Number of questions saved
        """
        from app.models.models import Question
        import uuid

        saved_count = 0

        for q in questions:
            try:
                # Build vignette with question stem if separate
                vignette = q.get("vignette", "")
                if q.get("question_stem") and q.get("question_stem") not in vignette:
                    vignette = f"{vignette}\n\n{q.get('question_stem')}"

                # Create Question model instance
                question = Question(
                    id=str(uuid.uuid4()),
                    vignette=vignette,
                    choices=q.get("choices", []),
                    answer_key=q.get("answer_key", ""),
                    explanation={"brief": q.get("explanation_brief", "")},
                    specialty=q.get("specialty", q.get("discipline", "internal_medicine")),
                    difficulty_level=q.get("difficulty", "medium"),
                    source_type=q.get("source_type", "ai_generated_cloud"),
                    content_status=status,
                    extra_data={
                        "system": q.get("system", ""),
                        "task": q.get("task", ""),
                        "generator": q.get("generator", "cloud"),
                        "generated_at": q.get("generated_at", "")
                    }
                )

                self.db.add(question)
                saved_count += 1

            except Exception as e:
                logger.warning(f"Failed to save question: {e}")
                continue

        try:
            self.db.commit()
            logger.info(f"Saved {saved_count} questions to database")
        except Exception as e:
            logger.error(f"Failed to commit questions: {e}")
            self.db.rollback()
            return 0

        return saved_count
