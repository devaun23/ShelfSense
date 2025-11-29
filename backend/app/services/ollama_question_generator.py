"""
Ollama Question Generator

Uses local Llama model (via Ollama) to generate USMLE Step 2 CK questions
at ZERO API cost. Questions are then validated by Claude/GPT-4.

Usage:
    from app.services.ollama_question_generator import OllamaQuestionGenerator

    generator = OllamaQuestionGenerator(db)
    questions = await generator.generate_for_gap("cardiovascular", "diagnosis", count=5)
"""

import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from app.services.ollama_service import ollama_service, OllamaNotAvailableError
from app.models.models import Question

logger = logging.getLogger(__name__)


# Curriculum-specific prompts
SYSTEM_CONTEXTS = {
    "cardiovascular": """Focus on: acute coronary syndromes, heart failure, arrhythmias,
        valvular disease, hypertension, peripheral vascular disease, DVT/PE.
        Include: ECG findings, cardiac enzymes, BNP, echocardiogram findings.""",

    "respiratory": """Focus on: pneumonia, COPD exacerbation, asthma, pulmonary embolism,
        lung cancer, pleural effusion, ARDS, OSA.
        Include: chest X-ray findings, ABG interpretation, PFT results.""",

    "gastrointestinal": """Focus on: GI bleeding, hepatitis, cirrhosis, pancreatitis,
        bowel obstruction, IBD, PUD, cholecystitis.
        Include: LFTs, lipase, imaging findings, endoscopy results.""",

    "renal_urinary_reproductive": """Focus on: AKI, CKD, UTI, nephrolithiasis, glomerulonephritis,
        BPH, prostate cancer, STIs, contraception.
        Include: urinalysis, creatinine, GFR, electrolytes.""",

    "nervous_system": """Focus on: stroke, seizure, meningitis, headache syndromes,
        dementia, Parkinson's, MS, peripheral neuropathy.
        Include: neurologic exam findings, CT/MRI findings, LP results.""",

    "musculoskeletal_skin": """Focus on: fractures, joint pain, back pain, rheumatoid arthritis,
        gout, osteoporosis, skin cancer, dermatitis.
        Include: X-ray findings, inflammatory markers, skin exam findings.""",

    "endocrine": """Focus on: diabetes management, thyroid disorders, adrenal insufficiency,
        pituitary disorders, calcium disorders.
        Include: HbA1c, TSH, cortisol, calcium, PTH levels.""",

    "behavioral_health": """Focus on: major depression, anxiety disorders, bipolar disorder,
        schizophrenia, substance use disorders, personality disorders.
        Include: mental status exam, screening tools, medication management.""",

    "immune": """Focus on: HIV/AIDS, allergic reactions, anaphylaxis, autoimmune disorders,
        immunodeficiency, transplant rejection.
        Include: CD4 count, viral load, allergy testing, autoantibodies.""",

    "blood_lymph": """Focus on: anemia (iron, B12, folate, hemolytic), thrombocytopenia,
        leukemia, lymphoma, bleeding disorders, anticoagulation.
        Include: CBC, peripheral smear, coagulation studies, bone marrow findings.""",

    "pregnancy_ob": """Focus on: prenatal care, gestational diabetes, preeclampsia,
        labor and delivery, postpartum complications, ectopic pregnancy.
        Include: gestational age, fetal monitoring, ultrasound findings.""",

    "biostatistics_epi": """Focus on: study design interpretation, screening test properties,
        confidence intervals, p-values, NNT, relative risk, odds ratio.
        Present data in table or figure format requiring calculation.""",

    "social_sciences_ethics": """Focus on: informed consent, capacity determination,
        end-of-life decisions, confidentiality, mandatory reporting,
        medical errors, quality improvement, patient safety.
        Present ethical dilemmas requiring professional judgment.""",

    "human_development": """Focus on: well-child visits, developmental milestones,
        adolescent health, preventive care by age, geriatric syndromes.
        Include age-appropriate screening and counseling.""",

    "multisystem": """Focus on: sepsis, shock, trauma, DKA, electrolyte emergencies,
        fever of unknown origin, unintentional weight loss.
        Include multi-organ assessment and stabilization priorities.""",
}

TASK_STEMS = {
    "diagnosis": [
        "Which of the following is the most likely diagnosis?",
        "What is the most likely cause of this patient's symptoms?",
        "Which of the following best explains these findings?",
    ],
    "lab_diagnostic": [
        "Which of the following is the most appropriate next step in evaluation?",
        "Which diagnostic test should be ordered next?",
        "What is the most appropriate initial workup?",
    ],
    "mixed_management": [
        "Which of the following is the most appropriate next step in management?",
        "What is the best initial management for this patient?",
        "Which of the following is the most appropriate treatment?",
    ],
    "pharmacotherapy": [
        "Which medication is most appropriate for this patient?",
        "Which of the following drugs should be initiated?",
        "What is the first-line pharmacologic treatment?",
    ],
    "clinical_interventions": [
        "Which procedure is indicated for this patient?",
        "What surgical intervention is most appropriate?",
        "Which of the following interventions should be performed?",
    ],
    "health_maintenance": [
        "Which screening test is recommended for this patient?",
        "What preventive measure should be discussed?",
        "Which immunization is indicated?",
    ],
    "prognosis": [
        "What is the most likely complication of this condition?",
        "Which of the following is the expected outcome without treatment?",
        "What is the most significant risk factor for poor prognosis?",
    ],
    "professionalism": [
        "What is the most appropriate response to this situation?",
        "How should you address this ethical concern?",
        "What is the best way to communicate with this patient?",
    ],
    "systems_practice": [
        "Which quality improvement measure would address this issue?",
        "What is the most appropriate next step regarding patient safety?",
        "How should this care transition be managed?",
    ],
    "practice_learning": [
        "Based on the study described, which conclusion is most supported?",
        "What is the most significant limitation of this study?",
        "How should these research findings affect clinical practice?",
    ],
}


class OllamaQuestionGenerator:
    """
    Generates USMLE Step 2 CK questions using local Llama model.

    Cost: $0 (runs locally via Ollama)
    Quality: Good enough for bulk generation, requires validation
    Speed: ~30-60 seconds per question on M1/M2 Mac
    """

    def __init__(self, db: Session, model: str = "llama3.2:3b"):
        self.db = db
        self.model = model
        self._generation_count = 0

    async def generate_for_gap(
        self,
        system: str,
        task: str,
        discipline: str = "internal_medicine",
        count: int = 5,
        difficulty: str = "medium"
    ) -> List[Dict[str, Any]]:
        """
        Generate questions for a specific curriculum gap.

        Args:
            system: Body system (e.g., "cardiovascular")
            task: Physician task (e.g., "diagnosis")
            discipline: Clinical discipline (e.g., "internal_medicine")
            count: Number of questions to generate
            difficulty: "easy", "medium", or "hard"

        Returns:
            List of question dictionaries ready for validation
        """
        logger.info(f"Generating {count} questions: {system} x {task} x {discipline}")

        # Check if Ollama is available
        if not await ollama_service.is_available():
            raise OllamaNotAvailableError(
                "Ollama is not running. Start with: ollama serve"
            )

        questions = []
        for i in range(count):
            try:
                question = await self._generate_single_question(
                    system=system,
                    task=task,
                    discipline=discipline,
                    difficulty=difficulty,
                    attempt=i + 1
                )
                if question:
                    questions.append(question)
                    self._generation_count += 1

            except Exception as e:
                logger.warning(f"Question generation failed (attempt {i+1}): {e}")
                continue

        logger.info(f"Generated {len(questions)}/{count} questions")
        return questions

    async def _generate_single_question(
        self,
        system: str,
        task: str,
        discipline: str,
        difficulty: str,
        attempt: int
    ) -> Optional[Dict[str, Any]]:
        """Generate a single question."""

        system_context = SYSTEM_CONTEXTS.get(system, SYSTEM_CONTEXTS["multisystem"])
        task_stems = TASK_STEMS.get(task, TASK_STEMS["diagnosis"])

        # Vary the question stem for diversity
        question_stem = task_stems[attempt % len(task_stems)]

        prompt = self._build_prompt(
            system=system,
            task=task,
            discipline=discipline,
            difficulty=difficulty,
            system_context=system_context,
            question_stem=question_stem
        )

        try:
            response = await ollama_service.generate(
                prompt=prompt,
                model=self.model,
                temperature=0.8,  # Higher for more creativity
                max_tokens=2000,
                timeout=300.0  # 5 minutes for complex generation
            )

            question = self._parse_response(response, system, task, discipline)

            if question:
                question["generated_at"] = datetime.utcnow().isoformat()
                question["generator"] = "ollama"
                question["model"] = self.model
                question["needs_validation"] = True

            return question

        except Exception as e:
            logger.error(f"Generation error: {e}")
            return None

    def _build_prompt(
        self,
        system: str,
        task: str,
        discipline: str,
        difficulty: str,
        system_context: str,
        question_stem: str
    ) -> str:
        """Build the generation prompt."""

        difficulty_guidance = {
            "easy": "straightforward presentation with classic findings",
            "medium": "typical presentation requiring integration of multiple findings",
            "hard": "atypical presentation or complex patient with comorbidities"
        }

        return f"""You are creating a USMLE Step 2 CK practice question.

CURRICULUM REQUIREMENTS:
- Body System: {system.replace("_", " ").title()}
- Physician Task: {task.replace("_", " ").title()}
- Discipline: {discipline.replace("_", " ").title()}
- Difficulty: {difficulty.title()} ({difficulty_guidance.get(difficulty, difficulty_guidance["medium"])})

CLINICAL CONTEXT:
{system_context}

QUESTION STEM TO USE:
{question_stem}

REQUIREMENTS:
1. Write a clinical vignette (150-250 words) with:
   - Patient demographics (age, sex)
   - Chief complaint with duration
   - Relevant history (medical, surgical, social, medications)
   - Physical exam findings with vital signs
   - Relevant laboratory or imaging results

2. Create 5 answer choices (A-E):
   - One clearly correct best answer
   - Four plausible distractors that represent common student errors
   - Each distractor should have a reason students might choose it

3. Provide a brief explanation (2-3 sentences) for the correct answer.

Generate a completely ORIGINAL clinical scenario. Do NOT copy existing questions.

Return ONLY valid JSON in this exact format:
{{
    "vignette": "A 45-year-old woman presents to the emergency department with...",
    "question_stem": "{question_stem}",
    "choices": {{
        "A": "Answer option A",
        "B": "Answer option B",
        "C": "Answer option C",
        "D": "Answer option D",
        "E": "Answer option E"
    }},
    "answer_key": "B",
    "explanation_brief": "This patient has [diagnosis] based on [key findings]. The correct answer is [answer] because...",
    "difficulty": "{difficulty}"
}}"""

    def _parse_response(
        self,
        response: str,
        system: str,
        task: str,
        discipline: str
    ) -> Optional[Dict[str, Any]]:
        """Parse the LLM response into a question dict."""

        try:
            # Find JSON in response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start < 0 or json_end <= json_start:
                logger.warning("No JSON found in response")
                return None

            json_str = response[json_start:json_end]
            question = json.loads(json_str)

            # Validate required fields
            required = ["vignette", "choices", "answer_key"]
            for field in required:
                if field not in question:
                    logger.warning(f"Missing required field: {field}")
                    return None

            # Normalize choices to list format
            if isinstance(question["choices"], dict):
                question["choices_dict"] = question["choices"]
                question["choices"] = [
                    f"{k}. {v}" for k, v in sorted(question["choices"].items())
                ]

            # Add metadata
            question["system"] = system
            question["task"] = task
            question["discipline"] = discipline
            question["specialty"] = discipline
            question["source_type"] = "ai_generated_ollama"

            return question

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            return None
        except Exception as e:
            logger.warning(f"Parse error: {e}")
            return None

    async def fill_priority_gaps(
        self,
        gaps_file: str = "curriculum_gaps.json",
        max_questions: int = 100,
        questions_per_cell: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate questions for priority curriculum gaps.

        Args:
            gaps_file: Path to gap analysis JSON
            max_questions: Maximum total questions to generate
            questions_per_cell: Questions to generate per gap cell

        Returns:
            List of generated questions
        """
        import json
        from pathlib import Path

        gaps_path = Path(gaps_file)
        if not gaps_path.exists():
            raise FileNotFoundError(f"Gaps file not found: {gaps_file}")

        with open(gaps_path) as f:
            gaps_data = json.load(f)

        matrix_gaps = gaps_data.get("matrix_gaps", [])

        all_questions = []
        questions_generated = 0

        for gap in matrix_gaps:
            if questions_generated >= max_questions:
                break

            system = gap["system"]
            task = gap["task"]
            gap_size = gap["gap"]

            # Generate questions for this gap
            count = min(questions_per_cell, gap_size, max_questions - questions_generated)

            logger.info(f"Filling gap: {system} x {task} (need {gap_size}, generating {count})")

            try:
                questions = await self.generate_for_gap(
                    system=system,
                    task=task,
                    count=count
                )
                all_questions.extend(questions)
                questions_generated += len(questions)

            except Exception as e:
                logger.error(f"Failed to fill gap {system} x {task}: {e}")
                continue

        logger.info(f"Total questions generated: {questions_generated}")
        return all_questions

    def save_questions_to_db(
        self,
        questions: List[Dict[str, Any]],
        status: str = "draft"
    ) -> int:
        """
        Save generated questions to database with validation and transaction safety.

        Args:
            questions: List of question dicts
            status: Content status ("draft", "pending_review", "active")

        Returns:
            Number of questions saved
        """
        import re

        # Validate status parameter
        valid_statuses = {"draft", "pending_review", "active", "archived"}
        if status not in valid_statuses:
            logger.error(f"Invalid status: {status}")
            return 0

        saved = 0

        try:
            for q in questions:
                try:
                    # Validate required fields exist
                    if not q.get("vignette") or not q.get("answer_key"):
                        logger.warning("Skipping question: missing vignette or answer_key")
                        continue

                    # Convert choices to list if needed
                    choices = q.get("choices", [])
                    if isinstance(choices, dict):
                        choices = [f"{k}. {v}" for k, v in sorted(choices.items())]

                    # Validate choices is a list
                    if not isinstance(choices, list) or len(choices) == 0:
                        logger.warning("Skipping question: invalid choices")
                        continue

                    # Sanitize cognitive_patterns to prevent injection
                    system = str(q.get("system", ""))[:100]
                    task = str(q.get("task", ""))[:100]

                    # Only allow alphanumeric, spaces, and underscores
                    system = re.sub(r'[^\w\s_]', '', system).strip()
                    task = re.sub(r'[^\w\s_]', '', task).strip()

                    cognitive_patterns = []
                    if system:
                        cognitive_patterns.append(system)
                    if task:
                        cognitive_patterns.append(task)

                    # Sanitize model name
                    model_name = str(q.get('model', 'unknown'))[:50]
                    model_name = re.sub(r'[^\w\s\.\-:]', '', model_name)

                    # Truncate vignette and explanation to reasonable limits
                    vignette = str(q["vignette"])[:10000]
                    explanation_brief = str(q.get("explanation_brief", ""))[:5000]

                    db_question = Question(
                        vignette=vignette,
                        answer_key=str(q["answer_key"])[:1].upper(),
                        choices=choices,
                        explanation={"brief": explanation_brief},
                        specialty=str(q.get("specialty", "general"))[:50],
                        difficulty_level=str(q.get("difficulty", "medium"))[:20],
                        source_type="ai_generated_ollama",
                        source=f"Ollama {model_name}",
                        content_status=status,
                        cognitive_patterns=cognitive_patterns,
                    )

                    self.db.add(db_question)
                    saved += 1

                except Exception as e:
                    logger.error(f"Failed to prepare question: {e}")
                    continue

            # Commit only if we have questions to save
            if saved > 0:
                self.db.commit()
                logger.info(f"Saved {saved} questions to database (status: {status})")
            else:
                logger.warning("No questions to save")

            return saved

        except Exception as e:
            # Rollback on commit failure
            self.db.rollback()
            logger.error(f"Database commit failed (rolled back {saved} questions): {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return {
            "total_generated": self._generation_count,
            "model": self.model,
            "ollama_status": ollama_service.get_status()
        }
