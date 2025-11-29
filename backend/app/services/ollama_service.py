"""
Local LLM Service using Ollama.

ZERO API COST - runs entirely on your Mac.

Usage:
    from app.services.ollama_service import ollama_service

    # Generate text
    response = await ollama_service.generate("Explain this concept...")

    # Critique an explanation
    critique = await ollama_service.critique_explanation(question_dict)

    # Check if Ollama is running
    if ollama_service.is_available():
        ...

Prerequisites:
    1. Install Ollama: brew install ollama
    2. Start server: ollama serve
    3. Pull model: ollama pull llama3:8b
"""

import json
import logging
import threading
from collections import deque
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


class OllamaServiceError(Exception):
    """Base exception for Ollama service errors."""
    pass


class OllamaNotAvailableError(OllamaServiceError):
    """Raised when Ollama server is not running."""
    pass


class OllamaService:
    """
    Local LLM service using Ollama.

    This service provides ZERO-COST AI capabilities by running models locally.
    Use for:
    - Critiquing explanations
    - Generating question variants
    - Quality validation
    - Any task where free > perfect

    For highest quality (one-time burst), use Anthropic Claude instead.
    """

    _instance: Optional['OllamaService'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'OllamaService':
        if cls._instance is None:
            with cls._lock:
                # Double-check after acquiring lock
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "llama3:8b"
    ):
        if self._initialized:
            return

        self.base_url = base_url
        self.default_model = default_model
        # Use deque with maxlen for automatic size limiting
        self._call_history: deque = deque(maxlen=500)
        self._initialized = True

        logger.info(f"Ollama Service initialized (model: {default_model})")

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = 120.0
    ) -> str:
        """
        Generate text using local Ollama model.

        Args:
            prompt: The prompt to generate from
            model: Model to use (default: llama3:8b)
            system: Optional system prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds

        Returns:
            Generated text string

        Raises:
            OllamaNotAvailableError: If Ollama server is not running
            OllamaServiceError: If generation fails
        """
        model = model or self.default_model
        start_time = datetime.utcnow()

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }

                if system:
                    payload["system"] = system

                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )

                if response.status_code == 404:
                    raise OllamaNotAvailableError(
                        f"Model '{model}' not found. "
                        f"Run: ollama pull {model}"
                    )

                response.raise_for_status()
                result = response.json()

                latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                self._record_call(model, success=True, latency_ms=latency_ms)

                return result.get("response", "")

        except httpx.ConnectError:
            self._record_call(model, success=False, error="Connection failed")
            raise OllamaNotAvailableError(
                "Ollama server is not running. "
                "Start it with: ollama serve"
            )
        except Exception as e:
            self._record_call(model, success=False, error=str(e))
            logger.error(f"Ollama generation failed: {e}")
            raise OllamaServiceError(f"Generation failed: {e}")

    # JSON response size limits
    MAX_JSON_RESPONSE_SIZE = 100000
    MAX_RESPONSE_SIZE = 50000

    async def critique_explanation(
        self,
        question: Dict[str, Any],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Critique a USMLE explanation for 285+ quality.

        Args:
            question: Question dict with 'vignette' and 'explanation'
            model: Model to use (default: llama3:8b)

        Returns:
            Dict with 'score' (0-100) and 'issues' list
        """
        # Sanitize inputs to prevent prompt injection
        vignette = str(question.get("vignette", ""))[:500]
        vignette = vignette.replace("</system>", "").replace("<|", "")
        explanation = question.get("explanation", {})

        # Safely serialize explanation
        try:
            explanation_json = json.dumps(explanation, indent=2)[:5000]
        except (TypeError, ValueError):
            explanation_json = str(explanation)[:5000]

        prompt = f"""You are a medical education expert reviewing a USMLE Step 2 CK explanation.

Review this explanation for 285+ scorer quality:

QUESTION STEM (truncated):
{vignette}

EXPLANATION:
{explanation_json}

Evaluate these criteria (each 0-20 points):
1. PATTERN RECOGNITION: Does quick_answer teach first-sentence diagnosis?
2. MECHANISM DEPTH: Are cause->finding->management chains explicit with arrows?
3. DISTRACTOR INSIGHT: Does each wrong answer explain why it's TEMPTING?
4. THRESHOLD CLARITY: Are clinical values defined with (normal X-Y)?
5. BREVITY: Is quick_answer <=30 words and memorable?

Return ONLY valid JSON:
{{"score": <0-100>, "issues": ["issue1", "issue2"], "strengths": ["strength1"]}}"""

        try:
            response = await self.generate(prompt, model=model, temperature=0.3)

            # Limit response size to prevent DoS
            response = response[:self.MAX_RESPONSE_SIZE]

            # Try to extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start < 0 or json_end <= json_start:
                logger.warning("No JSON found in critique response")
                return {
                    "score": 50,
                    "issues": ["Could not find JSON in model response"],
                    "raw_response": response[:500]
                }

            json_str = response[json_start:json_end]

            # Check size before parsing
            if len(json_str) > self.MAX_JSON_RESPONSE_SIZE:
                logger.warning("JSON response too large")
                return {"score": 0, "issues": ["Response exceeds size limit"], "error": True}

            result = json.loads(json_str)

            # Validate required structure
            if not isinstance(result, dict):
                raise ValueError("Expected dict response")

            # Ensure score is valid
            score = result.get("score", 50)
            if not isinstance(score, (int, float)):
                score = 50
            result["score"] = max(0, min(100, score))

            # Ensure issues is a list
            if not isinstance(result.get("issues"), list):
                result["issues"] = []

            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON from model: {e}")
            return {
                "score": 50,
                "issues": ["Could not parse model response as JSON"],
                "raw_response": response[:500] if 'response' in dir() else ""
            }
        except Exception as e:
            logger.warning(f"Critique failed: {e}")
            return {
                "score": 0,
                "issues": [f"Critique failed: {str(e)}"],
                "error": True
            }

    async def generate_variant(
        self,
        question: Dict[str, Any],
        variation_type: str = "age_extreme",
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a variant of an existing question.

        Args:
            question: Original question dict
            variation_type: Type of variation:
                - "age_extreme": Pediatric or geriatric version
                - "comorbidity": Add diabetes, CKD, or pregnancy
                - "atypical": Change classic to atypical presentation
                - "complication": Ask about complication instead
            model: Model to use

        Returns:
            New question dict with modified vignette and choices
        """
        vignette = question.get("vignette", "")
        answer_key = question.get("answer_key", "")

        variation_prompts = {
            "age_extreme": "Change the patient's age to either pediatric (<18) or geriatric (>75), adjusting vital signs and presentation accordingly.",
            "comorbidity": "Add a significant comorbidity (diabetes, CKD stage 3+, or pregnancy) that affects management decisions.",
            "atypical": "Change the presentation from classic to atypical while keeping the same underlying diagnosis.",
            "complication": "Instead of asking for diagnosis, ask about a complication or next step if initial treatment fails."
        }

        prompt = f"""You are creating a USMLE Step 2 CK question variant.

ORIGINAL QUESTION:
{vignette}

CORRECT ANSWER: {answer_key}

VARIATION TYPE: {variation_type}
INSTRUCTION: {variation_prompts.get(variation_type, variation_prompts["comorbidity"])}

Create a modified version of this question. The core medical concept should remain the same, but the presentation should change per the instruction.

Return ONLY valid JSON:
{{
    "vignette": "New clinical vignette...",
    "choices": ["A. ...", "B. ...", "C. ...", "D. ...", "E. ..."],
    "answer_key": "A/B/C/D/E",
    "variation_notes": "Brief explanation of what changed"
}}"""

        try:
            response = await self.generate(prompt, model=model, temperature=0.8)

            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                variant = json.loads(response[json_start:json_end])
                variant["source_question_id"] = question.get("id")
                variant["variation_type"] = variation_type
                return variant

            raise ValueError("No valid JSON in response")

        except Exception as e:
            logger.error(f"Variant generation failed: {e}")
            raise OllamaServiceError(f"Failed to generate variant: {e}")

    async def is_available(self) -> bool:
        """
        Check if Ollama server is running and model is available.

        Returns:
            bool: True if Ollama is ready to use
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """
        List available models in Ollama.

        Returns:
            List of model names
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.warning(f"Failed to list models: {e}")
            return []

    def _record_call(
        self,
        model: str,
        success: bool,
        latency_ms: float = 0,
        error: str = None
    ):
        """Record call for metrics tracking."""
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "model": model,
            "success": success,
            "latency_ms": latency_ms,
            "error": error
        }
        # deque with maxlen handles size automatically
        self._call_history.append(record)

    def get_status(self) -> Dict[str, Any]:
        """Get service status for monitoring."""
        recent_calls = list(self._call_history)[-50:] if self._call_history else []
        successful = sum(1 for c in recent_calls if c.get("success"))

        return {
            "base_url": self.base_url,
            "default_model": self.default_model,
            "recent_calls": len(recent_calls),
            "success_rate": f"{(successful / len(recent_calls) * 100):.1f}%" if recent_calls else "N/A",
            "avg_latency_ms": round(
                sum(c.get("latency_ms", 0) for c in recent_calls if c.get("success"))
                / max(successful, 1), 1
            )
        }


# Global singleton instance
ollama_service = OllamaService()
