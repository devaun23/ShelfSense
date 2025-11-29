# Question Generation: Technical Implementation Specification

**Date**: 2025-11-29
**Purpose**: Provide code-level specifications for AI question generation pipeline
**Related**: `ADAPTIVE_ALGORITHM_QUESTION_REQUIREMENTS.md`

---

## 1. Question Schema with Enhanced Metadata

### 1.1 Complete Question Object

```python
# Example fully-populated question for adaptive algorithm
question = Question(
    id=str(uuid.uuid4()),
    specialty="internal_medicine",
    difficulty_level="medium",  # LLM-predicted
    source_type="ai_generated",
    content_status="active",

    # Clinical content
    vignette="""A 58-year-old man presents to the emergency department with 2 hours of crushing substernal chest pain radiating to his left arm. He describes associated nausea and diaphoresis. His medical history includes hypertension and type 2 diabetes. Vital signs: BP 145/92, HR 98, RR 18, O2 sat 96% on room air. Physical exam reveals diaphoresis but is otherwise unremarkable. ECG shows ST-segment elevation in leads V1-V4.""",

    choices=[
        "A. Obtain chest X-ray",
        "B. Start aspirin and arrange urgent cardiac catheterization",
        "C. Order troponin levels and observe",
        "D. Administer nitroglycerin and obtain stress test",
        "E. Start broad-spectrum antibiotics for sepsis"
    ],

    answer_key="B",

    explanation={
        "correct_answer": {
            "choice": "B",
            "reasoning": "This patient has ST-elevation myocardial infarction (STEMI) based on typical chest pain and ST elevations in contiguous leads (V1-V4, anterior wall). Primary percutaneous coronary intervention (PCI) is the gold standard treatment when available within 90 minutes. Aspirin should be administered immediately as antiplatelet therapy. Time is myocardium.",
            "key_concepts": [
                "STEMI diagnosis requires ST elevation in ≥2 contiguous leads",
                "Primary PCI preferred over thrombolytics if available within 90 minutes",
                "Aspirin 325mg is first-line antiplatelet therapy",
                "Door-to-balloon time goal: <90 minutes"
            ]
        },
        "distractors": {
            "A": "Chest X-ray is not urgent in confirmed STEMI. While it may be obtained, it delays definitive treatment. CXR is useful for diagnosing aortic dissection or pneumothorax if diagnosis is uncertain.",
            "C": "Troponin levels are not needed to diagnose STEMI when ECG shows ST elevation. Waiting for troponin results delays treatment. Troponins are used for NSTEMI diagnosis, not STEMI.",
            "D": "Stress test is contraindicated in acute MI. Nitroglycerin can provide symptomatic relief but does not replace urgent revascularization. This answer delays definitive treatment.",
            "E": "No signs of sepsis (no fever, no hypotension, no end-organ dysfunction). This would be harmful delay and inappropriate antibiotic use."
        },
        "clinical_pearl": "In STEMI, the mantra is 'time is muscle.' Every 30-minute delay in reperfusion increases 1-year mortality by 7.5%. Immediate aspirin + urgent PCI saves lives."
    },

    # ENHANCED METADATA (critical for adaptive algorithm)
    extra_data={
        # Topic taxonomy
        "topic": "cardiology",
        "subtopic": "acute_coronary_syndrome",

        # Cognitive classification
        "cognitive_level": "application",  # Applying ACS knowledge to clinical scenario
        "clinical_task": "next_step",      # Best next step in management

        # Concept tagging (for concept-based spaced repetition)
        "concepts": [
            "stemi_diagnosis",
            "stemi_ecg_criteria",
            "primary_pci",
            "antiplatelet_therapy",
            "time_sensitive_intervention"
        ],

        # Priority flagging
        "high_yield": True,  # ACS is high-yield Step 2 CK topic

        # Difficulty estimation metadata
        "estimated_p_value": 0.65,  # LLM predicts 65% will answer correctly
        "complexity_factors": [
            "straightforward_diagnosis",
            "classic_presentation",
            "clear_best_answer"
        ],

        # Question type classification
        "question_format": "best_next_step",  # vs "diagnosis", "mechanism", "EXCEPT", etc.
        "vignette_length": "medium",          # short, medium, long
        "requires_calculation": False,

        # Clinical context
        "patient_age_group": "middle_aged",
        "patient_sex": "male",
        "clinical_setting": "emergency_department",
        "acuity": "emergent",

        # Learning objectives
        "nbme_blueprint_alignment": "Cardiovascular System (15% of exam)",
        "learning_objectives": [
            "Recognize STEMI by ECG criteria",
            "Know time-sensitive nature of STEMI treatment",
            "Understand primary PCI vs thrombolysis decision"
        ],

        # Generation metadata
        "generated_at": "2025-11-29T10:30:00Z",
        "generation_model": "gpt-4o",
        "validation_status": "expert_approved",
        "validator_notes": "Excellent distractor quality, clear clinical scenario"
    }
)
```

### 1.2 Metadata Validation Schema

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
from datetime import datetime

class QuestionMetadata(BaseModel):
    """Enhanced metadata schema for adaptive algorithm support."""

    # Topic taxonomy (REQUIRED)
    topic: str = Field(
        ...,
        description="Body system from INTERNAL_MEDICINE_TOPICS",
        example="cardiology"
    )
    subtopic: str = Field(
        ...,
        description="Specific disease or clinical condition",
        example="acute_coronary_syndrome"
    )

    # Cognitive classification (REQUIRED)
    cognitive_level: Literal[
        "recall", "comprehension", "application",
        "analysis", "synthesis", "evaluation"
    ] = Field(
        ...,
        description="Bloom's taxonomy level",
        example="application"
    )

    clinical_task: Literal[
        "diagnosis", "next_step", "mechanism", "risk_factor",
        "complication", "treatment", "screening", "prognosis", "preventive_measure"
    ] = Field(
        ...,
        description="NBME clinical task category",
        example="next_step"
    )

    # Concept tagging (REQUIRED)
    concepts: List[str] = Field(
        ...,
        min_items=3,
        max_items=8,
        description="Medical concepts tested by this question",
        example=["stemi_diagnosis", "primary_pci", "antiplatelet_therapy"]
    )

    # Priority flagging (REQUIRED)
    high_yield: bool = Field(
        ...,
        description="Matches HIGH_YIELD_TOPICS list",
        example=True
    )

    # Difficulty estimation (OPTIONAL but recommended)
    estimated_p_value: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="LLM-predicted proportion correct (0.0-1.0)",
        example=0.65
    )

    complexity_factors: Optional[List[str]] = Field(
        None,
        description="Factors affecting difficulty",
        example=["straightforward_diagnosis", "classic_presentation"]
    )

    # Question format (OPTIONAL but useful)
    question_format: Optional[str] = Field(
        None,
        description="Question stem type",
        example="best_next_step"
    )

    vignette_length: Optional[Literal["short", "medium", "long"]] = Field(
        None,
        description="Clinical vignette length category"
    )

    requires_calculation: Optional[bool] = Field(
        False,
        description="Does question require mathematical calculation?"
    )

    # Clinical context (OPTIONAL)
    patient_age_group: Optional[str] = Field(None, example="middle_aged")
    patient_sex: Optional[str] = Field(None, example="male")
    clinical_setting: Optional[str] = Field(None, example="emergency_department")
    acuity: Optional[Literal["emergent", "urgent", "routine"]] = Field(None)

    # Validation
    @validator('topic')
    def topic_must_be_valid(cls, v):
        VALID_TOPICS = [
            "cardiology", "pulmonology", "gastroenterology", "nephrology",
            "endocrinology", "hematology", "oncology", "infectious_disease",
            "rheumatology", "neurology", "psychiatry", "dermatology",
            "preventive_medicine"
        ]
        if v not in VALID_TOPICS:
            raise ValueError(f"Topic must be one of {VALID_TOPICS}")
        return v

    @validator('concepts')
    def concepts_must_be_snake_case(cls, v):
        for concept in v:
            if not concept.replace('_', '').isalnum() or ' ' in concept:
                raise ValueError(f"Concept '{concept}' must be snake_case")
        return v


# Usage in question generation
def validate_generated_question(question_data: dict) -> bool:
    """Validate generated question has required metadata."""
    try:
        metadata = QuestionMetadata(**question_data.get('extra_data', {}))
        return True
    except Exception as e:
        logger.error(f"Question validation failed: {e}")
        return False
```

---

## 2. AI Generation Prompt Templates

### 2.1 Master Question Generation Prompt

```python
QUESTION_GENERATION_PROMPT = """You are an expert medical educator creating USMLE Step 2 CK questions for Internal Medicine.

Generate a high-quality clinical vignette question with the following specifications:

**Topic**: {topic}
**Subtopic**: {subtopic}
**Difficulty**: {difficulty}
**Clinical Task**: {clinical_task}
**Cognitive Level**: {cognitive_level}

**Requirements**:

1. **Clinical Vignette**:
   - Realistic patient presentation
   - Include: age, sex, chief complaint, relevant history, physical exam, vitals
   - Length: 4-6 sentences for medium difficulty
   - Include key clinical findings that point to correct diagnosis
   - Add 1-2 subtle findings that distractors might miss

2. **Answer Choices**:
   - Exactly 5 choices (A through E)
   - One correct answer
   - Four plausible distractors that test common misconceptions
   - Distractors should be:
     * Partially correct but not the BEST answer
     * Common mistakes students make
     * Similar conditions in differential diagnosis
     * Correct for different clinical scenario
   - Avoid "all of the above" or "none of the above"

3. **Explanation Structure** (CRITICAL):
   ```json
   {{
     "correct_answer": {{
       "choice": "B",
       "reasoning": "Why this is the correct answer (3-4 sentences)",
       "key_concepts": ["Concept 1", "Concept 2", "Concept 3"]
     }},
     "distractors": {{
       "A": "Why this is wrong (1-2 sentences)",
       "C": "Why this is wrong",
       "D": "Why this is wrong",
       "E": "Why this is wrong"
     }},
     "clinical_pearl": "High-yield teaching point (1 sentence)"
   }}
   ```

4. **Metadata** (include in response):
   - `concepts`: List 3-5 medical concepts this question tests (snake_case)
   - `estimated_p_value`: Predict proportion correct (0.0-1.0)
   - `complexity_factors`: What makes this easy/medium/hard?
   - `high_yield`: Is this a high-yield Step 2 CK topic? (true/false)

**Clinical Task Guidelines**:

- **diagnosis**: "What is the most likely diagnosis?"
- **next_step**: "What is the best next step in management/workup?"
- **mechanism**: "What is the underlying mechanism?"
- **treatment**: "What is the most appropriate treatment?"

**Difficulty Calibration**:

- **Easy** (p-value 0.70-0.85):
  * Classic presentation
  * Straightforward diagnosis
  * Clear best answer
  * Obvious incorrect distractors

- **Medium** (p-value 0.55-0.70):
  * Typical presentation with 1-2 complicating factors
  * Requires integrating multiple findings
  * Distractors are plausible alternatives
  * Tests application of knowledge

- **Hard** (p-value 0.40-0.55):
  * Atypical presentation or rare condition
  * Multiple valid-sounding options
  * Requires synthesis of complex information
  * Tests clinical judgment under uncertainty

**Example Output Format**:

```json
{{
  "vignette": "A 58-year-old man presents to the emergency department with...",
  "choices": [
    "A. Obtain chest X-ray",
    "B. Start aspirin and arrange urgent cardiac catheterization",
    "C. Order troponin levels and observe",
    "D. Administer nitroglycerin and obtain stress test",
    "E. Start broad-spectrum antibiotics for sepsis"
  ],
  "answer_key": "B",
  "explanation": {{
    "correct_answer": {{
      "choice": "B",
      "reasoning": "...",
      "key_concepts": ["...", "..."]
    }},
    "distractors": {{
      "A": "...",
      "C": "...",
      "D": "...",
      "E": "..."
    }},
    "clinical_pearl": "..."
  }},
  "metadata": {{
    "concepts": ["stemi_diagnosis", "primary_pci", "antiplatelet_therapy"],
    "estimated_p_value": 0.65,
    "complexity_factors": ["classic_presentation", "clear_best_answer"],
    "high_yield": true
  }}
}}
```

Generate the question now.
"""

# Usage
async def generate_question_with_llm(
    topic: str,
    subtopic: str,
    difficulty: str,
    clinical_task: str,
    cognitive_level: str
) -> dict:
    """Generate question using LLM with structured prompt."""

    prompt = QUESTION_GENERATION_PROMPT.format(
        topic=topic,
        subtopic=subtopic,
        difficulty=difficulty,
        clinical_task=clinical_task,
        cognitive_level=cognitive_level
    )

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert medical educator."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.7  # Some creativity but not too random
    )

    question_data = json.loads(response.choices[0].message.content)

    # Add full metadata
    question_data['extra_data'] = {
        "topic": topic,
        "subtopic": subtopic,
        "cognitive_level": cognitive_level,
        "clinical_task": clinical_task,
        **question_data.get('metadata', {})
    }

    # Validate metadata
    if not validate_generated_question(question_data):
        raise ValueError("Generated question failed validation")

    return question_data
```

### 2.2 Concept Variation Prompt

```python
CONCEPT_VARIATION_PROMPT = """You are creating a VARIATION of an existing medical question to test the same concept with a different clinical presentation.

**Original Question**:
{original_vignette}

**Concept Being Tested**: {concept}

**Variation Instructions**:

Create a DIFFERENT clinical scenario that tests the SAME medical concept. You must:

1. **Change at least 3 of these elements**:
   - Patient demographics (age, sex)
   - Chief complaint wording
   - Clinical presentation details
   - Physical exam findings (while keeping diagnostic findings)
   - Setting (ED, clinic, inpatient, ICU)

2. **Keep the same**:
   - Core concept being tested
   - Diagnostic criteria / pathognomonic findings
   - Correct answer category (e.g., both should be "PCI", not one PCI and one thrombolysis)
   - Difficulty level

3. **Variation Types** (choose one):
   - **Atypical presentation**: Same disease, unusual symptoms (e.g., silent MI in diabetic)
   - **Different demographics**: Elderly, pregnant, pediatric presentation
   - **Different setting**: Outpatient vs ED vs ICU
   - **Earlier/later stage**: Prodrome vs established vs complication phase
   - **Diagnostic modality focus**: Clinical diagnosis vs lab-based vs imaging-based

**Example**:
- **Original**: "45yo M with crushing chest pain and ST elevations → diagnose STEMI"
- **Variation 1 (atypical)**: "70yo diabetic F with dyspnea and nausea, no chest pain, ST elevations → diagnose STEMI"
- **Variation 2 (setting)**: "62yo M in recovery room post-op with chest pain and ST elevations → diagnose STEMI"
- **Variation 3 (complication)**: "Patient with STEMI s/p PCI develops new systolic murmur → diagnose VSD"

Generate the variation now.
"""
```

---

## 3. Batch Generation Pipeline

### 3.1 Question Distribution Calculator

```python
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class GenerationTarget:
    """Target distribution for question generation."""
    topic: str
    subtopic: str
    count: int
    difficulty_distribution: Dict[str, int]
    task_distribution: Dict[str, int]

class QuestionBankPlanner:
    """Calculate optimal question distribution for bank generation."""

    # Target distributions from ADAPTIVE_ALGORITHM_QUESTION_REQUIREMENTS.md
    TOPIC_DISTRIBUTION_800 = {
        "cardiology": 120,
        "infectious_disease": 96,
        "gastroenterology": 80,
        "pulmonology": 64,
        "nephrology": 64,
        "endocrinology": 64,
        "neurology": 64,
        "hematology": 48,
        "psychiatry": 48,
        "rheumatology": 40,
        "oncology": 40,
        "dermatology": 32,
        "preventive_medicine": 40
    }

    SUBTOPIC_DISTRIBUTION = {
        "cardiology": {
            "acute_coronary_syndrome": 18,
            "heart_failure": 15,
            "arrhythmias": 12,
            "valvular_disease": 10,
            "hypertension": 10,
            "dyslipidemia": 8,
            "pericardial_disease": 8,
            "cardiomyopathy": 8,
            "peripheral_vascular": 6,
            "congenital_heart_disease": 5,
            "endocarditis": 5,
            "syncope": 5,
            "shock": 5,
            "other": 5
        },
        # ... define for all topics
    }

    DIFFICULTY_DISTRIBUTION = {
        "easy": 0.25,
        "medium": 0.50,
        "hard": 0.25
    }

    TASK_DISTRIBUTION = {
        "diagnosis": 0.40,
        "next_step": 0.30,
        "treatment": 0.20,
        "mechanism": 0.05,
        "other": 0.05
    }

    COGNITIVE_DISTRIBUTION = {
        "recall": 0.15,
        "comprehension": 0.20,
        "application": 0.30,
        "analysis": 0.20,
        "synthesis": 0.10,
        "evaluation": 0.05
    }

    def generate_targets(self, target_total: int = 800) -> List[GenerationTarget]:
        """
        Generate question targets with proper distribution.

        Returns list of GenerationTarget objects specifying exactly what to generate.
        """
        targets = []

        for topic, topic_count in self.TOPIC_DISTRIBUTION_800.items():
            subtopics = self.SUBTOPIC_DISTRIBUTION.get(topic, {topic: topic_count})

            for subtopic, subtopic_count in subtopics.items():
                # Calculate difficulty distribution for this subtopic
                difficulty_dist = {
                    "easy": int(subtopic_count * self.DIFFICULTY_DISTRIBUTION["easy"]),
                    "medium": int(subtopic_count * self.DIFFICULTY_DISTRIBUTION["medium"]),
                    "hard": int(subtopic_count * self.DIFFICULTY_DISTRIBUTION["hard"])
                }

                # Adjust for rounding
                total_assigned = sum(difficulty_dist.values())
                if total_assigned < subtopic_count:
                    difficulty_dist["medium"] += (subtopic_count - total_assigned)

                # Calculate task distribution
                task_dist = {
                    "diagnosis": int(subtopic_count * self.TASK_DISTRIBUTION["diagnosis"]),
                    "next_step": int(subtopic_count * self.TASK_DISTRIBUTION["next_step"]),
                    "treatment": int(subtopic_count * self.TASK_DISTRIBUTION["treatment"]),
                    "mechanism": int(subtopic_count * self.TASK_DISTRIBUTION["mechanism"]),
                    "screening": subtopic_count - sum([
                        int(subtopic_count * v) for v in list(self.TASK_DISTRIBUTION.values())[:-1]
                    ])
                }

                targets.append(GenerationTarget(
                    topic=topic,
                    subtopic=subtopic,
                    count=subtopic_count,
                    difficulty_distribution=difficulty_dist,
                    task_distribution=task_dist
                ))

        return targets

    def export_generation_plan(self, output_file: str = "generation_plan.json"):
        """Export detailed generation plan to JSON."""
        targets = self.generate_targets()

        plan = {
            "total_questions": sum(t.count for t in targets),
            "topics": {},
            "generation_tasks": []
        }

        for target in targets:
            # Group by topic
            if target.topic not in plan["topics"]:
                plan["topics"][target.topic] = {
                    "total": 0,
                    "subtopics": {}
                }

            plan["topics"][target.topic]["total"] += target.count
            plan["topics"][target.topic]["subtopics"][target.subtopic] = {
                "count": target.count,
                "difficulties": target.difficulty_distribution,
                "tasks": target.task_distribution
            }

            # Create generation tasks
            for difficulty, diff_count in target.difficulty_distribution.items():
                for task, task_count in target.task_distribution.items():
                    # Proportional allocation
                    count = int((task_count / target.count) * diff_count)
                    if count > 0:
                        plan["generation_tasks"].append({
                            "topic": target.topic,
                            "subtopic": target.subtopic,
                            "difficulty": difficulty,
                            "clinical_task": task,
                            "count": count
                        })

        with open(output_file, 'w') as f:
            json.dump(plan, f, indent=2)

        return plan


# Usage
planner = QuestionBankPlanner()
plan = planner.export_generation_plan("backend/data/generation_plan_800.json")

print(f"Total questions: {plan['total_questions']}")
print(f"Total generation tasks: {len(plan['generation_tasks'])}")
```

### 3.2 Parallel Batch Generation

```python
import asyncio
from typing import List
import logging

logger = logging.getLogger(__name__)

class QuestionBatchGenerator:
    """Parallel question generation with rate limiting and error handling."""

    def __init__(self, max_concurrent: int = 10, delay_seconds: float = 1.0):
        self.max_concurrent = max_concurrent
        self.delay_seconds = delay_seconds
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def generate_batch(
        self,
        generation_tasks: List[dict],
        output_file: str = "generated_questions.jsonl"
    ) -> Dict[str, Any]:
        """
        Generate questions in parallel batches with rate limiting.

        Args:
            generation_tasks: List of task specs from generation plan
            output_file: JSONL file to write results

        Returns:
            Summary statistics
        """
        results = {
            "total_requested": len(generation_tasks),
            "successful": 0,
            "failed": 0,
            "errors": []
        }

        async def generate_with_semaphore(task: dict, task_id: int):
            """Generate single question with concurrency control."""
            async with self.semaphore:
                try:
                    logger.info(
                        f"[Task {task_id}/{len(generation_tasks)}] "
                        f"Generating {task['topic']}/{task['subtopic']} "
                        f"({task['difficulty']}, {task['clinical_task']})"
                    )

                    # Generate question
                    question_data = await generate_question_with_llm(
                        topic=task['topic'],
                        subtopic=task['subtopic'],
                        difficulty=task['difficulty'],
                        clinical_task=task['clinical_task'],
                        cognitive_level=self._select_cognitive_level()
                    )

                    # Validate
                    if not validate_generated_question(question_data):
                        raise ValueError("Generated question failed validation")

                    # Write to JSONL (atomic append)
                    async with aiofiles.open(output_file, 'a') as f:
                        await f.write(json.dumps(question_data) + '\n')

                    results["successful"] += 1
                    logger.info(f"[Task {task_id}] SUCCESS")

                    # Rate limiting delay
                    await asyncio.sleep(self.delay_seconds)

                except Exception as e:
                    results["failed"] += 1
                    error_msg = f"Task {task_id} failed: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)

        # Execute all tasks in parallel with semaphore control
        tasks = [
            generate_with_semaphore(task, i)
            for i, task in enumerate(generation_tasks, start=1)
        ]

        await asyncio.gather(*tasks)

        # Log summary
        logger.info(
            f"\nGeneration Complete:\n"
            f"  Requested: {results['total_requested']}\n"
            f"  Successful: {results['successful']}\n"
            f"  Failed: {results['failed']}\n"
            f"  Success Rate: {results['successful']/results['total_requested']*100:.1f}%"
        )

        return results

    def _select_cognitive_level(self) -> str:
        """Select cognitive level based on target distribution."""
        return random.choices(
            population=list(QuestionBankPlanner.COGNITIVE_DISTRIBUTION.keys()),
            weights=list(QuestionBankPlanner.COGNITIVE_DISTRIBUTION.values()),
            k=1
        )[0]


# Usage
async def main():
    # Load generation plan
    with open("backend/data/generation_plan_800.json") as f:
        plan = json.load(f)

    # Generate questions
    generator = QuestionBatchGenerator(max_concurrent=10, delay_seconds=2.0)
    results = await generator.generate_batch(
        generation_tasks=plan["generation_tasks"],
        output_file="backend/data/generated_questions_800.jsonl"
    )

    print(f"Generation complete: {results['successful']}/{results['total_requested']} successful")

# Run
asyncio.run(main())
```

---

## 4. Quality Validation Pipeline

### 4.1 Pre-Deployment Validation

```python
from app.services.elite_quality_validator import EliteQualityValidator
from app.services.medical_fact_checker import MedicalFactChecker

class QuestionQualityPipeline:
    """Multi-stage quality validation before database insertion."""

    def __init__(self, db: Session):
        self.db = db
        self.quality_validator = EliteQualityValidator()
        self.fact_checker = MedicalFactChecker()

    async def validate_question(self, question_data: dict) -> Dict[str, Any]:
        """
        Run comprehensive validation on generated question.

        Returns validation result with pass/fail and recommendations.
        """
        results = {
            "question_id": question_data.get("id"),
            "overall_status": "pending",
            "quality_score": 0,
            "checks": {},
            "recommendations": []
        }

        # Stage 1: Schema Validation
        try:
            metadata = QuestionMetadata(**question_data.get('extra_data', {}))
            results["checks"]["schema"] = {"status": "pass", "score": 10}
        except Exception as e:
            results["checks"]["schema"] = {"status": "fail", "error": str(e), "score": 0}
            results["recommendations"].append("Fix metadata schema errors")
            results["overall_status"] = "fail"
            return results

        # Stage 2: Content Quality (Elite Validator)
        quality_result = await self.quality_validator.validate(question_data)
        results["checks"]["content_quality"] = {
            "status": "pass" if quality_result["is_valid"] else "fail",
            "score": quality_result.get("quality_score", 0),
            "issues": quality_result.get("issues", [])
        }
        if quality_result.get("issues"):
            results["recommendations"].extend(quality_result["suggestions"])

        # Stage 3: Medical Accuracy (Fact Checker)
        fact_check_result = await self.fact_checker.verify(
            vignette=question_data["vignette"],
            correct_answer=question_data["answer_key"],
            explanation=question_data["explanation"]
        )
        results["checks"]["medical_accuracy"] = {
            "status": "pass" if fact_check_result["accurate"] else "warning",
            "score": 15 if fact_check_result["accurate"] else 10,
            "confidence": fact_check_result.get("confidence"),
            "flags": fact_check_result.get("flags", [])
        }

        # Stage 4: Distractor Quality
        distractor_score = self._validate_distractors(question_data)
        results["checks"]["distractors"] = {
            "status": "pass" if distractor_score >= 15 else "warning",
            "score": distractor_score
        }

        # Stage 5: Explanation Quality
        explanation_score = self._validate_explanation(question_data)
        results["checks"]["explanation"] = {
            "status": "pass" if explanation_score >= 15 else "warning",
            "score": explanation_score
        }

        # Calculate overall quality score
        results["quality_score"] = sum(
            check.get("score", 0) for check in results["checks"].values()
        )

        # Determine overall status
        if results["quality_score"] >= 60:
            results["overall_status"] = "approved"
        elif results["quality_score"] >= 40:
            results["overall_status"] = "needs_review"
        else:
            results["overall_status"] = "rejected"

        return results

    def _validate_distractors(self, question_data: dict) -> int:
        """
        Validate distractor quality (0-20 points).

        Checks:
        - Exactly 4 distractors (1 correct + 4 wrong = 5 total)
        - All distractors have explanations
        - Distractors are plausible (not obviously wrong)
        - Distractors test common misconceptions
        """
        score = 20

        choices = question_data.get("choices", [])
        if len(choices) != 5:
            score -= 10

        explanation = question_data.get("explanation", {})
        distractors = explanation.get("distractors", {})

        # Check all wrong answers have explanations
        answer_key = question_data.get("answer_key")
        expected_distractors = [c[0] for c in choices if c[0] != answer_key]

        for choice in expected_distractors:
            if choice not in distractors or not distractors[choice]:
                score -= 3  # Missing or empty distractor explanation

        # Check distractor explanation quality
        for choice, explanation_text in distractors.items():
            if len(explanation_text) < 20:  # Too short
                score -= 2
            if "wrong" not in explanation_text.lower() and "not" not in explanation_text.lower():
                score -= 1  # Doesn't explain WHY it's wrong

        return max(0, score)

    def _validate_explanation(self, question_data: dict) -> int:
        """
        Validate explanation quality (0-20 points).

        Checks:
        - Correct answer has detailed reasoning
        - Key concepts listed (3-5)
        - Clinical pearl present
        - Framework-based (not just "A is correct")
        """
        score = 20

        explanation = question_data.get("explanation", {})
        correct = explanation.get("correct_answer", {})

        # Check reasoning quality
        reasoning = correct.get("reasoning", "")
        if len(reasoning) < 100:  # Too brief
            score -= 5
        if not any(keyword in reasoning.lower() for keyword in ["because", "since", "due to", "as"]):
            score -= 3  # No causal reasoning

        # Check key concepts
        key_concepts = correct.get("key_concepts", [])
        if len(key_concepts) < 3:
            score -= 4
        elif len(key_concepts) > 8:
            score -= 2  # Too many concepts

        # Check clinical pearl
        clinical_pearl = explanation.get("clinical_pearl", "")
        if not clinical_pearl or len(clinical_pearl) < 20:
            score -= 3

        return max(0, score)


# Usage
async def validate_batch(input_file: str, output_file: str):
    """Validate all generated questions and filter by quality."""

    validator = QuestionQualityPipeline(db)
    approved = []
    needs_review = []
    rejected = []

    with open(input_file, 'r') as f:
        for line in f:
            question_data = json.loads(line)

            validation_result = await validator.validate_question(question_data)

            if validation_result["overall_status"] == "approved":
                approved.append(question_data)
            elif validation_result["overall_status"] == "needs_review":
                needs_review.append({
                    "question": question_data,
                    "validation": validation_result
                })
            else:
                rejected.append({
                    "question": question_data,
                    "validation": validation_result
                })

    # Write approved questions
    with open(output_file, 'w') as f:
        for q in approved:
            f.write(json.dumps(q) + '\n')

    # Write review queue
    with open(output_file.replace('.jsonl', '_review.json'), 'w') as f:
        json.dump(needs_review, f, indent=2)

    # Log summary
    logger.info(
        f"\nValidation Summary:\n"
        f"  Approved: {len(approved)}\n"
        f"  Needs Review: {len(needs_review)}\n"
        f"  Rejected: {len(rejected)}\n"
        f"  Approval Rate: {len(approved)/(len(approved)+len(needs_review)+len(rejected))*100:.1f}%"
    )

    return {
        "approved": len(approved),
        "needs_review": len(needs_review),
        "rejected": len(rejected)
    }
```

---

## 5. Database Import Pipeline

### 5.1 Bulk Import with Transaction Safety

```python
from sqlalchemy.orm import Session
from app.models.models import Question, ContentVersion
from typing import List
import logging

logger = logging.getLogger(__name__)

class QuestionImporter:
    """Safe bulk import of validated questions to database."""

    def __init__(self, db: Session):
        self.db = db

    def import_batch(
        self,
        questions_file: str,
        batch_size: int = 100,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Import questions from JSONL file with transaction safety.

        Args:
            questions_file: Path to validated questions JSONL
            batch_size: Questions per transaction batch
            dry_run: If True, validate but don't commit

        Returns:
            Import statistics
        """
        stats = {
            "total_processed": 0,
            "successful": 0,
            "duplicates": 0,
            "errors": [],
            "imported_ids": []
        }

        with open(questions_file, 'r') as f:
            batch = []

            for line_num, line in enumerate(f, start=1):
                try:
                    question_data = json.loads(line)

                    # Check for duplicates (by vignette hash)
                    vignette_hash = hashlib.md5(
                        question_data["vignette"].encode()
                    ).hexdigest()

                    existing = self.db.query(Question).filter(
                        Question.extra_data['vignette_hash'].astext == vignette_hash
                    ).first()

                    if existing:
                        stats["duplicates"] += 1
                        logger.warning(f"Line {line_num}: Duplicate question (hash: {vignette_hash})")
                        continue

                    # Create Question object
                    question = Question(
                        id=str(uuid.uuid4()),
                        specialty=question_data.get("specialty", "internal_medicine"),
                        difficulty_level=question_data.get("difficulty_level", "medium"),
                        source_type="ai_generated",
                        content_status="active",
                        vignette=question_data["vignette"],
                        choices=question_data["choices"],
                        answer_key=question_data["answer_key"],
                        explanation=question_data["explanation"],
                        extra_data={
                            **question_data.get("extra_data", {}),
                            "vignette_hash": vignette_hash,
                            "imported_at": datetime.utcnow().isoformat(),
                            "batch_id": questions_file
                        },
                        created_at=datetime.utcnow()
                    )

                    batch.append(question)
                    stats["total_processed"] += 1

                    # Commit in batches
                    if len(batch) >= batch_size:
                        self._commit_batch(batch, dry_run, stats)
                        batch = []

                except Exception as e:
                    error_msg = f"Line {line_num}: {str(e)}"
                    stats["errors"].append(error_msg)
                    logger.error(error_msg)

            # Commit remaining questions
            if batch:
                self._commit_batch(batch, dry_run, stats)

        logger.info(
            f"\nImport Summary:\n"
            f"  Processed: {stats['total_processed']}\n"
            f"  Successful: {stats['successful']}\n"
            f"  Duplicates Skipped: {stats['duplicates']}\n"
            f"  Errors: {len(stats['errors'])}\n"
            f"  Dry Run: {dry_run}"
        )

        return stats

    def _commit_batch(
        self,
        batch: List[Question],
        dry_run: bool,
        stats: dict
    ):
        """Commit batch with transaction safety."""
        try:
            self.db.add_all(batch)

            if not dry_run:
                self.db.commit()
                stats["successful"] += len(batch)
                stats["imported_ids"].extend([q.id for q in batch])
                logger.info(f"Committed batch of {len(batch)} questions")
            else:
                self.db.rollback()
                logger.info(f"DRY RUN: Would commit {len(batch)} questions")

        except Exception as e:
            self.db.rollback()
            error_msg = f"Batch commit failed: {str(e)}"
            stats["errors"].append(error_msg)
            logger.error(error_msg)


# Usage
def run_import():
    """Execute full import pipeline."""
    from app.database import get_db

    db = next(get_db())
    importer = QuestionImporter(db)

    # Dry run first
    logger.info("Starting DRY RUN...")
    dry_stats = importer.import_batch(
        "backend/data/generated_questions_800_approved.jsonl",
        batch_size=100,
        dry_run=True
    )

    if dry_stats["errors"]:
        logger.error(f"Dry run found {len(dry_stats['errors'])} errors. Aborting import.")
        return

    # Actual import
    logger.info("\nStarting ACTUAL IMPORT...")
    input("Press Enter to proceed with import or Ctrl+C to cancel...")

    stats = importer.import_batch(
        "backend/data/generated_questions_800_approved.jsonl",
        batch_size=100,
        dry_run=False
    )

    logger.info(f"\nImport complete: {stats['successful']} questions imported")
    return stats
```

---

## 6. Post-Import Quality Monitoring

### 6.1 IRT Calibration Job

```python
from app.services.item_response_theory import IRTCalibrator

class PostImportMonitoring:
    """Monitor and calibrate imported questions as users answer them."""

    def __init__(self, db: Session):
        self.db = db
        self.calibrator = IRTCalibrator(db)

    async def run_weekly_calibration(self):
        """
        Weekly batch job to calibrate questions with sufficient responses.

        Identifies questions ready for IRT calibration (50+ responses) and
        updates their difficulty_level based on empirical performance.
        """
        # Get calibration candidates
        candidates = self.calibrator.get_calibration_candidates(limit=500)

        logger.info(f"Found {len(candidates)} questions ready for calibration")

        results = self.calibrator.batch_calibrate(candidates)

        # Log recalibrations
        for question_id, new_difficulty in results.items():
            question = self.db.query(Question).filter(Question.id == question_id).first()
            old_difficulty = question.difficulty_level

            logger.info(
                f"Recalibrated {question_id}: {old_difficulty} → {new_difficulty}"
            )

        # Generate quality report
        self._generate_quality_report(results)

        return results

    def _generate_quality_report(self, calibration_results: Dict[str, str]):
        """Generate report of question quality issues."""

        issues = {
            "negative_discrimination": [],
            "low_discrimination": [],
            "too_easy": [],
            "too_hard": []
        }

        for question_id in calibration_results.keys():
            psychometrics = self.calibrator.get_full_psychometrics(question_id)

            if not psychometrics:
                continue

            # Check for issues
            if psychometrics.irt_params.discrimination_index < 0:
                issues["negative_discrimination"].append(question_id)
            elif psychometrics.irt_params.discrimination_index < 0.20:
                issues["low_discrimination"].append(question_id)

            if psychometrics.irt_params.p_value > 0.90:
                issues["too_easy"].append(question_id)
            elif psychometrics.irt_params.p_value < 0.30:
                issues["too_hard"].append(question_id)

        # Log summary
        logger.warning(
            f"\nQuality Issues Found:\n"
            f"  Negative Discrimination: {len(issues['negative_discrimination'])}\n"
            f"  Low Discrimination: {len(issues['low_discrimination'])}\n"
            f"  Too Easy (>90%): {len(issues['too_easy'])}\n"
            f"  Too Hard (<30%): {len(issues['too_hard'])}"
        )

        # Flag questions for review
        for question_id in issues["negative_discrimination"]:
            question = self.db.query(Question).filter(Question.id == question_id).first()
            question.content_status = "needs_review"
            question.extra_data = {
                **question.extra_data,
                "quality_flags": ["NEGATIVE_DISCRIMINATION"],
                "flagged_at": datetime.utcnow().isoformat()
            }

        self.db.commit()

        return issues
```

---

## Summary

This technical specification provides:

1. **Complete metadata schema** with validation
2. **AI generation prompts** tuned for USMLE Step 2 CK quality
3. **Batch generation pipeline** for parallel question creation
4. **Quality validation** with multi-stage checks
5. **Safe database import** with transaction management
6. **Post-import monitoring** with IRT calibration

**Key Implementation Files**:
- `/Users/devaun/ShelfSense/backend/docs/ADAPTIVE_ALGORITHM_QUESTION_REQUIREMENTS.md` - Requirements
- `/Users/devaun/ShelfSense/backend/docs/QUESTION_GENERATION_TECHNICAL_SPEC.md` - This file (implementation)

**Next Steps**:
1. Review and approve metadata schema additions
2. Test AI generation prompts with sample topics
3. Run batch generation for first 100 questions (pilot)
4. Validate pilot batch and refine prompts
5. Scale to full 800-question Phase 1 target

---

**Document Version**: 1.0
**Last Updated**: 2025-11-29
