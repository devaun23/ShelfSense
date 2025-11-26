"""
Tests for QuestionGenerationAgent service.

Tests cover:
- Agent initialization
- Multi-step question generation pipeline
- Real-time quality scoring checkpoints
- Targeted question generation
- Batch question generation
- Learning stage optimization
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.services.question_agent import (
    QuestionGenerationAgent,
    generate_question_with_agent,
    generate_questions_batch,
    generate_weakness_targeted_question,
    generate_learning_stage_question,
    generate_optimal_question
)
from app.models.models import Question
from tests.mocks.openai_mocks import (
    MockOpenAIClient,
    MOCK_QUESTION_RESPONSE,
    MOCK_EXPLANATION,
    MOCK_QUALITY_SCORES,
    mock_openai_completion
)


class TestQuestionGenerationAgentInit:
    """Tests for agent initialization"""

    def test_init_with_defaults(self, db):
        """Test agent initializes with default values"""
        agent = QuestionGenerationAgent(db)

        assert agent.db == db
        assert agent.model == "gpt-4o"
        assert agent.conversation_history == []

    def test_init_with_custom_model(self, db):
        """Test agent initializes with custom model"""
        agent = QuestionGenerationAgent(db, model="gpt-4o-mini")

        assert agent.model == "gpt-4o-mini"


class TestScoreClinicalScenario:
    """Tests for _score_clinical_scenario method"""

    def test_perfect_scenario_scores_high(self, db):
        """Test that a complete scenario scores high"""
        agent = QuestionGenerationAgent(db)
        scenario = {
            "patient_demographics": "65-year-old male with history of diabetes",
            "presenting_complaint": "Chest pain for 2 hours",
            "history_details": "Heavy smoker, HTN",
            "physical_exam": "BP 150/90 mmHg, HR 98/min, diaphoretic",
            "diagnostic_data": "Troponin elevated",
            "correct_answer_concept": "Acute coronary syndrome"
        }

        score, issues = agent.score_clinical_scenario(scenario, "Internal Medicine")

        assert score >= 0.8
        assert len(issues) == 0

    def test_missing_fields_reduce_score(self, db):
        """Test that missing fields reduce score"""
        agent = QuestionGenerationAgent(db)
        scenario = {
            "patient_demographics": "65-year-old male",
            # Missing presenting_complaint, physical_exam
            "correct_answer_concept": "Test"
        }

        score, issues = agent.score_clinical_scenario(scenario, "Internal Medicine")

        assert score < 0.8
        assert len(issues) > 0

    def test_missing_vitals_flagged(self, db):
        """Test that missing vital signs are flagged"""
        agent = QuestionGenerationAgent(db)
        scenario = {
            "patient_demographics": "65-year-old male",
            "presenting_complaint": "Chest pain",
            "physical_exam": "Patient appears uncomfortable",  # No vitals
            "correct_answer_concept": "ACS"
        }

        score, issues = agent.score_clinical_scenario(scenario, "Internal Medicine")

        assert any("vital" in issue.lower() for issue in issues)

    def test_vague_concept_flagged(self, db):
        """Test that vague correct answer concept is flagged"""
        agent = QuestionGenerationAgent(db)
        scenario = {
            "patient_demographics": "65-year-old male",
            "presenting_complaint": "Pain",
            "physical_exam": "BP 120/80 mmHg",
            "correct_answer_concept": "Test"  # Too vague
        }

        score, issues = agent.score_clinical_scenario(scenario, "Internal Medicine")

        assert any("vague" in issue.lower() for issue in issues)


class TestScoreAnswerChoices:
    """Tests for _score_answer_choices method"""

    def test_valid_choices_score_high(self, db):
        """Test that valid choices score high"""
        agent = QuestionGenerationAgent(db)
        choices_data = {
            "choices": [
                "A. Acute cholecystitis",
                "B. Choledocholithiasis",
                "C. Acute pancreatitis",
                "D. Peptic ulcer disease",
                "E. Acute appendicitis"
            ],
            "correct_answer_letter": "A",
            "choice_type": "diagnosis"
        }

        score, issues = agent.score_answer_choices(choices_data)

        assert score >= 0.9
        assert len(issues) == 0

    def test_wrong_number_of_choices(self, db):
        """Test that wrong number of choices reduces score"""
        agent = QuestionGenerationAgent(db)
        choices_data = {
            "choices": ["A. Option 1", "B. Option 2", "C. Option 3"],  # Only 3
            "correct_answer_letter": "A",
            "choice_type": "diagnosis"
        }

        score, issues = agent.score_answer_choices(choices_data)

        assert score < 0.8
        assert any("number of choices" in issue.lower() for issue in issues)

    def test_duplicate_choices_detected(self, db):
        """Test that duplicate choices are detected"""
        agent = QuestionGenerationAgent(db)
        choices_data = {
            "choices": [
                "A. Acute cholecystitis",
                "B. Acute cholecystitis",  # Duplicate
                "C. Acute pancreatitis",
                "D. Peptic ulcer disease",
                "E. Acute appendicitis"
            ],
            "correct_answer_letter": "A",
            "choice_type": "diagnosis"
        }

        score, issues = agent.score_answer_choices(choices_data)

        assert score < 0.8
        assert any("duplicate" in issue.lower() for issue in issues)

    def test_invalid_correct_answer_letter(self, db):
        """Test that invalid correct answer letter reduces score"""
        agent = QuestionGenerationAgent(db)
        choices_data = {
            "choices": ["A", "B", "C", "D", "E"],
            "correct_answer_letter": "F",  # Invalid
            "choice_type": "diagnosis"
        }

        score, issues = agent.score_answer_choices(choices_data)

        assert score < 0.7
        assert any("invalid" in issue.lower() for issue in issues)


class TestScoreVignette:
    """Tests for _score_vignette method"""

    def test_valid_vignette_scores_high(self, db):
        """Test that a valid vignette scores high"""
        agent = QuestionGenerationAgent(db)
        vignette = """A 45-year-old woman presents to the emergency department with 2 days of
        right upper quadrant pain, fever, and nausea. Temperature is 38.9°C, blood pressure
        is 110/70 mm Hg, and pulse is 92 beats/min. Physical examination shows right upper
        quadrant tenderness with a positive Murphy sign. Which of the following is the most
        appropriate next step in management?"""
        scenario = {"correct_answer_concept": "Cholecystectomy"}

        score, issues = agent.score_vignette(vignette, scenario)

        assert score >= 0.8
        assert len(issues) == 0

    def test_short_vignette_flagged(self, db):
        """Test that short vignettes are flagged"""
        agent = QuestionGenerationAgent(db)
        vignette = "A patient has pain. What is wrong?"
        scenario = {"correct_answer_concept": "Test"}

        score, issues = agent.score_vignette(vignette, scenario)

        assert score < 0.8
        assert any("short" in issue.lower() for issue in issues)

    def test_missing_question_flagged(self, db):
        """Test that missing question is flagged"""
        agent = QuestionGenerationAgent(db)
        vignette = """A 45-year-old woman presents with RUQ pain. BP is 120/80 mmHg.
        She has a positive Murphy sign. Labs show elevated WBC."""  # No question mark
        scenario = {"correct_answer_concept": "Test"}

        score, issues = agent.score_vignette(vignette, scenario)

        assert any("question" in issue.lower() or "lead-in" in issue.lower() for issue in issues)

    def test_missing_vitals_flagged(self, db):
        """Test that missing vital signs in vignette are flagged"""
        agent = QuestionGenerationAgent(db)
        vignette = """A 45-year-old woman presents with right upper quadrant pain and fever.
        She has a positive Murphy sign. What is the diagnosis?"""  # No BP, HR, etc.
        scenario = {"correct_answer_concept": "Test"}

        score, issues = agent.score_vignette(vignette, scenario)

        assert any("vital" in issue.lower() for issue in issues)


class TestLLMIntegration:
    """Tests for LLM integration with mocks"""

    @patch("app.utils.openai_client.get_openai_client")
    def test_call_llm_uses_correct_model(self, mock_get_client, db):
        """Test that _call_llm uses the configured model"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "{}"
        mock_client.chat.completions.create.return_value = mock_response

        agent = QuestionGenerationAgent(db, model="gpt-4o-mini")
        result = agent._call_llm("System prompt", "User prompt")

        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4o-mini"

    @patch("app.utils.openai_client.get_openai_client")
    def test_call_llm_passes_temperature(self, mock_client, db):
        """Test that temperature is passed correctly"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "{}"
        mock_client.chat.completions.create.return_value = mock_response

        agent = QuestionGenerationAgent(db)
        agent._call_llm("System", "User", temperature=0.5)

        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.5

    @patch("app.utils.openai_client.get_openai_client")
    def test_call_llm_with_response_format(self, mock_client, db):
        """Test that response_format is passed correctly"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "{}"
        mock_client.chat.completions.create.return_value = mock_response

        agent = QuestionGenerationAgent(db)
        agent._call_llm("System", "User", response_format={"type": "json_object"})

        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["response_format"] == {"type": "json_object"}


class TestStep1AnalyzeExamples:
    """Tests for step1_analyze_examples method"""

    @patch("app.utils.openai_client.get_openai_client")
    def test_analyzes_examples_successfully(self, mock_client, db):
        """Test that examples are analyzed correctly"""
        expected_analysis = {
            "vignette_patterns": "Standard NBME format",
            "clinical_detail_level": "High",
            "distractor_patterns": "Common differentials",
            "language_style": "Formal medical",
            "difficulty_markers": "Multiple diagnostic criteria"
        }
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(expected_analysis)
        mock_client.chat.completions.create.return_value = mock_response

        agent = QuestionGenerationAgent(db)
        examples = [
            {
                "vignette": "A 45-year-old woman...",
                "choices": ["A", "B", "C", "D", "E"],
                "answer": "A",
                "explanation": "Test explanation"
            }
        ]

        result = agent.step1_analyze_examples("Internal Medicine", examples)

        assert result["vignette_patterns"] == "Standard NBME format"
        assert "clinical_detail_level" in result


class TestStep2CreateClinicalScenario:
    """Tests for step2_create_clinical_scenario method"""

    @patch("app.utils.openai_client.get_openai_client")
    def test_creates_scenario_with_all_fields(self, mock_client, db):
        """Test scenario creation includes all required fields"""
        expected_scenario = {
            "patient_demographics": "65-year-old male",
            "presenting_complaint": "Chest pain for 2 hours",
            "history_details": "Smoker, HTN, DM",
            "physical_exam": "BP 150/90 mmHg, diaphoretic",
            "diagnostic_data": "ECG shows ST elevation",
            "clinical_question": "Management",
            "correct_answer_concept": "PCI",
            "reasoning": "STEMI requires urgent intervention"
        }
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(expected_scenario)
        mock_client.chat.completions.create.return_value = mock_response

        agent = QuestionGenerationAgent(db)
        analysis = {"vignette_patterns": "test"}

        result = agent.step2_create_clinical_scenario(
            "Internal Medicine", "STEMI", "management", "ED", analysis
        )

        assert result["patient_demographics"] == "65-year-old male"
        assert result["correct_answer_concept"] == "PCI"

    @patch("app.utils.openai_client.get_openai_client")
    def test_difficulty_parameter_used(self, mock_client, db):
        """Test that difficulty parameter is incorporated"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "patient_demographics": "Test",
            "presenting_complaint": "Test",
            "correct_answer_concept": "Test"
        })
        mock_client.chat.completions.create.return_value = mock_response

        agent = QuestionGenerationAgent(db)

        # Call with hard difficulty
        agent.step2_create_clinical_scenario(
            "Surgery", "Appendicitis", "diagnosis", "ED", {}, difficulty="hard"
        )

        # Check that difficulty was mentioned in the prompt
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        user_message = messages[1]["content"]
        assert "HARD" in user_message or "hard" in user_message.lower()


class TestGetExampleQuestions:
    """Tests for _get_example_questions method"""

    def test_returns_non_ai_questions(self, db):
        """Test that AI-generated questions are excluded from examples"""
        # Create a non-AI question
        q1 = Question(
            id="example-q-1",
            vignette="A 45-year-old woman presents...",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            source="UWorld - Internal Medicine",
            recency_weight=0.9
        )
        # Create an AI-generated question
        q2 = Question(
            id="example-q-2",
            vignette="A patient presents...",
            answer_key="B",
            choices=["A", "B", "C", "D", "E"],
            source="AI Agent Generated - Internal Medicine",
            recency_weight=0.9
        )
        db.add_all([q1, q2])
        db.commit()

        agent = QuestionGenerationAgent(db)
        examples = agent._get_example_questions("Internal Medicine", limit=10)

        # Should only include non-AI question
        assert len(examples) >= 1
        for ex in examples:
            assert "AI Generated" not in ex["source"]

    def test_filters_by_specialty(self, db):
        """Test that examples are filtered by specialty"""
        q_im = Question(
            id="specialty-q-1",
            vignette="IM question",
            answer_key="A",
            choices=["A", "B", "C", "D", "E"],
            source="UWorld - Internal Medicine",
            recency_weight=0.8
        )
        q_surg = Question(
            id="specialty-q-2",
            vignette="Surgery question",
            answer_key="B",
            choices=["A", "B", "C", "D", "E"],
            source="UWorld - Surgery",
            recency_weight=0.8
        )
        db.add_all([q_im, q_surg])
        db.commit()

        agent = QuestionGenerationAgent(db)
        im_examples = agent._get_example_questions("Internal Medicine", limit=10)

        # Should include IM, exclude Surgery
        sources = [ex["source"] for ex in im_examples]
        im_count = sum(1 for s in sources if "Internal Medicine" in s)
        surg_count = sum(1 for s in sources if "Surgery" in s)
        assert im_count >= surg_count  # May include both if not enough IM


class TestGenerateQuestionPipeline:
    """Tests for the full question generation pipeline"""

    @patch("app.utils.openai_client.get_openai_client")
    @patch("app.services.question_agent.get_weighted_specialty")
    @patch("app.services.question_agent.get_high_yield_topic")
    def test_full_pipeline_returns_question(self, mock_topic, mock_specialty, mock_client, db):
        """Test that full pipeline generates a valid question"""
        mock_specialty.return_value = "Internal Medicine"
        mock_topic.return_value = "Acute Cholecystitis"

        # Set up mock responses for each step
        responses = [
            # Step 1: Analysis
            json.dumps({
                "vignette_patterns": "Standard NBME",
                "clinical_detail_level": "High",
                "distractor_patterns": "Common differentials",
                "language_style": "Formal",
                "difficulty_markers": "Multiple criteria"
            }),
            # Step 2: Scenario
            json.dumps({
                "patient_demographics": "45-year-old woman",
                "presenting_complaint": "RUQ pain for 2 days",
                "history_details": "Gallstones",
                "physical_exam": "BP 120/80 mmHg, HR 88/min, positive Murphy",
                "diagnostic_data": "WBC 15,000",
                "clinical_question": "Management",
                "correct_answer_concept": "Cholecystectomy",
                "reasoning": "Classic cholecystitis"
            }),
            # Step 3: Choices
            json.dumps({
                "choices": [
                    "A. Emergent cholecystectomy",
                    "B. IV antibiotics only",
                    "C. ERCP",
                    "D. Observation",
                    "E. CT scan"
                ],
                "correct_answer_letter": "A",
                "choice_type": "management",
                "distractor_rationale": {
                    "A": "Correct for uncomplicated cholecystitis",
                    "B": "Insufficient without source control",
                    "C": "For choledocholithiasis",
                    "D": "Risk of perforation",
                    "E": "Already have diagnosis"
                }
            }),
            # Step 4: Vignette (plain text)
            """A 45-year-old woman presents to the emergency department with 2 days of right upper quadrant pain, fever, and nausea. Temperature is 38.5°C, blood pressure is 120/80 mm Hg, and pulse is 88 beats/min. Physical examination shows right upper quadrant tenderness with a positive Murphy sign. Laboratory studies show WBC 15,000/μL. Ultrasound shows gallbladder wall thickening. Which of the following is the most appropriate next step in management?""",
            # Step 5: Explanation
            json.dumps(MOCK_EXPLANATION),
            # Step 6: Validation
            json.dumps({
                "passes_quality": True,
                "issues_found": [],
                "severity": "none",
                "clinical_accuracy_score": 9,
                "nbme_standards_score": 9,
                "specialty_rules_passed": True
            })
        ]

        call_count = [0]

        def mock_create(**kwargs):
            response = MagicMock()
            response.choices = [MagicMock()]
            response.choices[0].message.content = responses[call_count[0]]
            call_count[0] += 1
            return response

        mock_client.chat.completions.create.side_effect = mock_create

        agent = QuestionGenerationAgent(db)
        result = agent.generate_question(max_retries=0)

        assert "vignette" in result
        assert "choices" in result
        assert "answer_key" in result
        assert "explanation" in result
        assert result["answer_key"] == "A"
        assert len(result["choices"]) == 5


class TestGenerateQuestionWithAgent:
    """Tests for generate_question_with_agent entry point"""

    @patch("app.services.question_agent.QuestionGenerationAgent")
    def test_creates_agent_and_generates(self, MockAgent, db):
        """Test that function creates agent and calls generate"""
        mock_agent = MagicMock()
        mock_agent.generate_question.return_value = MOCK_QUESTION_RESPONSE
        MockAgent.return_value = mock_agent

        result = generate_question_with_agent(db, specialty="Surgery")

        MockAgent.assert_called_once_with(db)
        mock_agent.generate_question.assert_called_once()

    @patch("app.services.question_agent.QuestionGenerationAgent")
    def test_parallel_mode_calls_parallel_method(self, MockAgent, db):
        """Test that parallel=True calls generate_question_parallel"""
        mock_agent = MagicMock()
        mock_agent.generate_question_parallel.return_value = MOCK_QUESTION_RESPONSE
        MockAgent.return_value = mock_agent

        result = generate_question_with_agent(db, parallel=True)

        mock_agent.generate_question_parallel.assert_called_once()


class TestGenerateQuestionsBatch:
    """Tests for batch question generation"""

    @patch("app.services.question_agent.QuestionGenerationAgent")
    def test_respects_count_limit(self, MockAgent, db):
        """Test that batch generation respects count limit"""
        mock_agent = MagicMock()
        mock_agent.generate_question.return_value = MOCK_QUESTION_RESPONSE
        MockAgent.return_value = mock_agent

        # Request more than max (10)
        results = generate_questions_batch(db, count=15)

        # Should be capped at 10
        assert mock_agent.generate_question.call_count <= 10

    @patch("app.services.question_agent.QuestionGenerationAgent")
    def test_handles_partial_failures(self, MockAgent, db):
        """Test that batch handles some failures gracefully"""
        mock_agent = MagicMock()
        # First call succeeds, second fails, third succeeds
        mock_agent.generate_question.side_effect = [
            MOCK_QUESTION_RESPONSE,
            Exception("Generation failed"),
            MOCK_QUESTION_RESPONSE
        ]
        MockAgent.return_value = mock_agent

        results = generate_questions_batch(db, count=3)

        # Should return only successful generations
        assert len(results) == 2


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    @patch("app.utils.openai_client.get_openai_client")
    def test_handles_malformed_llm_response(self, mock_client, db):
        """Test handling of malformed LLM responses"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not valid json"
        mock_client.chat.completions.create.return_value = mock_response

        agent = QuestionGenerationAgent(db)

        with pytest.raises(json.JSONDecodeError):
            agent.step1_analyze_examples("Internal Medicine", [])

    def test_empty_examples_handled(self, db):
        """Test that empty examples list is handled"""
        agent = QuestionGenerationAgent(db)
        examples = agent._get_example_questions("NonexistentSpecialty", limit=5)

        # Should return empty list, not error
        assert isinstance(examples, list)

    @patch("app.utils.openai_client.get_openai_client")
    @patch("app.services.question_agent.get_weighted_specialty")
    @patch("app.services.question_agent.get_high_yield_topic")
    def test_retry_on_quality_failure(self, mock_topic, mock_specialty, mock_client, db):
        """Test that generation retries on quality validation failure"""
        mock_specialty.return_value = "Internal Medicine"
        mock_topic.return_value = "Test Topic"

        responses = [
            # First attempt - all steps then fail validation
            json.dumps({"vignette_patterns": "test", "clinical_detail_level": "test",
                       "distractor_patterns": "test", "language_style": "test",
                       "difficulty_markers": "test"}),
            json.dumps({"patient_demographics": "45yo", "presenting_complaint": "pain",
                       "physical_exam": "BP 120/80 mmHg, HR 80/min", "correct_answer_concept": "Test diagnosis"}),
            json.dumps({"choices": ["A", "B", "C", "D", "E"], "correct_answer_letter": "A", "choice_type": "test"}),
            "A 45-year-old patient presents with pain. BP 120/80 mmHg. What is the diagnosis?",
            json.dumps(MOCK_EXPLANATION),
            json.dumps({"passes_quality": False, "issues_found": ["Issue 1"], "severity": "major",
                       "clinical_accuracy_score": 5, "nbme_standards_score": 5, "specialty_rules_passed": False}),
            # Second attempt - passes
            json.dumps({"vignette_patterns": "test", "clinical_detail_level": "test",
                       "distractor_patterns": "test", "language_style": "test",
                       "difficulty_markers": "test"}),
            json.dumps({"patient_demographics": "45yo male", "presenting_complaint": "chest pain",
                       "physical_exam": "BP 140/90 mmHg, HR 100/min", "correct_answer_concept": "ACS"}),
            json.dumps({"choices": ["A. ACS", "B. GERD", "C. PE", "D. Pneumonia", "E. Costochondritis"],
                       "correct_answer_letter": "A", "choice_type": "diagnosis"}),
            "A 45-year-old male presents with chest pain. BP 140/90 mm Hg, HR 100/min. ECG shows ST changes. What is the most likely diagnosis?",
            json.dumps(MOCK_EXPLANATION),
            json.dumps({"passes_quality": True, "issues_found": [], "severity": "none",
                       "clinical_accuracy_score": 9, "nbme_standards_score": 9, "specialty_rules_passed": True})
        ]

        call_count = [0]

        def mock_create(**kwargs):
            response = MagicMock()
            response.choices = [MagicMock()]
            if call_count[0] < len(responses):
                response.choices[0].message.content = responses[call_count[0]]
            else:
                response.choices[0].message.content = "{}"
            call_count[0] += 1
            return response

        mock_client.chat.completions.create.side_effect = mock_create

        agent = QuestionGenerationAgent(db)
        result = agent.generate_question(max_retries=2)

        # Should have retried and succeeded
        assert result is not None
        assert "vignette" in result
