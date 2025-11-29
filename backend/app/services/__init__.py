# Services module

# Question generation and validation
from app.services.question_agent import (
    QuestionGenerationAgent,
    generate_question_with_agent,
    generate_question_fast,
    generate_questions_fast_batch,
    generate_questions_batch,
    generate_weakness_targeted_question,
    generate_learning_stage_question,
    generate_optimal_question,
)

# Quality validators (Issues #8, #10, #11, #12)
from app.services.medical_fact_checker import (
    ClinicalFactChecker,
    clinical_fact_checker,
    validate_question_facts,
    FactCheckResult,
    FactCheckReport,
)

from app.services.question_validators import (
    QuestionQualityValidator,
    VagueTermValidator,
    TestwisenessValidator,
    DistractorQualityValidator,
    validate_question,
    check_vague_terms,
    check_testwiseness,
    check_distractor_quality,
)

# IRT Calibration (Issue #9)
from app.services.item_response_theory import (
    IRTCalibrator,
    IRTParameters,
    DistractorMetrics,
    QuestionPsychometrics,
    get_empirical_difficulty,
    should_use_empirical_difficulty,
)

__all__ = [
    # Question generation
    "QuestionGenerationAgent",
    "generate_question_with_agent",
    "generate_question_fast",
    "generate_questions_fast_batch",
    "generate_questions_batch",
    "generate_weakness_targeted_question",
    "generate_learning_stage_question",
    "generate_optimal_question",
    # Fact checker
    "ClinicalFactChecker",
    "clinical_fact_checker",
    "validate_question_facts",
    "FactCheckResult",
    "FactCheckReport",
    # Question validators
    "QuestionQualityValidator",
    "VagueTermValidator",
    "TestwisenessValidator",
    "DistractorQualityValidator",
    "validate_question",
    "check_vague_terms",
    "check_testwiseness",
    "check_distractor_quality",
    # IRT
    "IRTCalibrator",
    "IRTParameters",
    "DistractorMetrics",
    "QuestionPsychometrics",
    "get_empirical_difficulty",
    "should_use_empirical_difficulty",
]
