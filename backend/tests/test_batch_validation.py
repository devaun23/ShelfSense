"""
Tests for Batch Validation Pipeline

Validates the validators to ensure quality gates work correctly.
"""

import pytest
from datetime import datetime
from typing import List, Dict

from app.services.batch_validation_pipeline import (
    BatchValidationPipeline,
    detect_plagiarism,
    ValidationResult,
    BatchValidationReport
)


# Test fixtures
@pytest.fixture
def sample_questions() -> List[Dict]:
    """Generate sample questions for testing"""
    return [
        {
            "id": "q1",
            "vignette": "A 65-year-old man with a history of hypertension presents with chest pain (BP 180/110 mmHg, HR 88/min). ECG shows ST elevations in leads V1-V4. What is the most appropriate next step?",
            "choices": [
                "A. Aspirin 325 mg PO",
                "B. Nitroglycerin sublingual",
                "C. Emergent cardiac catheterization",
                "D. IV beta-blocker",
                "E. Morphine for pain control"
            ],
            "answer_key": "C",
            "explanation": {
                "quick_answer": "Anterior STEMI requires emergent reperfusion via catheterization.",
                "clinical_reasoning": "ST elevations in V1-V4 indicate acute anterior MI. Cardiac catheterization for PCI is first-line within 90 minutes.",
                "correct_answer_explanation": "Emergent cardiac catheterization for PCI is the definitive treatment for STEMI within 90 minutes of presentation.",
                "distractor_explanations": {
                    "A": "Aspirin is given immediately but is adjunctive, not definitive.",
                    "B": "Nitroglycerin treats symptoms but not the occlusion.",
                    "D": "Beta-blockers are contraindicated in acute phase due to negative inotropy.",
                    "E": "Morphine is adjunctive for pain, not definitive treatment."
                },
                "principle": "STEMI management: door-to-balloon time <90 minutes improves mortality",
                "deep_dive": "Anterior MI → LAD occlusion → transmural ischemia → ST elevation → emergent reperfusion"
            },
            "specialty": "internal_medicine",
            "subsystem": "cardiology",
            "difficulty": "medium"
        },
        # Borderline quality question (should pass but not elite)
        {
            "id": "q2",
            "vignette": "A 45-year-old woman has fatigue. Labs show low hemoglobin. What test should be ordered next?",
            "choices": [
                "A. Iron studies",
                "B. Vitamin B12 level",
                "C. Folate level",
                "D. Reticulocyte count",
                "E. Bone marrow biopsy"
            ],
            "answer_key": "D",
            "explanation": {
                "quick_answer": "Reticulocyte count helps classify anemia.",
                "clinical_reasoning": "First step in anemia workup is to classify as hypoproliferative vs hemolytic using reticulocyte count.",
                "correct_answer_explanation": "Reticulocyte count distinguishes production vs destruction issues.",
                "distractor_explanations": {
                    "A": "Iron studies are premature without reticulocyte count.",
                    "B": "B12 is specific for macrocytic anemia.",
                    "C": "Folate is also for macrocytic anemia.",
                    "E": "Bone marrow biopsy is invasive and not first-line."
                }
            },
            "specialty": "internal_medicine",
            "subsystem": "hematology"
        },
        # Poor quality question (should be rejected)
        {
            "id": "q3",
            "vignette": "A patient is sick. What do you do?",  # Vague, no vitals
            "choices": [
                "A. Do nothing",
                "B. Give medicine",
                "C. Call doctor",
                "D. Send home",
                "E. Admit to hospital"
            ],
            "answer_key": "B",
            "explanation": {
                "quick_answer": "Give medicine."
            },
            "specialty": "internal_medicine"
        },
        # Question with dangerous misinformation (should be rejected)
        {
            "id": "q4",
            "vignette": "A 25-year-old pregnant woman at 8 weeks gestation has a UTI. What is the most appropriate treatment?",
            "choices": [
                "A. Nitrofurantoin",
                "B. Ciprofloxacin",
                "C. Trimethoprim-sulfamethoxazole",
                "D. Doxycycline",
                "E. Amoxicillin"
            ],
            "answer_key": "B",  # WRONG - Ciprofloxacin is contraindicated in pregnancy!
            "explanation": {
                "quick_answer": "Ciprofloxacin is first-line for UTI.",
                "clinical_reasoning": "Fluoroquinolones are effective against common UTI pathogens.",
                "correct_answer_explanation": "Ciprofloxacin covers E. coli and is well-tolerated.",
                "distractor_explanations": {
                    "A": "Nitrofurantoin is less effective.",
                    "E": "Amoxicillin has high resistance rates."
                }
            },
            "specialty": "internal_medicine",
            "subsystem": "infectious_disease"
        }
    ]


@pytest.fixture
def mock_db(mocker):
    """Mock database session"""
    return mocker.MagicMock()


class TestBatchValidationPipeline:
    """Test suite for validation pipeline"""

    @pytest.mark.asyncio
    async def test_stage1_filters_bad_questions(self, sample_questions, mock_db):
        """Test that Stage 1 rejects structurally bad questions"""
        pipeline = BatchValidationPipeline(mock_db)

        bad_question = sample_questions[2]  # "A patient is sick"
        result = pipeline._run_stage1(bad_question)

        assert result["passed"] == False
        assert len(result["issues"]) > 0

    @pytest.mark.asyncio
    async def test_good_question_passes_stage1(self, sample_questions, mock_db):
        """Test that high-quality questions pass Stage 1"""
        pipeline = BatchValidationPipeline(mock_db)

        good_question = sample_questions[0]  # STEMI question
        result = pipeline._run_stage1(good_question)

        assert result["passed"] == True
        assert result["time_ms"] > 0

    @pytest.mark.asyncio
    async def test_elite_validation_identifies_elite_questions(self, sample_questions, mock_db):
        """Test that Stage 3 correctly identifies elite-quality explanations"""
        pipeline = BatchValidationPipeline(mock_db)

        # Question with excellent explanation
        elite_question = sample_questions[0]
        result = pipeline._run_stage3(elite_question)

        assert result["score"] >= 85  # Elite threshold
        assert result["is_elite"] == True

    @pytest.mark.asyncio
    async def test_borderline_question_passes_but_not_elite(self, sample_questions, mock_db):
        """Test that acceptable questions pass but aren't marked elite"""
        pipeline = BatchValidationPipeline(mock_db)

        borderline_question = sample_questions[1]  # Anemia question
        result = pipeline._run_stage3(borderline_question)

        assert result["score"] >= 70  # Passes threshold
        assert result["score"] < 85  # But not elite
        assert result["is_elite"] == False

    def test_sample_size_calculation(self, mock_db):
        """Test sample size calculation for human review"""
        pipeline = BatchValidationPipeline(mock_db)

        # For 2,500 questions, 95% confidence, 5% margin
        sample_size = pipeline.calculate_sample_size(population_size=2500)

        # Should be around 333 questions
        assert 320 <= sample_size <= 350

    def test_stratified_sampling(self, sample_questions, mock_db):
        """Test that stratified sampling works correctly"""
        pipeline = BatchValidationPipeline(mock_db)

        # Create 100 questions with different scores
        questions_with_scores = []
        for i in range(100):
            q = sample_questions[0].copy()
            q["id"] = f"q_{i}"
            q["validation_score"] = 60 + (i % 40)  # Scores 60-100
            questions_with_scores.append(q)

        sample = pipeline.select_human_review_sample(questions_with_scores, sample_size=20)

        # Should return requested sample size
        assert len(sample) == 20

        # Should include some borderline questions (65-75)
        borderline_in_sample = sum(
            1 for q in sample
            if 65 <= q.get("validation_score", 0) < 75
        )
        assert borderline_in_sample > 0

    def test_plagiarism_detection_exact_match(self, sample_questions):
        """Test plagiarism detection for exact duplicates"""
        question = sample_questions[0]
        known_questions = [sample_questions[0]]  # Exact duplicate

        result = detect_plagiarism(question, known_questions)

        assert result["is_plagiarism"] == True
        assert result["max_similarity"] > 0.95

    def test_plagiarism_detection_no_match(self, sample_questions):
        """Test that different questions are not flagged"""
        question = sample_questions[0]
        known_questions = [sample_questions[1]]  # Different question

        result = detect_plagiarism(question, known_questions)

        assert result["is_plagiarism"] == False
        assert result["max_similarity"] < 0.70

    @pytest.mark.asyncio
    async def test_quality_gate_triggers_on_low_acceptance(self, sample_questions, mock_db):
        """Test that quality gate triggers when acceptance rate drops"""
        pipeline = BatchValidationPipeline(mock_db)

        # Create batch of mostly bad questions
        bad_batch = [sample_questions[2]] * 150  # 150 bad questions
        for i, q in enumerate(bad_batch):
            q["id"] = f"bad_{i}"

        report = await pipeline.validate_batch(bad_batch, enable_gates=True)

        # Should have quality gate failures
        assert len(report.quality_gate_failures) > 0

        # Acceptance rate should be low
        assert report.acceptance_rate < 0.50

    @pytest.mark.asyncio
    async def test_cost_estimation(self, sample_questions, mock_db):
        """Test that cost estimation is accurate"""
        pipeline = BatchValidationPipeline(mock_db)

        # Validate 100 questions
        batch = sample_questions[:2] * 50  # 100 total
        for i, q in enumerate(batch):
            q["id"] = f"q_{i}"

        report = await pipeline.validate_batch(batch, enable_gates=False)

        # Cost should be ~$0.025 for 100 questions ($0.25 per 1000)
        expected_cost = 100 * 0.00025
        assert abs(report.estimated_cost - expected_cost) < 0.01

    def test_confidence_interval_calculation(self, mock_db):
        """Test population quality estimate from sample"""
        pipeline = BatchValidationPipeline(mock_db)

        # Simulate sample: 95 out of 100 passed
        sample_results = [
            {"expert_approved": True} for _ in range(95)
        ] + [
            {"expert_approved": False} for _ in range(5)
        ]

        estimate = pipeline.calculate_population_quality(
            sample_results=sample_results,
            population_size=2500
        )

        # Sample pass rate should be 0.95
        assert estimate["sample_pass_rate"] == 0.95

        # Confidence interval should be reasonable
        assert 0.88 <= estimate["ci_lower"] <= 0.92
        assert 0.97 <= estimate["ci_upper"] <= 1.0

        # Estimated passing questions
        assert 2200 <= estimate["estimated_passing_questions"] <= 2400


class TestRedFlags:
    """Test red flag detection"""

    def test_detect_vague_terms(self, mock_db):
        """Test detection of vague clinical terms"""
        pipeline = BatchValidationPipeline(mock_db)

        vague_question = {
            "vignette": "A patient is hypotensive and tachycardic with low hemoglobin.",  # No values!
            "choices": ["A", "B", "C", "D", "E"],
            "answer_key": "A"
        }

        result = pipeline._run_stage1(vague_question)

        assert result["passed"] == False
        assert any("vague" in issue.lower() for issue in result["issues"])

    def test_detect_testwiseness_cues(self, mock_db):
        """Test detection of testwiseness cues"""
        pipeline = BatchValidationPipeline(mock_db)

        # Correct answer is much longer (testwiseness cue)
        testwiseness_question = {
            "vignette": "A patient has chest pain. What is the diagnosis?",
            "choices": [
                "A. MI",
                "B. PE",
                "C. Unstable angina pectoris secondary to atherosclerotic coronary artery disease with associated risk factors",  # Way too long!
                "D. GERD",
                "E. MSK"
            ],
            "answer_key": "C"
        }

        result = pipeline._run_stage1(testwiseness_question)

        # Should detect length cue
        assert result["passed"] == False or len(result["issues"]) > 0


@pytest.mark.integration
class TestIntegration:
    """Integration tests with real database"""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_real_questions(self, sample_questions, db):
        """Test full validation pipeline end-to-end"""
        pipeline = BatchValidationPipeline(db)

        report = await pipeline.validate_batch(
            questions=sample_questions,
            enable_gates=True
        )

        # Should process all questions
        assert report.total_questions == len(sample_questions)

        # Should accept at least the good question
        assert report.accepted >= 1

        # Should reject the bad questions
        assert report.rejected >= 2

        # Elite rate should be reasonable
        assert 0 <= report.elite_rate <= 1.0

        # Cost should be minimal
        assert report.estimated_cost < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
