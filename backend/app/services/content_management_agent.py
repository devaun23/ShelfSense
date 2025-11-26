"""
Content Management Agent for ShelfSense
Handles all content lifecycle operations including:
- Question database CRUD
- Rating system (approve/reject)
- Feedback collection
- Quality filtering
- Source tracking (NBME vs AI)
- Community-contributed questions
- Expert review pipeline
- Content freshness scoring
"""

import os
import json
import math
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc
from openai import OpenAI

from app.models.models import (
    Question, QuestionRating, QuestionAttempt,
    ContentVersion, ReviewQueue, ContentAuditLog,
    CommunityContribution, ContentFreshnessScore, ExpertReviewer,
    User, ExplanationQualityLog
)

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Content status constants
class ContentStatus:
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    ARCHIVED = "archived"

# Source type constants
class SourceType:
    NBME = "nbme"
    AI_GENERATED = "ai_generated"
    COMMUNITY = "community"
    IMPORTED = "imported"

# Review status constants
class ReviewStatus:
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"

# Specialties mapping
SPECIALTIES = {
    "internal_medicine": ["Internal Medicine", "Medicine", "IM"],
    "surgery": ["Surgery", "Surg"],
    "pediatrics": ["Pediatrics", "Peds"],
    "obstetrics_gynecology": ["OB/GYN", "Obstetrics", "Gynecology", "ObGyn"],
    "psychiatry": ["Psychiatry", "Psych"],
    "neurology": ["Neurology", "Neuro"],
    "family_medicine": ["Family Medicine", "FM"],
    "emergency_medicine": ["Emergency Medicine", "EM"],
}


class ContentManagementAgent:
    """
    Comprehensive content management agent for the ShelfSense question database.
    Handles CRUD operations, quality assessment, review workflows, and analytics.
    """

    def __init__(self, db: Session, user_id: Optional[str] = None):
        self.db = db
        self.user_id = user_id
        self.model = "gpt-4o"

    # =========================================================================
    # QUESTION CRUD OPERATIONS
    # =========================================================================

    def create_question(
        self,
        vignette: str,
        choices: List[str],
        answer_key: str,
        explanation: Optional[Dict] = None,
        source: Optional[str] = None,
        source_type: str = SourceType.AI_GENERATED,
        specialty: Optional[str] = None,
        difficulty_level: Optional[str] = None,
        recency_tier: Optional[int] = None,
        recency_weight: Optional[float] = None,
        extra_data: Optional[Dict] = None,
        submit_for_review: bool = False
    ) -> Question:
        """Create a new question with full content management tracking."""

        # Normalize specialty
        normalized_specialty = self._normalize_specialty(specialty)

        question = Question(
            vignette=vignette,
            choices=choices,
            answer_key=answer_key,
            explanation=explanation,
            source=source,
            source_type=source_type,
            specialty=normalized_specialty,
            difficulty_level=difficulty_level,
            recency_tier=recency_tier,
            recency_weight=recency_weight,
            extra_data=extra_data,
            content_status=ContentStatus.DRAFT if submit_for_review else ContentStatus.ACTIVE,
            created_by=self.user_id,
            version=1
        )

        self.db.add(question)
        self.db.flush()  # Get the ID

        # Create initial version
        self._create_version(
            question=question,
            change_type="created",
            change_reason="Initial creation"
        )

        # Log the action
        self._log_audit(
            action="create",
            entity_type="question",
            entity_id=question.id,
            details={"source_type": source_type, "specialty": normalized_specialty}
        )

        # Submit for review if requested
        if submit_for_review:
            self._submit_to_review_queue(question, submission_source=source_type)

        # Initialize freshness score
        self._initialize_freshness_score(question.id)

        self.db.commit()
        return question

    def get_question(self, question_id: str) -> Optional[Question]:
        """Get a question by ID."""
        return self.db.query(Question).filter(Question.id == question_id).first()

    def update_question(
        self,
        question_id: str,
        updates: Dict[str, Any],
        change_reason: Optional[str] = None
    ) -> Optional[Question]:
        """Update a question with version tracking."""

        question = self.get_question(question_id)
        if not question:
            return None

        # Track which fields changed
        fields_changed = []
        for field, value in updates.items():
            if hasattr(question, field):
                old_value = getattr(question, field)
                if old_value != value:
                    fields_changed.append(field)
                    setattr(question, field, value)

        if fields_changed:
            # Increment version
            question.version += 1
            question.last_edited_by = self.user_id
            question.last_edited_at = datetime.utcnow()

            # Create version snapshot
            self._create_version(
                question=question,
                change_type="edited",
                change_reason=change_reason,
                fields_changed=fields_changed
            )

            # Log the action
            self._log_audit(
                action="update",
                entity_type="question",
                entity_id=question_id,
                details={"fields_changed": fields_changed, "reason": change_reason}
            )

            self.db.commit()

        return question

    def delete_question(self, question_id: str, hard_delete: bool = False) -> bool:
        """Delete a question (soft delete by default - archives it)."""

        question = self.get_question(question_id)
        if not question:
            return False

        if hard_delete:
            self.db.delete(question)
            action = "delete"
        else:
            question.content_status = ContentStatus.ARCHIVED
            action = "archive"

        self._log_audit(
            action=action,
            entity_type="question",
            entity_id=question_id,
            details={"hard_delete": hard_delete}
        )

        self.db.commit()
        return True

    def restore_question(self, question_id: str) -> Optional[Question]:
        """Restore an archived question."""

        question = self.get_question(question_id)
        if not question or question.content_status != ContentStatus.ARCHIVED:
            return None

        question.content_status = ContentStatus.ACTIVE

        self._log_audit(
            action="restore",
            entity_type="question",
            entity_id=question_id
        )

        self.db.commit()
        return question

    def list_questions(
        self,
        filters: Optional[Dict] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Question], int]:
        """List questions with filtering and pagination."""

        query = self.db.query(Question)

        if filters:
            if filters.get("content_status"):
                query = query.filter(Question.content_status == filters["content_status"])
            if filters.get("source_type"):
                query = query.filter(Question.source_type == filters["source_type"])
            if filters.get("specialty"):
                query = query.filter(Question.specialty == filters["specialty"])
            if filters.get("difficulty_level"):
                query = query.filter(Question.difficulty_level == filters["difficulty_level"])
            if filters.get("expert_reviewed") is not None:
                query = query.filter(Question.expert_reviewed == filters["expert_reviewed"])
            if filters.get("rejected") is not None:
                query = query.filter(Question.rejected == filters["rejected"])
            if filters.get("min_quality_score"):
                query = query.filter(Question.quality_score >= filters["min_quality_score"])
            if filters.get("search"):
                search_term = f"%{filters['search']}%"
                query = query.filter(Question.vignette.ilike(search_term))

        # Get total count before pagination
        total = query.count()

        # Apply sorting
        sort_column = getattr(Question, sort_by, Question.created_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Apply pagination
        questions = query.offset(offset).limit(limit).all()

        return questions, total

    # =========================================================================
    # RATING SYSTEM (APPROVE/REJECT)
    # =========================================================================

    def rate_question(
        self,
        question_id: str,
        rating: bool,  # True = approve, False = reject
        feedback_text: Optional[str] = None
    ) -> QuestionRating:
        """Record a user rating for a question."""

        # Check for existing rating by this user
        existing = self.db.query(QuestionRating).filter(
            QuestionRating.question_id == question_id,
            QuestionRating.user_id == self.user_id
        ).first()

        if existing:
            existing.rating = rating
            existing.feedback_text = feedback_text
            existing.created_at = datetime.utcnow()
            rating_record = existing
        else:
            rating_record = QuestionRating(
                question_id=question_id,
                user_id=self.user_id,
                rating=rating,
                feedback_text=feedback_text
            )
            self.db.add(rating_record)

        # Update question's rejected status if multiple rejections
        self._update_rejection_status(question_id)

        # Update freshness score with new rating
        self._update_freshness_from_rating(question_id)

        self._log_audit(
            action="approve" if rating else "reject",
            entity_type="question",
            entity_id=question_id,
            details={"feedback": feedback_text[:100] if feedback_text else None}
        )

        self.db.commit()
        return rating_record

    def get_question_ratings(self, question_id: str) -> Dict:
        """Get rating summary for a question."""

        ratings = self.db.query(QuestionRating).filter(
            QuestionRating.question_id == question_id
        ).all()

        approvals = sum(1 for r in ratings if r.rating)
        rejections = sum(1 for r in ratings if not r.rating)

        feedback = [
            {
                "rating": r.rating,
                "feedback": r.feedback_text,
                "created_at": r.created_at.isoformat()
            }
            for r in ratings if r.feedback_text
        ]

        return {
            "total_ratings": len(ratings),
            "approvals": approvals,
            "rejections": rejections,
            "approval_rate": approvals / len(ratings) if ratings else 0,
            "feedback": feedback
        }

    def _update_rejection_status(self, question_id: str):
        """Update question's rejected status based on ratings."""

        ratings = self.db.query(QuestionRating).filter(
            QuestionRating.question_id == question_id
        ).all()

        if len(ratings) >= 3:
            rejection_rate = sum(1 for r in ratings if not r.rating) / len(ratings)
            question = self.get_question(question_id)
            if question:
                question.rejected = rejection_rate > 0.5

    # =========================================================================
    # FEEDBACK COLLECTION
    # =========================================================================

    def collect_feedback(
        self,
        question_id: str,
        feedback_type: str,  # "quality", "accuracy", "clarity", "difficulty", "other"
        feedback_text: str,
        severity: Optional[str] = None  # "minor", "major", "critical"
    ) -> Dict:
        """Collect detailed feedback about a question."""

        # Store feedback in rating with structured format
        feedback_data = {
            "type": feedback_type,
            "text": feedback_text,
            "severity": severity,
            "submitted_at": datetime.utcnow().isoformat(),
            "user_id": self.user_id
        }

        question = self.get_question(question_id)
        if not question:
            return {"success": False, "error": "Question not found"}

        # Store in extra_data
        extra = question.extra_data or {}
        if "feedback" not in extra:
            extra["feedback"] = []
        extra["feedback"].append(feedback_data)
        question.extra_data = extra

        # Update freshness score if critical feedback
        if severity == "critical":
            self._flag_for_review(question_id, reason="critical_feedback")

        self._log_audit(
            action="feedback",
            entity_type="question",
            entity_id=question_id,
            details={"type": feedback_type, "severity": severity}
        )

        self.db.commit()

        return {"success": True, "feedback_id": len(extra["feedback"])}

    def get_feedback_summary(self, question_id: str) -> Dict:
        """Get aggregated feedback for a question."""

        question = self.get_question(question_id)
        if not question:
            return {}

        feedback_list = (question.extra_data or {}).get("feedback", [])

        by_type = {}
        for fb in feedback_list:
            fb_type = fb.get("type", "other")
            if fb_type not in by_type:
                by_type[fb_type] = []
            by_type[fb_type].append(fb)

        critical_count = sum(1 for fb in feedback_list if fb.get("severity") == "critical")

        return {
            "total_feedback": len(feedback_list),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "critical_issues": critical_count,
            "recent_feedback": feedback_list[-5:] if feedback_list else []
        }

    # =========================================================================
    # QUALITY FILTERING
    # =========================================================================

    def calculate_quality_score(self, question_id: str) -> float:
        """Calculate comprehensive quality score for a question."""

        question = self.get_question(question_id)
        if not question:
            return 0.0

        scores = []
        weights = []

        # Rating-based score (weight: 30%)
        rating_data = self.get_question_ratings(question_id)
        if rating_data["total_ratings"] > 0:
            scores.append(rating_data["approval_rate"] * 100)
            weights.append(0.3)

        # Performance-based score (weight: 25%)
        perf_score = self._calculate_performance_score(question_id)
        if perf_score is not None:
            scores.append(perf_score)
            weights.append(0.25)

        # Explanation quality score (weight: 20%)
        explanation_log = self.db.query(ExplanationQualityLog).filter(
            ExplanationQualityLog.question_id == question_id
        ).order_by(desc(ExplanationQualityLog.validated_at)).first()

        if explanation_log and explanation_log.quality_score:
            scores.append(explanation_log.quality_score)
            weights.append(0.2)

        # Expert review score (weight: 15%)
        if question.expert_reviewed:
            review = self.db.query(ReviewQueue).filter(
                ReviewQueue.question_id == question_id,
                ReviewQueue.status == ReviewStatus.APPROVED
            ).first()

            if review:
                review_scores = [
                    review.clinical_accuracy_score or 0,
                    review.question_clarity_score or 0,
                    review.distractor_quality_score or 0,
                    review.explanation_quality_score or 0
                ]
                avg_review = sum(review_scores) / 4 * 20  # Convert 1-5 to 0-100
                scores.append(avg_review)
                weights.append(0.15)

        # Content completeness score (weight: 10%)
        completeness = self._calculate_completeness_score(question)
        scores.append(completeness)
        weights.append(0.1)

        # Calculate weighted average
        if not scores:
            return 50.0  # Default score

        total_weight = sum(weights)
        quality_score = sum(s * w for s, w in zip(scores, weights)) / total_weight

        # Update question
        question.quality_score = quality_score
        self.db.commit()

        return quality_score

    def _calculate_performance_score(self, question_id: str) -> Optional[float]:
        """Calculate score based on how well the question performs in practice."""

        attempts = self.db.query(QuestionAttempt).filter(
            QuestionAttempt.question_id == question_id
        ).all()

        if len(attempts) < 5:
            return None

        # Ideal difficulty is around 60-70% correct
        correct_rate = sum(1 for a in attempts if a.is_correct) / len(attempts)

        # Score based on how close to ideal difficulty
        ideal = 0.65
        deviation = abs(correct_rate - ideal)
        difficulty_score = max(0, 100 - (deviation * 200))

        # Discrimination - high performers should do better
        # (simplified - would need more data in practice)

        return difficulty_score

    def _calculate_completeness_score(self, question: Question) -> float:
        """Calculate how complete the question content is."""

        score = 0
        max_score = 100

        # Vignette exists and has reasonable length
        if question.vignette and len(question.vignette) > 100:
            score += 25

        # Has 5 choices
        if question.choices and len(question.choices) >= 5:
            score += 20

        # Has explanation
        if question.explanation:
            score += 25
            # Structured explanation is better
            if isinstance(question.explanation, dict):
                score += 10

        # Has specialty
        if question.specialty:
            score += 10

        # Has source
        if question.source:
            score += 10

        return score

    def get_quality_filtered_questions(
        self,
        min_score: float = 70.0,
        specialty: Optional[str] = None,
        limit: int = 50
    ) -> List[Question]:
        """Get questions filtered by quality score."""

        query = self.db.query(Question).filter(
            Question.content_status == ContentStatus.ACTIVE,
            Question.rejected == False,
            Question.quality_score >= min_score
        )

        if specialty:
            query = query.filter(Question.specialty == specialty)

        return query.order_by(desc(Question.quality_score)).limit(limit).all()

    # =========================================================================
    # SOURCE TRACKING (NBME vs AI)
    # =========================================================================

    def get_content_by_source(self, source_type: str) -> Dict:
        """Get content statistics by source type."""

        questions = self.db.query(Question).filter(
            Question.source_type == source_type,
            Question.content_status == ContentStatus.ACTIVE
        ).all()

        # Calculate stats
        total = len(questions)
        with_ratings = sum(1 for q in questions if q.quality_score)
        avg_quality = sum(q.quality_score or 0 for q in questions) / total if total else 0

        # By specialty breakdown
        by_specialty = {}
        for q in questions:
            spec = q.specialty or "unknown"
            if spec not in by_specialty:
                by_specialty[spec] = 0
            by_specialty[spec] += 1

        return {
            "source_type": source_type,
            "total_questions": total,
            "questions_with_quality_score": with_ratings,
            "average_quality_score": round(avg_quality, 2),
            "by_specialty": by_specialty
        }

    def get_source_comparison(self) -> Dict:
        """Compare quality metrics across different sources."""

        sources = [SourceType.NBME, SourceType.AI_GENERATED, SourceType.COMMUNITY, SourceType.IMPORTED]
        comparison = {}

        for source in sources:
            stats = self.get_content_by_source(source)
            comparison[source] = stats

        return comparison

    def update_source_type(
        self,
        question_id: str,
        source_type: str,
        source_reference: Optional[str] = None
    ) -> Optional[Question]:
        """Update the source type for a question."""

        question = self.get_question(question_id)
        if not question:
            return None

        old_source = question.source_type
        question.source_type = source_type
        if source_reference:
            question.source = source_reference

        self._log_audit(
            action="update",
            entity_type="question",
            entity_id=question_id,
            details={"source_change": {"from": old_source, "to": source_type}}
        )

        self.db.commit()
        return question

    # =========================================================================
    # COMMUNITY-CONTRIBUTED QUESTIONS
    # =========================================================================

    def submit_community_question(
        self,
        vignette: str,
        choices: List[str],
        answer_key: str,
        explanation: Optional[Dict] = None,
        specialty: Optional[str] = None,
        source_reference: Optional[str] = None,
        is_original: bool = True
    ) -> CommunityContribution:
        """Submit a community-contributed question for review."""

        contribution = CommunityContribution(
            submitted_by=self.user_id,
            vignette=vignette,
            choices=choices,
            answer_key=answer_key,
            explanation=explanation,
            specialty=self._normalize_specialty(specialty),
            source_reference=source_reference,
            is_original=is_original,
            status="submitted"
        )

        self.db.add(contribution)
        self.db.flush()

        self._log_audit(
            action="submit",
            entity_type="community_contribution",
            entity_id=contribution.id,
            details={"specialty": specialty}
        )

        self.db.commit()
        return contribution

    def get_community_contributions(
        self,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[CommunityContribution]:
        """Get community contributions with optional filtering."""

        query = self.db.query(CommunityContribution)

        if status:
            query = query.filter(CommunityContribution.status == status)
        if user_id:
            query = query.filter(CommunityContribution.submitted_by == user_id)

        return query.order_by(desc(CommunityContribution.created_at)).limit(limit).all()

    def approve_community_contribution(
        self,
        contribution_id: str,
        reviewer_feedback: Optional[str] = None
    ) -> Tuple[Optional[Question], Optional[CommunityContribution]]:
        """Approve a community contribution and create a question from it."""

        contribution = self.db.query(CommunityContribution).filter(
            CommunityContribution.id == contribution_id
        ).first()

        if not contribution:
            return None, None

        # Create question from contribution
        question = self.create_question(
            vignette=contribution.vignette,
            choices=contribution.choices,
            answer_key=contribution.answer_key,
            explanation=contribution.explanation,
            source=f"Community: {contribution.source_reference}" if contribution.source_reference else "Community Contribution",
            source_type=SourceType.COMMUNITY,
            specialty=contribution.specialty,
            submit_for_review=False
        )

        # Update contribution
        contribution.status = "approved"
        contribution.question_id = question.id
        contribution.reviewer_feedback = reviewer_feedback
        contribution.contribution_quality_score = 80.0  # Base score for approved

        self._log_audit(
            action="approve",
            entity_type="community_contribution",
            entity_id=contribution_id,
            details={"created_question_id": question.id}
        )

        self.db.commit()
        return question, contribution

    def reject_community_contribution(
        self,
        contribution_id: str,
        reviewer_feedback: str
    ) -> Optional[CommunityContribution]:
        """Reject a community contribution with feedback."""

        contribution = self.db.query(CommunityContribution).filter(
            CommunityContribution.id == contribution_id
        ).first()

        if not contribution:
            return None

        contribution.status = "rejected"
        contribution.reviewer_feedback = reviewer_feedback
        contribution.contribution_quality_score = 20.0  # Low score for rejected

        self._log_audit(
            action="reject",
            entity_type="community_contribution",
            entity_id=contribution_id,
            details={"feedback": reviewer_feedback[:100]}
        )

        self.db.commit()
        return contribution

    # =========================================================================
    # EXPERT REVIEW PIPELINE
    # =========================================================================

    def _submit_to_review_queue(
        self,
        question: Question,
        submission_source: str,
        priority: int = 5
    ) -> ReviewQueue:
        """Submit a question to the expert review queue."""

        review = ReviewQueue(
            question_id=question.id,
            status=ReviewStatus.PENDING,
            priority=priority,
            submission_source=submission_source,
            submitted_by=self.user_id
        )

        self.db.add(review)
        return review

    def get_review_queue(
        self,
        status: Optional[str] = None,
        specialty: Optional[str] = None,
        assigned_to: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get items in the review queue with question details."""

        query = self.db.query(ReviewQueue).join(Question)

        if status:
            query = query.filter(ReviewQueue.status == status)
        if specialty:
            query = query.filter(Question.specialty == specialty)
        if assigned_to:
            query = query.filter(ReviewQueue.assigned_to == assigned_to)

        reviews = query.order_by(
            asc(ReviewQueue.priority),
            asc(ReviewQueue.created_at)
        ).limit(limit).all()

        return [
            {
                "review_id": r.id,
                "question_id": r.question_id,
                "status": r.status,
                "priority": r.priority,
                "assigned_to": r.assigned_to,
                "submission_source": r.submission_source,
                "created_at": r.created_at.isoformat(),
                "question": {
                    "vignette": r.question.vignette[:200] + "..." if len(r.question.vignette) > 200 else r.question.vignette,
                    "specialty": r.question.specialty,
                    "source_type": r.question.source_type
                }
            }
            for r in reviews
        ]

    def assign_reviewer(
        self,
        review_id: str,
        reviewer_id: str
    ) -> Optional[ReviewQueue]:
        """Assign an expert reviewer to a review item."""

        review = self.db.query(ReviewQueue).filter(ReviewQueue.id == review_id).first()
        if not review:
            return None

        # Verify reviewer is an expert
        expert = self.db.query(ExpertReviewer).filter(
            ExpertReviewer.user_id == reviewer_id,
            ExpertReviewer.is_active == True
        ).first()

        if not expert:
            return None

        review.assigned_to = reviewer_id
        review.assigned_at = datetime.utcnow()
        review.status = ReviewStatus.IN_REVIEW

        # Update expert's review count
        expert.current_week_reviews += 1

        self._log_audit(
            action="assign_reviewer",
            entity_type="review",
            entity_id=review_id,
            details={"reviewer_id": reviewer_id}
        )

        self.db.commit()
        return review

    def submit_review(
        self,
        review_id: str,
        decision: str,  # "approve", "reject", "revise"
        clinical_accuracy_score: int,
        question_clarity_score: int,
        distractor_quality_score: int,
        explanation_quality_score: int,
        decision_notes: Optional[str] = None,
        revision_notes: Optional[str] = None
    ) -> Optional[ReviewQueue]:
        """Submit an expert review decision."""

        review = self.db.query(ReviewQueue).filter(ReviewQueue.id == review_id).first()
        if not review:
            return None

        review.reviewed_by = self.user_id
        review.reviewed_at = datetime.utcnow()
        review.decision = decision
        review.decision_notes = decision_notes
        review.clinical_accuracy_score = clinical_accuracy_score
        review.question_clarity_score = question_clarity_score
        review.distractor_quality_score = distractor_quality_score
        review.explanation_quality_score = explanation_quality_score

        if decision == "approve":
            review.status = ReviewStatus.APPROVED
            self._finalize_approved_question(review)
        elif decision == "reject":
            review.status = ReviewStatus.REJECTED
            self._handle_rejected_question(review)
        elif decision == "revise":
            review.status = ReviewStatus.NEEDS_REVISION
            review.revision_requested = True
            review.revision_notes = revision_notes
            review.revision_count += 1

        # Update expert stats
        expert = self.db.query(ExpertReviewer).filter(
            ExpertReviewer.user_id == self.user_id
        ).first()
        if expert:
            expert.total_reviews += 1

        self._log_audit(
            action=f"review_{decision}",
            entity_type="review",
            entity_id=review_id,
            details={
                "scores": {
                    "clinical_accuracy": clinical_accuracy_score,
                    "clarity": question_clarity_score,
                    "distractors": distractor_quality_score,
                    "explanation": explanation_quality_score
                }
            }
        )

        self.db.commit()
        return review

    def _finalize_approved_question(self, review: ReviewQueue):
        """Finalize a question after expert approval."""

        question = review.question
        question.content_status = ContentStatus.ACTIVE
        question.expert_reviewed = True
        question.expert_reviewed_at = datetime.utcnow()
        question.expert_reviewer_id = review.reviewed_by
        question.clinical_accuracy_verified = review.clinical_accuracy_score >= 4

        # Calculate and update quality score
        self.calculate_quality_score(question.id)

    def _handle_rejected_question(self, review: ReviewQueue):
        """Handle a rejected question."""

        question = review.question
        question.content_status = ContentStatus.ARCHIVED
        question.rejected = True

    def register_expert_reviewer(
        self,
        user_id: str,
        specialties: List[str],
        credentials: Optional[str] = None,
        institution: Optional[str] = None,
        years_experience: Optional[int] = None
    ) -> ExpertReviewer:
        """Register a user as an expert reviewer."""

        # Check if already registered
        existing = self.db.query(ExpertReviewer).filter(
            ExpertReviewer.user_id == user_id
        ).first()

        if existing:
            existing.specialties = specialties
            existing.credentials = credentials
            existing.institution = institution
            existing.years_experience = years_experience
            existing.is_active = True
            self.db.commit()
            return existing

        expert = ExpertReviewer(
            user_id=user_id,
            specialties=specialties,
            credentials=credentials,
            institution=institution,
            years_experience=years_experience
        )

        self.db.add(expert)

        self._log_audit(
            action="register_expert",
            entity_type="expert_reviewer",
            entity_id=expert.id,
            details={"specialties": specialties}
        )

        self.db.commit()
        return expert

    def get_available_reviewers(self, specialty: Optional[str] = None) -> List[Dict]:
        """Get available expert reviewers, optionally filtered by specialty."""

        query = self.db.query(ExpertReviewer).filter(
            ExpertReviewer.is_active == True,
            ExpertReviewer.current_week_reviews < ExpertReviewer.max_reviews_per_week
        )

        reviewers = query.all()

        if specialty:
            reviewers = [
                r for r in reviewers
                if specialty in r.specialties
            ]

        return [
            {
                "user_id": r.user_id,
                "specialties": r.specialties,
                "credentials": r.credentials,
                "total_reviews": r.total_reviews,
                "agreement_rate": r.agreement_rate,
                "available_capacity": r.max_reviews_per_week - r.current_week_reviews
            }
            for r in reviewers
        ]

    # =========================================================================
    # CONTENT FRESHNESS SCORING
    # =========================================================================

    def _initialize_freshness_score(self, question_id: str):
        """Initialize freshness score for a new question."""

        freshness = ContentFreshnessScore(
            question_id=question_id,
            freshness_score=100.0,
            last_updated=datetime.utcnow()
        )
        self.db.add(freshness)

    def calculate_freshness_score(self, question_id: str) -> float:
        """Calculate the current freshness score for a question."""

        freshness = self.db.query(ContentFreshnessScore).filter(
            ContentFreshnessScore.question_id == question_id
        ).first()

        if not freshness:
            self._initialize_freshness_score(question_id)
            return 100.0

        # Time-based decay
        days_since_update = (datetime.utcnow() - freshness.last_updated).days
        time_decay = freshness.decay_rate * days_since_update

        # Usage-based factors
        usage_factor = 1.0
        if freshness.times_attempted > 0:
            # More attempts = more validated
            usage_factor += min(0.1, freshness.times_attempted / 1000)

        # Rating-based factors
        rating_factor = 1.0
        if freshness.rating_count > 0:
            # Good ratings boost freshness
            rating_factor = 0.5 + (freshness.average_rating or 0.5)

        # Report penalty
        report_penalty = freshness.times_reported * 5

        # Calculate new score
        base_score = 100 - time_decay
        adjusted_score = base_score * usage_factor * rating_factor - report_penalty
        new_score = max(0, min(100, adjusted_score))

        # Update record
        freshness.freshness_score = new_score
        freshness.last_decay_calculation = datetime.utcnow()

        # Check if needs review
        if new_score < 50 or freshness.times_reported >= 3:
            freshness.needs_review = True
            if new_score < 50:
                freshness.review_reason = "low_freshness"
            elif freshness.times_reported >= 3:
                freshness.review_reason = "high_reports"

        self.db.commit()
        return new_score

    def _update_freshness_from_rating(self, question_id: str):
        """Update freshness metrics when a rating is added."""

        freshness = self.db.query(ContentFreshnessScore).filter(
            ContentFreshnessScore.question_id == question_id
        ).first()

        if not freshness:
            return

        # Recalculate average rating
        ratings = self.db.query(QuestionRating).filter(
            QuestionRating.question_id == question_id
        ).all()

        freshness.rating_count = len(ratings)
        if ratings:
            freshness.average_rating = sum(1 if r.rating else 0 for r in ratings) / len(ratings)

    def _flag_for_review(self, question_id: str, reason: str):
        """Flag a question for review due to quality concerns."""

        freshness = self.db.query(ContentFreshnessScore).filter(
            ContentFreshnessScore.question_id == question_id
        ).first()

        if freshness:
            freshness.needs_review = True
            freshness.review_reason = reason
            freshness.times_reported += 1

    def get_stale_content(self, threshold: float = 50.0, limit: int = 50) -> List[Dict]:
        """Get content that needs attention due to low freshness."""

        stale = self.db.query(ContentFreshnessScore).filter(
            or_(
                ContentFreshnessScore.freshness_score < threshold,
                ContentFreshnessScore.needs_review == True
            )
        ).order_by(asc(ContentFreshnessScore.freshness_score)).limit(limit).all()

        return [
            {
                "question_id": s.question_id,
                "freshness_score": s.freshness_score,
                "needs_review": s.needs_review,
                "review_reason": s.review_reason,
                "times_reported": s.times_reported,
                "last_updated": s.last_updated.isoformat()
            }
            for s in stale
        ]

    def refresh_content(self, question_id: str):
        """Mark content as refreshed/updated."""

        freshness = self.db.query(ContentFreshnessScore).filter(
            ContentFreshnessScore.question_id == question_id
        ).first()

        if freshness:
            freshness.freshness_score = 100.0
            freshness.last_updated = datetime.utcnow()
            freshness.needs_review = False
            freshness.review_reason = None
            self.db.commit()

    def batch_refresh_freshness_scores(self):
        """Batch update freshness scores for all questions."""

        all_freshness = self.db.query(ContentFreshnessScore).all()
        updated = 0

        for f in all_freshness:
            old_score = f.freshness_score
            new_score = self.calculate_freshness_score(f.question_id)
            if old_score != new_score:
                updated += 1

        self._log_audit(
            action="batch_refresh",
            entity_type="freshness",
            affected_count=updated,
            details={"total_processed": len(all_freshness)}
        )

        return {"updated": updated, "total": len(all_freshness)}

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _normalize_specialty(self, specialty: Optional[str]) -> Optional[str]:
        """Normalize specialty names to consistent format."""

        if not specialty:
            return None

        specialty_lower = specialty.lower().strip()

        for normalized, aliases in SPECIALTIES.items():
            if specialty_lower == normalized:
                return normalized
            for alias in aliases:
                if specialty_lower == alias.lower():
                    return normalized

        return specialty_lower.replace(" ", "_")

    def _create_version(
        self,
        question: Question,
        change_type: str,
        change_reason: Optional[str] = None,
        fields_changed: Optional[List[str]] = None
    ):
        """Create a version snapshot of the question."""

        version = ContentVersion(
            question_id=question.id,
            version_number=question.version,
            vignette_snapshot=question.vignette,
            choices_snapshot=question.choices,
            answer_key_snapshot=question.answer_key,
            explanation_snapshot=question.explanation,
            change_type=change_type,
            change_reason=change_reason,
            changed_by=self.user_id,
            changed_by_system=self.user_id is None,
            fields_changed=fields_changed
        )
        self.db.add(version)

    def _log_audit(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        details: Optional[Dict] = None,
        affected_count: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Log an audit entry for tracking."""

        log = ContentAuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            performed_by=self.user_id,
            performed_by_system=self.user_id is None,
            details=details,
            affected_count=affected_count,
            success=success,
            error_message=error_message
        )
        self.db.add(log)

    def get_audit_log(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get audit log entries."""

        query = self.db.query(ContentAuditLog)

        if entity_type:
            query = query.filter(ContentAuditLog.entity_type == entity_type)
        if entity_id:
            query = query.filter(ContentAuditLog.entity_id == entity_id)
        if action:
            query = query.filter(ContentAuditLog.action == action)

        logs = query.order_by(desc(ContentAuditLog.created_at)).limit(limit).all()

        return [
            {
                "id": log.id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "performed_by": log.performed_by,
                "performed_by_system": log.performed_by_system,
                "details": log.details,
                "affected_count": log.affected_count,
                "success": log.success,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]

    # =========================================================================
    # BULK OPERATIONS
    # =========================================================================

    def bulk_import_questions(
        self,
        questions_data: List[Dict],
        source_type: str = SourceType.IMPORTED,
        submit_for_review: bool = True
    ) -> Dict:
        """Bulk import questions from structured data."""

        imported = 0
        errors = []

        for i, q_data in enumerate(questions_data):
            try:
                self.create_question(
                    vignette=q_data["vignette"],
                    choices=q_data["choices"],
                    answer_key=q_data["answer_key"],
                    explanation=q_data.get("explanation"),
                    source=q_data.get("source"),
                    source_type=source_type,
                    specialty=q_data.get("specialty"),
                    difficulty_level=q_data.get("difficulty_level"),
                    submit_for_review=submit_for_review
                )
                imported += 1
            except Exception as e:
                errors.append({"index": i, "error": str(e)})

        self._log_audit(
            action="bulk_import",
            entity_type="batch",
            affected_count=imported,
            details={"total_attempted": len(questions_data), "errors": len(errors)}
        )

        return {
            "imported": imported,
            "errors": errors,
            "total": len(questions_data)
        }

    def bulk_update_status(
        self,
        question_ids: List[str],
        new_status: str
    ) -> Dict:
        """Bulk update content status for multiple questions."""

        updated = 0
        for q_id in question_ids:
            question = self.get_question(q_id)
            if question:
                question.content_status = new_status
                updated += 1

        self._log_audit(
            action="bulk_update",
            entity_type="batch",
            affected_count=updated,
            details={"new_status": new_status, "question_ids": question_ids}
        )

        self.db.commit()
        return {"updated": updated, "total": len(question_ids)}

    def export_questions(
        self,
        filters: Optional[Dict] = None,
        format: str = "json"
    ) -> List[Dict]:
        """Export questions matching filters."""

        questions, _ = self.list_questions(filters=filters, limit=10000)

        export_data = [
            {
                "id": q.id,
                "vignette": q.vignette,
                "choices": q.choices,
                "answer_key": q.answer_key,
                "explanation": q.explanation,
                "source": q.source,
                "source_type": q.source_type,
                "specialty": q.specialty,
                "difficulty_level": q.difficulty_level,
                "quality_score": q.quality_score,
                "content_status": q.content_status
            }
            for q in questions
        ]

        self._log_audit(
            action="export",
            entity_type="batch",
            affected_count=len(export_data),
            details={"filters": filters, "format": format}
        )

        return export_data

    # =========================================================================
    # ANALYTICS & REPORTING
    # =========================================================================

    def get_content_dashboard(self) -> Dict:
        """Get comprehensive content management dashboard data."""

        # Total questions by status
        status_counts = self.db.query(
            Question.content_status,
            func.count(Question.id)
        ).group_by(Question.content_status).all()

        # Questions by source
        source_counts = self.db.query(
            Question.source_type,
            func.count(Question.id)
        ).filter(Question.content_status == ContentStatus.ACTIVE).group_by(Question.source_type).all()

        # Review queue stats
        pending_reviews = self.db.query(ReviewQueue).filter(
            ReviewQueue.status == ReviewStatus.PENDING
        ).count()

        in_review = self.db.query(ReviewQueue).filter(
            ReviewQueue.status == ReviewStatus.IN_REVIEW
        ).count()

        # Quality distribution
        quality_ranges = {
            "excellent": self.db.query(Question).filter(Question.quality_score >= 90).count(),
            "good": self.db.query(Question).filter(Question.quality_score >= 70, Question.quality_score < 90).count(),
            "fair": self.db.query(Question).filter(Question.quality_score >= 50, Question.quality_score < 70).count(),
            "poor": self.db.query(Question).filter(Question.quality_score < 50).count()
        }

        # Stale content
        stale_count = self.db.query(ContentFreshnessScore).filter(
            ContentFreshnessScore.needs_review == True
        ).count()

        # Recent activity
        recent_logs = self.get_audit_log(limit=10)

        return {
            "status_breakdown": dict(status_counts),
            "source_breakdown": dict(source_counts),
            "review_queue": {
                "pending": pending_reviews,
                "in_review": in_review
            },
            "quality_distribution": quality_ranges,
            "stale_content_count": stale_count,
            "recent_activity": recent_logs
        }
