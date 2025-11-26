"""
Study Plan Agent for ShelfSense

This agent is responsible for:
1. Generating personalized daily study schedules
2. Balancing weak areas with review sessions
3. Optimizing study time allocation
4. Adapting plans based on user progress
5. Managing spaced repetition integration
6. Providing study recommendations and tips

The agent creates actionable, time-bound study plans that maximize
learning efficiency while preventing burnout.
"""


import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.utils.openai_client import get_openai_client

from app.models.models import (
    User, Question, QuestionAttempt, UserPerformance,
    ScheduledReview, LearningMetricsCache
)
from app.services.adaptive_learning_engine import AdaptiveLearningEngineAgent



# Study configuration constants
DEFAULT_DAILY_QUESTIONS = 40
MIN_DAILY_QUESTIONS = 10
MAX_DAILY_QUESTIONS = 100
REVIEW_PERCENTAGE = 0.3  # 30% of time on reviews
WEAK_AREA_PERCENTAGE = 0.5  # 50% of new questions from weak areas


class StudyPlanAgent:
    """
    Agent responsible for generating and managing personalized study plans.

    Creates daily, weekly, and exam-focused study schedules that:
    - Prioritize weak areas
    - Balance new material with spaced repetition
    - Adapt to user's learning velocity
    - Account for exam date and target score
    """

    def __init__(self, db: Session, model: str = "gpt-4o"):
        self.db = db
        self.model = model
        self.adaptive_agent = AdaptiveLearningEngineAgent(db, model)

    def _call_llm(self, system_prompt: str, user_prompt: str,
                  temperature: float = 0.5, response_format: Optional[Dict] = None) -> str:
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

        response = get_openai_client().chat.completions.create(**kwargs)
        return response.choices[0].message.content

    # =========================================================================
    # SECTION 1: DAILY STUDY PLAN
    # =========================================================================

    def generate_daily_plan(self, user_id: str,
                            target_questions: Optional[int] = None,
                            available_minutes: Optional[int] = None) -> Dict:
        """
        Generate a personalized daily study plan.

        Args:
            user_id: The user's ID
            target_questions: Target number of questions (auto-calculated if None)
            available_minutes: Available study time in minutes

        Returns:
            Comprehensive daily study plan with sessions and recommendations
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}

        # Get user's performance data
        weak_areas = self.adaptive_agent.get_detailed_weak_areas(user_id)
        time_analysis = self.adaptive_agent.analyze_time_patterns(user_id)
        prediction = self.adaptive_agent.predict_exam_performance(user_id)

        # Get today's scheduled reviews
        today = datetime.utcnow().date()
        reviews_due = self.db.query(ScheduledReview).filter(
            ScheduledReview.user_id == user_id,
            func.date(ScheduledReview.scheduled_for) <= today
        ).count()

        # Calculate optimal question count
        if target_questions is None:
            target_questions = self._calculate_optimal_questions(user, prediction)

        # Calculate time per question from user's history
        avg_time = time_analysis.get("avg_time_correct", 90)  # Default 90 seconds
        if available_minutes:
            time_based_questions = int((available_minutes * 60) / avg_time)
            target_questions = min(target_questions, time_based_questions)

        # Allocate questions across categories
        allocation = self._allocate_questions(
            total=target_questions,
            reviews_due=reviews_due,
            weak_areas=weak_areas.get("weak_areas", []),
            user=user
        )

        # Build study sessions
        sessions = self._build_study_sessions(allocation, weak_areas, user)

        # Calculate estimated time
        estimated_minutes = int((target_questions * avg_time) / 60)

        # Generate tips based on user's patterns
        tips = self._generate_study_tips(user, weak_areas, time_analysis, prediction)

        # Days until exam
        days_to_exam = None
        if user.exam_date:
            days_to_exam = (user.exam_date.date() - today).days

        return {
            "date": today.isoformat(),
            "user_id": user_id,
            "target_questions": target_questions,
            "estimated_minutes": estimated_minutes,
            "allocation": allocation,
            "sessions": sessions,
            "reviews_due": reviews_due,
            "current_predicted_score": prediction.get("predicted_score"),
            "target_score": user.target_score,
            "days_to_exam": days_to_exam,
            "tips": tips,
            "weak_areas_focus": [a["source"] for a in weak_areas.get("weak_areas", [])[:3]],
            "progress_summary": self._get_progress_summary(user_id, prediction)
        }

    def _calculate_optimal_questions(self, user: User, prediction: Dict) -> int:
        """Calculate optimal daily question count based on user goals"""
        base_questions = DEFAULT_DAILY_QUESTIONS

        # Adjust based on exam proximity
        if user.exam_date:
            days_to_exam = (user.exam_date.date() - datetime.utcnow().date()).days

            if days_to_exam <= 7:
                # Final week - moderate but focused
                base_questions = 50
            elif days_to_exam <= 30:
                # Last month - intensive
                base_questions = 60
            elif days_to_exam <= 60:
                # Two months out - building
                base_questions = 50
            else:
                # Early preparation
                base_questions = 40

        # Adjust based on target score gap
        if user.target_score and prediction.get("predicted_score"):
            score_gap = user.target_score - prediction["predicted_score"]
            if score_gap > 30:
                base_questions = int(base_questions * 1.3)  # Need more practice
            elif score_gap > 15:
                base_questions = int(base_questions * 1.15)
            elif score_gap <= 0:
                base_questions = int(base_questions * 0.9)  # On track

        return max(MIN_DAILY_QUESTIONS, min(MAX_DAILY_QUESTIONS, base_questions))

    def _allocate_questions(self, total: int, reviews_due: int,
                           weak_areas: List[Dict], user: User) -> Dict:
        """Allocate questions across categories"""
        # Reviews first (capped at 30% of total or actual reviews due)
        review_allocation = min(int(total * REVIEW_PERCENTAGE), reviews_due)

        # Remaining for new questions
        new_questions = total - review_allocation

        # Weak areas get priority (50% of new questions)
        weak_area_questions = int(new_questions * WEAK_AREA_PERCENTAGE) if weak_areas else 0

        # Distribute weak area questions
        weak_area_distribution = {}
        if weak_area_questions > 0 and weak_areas:
            questions_per_area = max(3, weak_area_questions // len(weak_areas[:5]))
            remaining = weak_area_questions

            for area in weak_areas[:5]:  # Top 5 weak areas
                area_questions = min(questions_per_area, remaining)
                weak_area_distribution[area["source"]] = area_questions
                remaining -= area_questions
                if remaining <= 0:
                    break

        # General practice (remaining new questions)
        general_questions = new_questions - sum(weak_area_distribution.values())

        return {
            "total": total,
            "reviews": review_allocation,
            "new_questions": new_questions,
            "weak_area_breakdown": weak_area_distribution,
            "general_practice": general_questions
        }

    def _build_study_sessions(self, allocation: Dict, weak_areas: Dict, user: User) -> List[Dict]:
        """Build structured study sessions from allocation"""
        sessions = []

        # Session 1: Spaced Repetition Reviews (if any)
        if allocation["reviews"] > 0:
            sessions.append({
                "session_number": 1,
                "type": "review",
                "title": "Spaced Repetition Review",
                "description": "Review questions from your learning queue",
                "questions": allocation["reviews"],
                "estimated_minutes": int(allocation["reviews"] * 1.5),  # Reviews are faster
                "focus_areas": ["Previously learned material"],
                "importance": "high",
                "tips": [
                    "Try to recall before seeing the answer",
                    "Pay attention to questions you got wrong before"
                ]
            })

        # Session 2: Weak Area Focus
        if allocation["weak_area_breakdown"]:
            weak_sources = list(allocation["weak_area_breakdown"].keys())
            weak_questions = sum(allocation["weak_area_breakdown"].values())

            sessions.append({
                "session_number": len(sessions) + 1,
                "type": "weak_area",
                "title": "Weak Area Practice",
                "description": "Focus on your challenging topics",
                "questions": weak_questions,
                "estimated_minutes": int(weak_questions * 2),  # More time for weak areas
                "focus_areas": weak_sources,
                "breakdown": allocation["weak_area_breakdown"],
                "importance": "critical",
                "tips": [
                    "Take your time - understanding is key",
                    "Read explanations carefully even when correct",
                    "Note patterns in what you're getting wrong"
                ]
            })

        # Session 3: General Practice
        if allocation["general_practice"] > 0:
            sessions.append({
                "session_number": len(sessions) + 1,
                "type": "general",
                "title": "Mixed Practice",
                "description": "Practice across all topics",
                "questions": allocation["general_practice"],
                "estimated_minutes": int(allocation["general_practice"] * 1.5),
                "focus_areas": ["All specialties"],
                "importance": "medium",
                "tips": [
                    "Maintain good pacing",
                    "Trust your first instinct",
                    "Flag uncertain questions for review"
                ]
            })

        return sessions

    def _generate_study_tips(self, user: User, weak_areas: Dict,
                            time_analysis: Dict, prediction: Dict) -> List[str]:
        """Generate personalized study tips"""
        tips = []

        # Time-based tips
        if time_analysis.get("optimal_time_range"):
            optimal_range = time_analysis["optimal_time_range"]
            tips.append(f"Your optimal time per question is {optimal_range}. Try to stay in this range.")

        avg_correct = time_analysis.get("avg_time_correct", 0)
        avg_incorrect = time_analysis.get("avg_time_incorrect", 0)
        if avg_incorrect < avg_correct - 20:
            tips.append("You tend to rush on questions you get wrong. Slow down when uncertain.")

        # Weak area tips
        if weak_areas.get("weak_areas"):
            weakest = weak_areas["weak_areas"][0]
            if weakest.get("trend") == "declining":
                tips.append(f"Priority: {weakest['source']} is declining. Focus extra attention here today.")
            elif weakest.get("trend") == "improving":
                tips.append(f"Good progress on {weakest['source']}! Keep up the momentum.")

        # Score-based tips
        if prediction.get("predicted_score") and user.target_score:
            gap = user.target_score - prediction["predicted_score"]
            if gap > 20:
                tips.append("Focus on accuracy over speed today. Quality learning beats quantity.")
            elif gap <= 0:
                tips.append("You're on track for your target! Maintain consistency.")

        # General tips
        tips.extend([
            "Take a 5-minute break every 25-30 questions",
            "Stay hydrated and avoid distractions"
        ])

        return tips[:5]  # Max 5 tips

    def _get_progress_summary(self, user_id: str, prediction: Dict) -> Dict:
        """Get a brief progress summary"""
        # Get recent accuracy
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_attempts = self.db.query(QuestionAttempt).filter(
            QuestionAttempt.user_id == user_id,
            QuestionAttempt.attempted_at >= week_ago
        ).all()

        if recent_attempts:
            recent_correct = sum(1 for a in recent_attempts if a.is_correct)
            recent_accuracy = recent_correct / len(recent_attempts)
        else:
            recent_accuracy = 0

        return {
            "recent_accuracy": round(recent_accuracy * 100, 1),
            "questions_this_week": len(recent_attempts),
            "predicted_score": prediction.get("predicted_score"),
            "readiness": prediction.get("readiness_label", "Unknown")
        }

    # =========================================================================
    # SECTION 2: WEEKLY STUDY PLAN
    # =========================================================================

    def generate_weekly_plan(self, user_id: str,
                             daily_questions: Optional[int] = None,
                             rest_days: List[int] = None) -> Dict:
        """
        Generate a weekly study plan.

        Args:
            user_id: The user's ID
            daily_questions: Target questions per day (auto if None)
            rest_days: List of day numbers to rest (0=Monday, 6=Sunday)

        Returns:
            Weekly plan with daily allocations
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}

        # Default rest day is Sunday
        if rest_days is None:
            rest_days = [6]

        prediction = self.adaptive_agent.predict_exam_performance(user_id)
        weak_areas = self.adaptive_agent.get_detailed_weak_areas(user_id)

        if daily_questions is None:
            daily_questions = self._calculate_optimal_questions(user, prediction)

        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday())  # Monday

        daily_plans = []
        weekly_total = 0
        specialties_covered = set()

        for day_offset in range(7):
            day_date = week_start + timedelta(days=day_offset)
            day_num = day_offset  # 0=Monday

            if day_num in rest_days:
                daily_plans.append({
                    "date": day_date.isoformat(),
                    "day_name": day_date.strftime("%A"),
                    "is_rest_day": True,
                    "questions": 0,
                    "focus": "Rest & Review Notes"
                })
                continue

            # Get scheduled reviews for this day
            reviews = self.db.query(ScheduledReview).filter(
                ScheduledReview.user_id == user_id,
                func.date(ScheduledReview.scheduled_for) == day_date
            ).count()

            # Vary focus areas throughout the week
            day_weak_areas = weak_areas.get("weak_areas", [])
            if day_weak_areas:
                # Rotate through weak areas
                focus_index = day_offset % len(day_weak_areas)
                primary_focus = day_weak_areas[focus_index]["source"]
            else:
                primary_focus = "General Practice"

            specialties_covered.add(primary_focus)

            daily_plans.append({
                "date": day_date.isoformat(),
                "day_name": day_date.strftime("%A"),
                "is_rest_day": False,
                "questions": daily_questions,
                "reviews_scheduled": reviews,
                "primary_focus": primary_focus,
                "is_today": day_date == today,
                "is_past": day_date < today
            })

            weekly_total += daily_questions

        # Weekly summary
        active_days = 7 - len(rest_days)

        return {
            "week_of": week_start.isoformat(),
            "user_id": user_id,
            "total_questions": weekly_total,
            "active_days": active_days,
            "rest_days": len(rest_days),
            "daily_target": daily_questions,
            "daily_plans": daily_plans,
            "specialties_focus": list(specialties_covered),
            "weekly_goals": self._generate_weekly_goals(user, prediction, weak_areas),
            "current_stats": {
                "predicted_score": prediction.get("predicted_score"),
                "target_score": user.target_score,
                "weak_areas_count": len(weak_areas.get("weak_areas", []))
            }
        }

    def _generate_weekly_goals(self, user: User, prediction: Dict, weak_areas: Dict) -> List[Dict]:
        """Generate weekly goals"""
        goals = []

        # Accuracy goal
        if prediction.get("weighted_accuracy"):
            current_acc = prediction["weighted_accuracy"] * 100
            goals.append({
                "type": "accuracy",
                "title": "Maintain Accuracy",
                "target": f"Keep accuracy above {int(current_acc)}%",
                "current": f"{current_acc:.1f}%"
            })

        # Weak area improvement
        if weak_areas.get("weak_areas"):
            weakest = weak_areas["weak_areas"][0]
            goals.append({
                "type": "improvement",
                "title": f"Improve {weakest['source']}",
                "target": f"Increase accuracy from {weakest['weighted_accuracy']*100:.0f}% to {(weakest['weighted_accuracy']+0.1)*100:.0f}%",
                "current": f"{weakest['weighted_accuracy']*100:.1f}%"
            })

        # Consistency goal
        goals.append({
            "type": "consistency",
            "title": "Study Streak",
            "target": "Complete daily practice 6 days this week",
            "current": "Track your streak"
        })

        return goals

    # =========================================================================
    # SECTION 3: EXAM COUNTDOWN PLAN
    # =========================================================================

    def generate_exam_countdown_plan(self, user_id: str) -> Dict:
        """
        Generate a study plan based on time until exam.

        Creates phase-based approach:
        - Foundation phase (>60 days)
        - Building phase (30-60 days)
        - Intensive phase (14-30 days)
        - Final review (7-14 days)
        - Test week (<7 days)
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.exam_date:
            return {"error": "User not found or no exam date set"}

        today = datetime.utcnow().date()
        exam_date = user.exam_date.date()
        days_remaining = (exam_date - today).days

        if days_remaining < 0:
            return {"error": "Exam date has passed"}

        prediction = self.adaptive_agent.predict_exam_performance(user_id)
        weak_areas = self.adaptive_agent.get_detailed_weak_areas(user_id)
        velocity = self.adaptive_agent.calculate_learning_velocity(user_id)

        # Determine current phase
        phase = self._determine_study_phase(days_remaining)

        # Generate phase-specific recommendations
        phase_plan = self._generate_phase_plan(
            phase, days_remaining, user, prediction, weak_areas, velocity
        )

        # Calculate if on track
        score_gap = 0
        if user.target_score and prediction.get("predicted_score"):
            score_gap = user.target_score - prediction["predicted_score"]

        weeks_remaining = days_remaining / 7
        velocity_per_week = velocity.get("velocity_per_week", 0)

        if velocity_per_week > 0 and score_gap > 0:
            predicted_final_score = prediction["predicted_score"] + (velocity_per_week * weeks_remaining * 100 * 265)
            on_track = predicted_final_score >= user.target_score
        else:
            on_track = score_gap <= 0

        return {
            "user_id": user_id,
            "exam_date": exam_date.isoformat(),
            "days_remaining": days_remaining,
            "weeks_remaining": round(weeks_remaining, 1),
            "current_phase": phase,
            "phase_plan": phase_plan,
            "score_tracking": {
                "current_predicted": prediction.get("predicted_score"),
                "target_score": user.target_score,
                "score_gap": score_gap,
                "on_track": on_track
            },
            "velocity": {
                "learning_velocity": velocity.get("velocity_label"),
                "weekly_improvement": f"{velocity.get('velocity_per_week', 0)*100:.1f}%"
            },
            "priority_areas": [a["source"] for a in weak_areas.get("weak_areas", [])[:5]],
            "milestones": self._generate_milestones(days_remaining, user, prediction)
        }

    def _determine_study_phase(self, days_remaining: int) -> Dict:
        """Determine current study phase"""
        if days_remaining > 60:
            return {
                "name": "Foundation",
                "description": "Build strong fundamentals across all topics",
                "intensity": "moderate",
                "focus": "breadth"
            }
        elif days_remaining > 30:
            return {
                "name": "Building",
                "description": "Strengthen weak areas and solidify knowledge",
                "intensity": "high",
                "focus": "weak_areas"
            }
        elif days_remaining > 14:
            return {
                "name": "Intensive",
                "description": "High-volume practice with focus on weak areas",
                "intensity": "very_high",
                "focus": "practice"
            }
        elif days_remaining > 7:
            return {
                "name": "Final Review",
                "description": "Review missed questions and high-yield topics",
                "intensity": "high",
                "focus": "review"
            }
        else:
            return {
                "name": "Test Week",
                "description": "Light review, rest, and confidence building",
                "intensity": "low",
                "focus": "maintenance"
            }

    def _generate_phase_plan(self, phase: Dict, days_remaining: int,
                            user: User, prediction: Dict,
                            weak_areas: Dict, velocity: Dict) -> Dict:
        """Generate phase-specific study plan"""
        phase_name = phase["name"]

        if phase_name == "Foundation":
            return {
                "daily_questions": 40,
                "focus_split": {
                    "new_topics": 60,
                    "weak_areas": 25,
                    "review": 15
                },
                "recommendations": [
                    "Cover all specialties systematically",
                    "Focus on understanding over speed",
                    "Build a strong foundation of core concepts",
                    "Start identifying your weak areas"
                ],
                "weekly_goals": ["Complete 250-280 questions", "Cover all 8 specialties"]
            }

        elif phase_name == "Building":
            return {
                "daily_questions": 50,
                "focus_split": {
                    "new_topics": 30,
                    "weak_areas": 50,
                    "review": 20
                },
                "recommendations": [
                    "Prioritize your weakest specialties",
                    "Use timed practice to build stamina",
                    "Focus on commonly tested topics",
                    "Start doing practice exams"
                ],
                "weekly_goals": ["Complete 300-350 questions", "Improve weak areas by 10%"]
            }

        elif phase_name == "Intensive":
            return {
                "daily_questions": 60,
                "focus_split": {
                    "new_topics": 20,
                    "weak_areas": 50,
                    "review": 30
                },
                "recommendations": [
                    "Simulate exam conditions regularly",
                    "Review all missed questions",
                    "Focus on question patterns",
                    "Time management practice"
                ],
                "weekly_goals": ["Complete 350-400 questions", "Maintain 70%+ accuracy"]
            }

        elif phase_name == "Final Review":
            return {
                "daily_questions": 40,
                "focus_split": {
                    "new_topics": 10,
                    "weak_areas": 40,
                    "review": 50
                },
                "recommendations": [
                    "Review all flagged/missed questions",
                    "Focus on high-yield topics",
                    "Don't learn new material",
                    "Practice under timed conditions"
                ],
                "weekly_goals": ["Complete 200-250 questions", "Review all weak areas"]
            }

        else:  # Test Week
            return {
                "daily_questions": 20,
                "focus_split": {
                    "new_topics": 0,
                    "weak_areas": 30,
                    "review": 70
                },
                "recommendations": [
                    "Light review only - no cramming",
                    "Focus on confidence building",
                    "Get adequate rest",
                    "Review high-yield facts",
                    "Trust your preparation"
                ],
                "weekly_goals": ["Stay relaxed", "Maintain confidence", "Get good sleep"]
            }

    def _generate_milestones(self, days_remaining: int, user: User, prediction: Dict) -> List[Dict]:
        """Generate milestones for exam countdown"""
        milestones = []
        today = datetime.utcnow().date()
        exam_date = user.exam_date.date()

        # Milestone at 30 days
        if days_remaining > 30:
            milestone_date = exam_date - timedelta(days=30)
            milestones.append({
                "days_out": 30,
                "date": milestone_date.isoformat(),
                "goal": "Complete all weak area review",
                "target_score": (user.target_score - 10) if user.target_score else None
            })

        # Milestone at 14 days
        if days_remaining > 14:
            milestone_date = exam_date - timedelta(days=14)
            milestones.append({
                "days_out": 14,
                "date": milestone_date.isoformat(),
                "goal": "Complete intensive practice phase",
                "target_score": (user.target_score - 5) if user.target_score else None
            })

        # Milestone at 7 days
        if days_remaining > 7:
            milestone_date = exam_date - timedelta(days=7)
            milestones.append({
                "days_out": 7,
                "date": milestone_date.isoformat(),
                "goal": "Final review complete",
                "target_score": user.target_score
            })

        # Day before exam
        if days_remaining > 1:
            milestone_date = exam_date - timedelta(days=1)
            milestones.append({
                "days_out": 1,
                "date": milestone_date.isoformat(),
                "goal": "Rest and prepare mentally",
                "target_score": None
            })

        return milestones

    # =========================================================================
    # SECTION 4: AI-POWERED RECOMMENDATIONS
    # =========================================================================

    def get_personalized_recommendations(self, user_id: str) -> Dict:
        """
        Get AI-powered personalized study recommendations.

        Analyzes user's performance patterns and generates
        specific, actionable recommendations.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}

        # Gather all analytics
        weak_areas = self.adaptive_agent.get_detailed_weak_areas(user_id)
        time_analysis = self.adaptive_agent.analyze_time_patterns(user_id)
        confidence = self.adaptive_agent.analyze_confidence_patterns(user_id)
        velocity = self.adaptive_agent.calculate_learning_velocity(user_id)
        prediction = self.adaptive_agent.predict_exam_performance(user_id)

        # Build context for AI
        context = {
            "predicted_score": prediction.get("predicted_score"),
            "target_score": user.target_score,
            "weak_areas": [a["source"] for a in weak_areas.get("weak_areas", [])[:5]],
            "strong_areas": [a["source"] for a in weak_areas.get("strong_areas", [])[:3]],
            "learning_velocity": velocity.get("velocity_label"),
            "optimal_time_range": time_analysis.get("optimal_time_range"),
            "calibration_score": confidence.get("calibration_score"),
            "days_to_exam": None
        }

        if user.exam_date:
            context["days_to_exam"] = (user.exam_date.date() - datetime.utcnow().date()).days

        # Generate AI recommendations
        recommendations = self._generate_ai_recommendations(context)

        return {
            "user_id": user_id,
            "generated_at": datetime.utcnow().isoformat(),
            "context_summary": context,
            "recommendations": recommendations,
            "priority_actions": recommendations[:3] if recommendations else [],
            "next_focus": weak_areas.get("weak_areas", [{}])[0].get("source", "General practice")
        }

    def _generate_ai_recommendations(self, context: Dict) -> List[Dict]:
        """Use AI to generate personalized recommendations"""
        prompt = f"""Based on this medical student's study data, provide specific, actionable study recommendations.

STUDENT PROFILE:
- Predicted Score: {context.get('predicted_score', 'Unknown')}
- Target Score: {context.get('target_score', 'Not set')}
- Days to Exam: {context.get('days_to_exam', 'Not set')}
- Learning Velocity: {context.get('learning_velocity', 'Unknown')}
- Confidence Calibration: {context.get('calibration_score', 'Unknown')}/100

WEAK AREAS: {', '.join(context.get('weak_areas', ['None identified']))}
STRONG AREAS: {', '.join(context.get('strong_areas', ['None identified']))}
OPTIMAL TIME/QUESTION: {context.get('optimal_time_range', 'Unknown')}

Generate 5 specific, actionable recommendations. Each should include:
1. A clear action to take
2. Why it matters for this student
3. Expected impact

Return JSON array:
[
  {{
    "priority": 1-5,
    "category": "weak_area|time_management|confidence|strategy|general",
    "title": "Short action title",
    "action": "Specific action to take",
    "reasoning": "Why this matters for you",
    "expected_impact": "What improvement to expect"
  }}
]"""

        try:
            response = self._call_llm(
                "You are an expert medical education advisor helping students prepare for USMLE Step 2 CK.",
                prompt,
                temperature=0.6,
                response_format={"type": "json_object"}
            )
            result = json.loads(response)

            # Handle both array and object responses
            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and "recommendations" in result:
                return result["recommendations"]
            else:
                return []

        except Exception as e:
            print(f"Error generating AI recommendations: {e}")
            return self._get_default_recommendations(context)

    def _get_default_recommendations(self, context: Dict) -> List[Dict]:
        """Fallback recommendations if AI fails"""
        recommendations = []

        if context.get("weak_areas"):
            recommendations.append({
                "priority": 1,
                "category": "weak_area",
                "title": f"Focus on {context['weak_areas'][0]}",
                "action": f"Dedicate 50% of your study time to {context['weak_areas'][0]}",
                "reasoning": "This is your weakest area with the most room for improvement",
                "expected_impact": "10-15% improvement in this specialty"
            })

        if context.get("calibration_score") and context["calibration_score"] < 70:
            recommendations.append({
                "priority": 2,
                "category": "confidence",
                "title": "Improve Confidence Calibration",
                "action": "Practice rating your confidence before seeing answers",
                "reasoning": "Better calibration improves test-taking decisions",
                "expected_impact": "Fewer careless errors"
            })

        recommendations.append({
            "priority": 3,
            "category": "general",
            "title": "Maintain Consistency",
            "action": "Complete your daily question goal every day",
            "reasoning": "Consistent practice builds long-term retention",
            "expected_impact": "Steady score improvement"
        })

        return recommendations


# =========================================================================
# CONVENIENCE FUNCTIONS
# =========================================================================

def get_study_plan_agent(db: Session) -> StudyPlanAgent:
    """Factory function to create a StudyPlanAgent instance"""
    return StudyPlanAgent(db)


def generate_daily_plan(db: Session, user_id: str) -> Dict:
    """Generate a daily study plan for a user"""
    agent = StudyPlanAgent(db)
    return agent.generate_daily_plan(user_id)


def generate_weekly_plan(db: Session, user_id: str) -> Dict:
    """Generate a weekly study plan for a user"""
    agent = StudyPlanAgent(db)
    return agent.generate_weekly_plan(user_id)


def get_exam_countdown(db: Session, user_id: str) -> Dict:
    """Get exam countdown plan for a user"""
    agent = StudyPlanAgent(db)
    return agent.generate_exam_countdown_plan(user_id)
