"""
Adaptive Learning Engine Agent for ShelfSense

This agent is responsible for:
1. Weak area identification (<60% accuracy) with recency weighting
2. Question selection algorithm with difficulty adjustment
3. Pattern recognition for learning behavior
4. Time-to-answer analysis
5. Confidence tracking
6. Learning velocity measurement
7. Predictive analytics
8. Explanation validation and quality assurance

The agent ensures all practice questions have:
- Viable explanations following the 6 explanation types (TYPE_A through TYPE_F)
- Great answer choice explanations for each option
- Compliance with ShelfSense quality rules and NBME standards
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, Integer, Float, desc, case
from openai import OpenAI
from app.models.models import (
    Question, QuestionAttempt, User, UserPerformance,
    ErrorAnalysis, ScheduledReview
)

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Explanation type definitions following ShelfSense framework
EXPLANATION_TYPES = {
    "TYPE_A_STABILITY": {
        "name": "Stable/Unstable Bifurcation",
        "identify": "Vital sign thresholds (BP <90, HR >120, O2 <92)",
        "pattern": "[Finding] with [instability marker] requires [immediate action]"
    },
    "TYPE_B_TIME_SENSITIVE": {
        "name": "Time-Sensitive Decisions",
        "identify": "Time windows (<3 hrs, <4.5 hrs, <24 hrs, >48 hrs)",
        "pattern": "[Condition] within [time window] indicates [intervention]"
    },
    "TYPE_C_DIAGNOSTIC_SEQUENCE": {
        "name": "Diagnostic Sequence",
        "identify": "Test ordering (screening -> confirmatory -> definitive)",
        "pattern": "[Clinical picture] requires [test sequence]"
    },
    "TYPE_D_RISK_STRATIFICATION": {
        "name": "Risk Stratification",
        "identify": "Scoring systems (Wells, CHADS-VASc, CURB-65)",
        "pattern": "[Score threshold] determines [disposition/treatment]"
    },
    "TYPE_E_TREATMENT_HIERARCHY": {
        "name": "Treatment Hierarchy",
        "identify": "First-line vs second-line, contraindications",
        "pattern": "[Condition] treated with [agent] when [criteria met]"
    },
    "TYPE_F_DIFFERENTIAL": {
        "name": "Differential Narrowing",
        "identify": "Key distinguishing features",
        "pattern": "[Specific finding] differentiates [diagnosis] from alternatives"
    }
}

# Quality rules for ShelfSense explanations
EXPLANATION_QUALITY_RULES = {
    "principle_required": "Every explanation must have a clear 1-sentence principle statement",
    "numbers_defined": "Every number must be defined (what makes it abnormal)",
    "no_assumed_knowledge": "Cannot assume student knows thresholds or criteria",
    "clinical_reasoning_flow": "Must use arrow notation (->) to show reasoning flow",
    "distractor_specificity": "Each distractor explanation must be specific to THIS patient",
    "word_limit": "Total explanation should be under 200 words",
    "no_obscure_statistics": "Don't include statistics unless NBME commonly tests them",
    "teachable_pattern": "Pattern should be applicable to similar questions"
}


class AdaptiveLearningEngineAgent:
    """
    Comprehensive adaptive learning engine that manages:
    - Performance analysis and weak area identification
    - Question selection with difficulty adjustment
    - Explanation validation and improvement
    - Learning velocity and predictive analytics
    """

    def __init__(self, db: Session, model: str = "gpt-4o"):
        self.db = db
        self.model = model

    def _call_llm(self, system_prompt: str, user_prompt: str,
                  temperature: float = 0.3, response_format: Optional[Dict] = None) -> str:
        """Helper method to call OpenAI API"""
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    # =========================================================================
    # SECTION 1: WEAK AREA IDENTIFICATION WITH RECENCY WEIGHTING
    # =========================================================================

    def get_detailed_weak_areas(self, user_id: str, threshold: float = 0.6) -> Dict:
        """
        Advanced weak area identification with:
        - Recency weighting (recent performance matters more)
        - Topic-level granularity
        - Trend analysis (improving vs declining)
        - Confidence-weighted accuracy

        Returns detailed breakdown of weak areas with actionable insights.
        """
        # Get all attempts with question data, ordered by time
        attempts = self.db.query(
            QuestionAttempt,
            Question
        ).join(
            Question, QuestionAttempt.question_id == Question.id
        ).filter(
            QuestionAttempt.user_id == user_id
        ).order_by(
            QuestionAttempt.attempted_at.desc()
        ).all()

        if not attempts:
            return {
                "weak_areas": [],
                "analysis": "No attempts yet. Start practicing to get personalized insights.",
                "recommendations": []
            }

        # Calculate recency-weighted performance by source
        performance_by_source = {}
        now = datetime.utcnow()

        for attempt, question in attempts:
            source = question.source or "Unknown"

            if source not in performance_by_source:
                performance_by_source[source] = {
                    "total_weighted": 0.0,
                    "correct_weighted": 0.0,
                    "attempts": [],
                    "recent_trend": []  # Last 5 attempts for trend
                }

            # Calculate recency weight (more recent = higher weight)
            days_ago = (now - attempt.attempted_at).days
            recency_weight = max(0.3, 1.0 - (days_ago / 30) * 0.7)  # 0.3-1.0 range

            # Also factor in question recency weight
            question_weight = question.recency_weight or 0.5
            combined_weight = (recency_weight * 0.6) + (question_weight * 0.4)

            # Factor in confidence if available
            confidence_factor = 1.0
            if attempt.confidence_level:
                # High confidence wrong = worse, high confidence right = better
                if attempt.is_correct:
                    confidence_factor = 1.0 + (attempt.confidence_level - 3) * 0.1
                else:
                    confidence_factor = 1.0 + (attempt.confidence_level - 3) * 0.15  # Penalize overconfident errors

            final_weight = combined_weight * confidence_factor

            performance_by_source[source]["total_weighted"] += final_weight
            if attempt.is_correct:
                performance_by_source[source]["correct_weighted"] += final_weight

            performance_by_source[source]["attempts"].append({
                "is_correct": attempt.is_correct,
                "date": attempt.attempted_at,
                "weight": final_weight,
                "confidence": attempt.confidence_level,
                "time_spent": attempt.time_spent_seconds
            })

        # Calculate weighted accuracy and identify weak areas
        weak_areas = []
        strong_areas = []

        for source, data in performance_by_source.items():
            if data["total_weighted"] > 0:
                weighted_accuracy = data["correct_weighted"] / data["total_weighted"]

                # Calculate trend (improvement or decline)
                recent_attempts = sorted(data["attempts"], key=lambda x: x["date"], reverse=True)[:10]
                if len(recent_attempts) >= 5:
                    first_half = recent_attempts[5:]
                    second_half = recent_attempts[:5]

                    first_accuracy = sum(1 for a in first_half if a["is_correct"]) / len(first_half) if first_half else 0
                    second_accuracy = sum(1 for a in second_half if a["is_correct"]) / len(second_half) if second_half else 0

                    trend = "improving" if second_accuracy > first_accuracy + 0.1 else \
                            "declining" if second_accuracy < first_accuracy - 0.1 else "stable"
                else:
                    trend = "insufficient_data"

                area_data = {
                    "source": source,
                    "weighted_accuracy": round(weighted_accuracy, 3),
                    "raw_accuracy": round(sum(1 for a in data["attempts"] if a["is_correct"]) / len(data["attempts"]), 3),
                    "total_attempts": len(data["attempts"]),
                    "trend": trend,
                    "avg_time_spent": round(
                        sum(a["time_spent"] or 0 for a in data["attempts"]) / len(data["attempts"]), 1
                    ) if data["attempts"] else 0,
                    "avg_confidence": round(
                        sum(a["confidence"] or 3 for a in data["attempts"]) / len(data["attempts"]), 1
                    ) if data["attempts"] else 3.0
                }

                if weighted_accuracy < threshold:
                    weak_areas.append(area_data)
                elif weighted_accuracy >= 0.7:
                    strong_areas.append(area_data)

        # Sort weak areas by accuracy (lowest first)
        weak_areas.sort(key=lambda x: x["weighted_accuracy"])
        strong_areas.sort(key=lambda x: x["weighted_accuracy"], reverse=True)

        # Generate recommendations
        recommendations = self._generate_weak_area_recommendations(weak_areas, strong_areas)

        return {
            "weak_areas": weak_areas,
            "strong_areas": strong_areas,
            "threshold": threshold,
            "analysis": self._generate_performance_analysis(weak_areas, strong_areas),
            "recommendations": recommendations
        }

    def _generate_weak_area_recommendations(self, weak_areas: List[Dict], strong_areas: List[Dict]) -> List[Dict]:
        """Generate actionable recommendations based on weak areas"""
        recommendations = []

        for area in weak_areas[:5]:  # Top 5 weakest
            rec = {
                "source": area["source"],
                "priority": "high" if area["weighted_accuracy"] < 0.4 else "medium",
                "action": f"Focus on {area['source']} - currently at {area['weighted_accuracy']*100:.0f}% accuracy"
            }

            if area["trend"] == "declining":
                rec["urgency"] = "CRITICAL: Performance declining. Immediate review needed."
            elif area["trend"] == "improving":
                rec["encouragement"] = "Good progress! Continue practicing to solidify."

            if area["avg_time_spent"] < 60:
                rec["tip"] = "You're rushing through these. Take more time to analyze."
            elif area["avg_time_spent"] > 180:
                rec["tip"] = "You're spending too long. Work on pattern recognition."

            recommendations.append(rec)

        return recommendations

    def _generate_performance_analysis(self, weak_areas: List[Dict], strong_areas: List[Dict]) -> str:
        """Generate natural language analysis of performance"""
        if not weak_areas and not strong_areas:
            return "Keep practicing to build your performance profile."

        analysis_parts = []

        if weak_areas:
            weakest = weak_areas[0]
            analysis_parts.append(
                f"Your weakest area is {weakest['source']} at {weakest['weighted_accuracy']*100:.0f}% accuracy."
            )
            declining = [a for a in weak_areas if a["trend"] == "declining"]
            if declining:
                analysis_parts.append(
                    f"Warning: Performance is declining in {', '.join(a['source'] for a in declining[:3])}."
                )

        if strong_areas:
            strongest = strong_areas[0]
            analysis_parts.append(
                f"Your strongest area is {strongest['source']} at {strongest['weighted_accuracy']*100:.0f}% accuracy."
            )

        return " ".join(analysis_parts)

    # =========================================================================
    # SECTION 2: QUESTION SELECTION WITH DIFFICULTY ADJUSTMENT
    # =========================================================================

    def select_adaptive_question(self, user_id: str,
                                 prefer_weak_areas: bool = True,
                                 difficulty_adjustment: float = 0.0) -> Optional[Question]:
        """
        Advanced question selection algorithm that:
        - Prioritizes weak areas
        - Adjusts difficulty based on recent performance
        - Avoids recently answered questions
        - Balances review and new material

        Args:
            user_id: The user's ID
            prefer_weak_areas: Whether to prioritize weak areas
            difficulty_adjustment: -1.0 (easier) to 1.0 (harder) adjustment

        Returns:
            Selected Question object or None
        """
        # Get user's weak areas
        weak_analysis = self.get_detailed_weak_areas(user_id)
        weak_sources = [a["source"] for a in weak_analysis.get("weak_areas", [])]

        # Get recently answered question IDs (last 24 hours)
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_ids = [
            r[0] for r in self.db.query(QuestionAttempt.question_id).filter(
                QuestionAttempt.user_id == user_id,
                QuestionAttempt.attempted_at >= recent_cutoff
            ).all()
        ]

        # Get all attempted question IDs
        all_attempted = [
            r[0] for r in self.db.query(QuestionAttempt.question_id).filter(
                QuestionAttempt.user_id == user_id
            ).all()
        ]

        # Calculate target difficulty based on user's performance
        user_accuracy = self._get_recent_accuracy(user_id, days=7)

        # Adjust difficulty: if performing well (>70%), increase difficulty
        # If struggling (<50%), decrease difficulty
        base_difficulty = 0.5  # Assume questions have difficulty 0-1
        if user_accuracy > 0.7:
            target_difficulty = min(1.0, base_difficulty + 0.2 + difficulty_adjustment * 0.2)
        elif user_accuracy < 0.5:
            target_difficulty = max(0.0, base_difficulty - 0.2 + difficulty_adjustment * 0.2)
        else:
            target_difficulty = base_difficulty + difficulty_adjustment * 0.2

        # Build query for unanswered questions
        query = self.db.query(Question).filter(
            Question.rejected == False
        )

        # Exclude recently answered (but allow repeat of older ones if needed)
        if recent_ids:
            query = query.filter(~Question.id.in_(recent_ids))

        # Prioritize weak areas if requested
        if prefer_weak_areas and weak_sources:
            weak_query = query.filter(Question.source.in_(weak_sources))
            weak_questions = weak_query.order_by(
                Question.recency_weight.desc()
            ).limit(50).all()

            if weak_questions:
                # Filter out already attempted if we have enough new ones
                unattempted = [q for q in weak_questions if q.id not in all_attempted]
                if len(unattempted) >= 5:
                    return self._select_by_difficulty(unattempted, target_difficulty)
                return self._select_by_difficulty(weak_questions, target_difficulty)

        # Fall back to unanswered questions across all sources
        unanswered = query.filter(
            ~Question.id.in_(all_attempted) if all_attempted else True
        ).order_by(
            Question.recency_weight.desc()
        ).limit(100).all()

        if unanswered:
            return self._select_by_difficulty(unanswered, target_difficulty)

        # Last resort: any question not recently answered
        any_question = query.order_by(
            Question.recency_weight.desc()
        ).first()

        return any_question

    def _select_by_difficulty(self, questions: List[Question],
                              target_difficulty: float) -> Question:
        """Select a question closest to target difficulty from pool"""
        import random

        # For now, use recency_weight as a proxy for difficulty
        # (newer questions tend to be harder as they reflect current exam trends)
        # Later, add actual difficulty scoring based on user performance

        scored_questions = []
        for q in questions:
            # Use recency_weight as difficulty proxy (higher = harder)
            q_difficulty = q.recency_weight or 0.5
            distance = abs(q_difficulty - target_difficulty)
            scored_questions.append((q, distance))

        # Sort by distance and take top 20%
        scored_questions.sort(key=lambda x: x[1])
        top_candidates = [q for q, _ in scored_questions[:max(5, len(scored_questions) // 5)]]

        return random.choice(top_candidates)

    def _get_recent_accuracy(self, user_id: str, days: int = 7) -> float:
        """Get user's accuracy over recent days"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        recent_attempts = self.db.query(QuestionAttempt).filter(
            QuestionAttempt.user_id == user_id,
            QuestionAttempt.attempted_at >= cutoff
        ).all()

        if not recent_attempts:
            return 0.6  # Default to 60%

        correct = sum(1 for a in recent_attempts if a.is_correct)
        return correct / len(recent_attempts)

    # =========================================================================
    # SECTION 3: TIME-TO-ANSWER ANALYSIS
    # =========================================================================

    def analyze_time_patterns(self, user_id: str) -> Dict:
        """
        Comprehensive time-to-answer analysis:
        - Optimal time range identification
        - Correlation with correctness
        - Speed vs accuracy tradeoff
        - Time trends over sessions
        """
        attempts = self.db.query(QuestionAttempt).filter(
            QuestionAttempt.user_id == user_id,
            QuestionAttempt.time_spent_seconds.isnot(None)
        ).order_by(QuestionAttempt.attempted_at).all()

        if len(attempts) < 10:
            return {
                "analysis": "Need more attempts for time analysis",
                "optimal_time_range": None,
                "recommendations": []
            }

        # Group by time buckets
        time_buckets = {
            "rushed": {"range": "< 30s", "correct": 0, "total": 0},
            "quick": {"range": "30-60s", "correct": 0, "total": 0},
            "normal": {"range": "60-120s", "correct": 0, "total": 0},
            "careful": {"range": "120-180s", "correct": 0, "total": 0},
            "slow": {"range": "> 180s", "correct": 0, "total": 0}
        }

        for attempt in attempts:
            time = attempt.time_spent_seconds

            if time < 30:
                bucket = "rushed"
            elif time < 60:
                bucket = "quick"
            elif time < 120:
                bucket = "normal"
            elif time < 180:
                bucket = "careful"
            else:
                bucket = "slow"

            time_buckets[bucket]["total"] += 1
            if attempt.is_correct:
                time_buckets[bucket]["correct"] += 1

        # Calculate accuracy per bucket
        accuracies = {}
        for bucket, data in time_buckets.items():
            if data["total"] > 0:
                accuracies[bucket] = {
                    "accuracy": round(data["correct"] / data["total"], 3),
                    "count": data["total"],
                    "range": data["range"]
                }

        # Find optimal time range
        valid_buckets = [(b, d) for b, d in accuracies.items() if d["count"] >= 5]
        if valid_buckets:
            optimal_bucket = max(valid_buckets, key=lambda x: x[1]["accuracy"])
            optimal_time_range = optimal_bucket[1]["range"]
        else:
            optimal_time_range = "60-120s"  # Default

        # Calculate average time by correctness
        correct_times = [a.time_spent_seconds for a in attempts if a.is_correct]
        incorrect_times = [a.time_spent_seconds for a in attempts if not a.is_correct]

        avg_correct_time = sum(correct_times) / len(correct_times) if correct_times else 0
        avg_incorrect_time = sum(incorrect_times) / len(incorrect_times) if incorrect_times else 0

        # Generate recommendations
        recommendations = []
        if accuracies.get("rushed", {}).get("accuracy", 1) < 0.4:
            recommendations.append("Avoid rushing - your accuracy drops significantly under 30 seconds.")
        if accuracies.get("slow", {}).get("accuracy", 1) < accuracies.get("normal", {}).get("accuracy", 0):
            recommendations.append("Taking too long may indicate overthinking. Trust your first instinct.")
        if avg_incorrect_time < avg_correct_time - 20:
            recommendations.append("You tend to get questions wrong when rushing. Slow down slightly.")

        return {
            "time_buckets": accuracies,
            "optimal_time_range": optimal_time_range,
            "avg_time_correct": round(avg_correct_time, 1),
            "avg_time_incorrect": round(avg_incorrect_time, 1),
            "total_analyzed": len(attempts),
            "recommendations": recommendations,
            "analysis": f"Your optimal time range is {optimal_time_range}. "
                       f"Correct answers average {avg_correct_time:.0f}s vs {avg_incorrect_time:.0f}s for incorrect."
        }

    # =========================================================================
    # SECTION 4: CONFIDENCE TRACKING
    # =========================================================================

    def analyze_confidence_patterns(self, user_id: str) -> Dict:
        """
        Analyze correlation between confidence and accuracy:
        - Calibration analysis (overconfident vs underconfident)
        - Confidence by topic
        - Metacognitive awareness score
        """
        attempts = self.db.query(QuestionAttempt, Question).join(
            Question, QuestionAttempt.question_id == Question.id
        ).filter(
            QuestionAttempt.user_id == user_id,
            QuestionAttempt.confidence_level.isnot(None)
        ).all()

        if len(attempts) < 20:
            return {
                "analysis": "Need more confidence-rated attempts for analysis",
                "calibration_score": None,
                "by_confidence_level": {}
            }

        # Analyze by confidence level (1-5)
        by_confidence = {i: {"correct": 0, "total": 0} for i in range(1, 6)}
        by_source_confidence = {}

        for attempt, question in attempts:
            conf = attempt.confidence_level
            by_confidence[conf]["total"] += 1
            if attempt.is_correct:
                by_confidence[conf]["correct"] += 1

            # Track by source too
            source = question.source or "Unknown"
            if source not in by_source_confidence:
                by_source_confidence[source] = {"confident_correct": 0, "confident_total": 0,
                                                  "unconfident_correct": 0, "unconfident_total": 0}

            if conf >= 4:  # High confidence
                by_source_confidence[source]["confident_total"] += 1
                if attempt.is_correct:
                    by_source_confidence[source]["confident_correct"] += 1
            else:
                by_source_confidence[source]["unconfident_total"] += 1
                if attempt.is_correct:
                    by_source_confidence[source]["unconfident_correct"] += 1

        # Calculate calibration
        # Perfect calibration: confidence 1 = 20% right, confidence 5 = 100% right
        expected_accuracy = {1: 0.2, 2: 0.4, 3: 0.6, 4: 0.8, 5: 1.0}
        calibration_error = 0
        calibration_details = {}

        for conf, data in by_confidence.items():
            if data["total"] > 0:
                actual_accuracy = data["correct"] / data["total"]
                expected = expected_accuracy[conf]
                error = actual_accuracy - expected
                calibration_error += abs(error)

                calibration_details[conf] = {
                    "expected": expected,
                    "actual": round(actual_accuracy, 3),
                    "count": data["total"],
                    "calibration": "overconfident" if error < -0.1 else
                                   "underconfident" if error > 0.1 else "well-calibrated"
                }

        # Calculate overall calibration score (0-100, higher is better)
        calibration_score = max(0, 100 - (calibration_error * 20))

        # Identify problematic patterns
        overconfident_errors = by_confidence[5]["total"] - by_confidence[5]["correct"]
        underconfident_correct = by_confidence[1]["correct"]

        recommendations = []
        if calibration_details.get(5, {}).get("calibration") == "overconfident":
            recommendations.append(
                f"You're overconfident on 'very sure' answers ({calibration_details[5]['actual']*100:.0f}% correct vs expected 100%). "
                "Double-check when you feel most confident."
            )
        if calibration_details.get(1, {}).get("calibration") == "underconfident":
            recommendations.append(
                f"You're underconfident on 'guessing' answers ({calibration_details[1]['actual']*100:.0f}% correct vs expected 20%). "
                "Trust your knowledge more."
            )

        return {
            "calibration_score": round(calibration_score, 1),
            "by_confidence_level": calibration_details,
            "overconfident_errors": overconfident_errors,
            "underconfident_correct": underconfident_correct,
            "metacognitive_analysis": self._generate_metacognitive_analysis(calibration_details),
            "recommendations": recommendations,
            "total_analyzed": len(attempts)
        }

    def _generate_metacognitive_analysis(self, calibration_details: Dict) -> str:
        """Generate analysis of metacognitive awareness"""
        issues = []

        if calibration_details.get(5, {}).get("calibration") == "overconfident":
            issues.append("overconfident when certain")
        if calibration_details.get(1, {}).get("calibration") == "underconfident":
            issues.append("underconfident when guessing")

        if not issues:
            return "Your confidence calibration is excellent. You know what you know."

        return f"Metacognitive areas to work on: {', '.join(issues)}."

    # =========================================================================
    # SECTION 5: LEARNING VELOCITY MEASUREMENT
    # =========================================================================

    def calculate_learning_velocity(self, user_id: str) -> Dict:
        """
        Measure how quickly the user is learning:
        - Questions to mastery (attempts until consistently correct)
        - Improvement rate over time
        - Topic-specific learning speed
        - Predicted time to target score
        """
        # Get all attempts ordered by date
        attempts = self.db.query(QuestionAttempt, Question).join(
            Question, QuestionAttempt.question_id == Question.id
        ).filter(
            QuestionAttempt.user_id == user_id
        ).order_by(QuestionAttempt.attempted_at).all()

        if len(attempts) < 20:
            return {
                "analysis": "Need more attempts to measure learning velocity",
                "velocity_score": None
            }

        # Calculate weekly performance
        weekly_performance = {}
        for attempt, question in attempts:
            week = attempt.attempted_at.isocalendar()[1]
            year = attempt.attempted_at.year
            key = f"{year}-W{week}"

            if key not in weekly_performance:
                weekly_performance[key] = {"correct": 0, "total": 0}

            weekly_performance[key]["total"] += 1
            if attempt.is_correct:
                weekly_performance[key]["correct"] += 1

        # Calculate weekly accuracies
        weekly_accuracies = []
        for week, data in sorted(weekly_performance.items()):
            if data["total"] >= 5:  # Minimum attempts for meaningful data
                weekly_accuracies.append({
                    "week": week,
                    "accuracy": data["correct"] / data["total"],
                    "count": data["total"]
                })

        # Calculate velocity (improvement per week)
        if len(weekly_accuracies) >= 2:
            first_half = weekly_accuracies[:len(weekly_accuracies)//2]
            second_half = weekly_accuracies[len(weekly_accuracies)//2:]

            first_avg = sum(w["accuracy"] for w in first_half) / len(first_half)
            second_avg = sum(w["accuracy"] for w in second_half) / len(second_half)

            weeks_elapsed = len(weekly_accuracies)
            velocity_per_week = (second_avg - first_avg) / (weeks_elapsed / 2) if weeks_elapsed > 0 else 0
        else:
            velocity_per_week = 0
            first_avg = second_avg = sum(w["accuracy"] for w in weekly_accuracies) / len(weekly_accuracies) if weekly_accuracies else 0.5

        # Calculate topic-specific learning speed
        topic_velocity = {}
        topic_attempts = {}

        for attempt, question in attempts:
            source = question.source or "Unknown"
            if source not in topic_attempts:
                topic_attempts[source] = []
            topic_attempts[source].append({
                "correct": attempt.is_correct,
                "date": attempt.attempted_at
            })

        for source, source_attempts in topic_attempts.items():
            if len(source_attempts) >= 10:
                first_5 = source_attempts[:5]
                last_5 = source_attempts[-5:]

                first_acc = sum(1 for a in first_5 if a["correct"]) / 5
                last_acc = sum(1 for a in last_5 if a["correct"]) / 5

                topic_velocity[source] = {
                    "initial_accuracy": round(first_acc, 3),
                    "current_accuracy": round(last_acc, 3),
                    "improvement": round(last_acc - first_acc, 3),
                    "total_attempts": len(source_attempts)
                }

        # Generate velocity score (0-100)
        if velocity_per_week > 0.03:
            velocity_score = min(100, 70 + velocity_per_week * 1000)
            velocity_label = "Excellent - rapidly improving"
        elif velocity_per_week > 0.01:
            velocity_score = 50 + velocity_per_week * 1000
            velocity_label = "Good - steady improvement"
        elif velocity_per_week > -0.01:
            velocity_score = 50
            velocity_label = "Plateau - maintaining performance"
        else:
            velocity_score = max(0, 50 + velocity_per_week * 1000)
            velocity_label = "Declining - review strategy"

        # Estimate weeks to target
        current_accuracy = second_avg if len(weekly_accuracies) >= 2 else 0.5
        target_accuracy = 0.75  # 75% = ~245 predicted score

        if velocity_per_week > 0:
            weeks_to_target = max(0, (target_accuracy - current_accuracy) / velocity_per_week)
        else:
            weeks_to_target = None  # Cannot estimate

        return {
            "velocity_score": round(velocity_score, 1),
            "velocity_label": velocity_label,
            "velocity_per_week": round(velocity_per_week, 4),
            "current_accuracy": round(second_avg if len(weekly_accuracies) >= 2 else 0.5, 3),
            "weeks_to_target": round(weeks_to_target, 1) if weeks_to_target else None,
            "weekly_trend": weekly_accuracies[-5:] if weekly_accuracies else [],
            "topic_velocity": topic_velocity,
            "analysis": f"Learning velocity: {velocity_label}. "
                       f"Currently at {second_avg*100:.0f}% accuracy, "
                       f"{'improving' if velocity_per_week > 0 else 'declining'} by {abs(velocity_per_week)*100:.1f}% per week."
        }

    # =========================================================================
    # SECTION 6: PREDICTIVE ANALYTICS
    # =========================================================================

    def predict_exam_performance(self, user_id: str) -> Dict:
        """
        Comprehensive predictive analytics:
        - Predicted Step 2 CK score with confidence interval
        - Score breakdown by specialty
        - Risk areas for exam
        - Readiness assessment
        """
        # Get all attempts with recency weighting
        attempts = self.db.query(
            QuestionAttempt.is_correct,
            Question.recency_weight,
            Question.source
        ).join(
            Question, QuestionAttempt.question_id == Question.id
        ).filter(
            QuestionAttempt.user_id == user_id
        ).all()

        if len(attempts) < 50:
            return {
                "predicted_score": None,
                "confidence_interval": None,
                "analysis": f"Need at least 50 attempts for prediction (currently {len(attempts)})",
                "readiness": "insufficient_data"
            }

        # Calculate weighted accuracy
        total_weight = 0
        weighted_correct = 0
        by_source = {}

        for is_correct, weight, source in attempts:
            weight = weight or 0.5
            total_weight += weight
            if is_correct:
                weighted_correct += weight

            if source not in by_source:
                by_source[source] = {"weight": 0, "correct_weight": 0}
            by_source[source]["weight"] += weight
            if is_correct:
                by_source[source]["correct_weight"] += weight

        weighted_accuracy = weighted_correct / total_weight if total_weight > 0 else 0.5

        # Predict score using the ShelfSense formula
        # Score = 194 + (weighted_accuracy - 0.6) * 265
        predicted_score = 194 + (weighted_accuracy - 0.6) * 265
        predicted_score = round(max(194, min(300, predicted_score)))

        # Calculate confidence interval based on sample size
        sample_factor = min(1.0, len(attempts) / 200)  # More attempts = tighter interval
        base_interval = 15  # Base +/- points
        confidence_interval = round(base_interval * (2 - sample_factor))

        # Calculate by-specialty predictions
        specialty_predictions = {}
        for source, data in by_source.items():
            if data["weight"] > 5:  # Minimum weight threshold
                specialty_acc = data["correct_weight"] / data["weight"]
                specialty_score = 194 + (specialty_acc - 0.6) * 265
                specialty_predictions[source] = {
                    "accuracy": round(specialty_acc, 3),
                    "predicted_contribution": round(max(194, min(300, specialty_score))),
                    "weight": round(data["weight"], 1)
                }

        # Identify risk areas (specialties significantly below average)
        avg_specialty_score = sum(s["predicted_contribution"] for s in specialty_predictions.values()) / len(specialty_predictions) if specialty_predictions else predicted_score
        risk_areas = [
            {"source": source, "score": data["predicted_contribution"]}
            for source, data in specialty_predictions.items()
            if data["predicted_contribution"] < avg_specialty_score - 10
        ]
        risk_areas.sort(key=lambda x: x["score"])

        # Determine readiness
        if predicted_score >= 250:
            readiness = "high"
            readiness_label = "Well prepared for exam"
        elif predicted_score >= 230:
            readiness = "moderate"
            readiness_label = "On track, continue practicing"
        elif predicted_score >= 210:
            readiness = "developing"
            readiness_label = "More practice needed"
        else:
            readiness = "needs_work"
            readiness_label = "Focus on weak areas before exam"

        return {
            "predicted_score": predicted_score,
            "confidence_interval": confidence_interval,
            "score_range": f"{predicted_score - confidence_interval} - {predicted_score + confidence_interval}",
            "weighted_accuracy": round(weighted_accuracy, 3),
            "total_attempts": len(attempts),
            "specialty_predictions": specialty_predictions,
            "risk_areas": risk_areas[:5],
            "readiness": readiness,
            "readiness_label": readiness_label,
            "analysis": f"Predicted score: {predicted_score} ({predicted_score - confidence_interval}-{predicted_score + confidence_interval}). "
                       f"Based on {len(attempts)} questions at {weighted_accuracy*100:.0f}% weighted accuracy. "
                       f"Status: {readiness_label}."
        }

    # =========================================================================
    # SECTION 7: EXPLANATION VALIDATION & QUALITY ASSURANCE
    # =========================================================================

    def validate_question_explanation(self, question_id: str) -> Dict:
        """
        Validate that a question's explanation meets ShelfSense quality standards:
        - Has all required explanation components
        - Follows one of the 6 explanation types
        - Each answer choice has a specific explanation
        - Meets quality rules

        Returns validation result with specific issues and suggestions.
        """
        question = self.db.query(Question).filter(Question.id == question_id).first()

        if not question:
            return {"valid": False, "error": "Question not found"}

        explanation = question.explanation
        choices = question.choices
        answer_key = question.answer_key

        issues = []
        suggestions = []

        # Check if explanation exists
        if not explanation:
            return {
                "valid": False,
                "question_id": question_id,
                "issues": ["No explanation found"],
                "suggestions": ["Generate explanation using the explanation framework"],
                "needs_regeneration": True
            }

        # Handle both dict and string explanations
        if isinstance(explanation, str):
            issues.append("Explanation is plain text, not structured JSON")
            suggestions.append("Convert to structured explanation with type, principle, clinical_reasoning, and distractor_explanations")
            return {
                "valid": False,
                "question_id": question_id,
                "issues": issues,
                "suggestions": suggestions,
                "needs_regeneration": True,
                "current_explanation": explanation[:500]
            }

        # Validate explanation structure
        required_fields = ["principle", "clinical_reasoning", "correct_answer_explanation"]

        for field in required_fields:
            if field not in explanation or not explanation[field]:
                issues.append(f"Missing required field: {field}")

        # Check for explanation type
        explanation_type = explanation.get("type", "")
        if explanation_type and explanation_type not in EXPLANATION_TYPES:
            issues.append(f"Invalid explanation type: {explanation_type}")
            suggestions.append(f"Use one of: {', '.join(EXPLANATION_TYPES.keys())}")
        elif not explanation_type:
            issues.append("Missing explanation type classification")
            suggestions.append("Classify into one of the 6 explanation types (TYPE_A through TYPE_F)")

        # Check distractor explanations
        distractor_explanations = explanation.get("distractor_explanations", {})

        if not distractor_explanations:
            issues.append("Missing distractor explanations")
            suggestions.append("Add explanations for why each wrong answer is incorrect")
        else:
            # Check that each choice has an explanation
            choice_letters = ["A", "B", "C", "D", "E"][:len(choices)]

            for letter in choice_letters:
                if letter == answer_key:
                    continue  # Skip correct answer

                if letter not in distractor_explanations:
                    issues.append(f"Missing explanation for choice {letter}")
                elif len(distractor_explanations[letter]) < 20:
                    issues.append(f"Explanation for choice {letter} is too brief")
                    suggestions.append(f"Expand explanation for {letter} to explain why it's wrong for THIS patient")

        # Check principle quality
        principle = explanation.get("principle", "")
        if principle:
            if len(principle) > 200:
                issues.append("Principle statement is too long (should be 1-2 sentences)")
            if not any(char in principle for char in [".", "requires", "indicates", "treated with"]):
                suggestions.append("Principle should be a clear decision rule")

        # Check clinical reasoning
        clinical_reasoning = explanation.get("clinical_reasoning", "")
        if clinical_reasoning:
            if "->" not in clinical_reasoning and "→" not in clinical_reasoning:
                suggestions.append("Clinical reasoning should use arrow notation (→) to show reasoning flow")

            # Check for undefined numbers
            import re
            numbers = re.findall(r'\d+(?:\.\d+)?', clinical_reasoning)
            if numbers and "(" not in clinical_reasoning:
                suggestions.append("Numbers should be defined with what makes them abnormal (e.g., 'BP 80/50 (systolic <90)')")

        # Calculate quality score
        total_checks = 10
        passed_checks = total_checks - len(issues)
        quality_score = (passed_checks / total_checks) * 100

        return {
            "valid": len(issues) == 0,
            "question_id": question_id,
            "quality_score": round(quality_score, 1),
            "issues": issues,
            "suggestions": suggestions,
            "needs_regeneration": quality_score < 60,
            "explanation_type": explanation_type,
            "has_distractor_explanations": bool(distractor_explanations),
            "answer_key": answer_key
        }

    def generate_improved_explanation(self, question_id: str) -> Dict:
        """
        Generate an improved explanation for a question that:
        - Follows the 6 explanation types framework
        - Has proper principle, clinical reasoning, and distractor explanations
        - Meets all ShelfSense quality rules
        """
        question = self.db.query(Question).filter(Question.id == question_id).first()

        if not question:
            return {"success": False, "error": "Question not found"}

        vignette = question.vignette
        choices = question.choices
        answer_key = question.answer_key
        current_explanation = question.explanation

        # Determine the appropriate explanation type
        type_prompt = f"""Analyze this USMLE question and determine which explanation type it fits best.

VIGNETTE:
{vignette}

CHOICES:
{chr(10).join([f'{chr(65+i)}. {choice}' for i, choice in enumerate(choices)])}

CORRECT ANSWER: {answer_key}

EXPLANATION TYPES:
{json.dumps(EXPLANATION_TYPES, indent=2)}

Return JSON with:
{{
    "best_type": "TYPE_X_NAME",
    "reasoning": "Why this type fits"
}}"""

        type_response = self._call_llm(
            "You are a medical education expert classifying USMLE questions.",
            type_prompt,
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        type_result = json.loads(type_response)
        explanation_type = type_result.get("best_type", "TYPE_E_TREATMENT_HIERARCHY")

        # Generate the full explanation
        generation_prompt = f"""Generate a high-quality educational explanation for this USMLE question.

VIGNETTE:
{vignette}

CHOICES:
{chr(10).join([f'{chr(65+i)}. {choice}' for i, choice in enumerate(choices)])}

CORRECT ANSWER: {answer_key}

EXPLANATION TYPE TO USE: {explanation_type}
TYPE DEFINITION: {json.dumps(EXPLANATION_TYPES.get(explanation_type, {}), indent=2)}

QUALITY RULES TO FOLLOW:
{json.dumps(EXPLANATION_QUALITY_RULES, indent=2)}

Generate a complete explanation following this exact JSON structure:
{{
    "type": "{explanation_type}",
    "principle": "One sentence with the exact decision rule (max 50 words)",
    "clinical_reasoning": "2-3 sentences using arrow notation (→) to show reasoning flow. Define all numbers explicitly. Example: 'BP 80/50 (systolic <90) → septic shock → source control required'",
    "correct_answer_explanation": "Why the correct answer ({answer_key}) is right. Include pathophysiology and clinical logic. Use → notation.",
    "distractor_explanations": {{
        "A": "Why A is wrong for THIS patient (skip if A is correct)",
        "B": "Why B is wrong for THIS patient (skip if B is correct)",
        "C": "Why C is wrong for THIS patient (skip if C is correct)",
        "D": "Why D is wrong for THIS patient (skip if D is correct)",
        "E": "Why E is wrong for THIS patient (skip if E is correct)"
    }},
    "educational_objective": "One sentence: what the student should learn from this question",
    "concept": "Topic area (e.g., 'Cardiology', 'Acute Care Surgery')"
}}

IMPORTANT:
- Principle must be a clear, actionable decision rule
- All numbers must be defined (what makes them abnormal)
- Use → to show causation and reasoning flow
- Each distractor must explain why it's wrong for THIS specific patient
- Keep total under 200 words
- No assumed knowledge - explain thresholds explicitly"""

        explanation_response = self._call_llm(
            "You are an expert medical educator writing USMLE explanations following strict quality standards.",
            generation_prompt,
            temperature=0.4,
            response_format={"type": "json_object"}
        )

        new_explanation = json.loads(explanation_response)

        # Validate the generated explanation
        validation = self._validate_generated_explanation(new_explanation, answer_key, len(choices))

        if validation["valid"]:
            return {
                "success": True,
                "question_id": question_id,
                "new_explanation": new_explanation,
                "validation": validation,
                "explanation_type": explanation_type
            }
        else:
            return {
                "success": False,
                "question_id": question_id,
                "new_explanation": new_explanation,
                "validation": validation,
                "needs_manual_review": True
            }

    def _validate_generated_explanation(self, explanation: Dict, answer_key: str, num_choices: int) -> Dict:
        """Validate a generated explanation meets all requirements"""
        issues = []

        # Check required fields
        required = ["type", "principle", "clinical_reasoning", "correct_answer_explanation", "distractor_explanations"]
        for field in required:
            if field not in explanation or not explanation[field]:
                issues.append(f"Missing {field}")

        # Check distractor completeness
        distractors = explanation.get("distractor_explanations", {})
        choice_letters = ["A", "B", "C", "D", "E"][:num_choices]

        for letter in choice_letters:
            if letter != answer_key and letter not in distractors:
                issues.append(f"Missing distractor explanation for {letter}")

        # Check for arrow notation
        reasoning = explanation.get("clinical_reasoning", "")
        if "→" not in reasoning and "->" not in reasoning:
            issues.append("Clinical reasoning missing arrow notation")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "checks_passed": len(required) + num_choices - 1 - len(issues)
        }

    def batch_validate_explanations(self, limit: int = 100, source_filter: Optional[str] = None) -> Dict:
        """
        Validate explanations for multiple questions and identify those needing improvement.

        Args:
            limit: Maximum number of questions to validate
            source_filter: Optional filter by source

        Returns:
            Summary of validation results and list of questions needing attention
        """
        query = self.db.query(Question).filter(Question.rejected == False)

        if source_filter:
            query = query.filter(Question.source.like(f"%{source_filter}%"))

        questions = query.limit(limit).all()

        results = {
            "total_validated": 0,
            "valid": 0,
            "needs_improvement": 0,
            "needs_regeneration": 0,
            "questions_needing_attention": [],
            "by_issue_type": {}
        }

        for question in questions:
            validation = self.validate_question_explanation(question.id)
            results["total_validated"] += 1

            if validation["valid"]:
                results["valid"] += 1
            elif validation.get("needs_regeneration"):
                results["needs_regeneration"] += 1
                results["questions_needing_attention"].append({
                    "question_id": question.id,
                    "source": question.source,
                    "issues": validation["issues"],
                    "priority": "high"
                })
            else:
                results["needs_improvement"] += 1
                results["questions_needing_attention"].append({
                    "question_id": question.id,
                    "source": question.source,
                    "issues": validation["issues"],
                    "quality_score": validation.get("quality_score", 0),
                    "priority": "medium"
                })

            # Track issue types
            for issue in validation.get("issues", []):
                issue_key = issue.split(":")[0] if ":" in issue else issue
                results["by_issue_type"][issue_key] = results["by_issue_type"].get(issue_key, 0) + 1

        # Sort by priority
        results["questions_needing_attention"].sort(
            key=lambda x: (0 if x["priority"] == "high" else 1, x.get("quality_score", 100))
        )

        return results

    # =========================================================================
    # SECTION 8: ANSWER CHOICE QUALITY VALIDATION
    # =========================================================================

    def validate_answer_choices(self, question_id: str) -> Dict:
        """
        Validate that answer choices meet ShelfSense quality standards:
        - All choices are distinct (no duplicates)
        - All choices are same category (all diagnoses OR all treatments)
        - Distractors are plausible but clearly wrong
        - One answer is unambiguously correct
        - Proper medical terminology
        """
        question = self.db.query(Question).filter(Question.id == question_id).first()

        if not question:
            return {"valid": False, "error": "Question not found"}

        choices = question.choices
        answer_key = question.answer_key
        vignette = question.vignette

        issues = []
        suggestions = []

        # Check for minimum choices
        if len(choices) < 4:
            issues.append(f"Only {len(choices)} choices - need at least 4")

        # Check for duplicates
        normalized_choices = [c.lower().strip() for c in choices]
        if len(normalized_choices) != len(set(normalized_choices)):
            issues.append("Duplicate answer choices detected")

        # Use AI to validate choice quality
        validation_prompt = f"""Analyze these USMLE answer choices for quality issues.

QUESTION VIGNETTE:
{vignette}

ANSWER CHOICES:
{chr(10).join([f'{chr(65+i)}. {choice}' for i, choice in enumerate(choices)])}

CORRECT ANSWER: {answer_key}

Check for these issues:
1. Are all choices the SAME CATEGORY? (all diagnoses OR all treatments OR all tests - not mixed)
2. Are there any near-duplicates or overlapping answers?
3. Is the correct answer unambiguously the best choice based on the vignette?
4. Are distractors plausible (not obviously wrong)?
5. Is there a "giveaway" choice that's too obviously wrong?
6. Do all choices use proper medical terminology?
7. Are any choices too similar, making the question unfair?

Return JSON:
{{
    "same_category": true/false,
    "category_type": "diagnosis/treatment/test/mechanism/other",
    "has_duplicates": true/false,
    "duplicate_details": "description if any",
    "correct_is_unambiguous": true/false,
    "ambiguity_concern": "description if any",
    "distractors_plausible": true/false,
    "weak_distractor": "letter and reason if any",
    "has_giveaway": true/false,
    "giveaway_details": "description if any",
    "terminology_issues": ["list of issues or empty"],
    "overall_quality": 1-10,
    "improvement_suggestions": ["list of specific suggestions"]
}}"""

        response = self._call_llm(
            "You are an expert USMLE question reviewer analyzing answer choice quality.",
            validation_prompt,
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        validation = json.loads(response)

        # Compile issues
        if not validation.get("same_category"):
            issues.append(f"Mixed categories - choices should all be {validation.get('category_type', 'same type')}")

        if validation.get("has_duplicates"):
            issues.append(f"Near-duplicate choices: {validation.get('duplicate_details', 'detected')}")

        if not validation.get("correct_is_unambiguous"):
            issues.append(f"Correct answer ambiguous: {validation.get('ambiguity_concern', 'unclear')}")

        if validation.get("has_giveaway"):
            issues.append(f"Giveaway choice: {validation.get('giveaway_details', 'detected')}")

        if validation.get("terminology_issues"):
            issues.extend(validation["terminology_issues"])

        suggestions.extend(validation.get("improvement_suggestions", []))

        quality_score = validation.get("overall_quality", 5) * 10

        return {
            "valid": len(issues) == 0 and quality_score >= 70,
            "question_id": question_id,
            "quality_score": quality_score,
            "category_type": validation.get("category_type"),
            "issues": issues,
            "suggestions": suggestions,
            "ai_validation": validation,
            "needs_revision": quality_score < 60
        }

    def generate_improved_answer_choices(self, question_id: str) -> Dict:
        """
        Generate improved answer choices for a question with quality issues.
        Maintains the correct answer concept but improves distractors.
        """
        question = self.db.query(Question).filter(Question.id == question_id).first()

        if not question:
            return {"success": False, "error": "Question not found"}

        # First validate to understand issues
        validation = self.validate_answer_choices(question_id)

        if validation["valid"]:
            return {
                "success": True,
                "message": "Answer choices already meet quality standards",
                "current_choices": question.choices
            }

        generation_prompt = f"""Improve the answer choices for this USMLE question based on the identified issues.

VIGNETTE:
{question.vignette}

CURRENT CHOICES:
{chr(10).join([f'{chr(65+i)}. {choice}' for i, choice in enumerate(question.choices)])}

CORRECT ANSWER: {question.answer_key} - {question.choices[ord(question.answer_key) - ord('A')]}

ISSUES TO FIX:
{chr(10).join(validation['issues'])}

SUGGESTIONS:
{chr(10).join(validation['suggestions'])}

Generate improved answer choices that:
1. Keep the correct answer ({question.answer_key}) the same or very similar
2. Make all choices the SAME CATEGORY
3. Make distractors plausible but clearly distinguishable
4. Remove any giveaway answers
5. Use proper, consistent medical terminology
6. Ensure the correct answer is unambiguously best

Return JSON:
{{
    "improved_choices": ["Choice A", "Choice B", "Choice C", "Choice D", "Choice E"],
    "correct_answer_letter": "{question.answer_key}",
    "category": "diagnosis/treatment/test/etc",
    "distractor_rationales": {{
        "A": "Why A is plausible but wrong (if not correct)",
        "B": "Why B is plausible but wrong (if not correct)",
        "C": "Why C is plausible but wrong (if not correct)",
        "D": "Why D is plausible but wrong (if not correct)",
        "E": "Why E is plausible but wrong (if not correct)"
    }},
    "changes_made": ["List of specific changes made"]
}}"""

        response = self._call_llm(
            "You are an expert USMLE question writer improving answer choices to meet NBME standards.",
            generation_prompt,
            temperature=0.5,
            response_format={"type": "json_object"}
        )

        result = json.loads(response)

        # Validate the new choices
        new_choices = result.get("improved_choices", [])
        if len(new_choices) != len(question.choices):
            return {
                "success": False,
                "error": "Generated wrong number of choices",
                "result": result
            }

        return {
            "success": True,
            "question_id": question_id,
            "original_choices": question.choices,
            "improved_choices": new_choices,
            "correct_answer": result.get("correct_answer_letter"),
            "category": result.get("category"),
            "distractor_rationales": result.get("distractor_rationales", {}),
            "changes_made": result.get("changes_made", [])
        }

    # =========================================================================
    # SECTION 9: COMPREHENSIVE LEARNING REPORT
    # =========================================================================

    def generate_comprehensive_report(self, user_id: str) -> Dict:
        """
        Generate a comprehensive learning report combining all analytics:
        - Weak areas with recommendations
        - Time analysis
        - Confidence calibration
        - Learning velocity
        - Predicted performance
        - Personalized study plan
        """
        # Gather all analytics
        weak_areas = self.get_detailed_weak_areas(user_id)
        time_analysis = self.analyze_time_patterns(user_id)
        confidence_analysis = self.analyze_confidence_patterns(user_id)
        velocity = self.calculate_learning_velocity(user_id)
        prediction = self.predict_exam_performance(user_id)

        # Generate personalized recommendations
        recommendations = []

        # Priority 1: Address declining weak areas
        declining_weak = [a for a in weak_areas.get("weak_areas", []) if a.get("trend") == "declining"]
        if declining_weak:
            recommendations.append({
                "priority": 1,
                "type": "critical",
                "action": f"Immediately focus on {declining_weak[0]['source']} - performance is declining",
                "target": declining_weak[0]['source']
            })

        # Priority 2: Fix time issues
        if time_analysis.get("recommendations"):
            recommendations.append({
                "priority": 2,
                "type": "timing",
                "action": time_analysis["recommendations"][0],
                "target": "time_management"
            })

        # Priority 3: Confidence calibration
        if confidence_analysis.get("calibration_score", 100) < 70:
            recommendations.append({
                "priority": 3,
                "type": "metacognition",
                "action": confidence_analysis.get("recommendations", ["Work on confidence calibration"])[0],
                "target": "confidence"
            })

        # Priority 4: Learning velocity
        if velocity.get("velocity_per_week", 0) < 0:
            recommendations.append({
                "priority": 4,
                "type": "strategy",
                "action": "Your improvement rate is declining. Consider changing your study approach.",
                "target": "study_strategy"
            })

        return {
            "user_id": user_id,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "predicted_score": prediction.get("predicted_score"),
                "score_range": prediction.get("score_range"),
                "readiness": prediction.get("readiness_label"),
                "learning_velocity": velocity.get("velocity_label"),
                "calibration_score": confidence_analysis.get("calibration_score")
            },
            "weak_areas": weak_areas,
            "time_analysis": time_analysis,
            "confidence_analysis": confidence_analysis,
            "learning_velocity": velocity,
            "performance_prediction": prediction,
            "top_recommendations": recommendations[:5],
            "next_session_focus": weak_areas.get("weak_areas", [{}])[0].get("source", "General practice")
        }


# =========================================================================
# CONVENIENCE FUNCTIONS FOR EXTERNAL USE
# =========================================================================

def get_adaptive_learning_engine(db: Session) -> AdaptiveLearningEngineAgent:
    """Factory function to create an AdaptiveLearningEngineAgent instance"""
    return AdaptiveLearningEngineAgent(db)


def validate_all_explanations(db: Session, limit: int = 100) -> Dict:
    """Convenience function to validate explanations in batch"""
    agent = AdaptiveLearningEngineAgent(db)
    return agent.batch_validate_explanations(limit)


def get_user_learning_report(db: Session, user_id: str) -> Dict:
    """Convenience function to get comprehensive user report"""
    agent = AdaptiveLearningEngineAgent(db)
    return agent.generate_comprehensive_report(user_id)


def improve_question_explanation(db: Session, question_id: str) -> Dict:
    """Convenience function to generate improved explanation"""
    agent = AdaptiveLearningEngineAgent(db)
    return agent.generate_improved_explanation(question_id)


def select_next_adaptive_question(db: Session, user_id: str) -> Optional[Question]:
    """Convenience function for adaptive question selection"""
    agent = AdaptiveLearningEngineAgent(db)
    return agent.select_adaptive_question(user_id)
