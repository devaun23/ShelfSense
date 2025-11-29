"""
Cognitive Pattern Aggregator

Analyzes student answer behavior to detect reasoning patterns and cognitive archetypes.
Works with the interaction_data collected during study sessions.

Cognitive Archetypes Detected:
- aggressive_interventionist: Always chooses "do something" over watchful waiting
- conservative_hesitator: Avoids invasive procedures, over-monitors
- pattern_matcher: Relies on keyword matching, misses atypical presentations
- premature_closer: Locks in first answer, doesn't consider alternatives
- second_guesser: Changes answers frequently, often from correct to incorrect
- time_pressured: Rushes through questions, misses key details

Usage:
    from app.services.cognitive_aggregator import CognitiveAggregator

    aggregator = CognitiveAggregator(db, user_id)
    profile = await aggregator.analyze_patterns()
    # profile.primary_archetype = "second_guesser"
    # profile.vulnerabilities = [...]
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

logger = logging.getLogger(__name__)


class CognitiveArchetype(Enum):
    """Detected cognitive archetypes."""
    AGGRESSIVE_INTERVENTIONIST = "aggressive_interventionist"
    CONSERVATIVE_HESITATOR = "conservative_hesitator"
    PATTERN_MATCHER = "pattern_matcher"
    PREMATURE_CLOSER = "premature_closer"
    SECOND_GUESSER = "second_guesser"
    TIME_PRESSURED = "time_pressured"
    BALANCED = "balanced"  # No strong archetype detected


@dataclass
class CognitiveVulnerability:
    """A detected cognitive vulnerability."""
    name: str
    description: str
    severity: float  # 0-1, higher = more problematic
    evidence: List[str]  # Examples from their answers
    remediation: str  # Suggested fix


@dataclass
class CognitiveProfile:
    """Complete cognitive profile for a user."""
    user_id: str
    primary_archetype: CognitiveArchetype
    secondary_archetypes: List[CognitiveArchetype]
    vulnerabilities: List[CognitiveVulnerability]
    strengths: List[str]
    answer_change_rate: float  # Percentage of questions with changed answers
    changed_from_correct_rate: float  # How often changes were wrong
    avg_time_per_question: float  # Seconds
    confidence_accuracy_correlation: float  # -1 to 1
    questions_analyzed: int
    analysis_date: datetime
    raw_stats: Dict[str, Any] = field(default_factory=dict)


class CognitiveAggregator:
    """
    Aggregates and analyzes cognitive patterns from question attempts.

    Requires minimum 50 questions for reliable pattern detection.
    More questions = more accurate profile.
    """

    MIN_QUESTIONS_FOR_ANALYSIS = 50
    MIN_QUESTIONS_FOR_ARCHETYPE = 100

    # Thresholds for archetype detection
    THRESHOLDS = {
        "answer_change_high": 0.3,  # 30%+ questions have answer changes
        "answer_change_low": 0.05,  # <5% questions have answer changes
        "changed_from_correct_high": 0.4,  # 40%+ changes were from correct
        "time_fast": 45,  # seconds - rushing
        "time_slow": 180,  # seconds - overthinking
        "confidence_mismatch": 0.3,  # Low correlation = overconfident/underconfident
    }

    def __init__(self, db: Session, user_id: str):
        """
        Initialize the aggregator.

        Args:
            db: Database session
            user_id: User to analyze
        """
        self.db = db
        self.user_id = user_id

    def _validate_interaction_data(self, data: Any) -> Dict[str, Any]:
        """
        Validate and sanitize interaction data to prevent injection attacks.

        Args:
            data: Raw interaction_data from database

        Returns:
            Sanitized dictionary with validated fields
        """
        if data is None:
            return {}

        if not isinstance(data, dict):
            logger.warning(f"Invalid interaction_data type: {type(data)}")
            return {}

        validated = {}

        # Validate answer_changes (must be non-negative integer)
        if "answer_changes" in data:
            try:
                answer_changes = int(data["answer_changes"])
                validated["answer_changes"] = max(0, min(answer_changes, 100))  # Cap at 100
            except (ValueError, TypeError):
                validated["answer_changes"] = 0
        else:
            validated["answer_changes"] = 0

        # Validate answer_history (must be list of single letters A-E)
        if "answer_history" in data:
            if isinstance(data["answer_history"], list):
                validated["answer_history"] = []
                for ans in data["answer_history"][:50]:  # Limit to 50 entries
                    if ans is None:
                        validated["answer_history"].append(None)
                    else:
                        # Only allow single uppercase letters A-E
                        ans_str = str(ans)[:1].upper()
                        if ans_str in ['A', 'B', 'C', 'D', 'E']:
                            validated["answer_history"].append(ans_str)
                        else:
                            logger.warning(f"Invalid answer in history: {ans}")
                            validated["answer_history"].append(None)
            else:
                validated["answer_history"] = []
        else:
            validated["answer_history"] = []

        return validated

    async def analyze_patterns(
        self,
        lookback_days: int = 90
    ) -> Optional[CognitiveProfile]:
        """
        Analyze cognitive patterns from recent question attempts.

        Args:
            lookback_days: How far back to analyze (default 90 days)

        Returns:
            CognitiveProfile or None if insufficient data
        """
        from app.models.models import QuestionAttempt, Question

        # Get recent attempts with interaction data
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

        attempts = self.db.query(QuestionAttempt).filter(
            and_(
                QuestionAttempt.user_id == self.user_id,
                QuestionAttempt.created_at >= cutoff_date
            )
        ).all()

        if len(attempts) < self.MIN_QUESTIONS_FOR_ANALYSIS:
            logger.warning(
                f"Insufficient data for {self.user_id}: {len(attempts)} attempts "
                f"(need {self.MIN_QUESTIONS_FOR_ANALYSIS})"
            )
            return None

        # Aggregate statistics
        stats = self._compute_stats(attempts)

        # Detect archetypes
        archetypes = self._detect_archetypes(stats, len(attempts))

        # Identify vulnerabilities
        vulnerabilities = self._identify_vulnerabilities(stats, attempts)

        # Identify strengths
        strengths = self._identify_strengths(stats)

        # Build profile
        profile = CognitiveProfile(
            user_id=self.user_id,
            primary_archetype=archetypes[0] if archetypes else CognitiveArchetype.BALANCED,
            secondary_archetypes=archetypes[1:3] if len(archetypes) > 1 else [],
            vulnerabilities=vulnerabilities,
            strengths=strengths,
            answer_change_rate=stats["answer_change_rate"],
            changed_from_correct_rate=stats["changed_from_correct_rate"],
            avg_time_per_question=stats["avg_time"],
            confidence_accuracy_correlation=stats["confidence_correlation"],
            questions_analyzed=len(attempts),
            analysis_date=datetime.utcnow(),
            raw_stats=stats
        )

        logger.info(
            f"Cognitive profile for {self.user_id}: "
            f"{profile.primary_archetype.value}, "
            f"{len(vulnerabilities)} vulnerabilities detected"
        )

        return profile

    def _compute_stats(self, attempts: List[Any]) -> Dict[str, Any]:
        """Compute aggregate statistics from attempts."""

        total = len(attempts)
        correct = 0
        questions_with_changes = 0
        changes_from_correct = 0
        total_changes = 0
        times = []
        confidence_accuracy = []  # (confidence, is_correct) pairs

        for attempt in attempts:
            # Basic stats
            if attempt.is_correct:
                correct += 1

            if attempt.time_spent:
                times.append(attempt.time_spent)

            if attempt.confidence_level is not None:
                confidence_accuracy.append(
                    (attempt.confidence_level, 1 if attempt.is_correct else 0)
                )

            # Interaction data stats (validated to prevent injection)
            interaction = self._validate_interaction_data(attempt.interaction_data)

            answer_changes = interaction.get("answer_changes", 0)
            if answer_changes > 0:
                questions_with_changes += 1
                total_changes += answer_changes

                # Check if any change was from correct
                answer_history = interaction.get("answer_history", [])
                if answer_history and len(answer_history) > 1:
                    # Get the correct answer from the question
                    if attempt.question:
                        correct_answer = attempt.question.answer_key
                        # Check if correct answer was in history before final
                        for i, ans in enumerate(answer_history[:-1]):
                            if ans and correct_answer and ans.upper() == correct_answer.upper():
                                changes_from_correct += 1
                                break

        # Calculate rates
        stats = {
            "total_attempts": total,
            "correct": correct,
            "accuracy": correct / total if total > 0 else 0,
            "answer_change_rate": questions_with_changes / total if total > 0 else 0,
            "avg_changes_when_changed": total_changes / questions_with_changes if questions_with_changes > 0 else 0,
            "changed_from_correct_rate": changes_from_correct / questions_with_changes if questions_with_changes > 0 else 0,
            "avg_time": sum(times) / len(times) if times else 0,
            "time_stddev": self._stddev(times) if len(times) > 1 else 0,
            "confidence_correlation": self._correlation(confidence_accuracy) if len(confidence_accuracy) > 10 else 0,
        }

        # Time distribution
        if times:
            stats["time_percentiles"] = {
                "p25": sorted(times)[len(times) // 4],
                "p50": sorted(times)[len(times) // 2],
                "p75": sorted(times)[3 * len(times) // 4],
            }
            stats["fast_answer_rate"] = sum(1 for t in times if t < self.THRESHOLDS["time_fast"]) / len(times)
            stats["slow_answer_rate"] = sum(1 for t in times if t > self.THRESHOLDS["time_slow"]) / len(times)

        return stats

    def _detect_archetypes(
        self,
        stats: Dict[str, Any],
        num_attempts: int
    ) -> List[CognitiveArchetype]:
        """Detect cognitive archetypes from stats."""

        archetypes = []
        scores = {}

        # Second guesser: High answer changes + often changes from correct
        if (stats["answer_change_rate"] >= self.THRESHOLDS["answer_change_high"] and
            stats["changed_from_correct_rate"] >= self.THRESHOLDS["changed_from_correct_high"]):
            scores[CognitiveArchetype.SECOND_GUESSER] = (
                stats["answer_change_rate"] + stats["changed_from_correct_rate"]
            ) / 2

        # Premature closer: Very low answer changes (never reconsiders)
        if stats["answer_change_rate"] <= self.THRESHOLDS["answer_change_low"]:
            # Additional check: confidence doesn't match accuracy
            if abs(stats["confidence_correlation"]) < self.THRESHOLDS["confidence_mismatch"]:
                scores[CognitiveArchetype.PREMATURE_CLOSER] = 1 - stats["answer_change_rate"]

        # Time pressured: Very fast answers
        if stats.get("fast_answer_rate", 0) > 0.4:  # 40%+ questions answered very quickly
            scores[CognitiveArchetype.TIME_PRESSURED] = stats["fast_answer_rate"]

        # Conservative hesitator: Very slow + low confidence
        if stats.get("slow_answer_rate", 0) > 0.3:
            scores[CognitiveArchetype.CONSERVATIVE_HESITATOR] = stats["slow_answer_rate"]

        # Sort by score and return top archetypes
        sorted_archetypes = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Only include archetypes with significant scores
        for archetype, score in sorted_archetypes:
            if score >= 0.3 and num_attempts >= self.MIN_QUESTIONS_FOR_ARCHETYPE:
                archetypes.append(archetype)

        if not archetypes:
            archetypes.append(CognitiveArchetype.BALANCED)

        return archetypes

    def _identify_vulnerabilities(
        self,
        stats: Dict[str, Any],
        attempts: List[Any]
    ) -> List[CognitiveVulnerability]:
        """Identify specific cognitive vulnerabilities."""

        vulnerabilities = []

        # Vulnerability: Second-guessing correct answers
        if stats["changed_from_correct_rate"] > 0.2:
            vulnerabilities.append(CognitiveVulnerability(
                name="Answer Change Regret",
                description="You frequently change your answer from correct to incorrect",
                severity=min(stats["changed_from_correct_rate"], 1.0),
                evidence=self._get_changed_from_correct_examples(attempts),
                remediation=(
                    "Trust your first instinct more. Only change answers when you find "
                    "specific evidence in the question you missed, not just because you're uncertain."
                )
            ))

        # Vulnerability: Rushing
        if stats.get("fast_answer_rate", 0) > 0.3 and stats["accuracy"] < 0.7:
            vulnerabilities.append(CognitiveVulnerability(
                name="Time Pressure Mistakes",
                description="You answer quickly but miss key details in the vignette",
                severity=stats["fast_answer_rate"] * (1 - stats["accuracy"]),
                evidence=[],
                remediation=(
                    "Before selecting an answer, identify at least 3 key findings in the vignette. "
                    "Use the extra time to systematically eliminate distractors."
                )
            ))

        # Vulnerability: Overconfidence
        if stats["confidence_correlation"] < 0:
            vulnerabilities.append(CognitiveVulnerability(
                name="Calibration Gap",
                description="Your confidence doesn't match your accuracy (often wrong when confident)",
                severity=abs(stats["confidence_correlation"]),
                evidence=[],
                remediation=(
                    "Before marking high confidence, explicitly state why each other answer is wrong. "
                    "If you can't, reduce your confidence."
                )
            ))

        # Vulnerability: Never reconsidering
        if stats["answer_change_rate"] < 0.05 and stats["accuracy"] < 0.6:
            vulnerabilities.append(CognitiveVulnerability(
                name="Confirmation Lock",
                description="You rarely reconsider initial answers even when accuracy is low",
                severity=0.6 - stats["accuracy"],
                evidence=[],
                remediation=(
                    "After selecting an answer, actively look for evidence that contradicts it. "
                    "If you find any, reconsider your choice."
                )
            ))

        return vulnerabilities

    def _identify_strengths(self, stats: Dict[str, Any]) -> List[str]:
        """Identify cognitive strengths."""

        strengths = []

        if stats["accuracy"] >= 0.8:
            strengths.append("High overall accuracy")

        if stats["confidence_correlation"] > 0.5:
            strengths.append("Well-calibrated confidence (knows what you know)")

        if 0.05 < stats["answer_change_rate"] < 0.2 and stats["changed_from_correct_rate"] < 0.2:
            strengths.append("Appropriate answer revision (changes improve accuracy)")

        if stats.get("time_percentiles", {}).get("p50", 0) > 60 and stats["accuracy"] > 0.7:
            strengths.append("Thorough analysis (takes time, gets it right)")

        return strengths

    def _get_changed_from_correct_examples(
        self,
        attempts: List[Any],
        max_examples: int = 3
    ) -> List[str]:
        """Get examples where answer was changed from correct to incorrect."""

        examples = []

        for attempt in attempts:
            if len(examples) >= max_examples:
                break

            interaction = attempt.interaction_data or {}
            answer_history = interaction.get("answer_history", [])

            if attempt.question and len(answer_history) > 1:
                correct_answer = attempt.question.answer_key
                final_answer = answer_history[-1] if answer_history else None

                # Check if changed from correct to incorrect
                for i, ans in enumerate(answer_history[:-1]):
                    if (ans and correct_answer and
                        ans.upper() == correct_answer.upper() and
                        final_answer and final_answer.upper() != correct_answer.upper()):

                        # Found an example
                        vignette_preview = (attempt.question.vignette or "")[:100]
                        examples.append(
                            f"Changed from {correct_answer} to {final_answer}: {vignette_preview}..."
                        )
                        break

        return examples

    def _stddev(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5

    def _correlation(self, pairs: List[tuple]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(pairs) < 3:
            return 0

        n = len(pairs)
        x = [p[0] for p in pairs]
        y = [p[1] for p in pairs]

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denom_x = sum((xi - mean_x) ** 2 for xi in x) ** 0.5
        denom_y = sum((yi - mean_y) ** 2 for yi in y) ** 0.5

        if denom_x * denom_y == 0:
            return 0

        return numerator / (denom_x * denom_y)

    async def get_targeted_practice_recommendations(
        self,
        profile: CognitiveProfile,
        num_questions: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get question recommendations that target detected vulnerabilities.

        Args:
            profile: The user's cognitive profile
            num_questions: Number of questions to recommend

        Returns:
            List of question selection criteria
        """
        recommendations = []

        for vuln in profile.vulnerabilities:
            if vuln.name == "Answer Change Regret":
                # Recommend questions with plausible distractors
                recommendations.append({
                    "type": "distractor_quality",
                    "target": "high",
                    "reason": "Practice committing to well-reasoned answers",
                    "count": num_questions // len(profile.vulnerabilities)
                })

            elif vuln.name == "Time Pressure Mistakes":
                # Recommend longer vignettes
                recommendations.append({
                    "type": "vignette_length",
                    "target": "long",
                    "reason": "Practice careful reading under time pressure",
                    "count": num_questions // len(profile.vulnerabilities)
                })

            elif vuln.name == "Calibration Gap":
                # Recommend questions with atypical presentations
                recommendations.append({
                    "type": "presentation",
                    "target": "atypical",
                    "reason": "Challenge overconfidence with unusual cases",
                    "count": num_questions // len(profile.vulnerabilities)
                })

        return recommendations


# Convenience function
async def get_cognitive_profile(db: Session, user_id: str) -> Optional[CognitiveProfile]:
    """Get cognitive profile for a user."""
    aggregator = CognitiveAggregator(db, user_id)
    return await aggregator.analyze_patterns()
