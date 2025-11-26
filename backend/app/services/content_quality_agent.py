"""
Content Quality Agent for ShelfSense

This agent is responsible for:
1. Batch processing and validating all 1,994+ questions
2. Identifying questions with missing or poor quality explanations
3. Generating improved explanations following the 6-type framework
4. Validating answer choices for quality and consistency
5. Tracking quality improvements over time
6. Providing quality reports and metrics

The agent ensures every practice question meets ShelfSense standards:
- Viable explanations for each question
- Great answer choice explanations
- Compliance with NBME Gold Book principles
"""


import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.utils.openai_client import get_openai_client
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.models.models import (
    Question, ExplanationQualityLog
)
from app.services.adaptive_learning_engine import (
    EXPLANATION_TYPES,
    EXPLANATION_QUALITY_RULES
)




class ContentQualityAgent:
    """
    Agent responsible for ensuring all content meets ShelfSense quality standards.

    Capabilities:
    - Batch validation of questions
    - Explanation generation and improvement
    - Answer choice validation
    - Quality metrics and reporting
    - Automated quality improvement pipelines
    """

    def __init__(self, db: Session, model: str = "gpt-4o"):
        self.db = db
        self.model = model
        self.batch_size = 10  # Process in batches to manage API costs

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

        response = get_openai_client().chat.completions.create(**kwargs)
        return response.choices[0].message.content

    # =========================================================================
    # SECTION 1: QUALITY ASSESSMENT
    # =========================================================================

    def get_quality_overview(self) -> Dict:
        """
        Get a comprehensive overview of content quality across all questions.

        Returns:
            Dictionary with quality metrics and statistics
        """
        total_questions = self.db.query(Question).filter(
            Question.rejected == False
        ).count()

        # Questions with structured explanations
        questions_with_explanation = self.db.query(Question).filter(
            Question.rejected == False,
            Question.explanation.isnot(None)
        ).all()

        structured_count = 0
        has_distractors = 0
        by_type = {}

        for q in questions_with_explanation:
            if isinstance(q.explanation, dict):
                structured_count += 1

                exp_type = q.explanation.get("type", "unknown")
                by_type[exp_type] = by_type.get(exp_type, 0) + 1

                if q.explanation.get("distractor_explanations"):
                    has_distractors += 1

        # Questions without any explanation
        no_explanation = self.db.query(Question).filter(
            Question.rejected == False,
            or_(
                Question.explanation.is_(None),
                Question.explanation == ""
            )
        ).count()

        # Recent quality logs
        recent_logs = self.db.query(ExplanationQualityLog).filter(
            ExplanationQualityLog.validated_at >= datetime.utcnow() - timedelta(days=7)
        ).all()

        recent_valid = sum(1 for log in recent_logs if log.is_valid)
        recent_needs_regen = sum(1 for log in recent_logs if log.needs_regeneration)

        # Calculate percentages
        explanation_coverage = (len(questions_with_explanation) / total_questions * 100) if total_questions > 0 else 0
        structured_pct = (structured_count / total_questions * 100) if total_questions > 0 else 0
        distractor_pct = (has_distractors / total_questions * 100) if total_questions > 0 else 0

        return {
            "total_questions": total_questions,
            "with_explanation": len(questions_with_explanation),
            "without_explanation": no_explanation,
            "structured_explanations": structured_count,
            "with_distractor_explanations": has_distractors,
            "coverage_metrics": {
                "explanation_coverage": round(explanation_coverage, 1),
                "structured_percentage": round(structured_pct, 1),
                "distractor_coverage": round(distractor_pct, 1)
            },
            "by_explanation_type": by_type,
            "recent_validation": {
                "total_validated": len(recent_logs),
                "valid": recent_valid,
                "needs_regeneration": recent_needs_regen
            },
            "quality_score": self._calculate_overall_quality_score(
                total_questions, structured_count, has_distractors
            )
        }

    def _calculate_overall_quality_score(self, total: int, structured: int, distractors: int) -> float:
        """Calculate overall quality score (0-100)"""
        if total == 0:
            return 0

        # Weight: 40% structured, 40% distractors, 20% coverage
        structured_score = (structured / total) * 40
        distractor_score = (distractors / total) * 40
        coverage_score = (structured / total) * 20  # Same as having explanation

        return round(structured_score + distractor_score + coverage_score, 1)

    # =========================================================================
    # SECTION 2: BATCH VALIDATION
    # =========================================================================

    def identify_questions_needing_attention(self, limit: int = 100) -> Dict:
        """
        Identify questions that need quality improvements.

        Categories:
        - missing_explanation: No explanation at all
        - text_only_explanation: String explanation (not structured)
        - missing_distractors: No distractor explanations
        - low_quality: Poor quality based on previous validation

        Returns:
            Dictionary with categorized questions needing attention
        """
        results = {
            "missing_explanation": [],
            "text_only_explanation": [],
            "missing_distractors": [],
            "low_quality": [],
            "summary": {}
        }

        # Get all questions
        questions = self.db.query(Question).filter(
            Question.rejected == False
        ).limit(limit * 4).all()  # Get more to fill categories

        for q in questions:
            question_info = {
                "id": q.id,
                "source": q.source,
                "vignette_preview": q.vignette[:100] + "..." if len(q.vignette) > 100 else q.vignette
            }

            # Check for missing explanation
            if not q.explanation:
                if len(results["missing_explanation"]) < limit:
                    results["missing_explanation"].append(question_info)
                continue

            # Check for text-only explanation
            if isinstance(q.explanation, str):
                if len(results["text_only_explanation"]) < limit:
                    results["text_only_explanation"].append(question_info)
                continue

            # Check for missing distractors (structured but incomplete)
            if isinstance(q.explanation, dict):
                if not q.explanation.get("distractor_explanations"):
                    if len(results["missing_distractors"]) < limit:
                        results["missing_distractors"].append(question_info)

        # Check quality logs for low-quality questions
        low_quality_logs = self.db.query(ExplanationQualityLog).filter(
            ExplanationQualityLog.quality_score < 60,
            ExplanationQualityLog.was_improved == False
        ).limit(limit).all()

        for log in low_quality_logs:
            if len(results["low_quality"]) < limit:
                results["low_quality"].append({
                    "id": log.question_id,
                    "quality_score": log.quality_score,
                    "issues": log.issues
                })

        # Summary
        results["summary"] = {
            "missing_explanation": len(results["missing_explanation"]),
            "text_only_explanation": len(results["text_only_explanation"]),
            "missing_distractors": len(results["missing_distractors"]),
            "low_quality": len(results["low_quality"]),
            "total_needing_attention": (
                len(results["missing_explanation"]) +
                len(results["text_only_explanation"]) +
                len(results["missing_distractors"]) +
                len(results["low_quality"])
            )
        }

        return results

    def batch_validate_questions(self, question_ids: Optional[List[str]] = None,
                                  limit: int = 100, log_results: bool = True) -> Dict:
        """
        Validate multiple questions and optionally log results.

        Args:
            question_ids: Specific question IDs to validate (or None for auto-select)
            limit: Maximum number of questions to validate
            log_results: Whether to save validation results to database

        Returns:
            Validation results summary
        """
        if question_ids:
            questions = self.db.query(Question).filter(
                Question.id.in_(question_ids)
            ).all()
        else:
            # Get questions not recently validated
            recent_validated_ids = self.db.query(ExplanationQualityLog.question_id).filter(
                ExplanationQualityLog.validated_at >= datetime.utcnow() - timedelta(days=7)
            ).all()
            recent_ids = [r[0] for r in recent_validated_ids]

            questions = self.db.query(Question).filter(
                Question.rejected == False,
                ~Question.id.in_(recent_ids) if recent_ids else True
            ).limit(limit).all()

        results = {
            "validated": 0,
            "valid": 0,
            "needs_improvement": 0,
            "needs_regeneration": 0,
            "details": [],
            "by_issue": {}
        }

        for question in questions:
            validation = self._validate_single_question(question)
            results["validated"] += 1

            if validation["valid"]:
                results["valid"] += 1
            elif validation.get("needs_regeneration"):
                results["needs_regeneration"] += 1
            else:
                results["needs_improvement"] += 1

            results["details"].append({
                "question_id": question.id,
                "source": question.source,
                "valid": validation["valid"],
                "quality_score": validation.get("quality_score", 0),
                "issues": validation.get("issues", [])
            })

            # Track issues
            for issue in validation.get("issues", []):
                issue_key = issue.split(":")[0] if ":" in issue else issue[:50]
                results["by_issue"][issue_key] = results["by_issue"].get(issue_key, 0) + 1

            # Log results if requested
            if log_results:
                self._log_validation_result(question.id, validation)

        return results

    def _validate_single_question(self, question: Question) -> Dict:
        """Validate a single question's explanation quality against full EXPLANATION_FRAMEWORK.md"""
        issues = []
        suggestions = []
        import re

        explanation = question.explanation
        choices = question.choices
        answer_key = question.answer_key

        # Check if explanation exists
        if not explanation:
            return {
                "valid": False,
                "issues": ["No explanation found"],
                "suggestions": ["Generate explanation using the framework"],
                "needs_regeneration": True,
                "quality_score": 0
            }

        # Handle string explanations
        if isinstance(explanation, str):
            return {
                "valid": False,
                "issues": ["Explanation is plain text, not structured JSON"],
                "suggestions": ["Convert to structured explanation"],
                "needs_regeneration": True,
                "quality_score": 20
            }

        # === CORE REQUIRED FIELDS ===
        core_required = ["type", "principle", "clinical_reasoning", "correct_answer_explanation", "distractor_explanations"]
        for field in core_required:
            if field not in explanation or not explanation[field]:
                issues.append(f"Missing core field: {field}")

        # === ENHANCED REQUIRED FIELDS (per EXPLANATION_FRAMEWORK.md) ===
        enhanced_required = ["quick_answer", "deep_dive", "memory_hooks", "step_by_step"]
        for field in enhanced_required:
            if field not in explanation or not explanation[field]:
                suggestions.append(f"Missing enhanced field: {field}")

        # Check for explanation type
        explanation_type = explanation.get("type", "")
        if not explanation_type:
            issues.append("Missing explanation type classification")
        elif explanation_type not in EXPLANATION_TYPES:
            issues.append(f"Invalid explanation type: {explanation_type}")

        # === QUICK_ANSWER CHECK ===
        quick_answer = explanation.get("quick_answer", "")
        if quick_answer:
            word_count = len(quick_answer.split())
            if word_count > 30:
                issues.append(f"quick_answer too long ({word_count} words, max 30)")
        else:
            suggestions.append("Add quick_answer (30-word rapid review)")

        # === ARROW NOTATION CHECK ===
        principle = explanation.get("principle", "")
        clinical_reasoning = explanation.get("clinical_reasoning", "")
        combined_text = principle + " " + clinical_reasoning

        if "→" not in combined_text:
            issues.append("Missing arrow notation (→) in principle/reasoning")
            suggestions.append("Use → to show decision paths (e.g., 'BP <90 → shock → fluids')")

        # === EXPLICIT THRESHOLDS CHECK ===
        has_explicit_threshold = (
            bool(re.search(r'[<>≥≤]\s*\d+', combined_text)) or
            bool(re.search(r'\d+\s*(mg|mcg|mL|mmHg|bpm|%|hours?|days?)', combined_text))
        )
        if not has_explicit_threshold:
            suggestions.append("Add explicit thresholds (e.g., 'BP 80/50 (systolic <90)')")

        # === VAGUE TERMS CHECK ===
        vague_terms = ['hypotensive', 'tachycardic', 'bradycardic', 'elevated', 'decreased', 'abnormal']
        found_vague = []
        for term in vague_terms:
            if term in combined_text.lower():
                # Check if it's followed by a number
                if not re.search(rf'{term}[^.]*\d', combined_text.lower()):
                    found_vague.append(term)
        if found_vague:
            issues.append(f"Vague terms without numbers: {found_vague[:2]}")

        # === DISTRACTOR EXPLANATIONS CHECK ===
        distractor_explanations = explanation.get("distractor_explanations", {})
        if not distractor_explanations:
            issues.append("Missing distractor explanations")
        else:
            choice_letters = ["A", "B", "C", "D", "E"][:len(choices)]
            for letter in choice_letters:
                if letter == answer_key:
                    continue
                if letter not in distractor_explanations:
                    issues.append(f"Missing explanation for choice {letter}")
                elif len(str(distractor_explanations[letter])) < 20:
                    suggestions.append(f"Distractor {letter} explanation too brief")

        # === PRINCIPLE QUALITY CHECK ===
        if principle:
            if len(principle) > 300:
                issues.append("Principle too long (max 300 chars)")
            # Check for decision rule language
            decision_keywords = ['requires', 'indicates', 'confirms', 'when', 'if', '→']
            has_decision_rule = any(kw in principle.lower() for kw in decision_keywords)
            if not has_decision_rule:
                suggestions.append("Principle should state clear decision rule")

        # === DEEP_DIVE CHECK ===
        deep_dive = explanation.get("deep_dive", {})
        if deep_dive:
            if not deep_dive.get("pathophysiology"):
                suggestions.append("deep_dive missing pathophysiology")
            if not deep_dive.get("clinical_pearls"):
                suggestions.append("deep_dive missing clinical_pearls")

        # === STEP_BY_STEP CHECK ===
        step_by_step = explanation.get("step_by_step", [])
        if step_by_step and len(step_by_step) < 2:
            suggestions.append("step_by_step should have at least 2-3 steps")

        # === CALCULATE QUALITY SCORE ===
        # Core checks (60 points possible)
        core_checks = 6  # type, principle, reasoning, correct_expl, distractors, arrow notation
        core_passed = core_checks - len([i for i in issues if not i.startswith("Vague")])

        # Enhanced checks (40 points possible)
        enhanced_checks = 4  # quick_answer, deep_dive, memory_hooks, step_by_step
        enhanced_present = sum(1 for f in enhanced_required if explanation.get(f))

        core_score = (core_passed / core_checks) * 60
        enhanced_score = (enhanced_present / enhanced_checks) * 40
        quality_score = max(0, core_score + enhanced_score)

        return {
            "valid": len(issues) == 0 and len(suggestions) <= 2,
            "quality_score": round(quality_score, 1),
            "issues": issues,
            "suggestions": suggestions,
            "needs_regeneration": quality_score < 40,
            "explanation_type": explanation_type,
            "has_distractor_explanations": bool(distractor_explanations),
            "has_enhanced_elements": enhanced_present >= 3,
            "has_arrow_notation": "→" in combined_text
        }

    def _log_validation_result(self, question_id: str, validation: Dict):
        """Log validation result to database"""
        # Check for existing log
        existing = self.db.query(ExplanationQualityLog).filter(
            ExplanationQualityLog.question_id == question_id
        ).order_by(ExplanationQualityLog.validated_at.desc()).first()

        log = ExplanationQualityLog(
            question_id=question_id,
            quality_score=validation.get("quality_score", 0),
            is_valid=validation.get("valid", False),
            needs_regeneration=validation.get("needs_regeneration", False),
            issues=validation.get("issues", []),
            suggestions=validation.get("suggestions", []),
            explanation_type=validation.get("explanation_type"),
            has_distractor_explanations=validation.get("has_distractor_explanations", False),
            validated_at=datetime.utcnow()
        )
        self.db.add(log)
        self.db.commit()

    # =========================================================================
    # SECTION 3: EXPLANATION GENERATION
    # =========================================================================

    def generate_explanation_for_question(self, question_id: str) -> Dict:
        """
        Generate a high-quality explanation for a specific question.

        Follows the ShelfSense 6-type explanation framework.
        """
        question = self.db.query(Question).filter(Question.id == question_id).first()

        if not question:
            return {"success": False, "error": "Question not found"}

        # First, determine the best explanation type
        type_result = self._classify_question_type(question)
        explanation_type = type_result.get("type", "TYPE_E_TREATMENT_HIERARCHY")

        # Generate the full explanation
        explanation = self._generate_framework_explanation(question, explanation_type)

        if explanation:
            return {
                "success": True,
                "question_id": question_id,
                "explanation_type": explanation_type,
                "explanation": explanation,
                "validation": self._validate_single_question_with_explanation(question, explanation)
            }
        else:
            return {
                "success": False,
                "question_id": question_id,
                "error": "Failed to generate explanation"
            }

    def _classify_question_type(self, question: Question) -> Dict:
        """Determine the best explanation type for a question"""
        prompt = f"""Analyze this USMLE question and determine which explanation type it fits best.

VIGNETTE:
{question.vignette}

CHOICES:
{chr(10).join([f'{chr(65+i)}. {choice}' for i, choice in enumerate(question.choices)])}

CORRECT ANSWER: {question.answer_key}

EXPLANATION TYPES:
1. TYPE_A_STABILITY - Stable/Unstable decisions based on vital signs
2. TYPE_B_TIME_SENSITIVE - Time-window dependent interventions
3. TYPE_C_DIAGNOSTIC_SEQUENCE - Test ordering and diagnostic workup
4. TYPE_D_RISK_STRATIFICATION - Scoring systems and risk assessment
5. TYPE_E_TREATMENT_HIERARCHY - First-line treatments and contraindications
6. TYPE_F_DIFFERENTIAL - Distinguishing between similar diagnoses

Return JSON:
{{"type": "TYPE_X_NAME", "reasoning": "Brief explanation"}}"""

        response = self._call_llm(
            "You are a medical education expert classifying USMLE questions.",
            prompt,
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        return json.loads(response)

    def _generate_framework_explanation(self, question: Question, explanation_type: str) -> Optional[Dict]:
        """Generate a complete explanation following the full EXPLANATION_FRAMEWORK.md"""
        type_info = EXPLANATION_TYPES.get(explanation_type, {})

        prompt = f"""Generate a high-quality educational explanation for this USMLE question following the ShelfSense framework.

VIGNETTE:
{question.vignette}

CHOICES:
{chr(10).join([f'{chr(65+i)}. {choice}' for i, choice in enumerate(question.choices)])}

CORRECT ANSWER: {question.answer_key}

EXPLANATION TYPE: {explanation_type}
TYPE INFO: {json.dumps(type_info, indent=2)}

QUALITY RULES:
{json.dumps(EXPLANATION_QUALITY_RULES, indent=2)}

Generate a COMPLETE explanation with ALL these fields:
{{
    "type": "{explanation_type}",

    "quick_answer": "30-word MAX rapid review summary. Example: 'Septic shock from cholecystitis needs urgent surgery, not just antibiotics.'",

    "principle": "One sentence with EXACT decision rule using arrow notation (→). Pattern: {type_info.get('pattern', '')}. Example: 'BP <90 with lactate >4 → septic shock → source control required'",

    "clinical_reasoning": "2-5 sentences using → notation. EVERY number must be defined. Example: 'BP 76/50 (systolic <90) and HR 128 (>100) → hemodynamic instability → septic shock. Low CVP (2 mmHg, normal 3-8) after fluids → vasodilation, not hypovolemia.'",

    "correct_answer_explanation": "Why {question.answer_key} is right. Include pathophysiology and clinical logic with → notation.",

    "distractor_explanations": {{
        "A": "Why A is wrong for THIS patient (15-20 words, skip if A is correct)",
        "B": "Why B is wrong for THIS patient (15-20 words, skip if B is correct)",
        "C": "Why C is wrong for THIS patient (15-20 words, skip if C is correct)",
        "D": "Why D is wrong for THIS patient (15-20 words, skip if D is correct)",
        "E": "Why E is wrong for THIS patient (15-20 words, skip if E is correct)"
    }},

    "deep_dive": {{
        "pathophysiology": "Why this happens at biological/mechanistic level (2-3 sentences)",
        "differential_comparison": "How to distinguish from similar conditions",
        "clinical_pearls": ["High-yield fact 1", "Board-relevant detail 2", "Clinical tip 3"]
    }},

    "step_by_step": [
        {{"step": 1, "action": "First step", "rationale": "Why this step"}},
        {{"step": 2, "action": "Next step", "rationale": "Why this step"}},
        {{"step": 3, "action": "Final step", "rationale": "Why this step"}}
    ],

    "memory_hooks": {{
        "analogy": "Relatable comparison to remember the concept. Example: 'You can't put out a fire while fuel is still burning'",
        "mnemonic": "If applicable (e.g., MUDPILES for anion gap acidosis)",
        "clinical_story": "Brief memorable case pattern"
    }},

    "common_traps": [
        {{
            "trap": "What students commonly get wrong",
            "why_wrong": "Why this thinking fails",
            "correct_thinking": "The right approach"
        }}
    ],

    "educational_objective": "One sentence: what decision-making pattern this teaches",
    "concept": "Topic area (e.g., 'Cardiology', 'Acute Care Surgery')",
    "related_topics": ["Related topic 1", "Related topic 2"]
}}

CRITICAL QUALITY REQUIREMENTS:
1. Use → for ALL causal relationships and decision paths
2. EVERY number must have context (e.g., "BP 80/50 (systolic <90)" not just "hypotensive")
3. quick_answer MUST be ≤30 words
4. Principle must be one clear, actionable decision rule
5. Core explanation (principle + clinical_reasoning) under 200 words
6. Each distractor explanation specific to THIS patient, not generic"""

        try:
            response = self._call_llm(
                "You are an expert medical educator writing USMLE explanations.",
                prompt,
                temperature=0.4,
                response_format={"type": "json_object"}
            )
            return json.loads(response)
        except Exception as e:
            print(f"Error generating explanation: {e}")
            return None

    def _validate_single_question_with_explanation(self, question: Question, explanation: Dict) -> Dict:
        """Validate a generated explanation"""
        issues = []

        # Check required fields
        required = ["type", "principle", "clinical_reasoning", "correct_answer_explanation", "distractor_explanations"]
        for field in required:
            if field not in explanation or not explanation[field]:
                issues.append(f"Missing {field}")

        # Check distractor completeness
        distractors = explanation.get("distractor_explanations", {})
        choice_letters = ["A", "B", "C", "D", "E"][:len(question.choices)]

        for letter in choice_letters:
            if letter != question.answer_key and letter not in distractors:
                issues.append(f"Missing distractor for {letter}")

        # Check for arrow notation
        reasoning = explanation.get("clinical_reasoning", "")
        if "→" not in reasoning and "->" not in reasoning:
            issues.append("Missing arrow notation in reasoning")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "checks_passed": len(required) + len(question.choices) - 1 - len(issues)
        }

    # =========================================================================
    # SECTION 4: BATCH IMPROVEMENT
    # =========================================================================

    def batch_improve_explanations(self, max_questions: int = 10,
                                    priority: str = "missing",
                                    auto_apply: bool = False) -> Dict:
        """
        Batch improve explanations for questions needing attention.

        Args:
            max_questions: Maximum questions to process
            priority: "missing" (no explanation), "text_only", "low_quality", or "all"
            auto_apply: Whether to automatically save improvements

        Returns:
            Results summary with improvements
        """
        # Get questions needing attention
        attention = self.identify_questions_needing_attention(limit=max_questions * 2)

        # Select questions based on priority
        if priority == "missing":
            question_ids = [q["id"] for q in attention["missing_explanation"][:max_questions]]
        elif priority == "text_only":
            question_ids = [q["id"] for q in attention["text_only_explanation"][:max_questions]]
        elif priority == "low_quality":
            question_ids = [q["id"] for q in attention["low_quality"][:max_questions]]
        else:  # "all" - mix of categories
            question_ids = []
            for category in ["missing_explanation", "text_only_explanation", "missing_distractors", "low_quality"]:
                for q in attention[category]:
                    if len(question_ids) < max_questions and q["id"] not in question_ids:
                        question_ids.append(q["id"])

        results = {
            "processed": 0,
            "improved": 0,
            "failed": 0,
            "applied": 0,
            "details": []
        }

        for question_id in question_ids:
            try:
                improvement = self.generate_explanation_for_question(question_id)
                results["processed"] += 1

                if improvement.get("success"):
                    results["improved"] += 1

                    detail = {
                        "question_id": question_id,
                        "status": "improved",
                        "explanation_type": improvement.get("explanation_type"),
                        "applied": False
                    }

                    if auto_apply:
                        question = self.db.query(Question).filter(Question.id == question_id).first()
                        if question:
                            question.explanation = improvement["explanation"]
                            self.db.commit()
                            detail["applied"] = True
                            results["applied"] += 1

                            # Log the improvement
                            log = self.db.query(ExplanationQualityLog).filter(
                                ExplanationQualityLog.question_id == question_id
                            ).order_by(ExplanationQualityLog.validated_at.desc()).first()

                            if log:
                                log.was_improved = True
                                log.improved_at = datetime.utcnow()
                                log.improved_by = "auto"
                                self.db.commit()

                    results["details"].append(detail)
                else:
                    results["failed"] += 1
                    results["details"].append({
                        "question_id": question_id,
                        "status": "failed",
                        "error": improvement.get("error", "Unknown error")
                    })

            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "question_id": question_id,
                    "status": "error",
                    "error": str(e)
                })

        return results

    # =========================================================================
    # SECTION 5: QUALITY REPORTS
    # =========================================================================

    def generate_quality_report(self) -> Dict:
        """
        Generate a comprehensive quality report.

        Returns:
            Detailed report with metrics, trends, and recommendations
        """
        overview = self.get_quality_overview()
        attention = self.identify_questions_needing_attention(limit=50)

        # Get trends from quality logs
        week_ago = datetime.utcnow() - timedelta(days=7)
        month_ago = datetime.utcnow() - timedelta(days=30)

        week_logs = self.db.query(ExplanationQualityLog).filter(
            ExplanationQualityLog.validated_at >= week_ago
        ).all()

        month_logs = self.db.query(ExplanationQualityLog).filter(
            ExplanationQualityLog.validated_at >= month_ago
        ).all()

        # Calculate averages
        week_avg_score = sum(log.quality_score or 0 for log in week_logs) / len(week_logs) if week_logs else 0
        month_avg_score = sum(log.quality_score or 0 for log in month_logs) / len(month_logs) if month_logs else 0

        # Count improvements
        improved_this_week = sum(1 for log in week_logs if log.was_improved)
        improved_this_month = sum(1 for log in month_logs if log.was_improved)

        # Generate recommendations
        recommendations = []

        if attention["summary"]["missing_explanation"] > 0:
            recommendations.append({
                "priority": "high",
                "action": f"Generate explanations for {attention['summary']['missing_explanation']} questions without any explanation",
                "impact": "High - these questions are not educational without explanations"
            })

        if attention["summary"]["text_only_explanation"] > 0:
            recommendations.append({
                "priority": "medium",
                "action": f"Convert {attention['summary']['text_only_explanation']} text-only explanations to structured format",
                "impact": "Medium - structured explanations are more educational"
            })

        if attention["summary"]["missing_distractors"] > 0:
            recommendations.append({
                "priority": "medium",
                "action": f"Add distractor explanations to {attention['summary']['missing_distractors']} questions",
                "impact": "Medium - students need to understand why wrong answers are wrong"
            })

        if overview["coverage_metrics"]["structured_percentage"] < 80:
            recommendations.append({
                "priority": "high",
                "action": "Increase structured explanation coverage to 80%+",
                "impact": "High - consistent explanation format improves learning"
            })

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "overview": overview,
            "attention_needed": attention["summary"],
            "trends": {
                "week": {
                    "validated": len(week_logs),
                    "avg_quality_score": round(week_avg_score, 1),
                    "improved": improved_this_week
                },
                "month": {
                    "validated": len(month_logs),
                    "avg_quality_score": round(month_avg_score, 1),
                    "improved": improved_this_month
                }
            },
            "recommendations": recommendations,
            "quality_score": overview["quality_score"]
        }

    def get_source_quality_breakdown(self) -> Dict:
        """Get quality breakdown by question source"""
        questions = self.db.query(Question).filter(
            Question.rejected == False
        ).all()

        by_source = {}

        for q in questions:
            source = q.source or "Unknown"

            if source not in by_source:
                by_source[source] = {
                    "total": 0,
                    "with_explanation": 0,
                    "structured": 0,
                    "with_distractors": 0
                }

            by_source[source]["total"] += 1

            if q.explanation:
                by_source[source]["with_explanation"] += 1

                if isinstance(q.explanation, dict):
                    by_source[source]["structured"] += 1

                    if q.explanation.get("distractor_explanations"):
                        by_source[source]["with_distractors"] += 1

        # Calculate percentages
        for source, data in by_source.items():
            if data["total"] > 0:
                data["explanation_pct"] = round(data["with_explanation"] / data["total"] * 100, 1)
                data["structured_pct"] = round(data["structured"] / data["total"] * 100, 1)
                data["distractor_pct"] = round(data["with_distractors"] / data["total"] * 100, 1)
                data["quality_score"] = round(
                    (data["structured_pct"] * 0.4 + data["distractor_pct"] * 0.4 + data["explanation_pct"] * 0.2),
                    1
                )

        # Sort by quality score
        sorted_sources = sorted(
            by_source.items(),
            key=lambda x: x[1].get("quality_score", 0),
            reverse=True
        )

        return {
            "by_source": dict(sorted_sources),
            "total_sources": len(by_source)
        }


# =========================================================================
# CONVENIENCE FUNCTIONS
# =========================================================================

def get_content_quality_agent(db: Session) -> ContentQualityAgent:
    """Factory function to create a ContentQualityAgent instance"""
    return ContentQualityAgent(db)


def run_quality_check(db: Session, limit: int = 100) -> Dict:
    """Run a quick quality check on questions"""
    agent = ContentQualityAgent(db)
    return agent.batch_validate_questions(limit=limit, log_results=True)


def generate_quality_report(db: Session) -> Dict:
    """Generate a comprehensive quality report"""
    agent = ContentQualityAgent(db)
    return agent.generate_quality_report()


def batch_improve_questions(db: Session, max_questions: int = 10, auto_apply: bool = False) -> Dict:
    """Batch improve question explanations"""
    agent = ContentQualityAgent(db)
    return agent.batch_improve_explanations(max_questions=max_questions, auto_apply=auto_apply)
