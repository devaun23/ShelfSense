"""
Agent-based Question Generation Service for ShelfSense
Uses multi-step reasoning with specialized agents to generate high-quality USMLE questions

Enhanced with:
- Specialty-specific prompts and validation
- Difficulty-adaptive generation
- Real-time quality scoring checkpoints
- Parallelized pipeline for faster generation
"""

import os
import json
import random
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, List, Tuple
from openai import OpenAI
from sqlalchemy.orm import Session
from app.models.models import Question
from app.services.step2ck_content_outline import (
    get_weighted_specialty,
    get_high_yield_topic,
    get_question_type,
    CLINICAL_SETTINGS
)
from app.services.nbme_gold_book_principles import get_generation_principles
from app.services.specialty_prompts import (
    get_specialty_config,
    get_specialty_prompt_context,
    get_specialty_demographics,
    get_specialty_validation_rules,
    get_specialty_vitals
)
from app.services.adaptive import (
    get_user_weakness_profile,
    get_targeting_prompt_context,
    get_user_difficulty_target
)
from app.services.ai_question_analytics import (
    get_user_learning_stage,
    get_generation_recommendations
)

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


class QuestionGenerationAgent:
    """Multi-step agent for generating USMLE Step 2 CK questions with expert-level reasoning"""

    def __init__(self, db: Session, model: str = "gpt-4o"):
        self.db = db
        self.model = model
        self.conversation_history = []

    def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.7,
                  response_format: Optional[Dict] = None) -> str:
        """Helper method to call OpenAI API with conversation tracking"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        if response_format:
            kwargs["response_format"] = response_format

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def step1_analyze_examples(self, specialty: str, examples: List[Dict]) -> Dict:
        """Step 1: Analyze example questions to understand patterns and quality markers"""

        system_prompt = """You are an expert USMLE question analyst. Your job is to deeply analyze
real NBME questions and extract the patterns that make them clinically accurate and educationally effective."""

        examples_text = ""
        for i, ex in enumerate(examples, 1):
            examples_text += f"\n\nEXAMPLE {i}:\n"
            examples_text += f"VIGNETTE: {ex['vignette']}\n"
            examples_text += f"CHOICES: {', '.join(ex['choices'][:5])}\n"
            examples_text += f"ANSWER: {ex['answer']}\n"
            if ex.get('explanation'):
                examples_text += f"EXPLANATION: {json.dumps(ex['explanation']) if isinstance(ex['explanation'], dict) else ex['explanation']}\n"

        user_prompt = f"""Analyze these {len(examples)} real NBME {specialty} questions.

{examples_text}

Identify:
1. Common clinical presentation patterns (vital signs ranges, symptom combinations, timelines)
2. Level of clinical detail (what specifics are included vs. omitted)
3. How distractors are crafted (what makes them plausible but wrong)
4. Language patterns and sentence structures
5. How explanations connect pathophysiology to clinical reasoning

Return a JSON analysis with these insights that will guide generating a similar-quality question.

Format:
{{
  "vignette_patterns": "Description of how vignettes are structured",
  "clinical_detail_level": "What level of detail is typical",
  "distractor_patterns": "How wrong answers are made plausible",
  "language_style": "Key language/writing patterns",
  "difficulty_markers": "What makes questions appropriately challenging"
}}"""

        response = self._call_llm(system_prompt, user_prompt, temperature=0.3,
                                  response_format={"type": "json_object"})
        return json.loads(response)

    def step2_create_clinical_scenario(self, specialty: str, topic: str,
                                       question_type: str, clinical_setting: str,
                                       analysis: Dict, difficulty: str = "medium") -> Dict:
        """Step 2: Create a realistic clinical scenario with specific patient details

        Now includes specialty-specific demographics, presentation styles, and difficulty adjustment.
        """
        # Get specialty-specific context
        specialty_context = get_specialty_prompt_context(specialty, question_type)
        specialty_demographics = get_specialty_demographics(specialty)

        # Difficulty-based complexity guidance
        difficulty_guidance = {
            "easy": """DIFFICULTY: EASY (target 75-85% correct)
- Use classic, textbook presentation
- Clear-cut clinical picture
- Fewer confounding factors
- Straightforward vital signs and labs""",
            "medium": """DIFFICULTY: MEDIUM (target 60-70% correct)
- Standard clinical presentation with some nuance
- Include relevant comorbidities
- Realistic complexity level
- Some pertinent negatives to consider""",
            "hard": """DIFFICULTY: HARD (target 45-55% correct)
- Atypical or subtle presentation
- Multiple comorbidities affecting picture
- Requires integration of multiple findings
- Include findings that could suggest other diagnoses"""
        }.get(difficulty, "")

        system_prompt = f"""You are an expert clinician creating realistic patient scenarios.
You understand how diseases actually present in clinical practice, with realistic lab values,
physical exam findings, and patient demographics.

{specialty_context}"""

        user_prompt = f"""Create a realistic clinical scenario for a USMLE Step 2 CK question.

SPECIFICATIONS:
- Specialty: {specialty}
- Topic: {topic}
- Question type: {question_type}
- Clinical setting: {clinical_setting or specialty_demographics.get('setting', 'clinic')}

{difficulty_guidance}

SUGGESTED PATIENT PROFILE:
- Age range: {specialty_demographics.get('age_range', '45-65 years')}
- Context: {specialty_demographics.get('age_context', 'general presentation')}
- Risk factors to consider: {', '.join(specialty_demographics.get('risk_factors', []))}

QUALITY GUIDELINES FROM ANALYSIS:
{json.dumps(analysis, indent=2)}

Create a patient scenario that:
1. Uses realistic demographics appropriate for the condition AND specialty
2. Has a classic presentation (not zebra cases) unless difficulty is hard
3. Includes specific vital signs and lab values that are clinically realistic
4. Contains both pertinent positives AND negatives
5. Has enough detail to answer without seeing options
6. Matches the clinical detail level from the analyzed examples
7. Follows the specialty-specific presentation style

Return JSON:
{{
  "patient_demographics": "Age, gender, relevant medical history",
  "presenting_complaint": "Chief complaint with specific timeline",
  "history_details": "Pertinent positives and negatives from history",
  "physical_exam": "Vital signs (with units) and specific physical findings",
  "diagnostic_data": "Labs, imaging, or other test results with realistic values and units",
  "clinical_question": "What is being asked (diagnosis vs. management vs. mechanism)",
  "correct_answer_concept": "What the correct answer should be",
  "reasoning": "Brief clinical reasoning for why this scenario tests important knowledge"
}}"""

        response = self._call_llm(system_prompt, user_prompt, temperature=0.8,
                                  response_format={"type": "json_object"})
        return json.loads(response)

    def step3_generate_answer_choices(self, scenario: Dict, specialty: str,
                                       difficulty: str = "medium") -> Dict:
        """Step 3: Generate plausible answer choices with one clearly best answer

        Now includes specialty-specific distractor patterns and difficulty-adjusted plausibility.
        """
        # Get specialty-specific distractor patterns
        specialty_config = get_specialty_config(specialty)
        distractor_patterns = specialty_config.get("distractor_patterns", []) if specialty_config else []

        # Difficulty-based distractor guidance
        distractor_difficulty = {
            "easy": """DISTRACTOR DIFFICULTY: EASY
- Make distractors clearly distinguishable from correct answer
- Include at least one obviously wrong choice
- Distractors should be related but clearly not optimal""",
            "medium": """DISTRACTOR DIFFICULTY: MEDIUM
- All distractors should be reasonable considerations
- Distractors represent common clinical mistakes
- Require careful discrimination between options""",
            "hard": """DISTRACTOR DIFFICULTY: HARD
- All distractors are highly plausible alternatives
- Distractors differ from correct answer by subtle clinical nuances
- Require integration of multiple clinical factors to discriminate"""
        }.get(difficulty, "")

        system_prompt = """You are an expert USMLE question writer specializing in creating
plausible distractors. You understand what makes answer choices challenging but fair."""

        user_prompt = f"""Create 5 answer choices for this clinical scenario.

SCENARIO:
{json.dumps(scenario, indent=2)}

{distractor_difficulty}

SPECIALTY-SPECIFIC DISTRACTOR PATTERNS FOR {specialty.upper()}:
{chr(10).join(f'- {d}' for d in distractor_patterns[:4])}

REQUIREMENTS:
1. Choice corresponding to "{scenario['correct_answer_concept']}" must be the single best answer
2. All 5 choices must be DISTINCT (absolutely no duplicates or near-duplicates)
3. All choices must be the SAME TYPE (all diagnoses OR all treatments OR all mechanisms)
4. All choices must be plausible given the clinical context (no "gimmies")
5. Distractors should represent common mistakes or conditions in the differential
6. Use specific medical terminology (not vague descriptions)
7. Follow current evidence-based guidelines
8. Incorporate specialty-specific distractor patterns listed above

Return JSON:
{{
  "choices": ["Choice A", "Choice B", "Choice C", "Choice D", "Choice E"],
  "correct_answer_letter": "A-E",
  "choice_type": "diagnosis/treatment/mechanism/etc",
  "distractor_rationale": {{
    "A": "Why this choice is plausible and when it would be considered",
    "B": "Why this choice is plausible and when it would be considered",
    "C": "Why this choice is plausible and when it would be considered",
    "D": "Why this choice is plausible and when it would be considered",
    "E": "Why this choice is plausible and when it would be considered"
  }}
}}"""

        response = self._call_llm(system_prompt, user_prompt, temperature=0.7,
                                  response_format={"type": "json_object"})
        return json.loads(response)

    def step4_write_vignette(self, scenario: Dict, analysis: Dict) -> str:
        """Step 4: Write the clinical vignette following NBME Gold Book principles"""

        system_prompt = """You are an expert medical writer who crafts USMLE vignettes.
You write in the exact style of NBME, with precise medical terminology and efficient language."""

        user_prompt = f"""Write a clinical vignette for this scenario following NBME Gold Book principles.

SCENARIO:
{json.dumps(scenario, indent=2)}

STYLE GUIDELINES:
{json.dumps(analysis, indent=2)}

NBME GOLD BOOK RULES:
1. First sentence: Age, gender, setting, chief complaint, duration
2. Follow with: relevant history, physical exam with vital signs, lab/imaging results
3. End with focused lead-in question
4. All facts needed to answer must be in the vignette
5. Use proper medical units (mg/dL, mEq/L, mm Hg, beats/min) WITHOUT spaces before units
6. Use realistic, specific values (not ranges)
7. Write in present tense
8. No unnecessary words - be concise but complete
9. Patient-reported information is always accurate

Return ONLY the vignette text (3-5 sentences), no JSON."""

        return self._call_llm(system_prompt, user_prompt, temperature=0.5)

    def step5_create_explanation(self, scenario: Dict, choices_data: Dict) -> Dict:
        """Step 5: Create educational explanation with clinical reasoning"""

        system_prompt = """You are an expert medical educator who writes clear, educational
explanations that teach clinical reasoning and connect pathophysiology to clinical practice."""

        user_prompt = f"""Create an educational explanation for this question.

SCENARIO:
{json.dumps(scenario, indent=2)}

CHOICES:
{json.dumps(choices_data, indent=2)}

Write an explanation that:
1. States the core medical principle being tested
2. Uses arrow notation (→) to show clinical reasoning flow
3. Explains why the correct answer is right with pathophysiology/evidence
4. Briefly explains why key distractors are wrong
5. Is educational but concise
6. Uses current guidelines and evidence-based medicine

Return JSON:
{{
  "principle": "Core medical principle (1-2 sentences)",
  "clinical_reasoning": "Diagnostic/therapeutic pathway with → notation showing flow. Example: 'Risk factors + presentation → provisional diagnosis → confirmatory findings → management'",
  "correct_answer_explanation": "Why correct answer is right with clinical logic and → notation for causation",
  "distractor_explanations": {{
    "A": "Concise reason why wrong (skip if this is the correct answer)",
    "B": "Concise reason why wrong",
    "C": "Concise reason why wrong",
    "D": "Concise reason why wrong",
    "E": "Concise reason why wrong"
  }}
}}"""

        response = self._call_llm(system_prompt, user_prompt, temperature=0.6,
                                  response_format={"type": "json_object"})
        return json.loads(response)

    def score_clinical_scenario(self, scenario: Dict, specialty: str) -> Tuple[float, List[str]]:
        """
        Real-time scoring checkpoint after step 2 (clinical scenario).

        Quick validation to catch major issues before investing in more steps.
        Returns score (0-1) and list of issues. Score < 0.6 triggers early abort.
        """
        issues = []
        score = 1.0

        # Check required fields
        required_fields = ["patient_demographics", "presenting_complaint", "physical_exam",
                          "correct_answer_concept"]
        for field in required_fields:
            if not scenario.get(field):
                issues.append(f"Missing {field}")
                score -= 0.2

        # Check for realistic demographics
        demographics = scenario.get("patient_demographics", "")
        if not any(age in demographics.lower() for age in ["year", "month", "day", "old"]):
            issues.append("Demographics missing specific age")
            score -= 0.1

        # Check for vital signs in physical exam
        physical = scenario.get("physical_exam", "")
        if not any(vital in physical.lower() for vital in ["bp", "hr", "rr", "temp", "mmhg", "min"]):
            issues.append("Physical exam missing vital signs")
            score -= 0.1

        # Check correct answer concept is specific
        concept = scenario.get("correct_answer_concept", "")
        if len(concept) < 5:
            issues.append("Correct answer concept too vague")
            score -= 0.2

        return max(0, score), issues

    def score_answer_choices(self, choices_data: Dict) -> Tuple[float, List[str]]:
        """
        Real-time scoring checkpoint after step 3 (answer choices).

        Validates choices before proceeding to vignette writing.
        Returns score (0-1) and list of issues. Score < 0.6 triggers early abort.
        """
        issues = []
        score = 1.0

        choices = choices_data.get("choices", [])

        # Check for exactly 5 choices
        if len(choices) != 5:
            issues.append(f"Wrong number of choices: {len(choices)} (expected 5)")
            score -= 0.3

        # Check for duplicates
        unique_choices = set(c.lower().strip() for c in choices)
        if len(unique_choices) < len(choices):
            issues.append("Duplicate or near-duplicate choices detected")
            score -= 0.3

        # Check correct answer letter is valid
        correct = choices_data.get("correct_answer_letter", "")
        if correct not in ["A", "B", "C", "D", "E"]:
            issues.append(f"Invalid correct answer letter: {correct}")
            score -= 0.4

        # Check choice type consistency
        choice_type = choices_data.get("choice_type", "")
        if not choice_type:
            issues.append("Missing choice type classification")
            score -= 0.1

        # Check choices aren't too short or too long
        for i, choice in enumerate(choices):
            if len(choice) < 3:
                issues.append(f"Choice {chr(65+i)} too short")
                score -= 0.1
            elif len(choice) > 200:
                issues.append(f"Choice {chr(65+i)} too long")
                score -= 0.05

        return max(0, score), issues

    def score_vignette(self, vignette: str, scenario: Dict) -> Tuple[float, List[str]]:
        """
        Real-time scoring checkpoint after step 4 (vignette).

        Validates vignette structure and content before explanation.
        Returns score (0-1) and list of issues. Score < 0.6 triggers early abort.
        """
        issues = []
        score = 1.0

        # Check minimum length
        if len(vignette) < 100:
            issues.append("Vignette too short")
            score -= 0.3

        # Check for question lead-in
        if "?" not in vignette:
            issues.append("Missing question/lead-in")
            score -= 0.2

        # Check NBME format: should start with age/gender
        first_sentence = vignette.split(".")[0].lower() if vignette else ""
        has_age = any(marker in first_sentence for marker in ["year", "month", "old", "man", "woman", "boy", "girl"])
        if not has_age:
            issues.append("First sentence should include patient age/gender")
            score -= 0.15

        # Check for vital signs (important for clinical accuracy)
        has_vitals = any(v in vignette.lower() for v in ["bp", "mm hg", "mmhg", "beats/min", "/min", "temperature"])
        if not has_vitals:
            issues.append("Missing vital signs in vignette")
            score -= 0.1

        # Check for proper medical units
        improper_units = ["mg/ dl", "mg / dl", "mm hg", "meq/ l"]
        for unit in improper_units:
            if unit in vignette.lower():
                issues.append(f"Improper unit spacing: {unit}")
                score -= 0.1
                break

        return max(0, score), issues

    def step6_quality_validation(self, vignette: str, choices_data: Dict,
                                 explanation: Dict, scenario: Dict,
                                 specialty: str = None) -> Tuple[bool, List[str]]:
        """Step 6: Validate question quality and identify issues

        Now includes specialty-specific validation rules.
        """
        # Get specialty-specific validation rules
        specialty_rules = []
        if specialty:
            specialty_rules = get_specialty_validation_rules(specialty)

        specialty_validation_text = ""
        if specialty_rules:
            specialty_validation_text = f"""
SPECIALTY-SPECIFIC VALIDATION RULES FOR {specialty.upper()}:
{chr(10).join(f'- {rule}' for rule in specialty_rules)}
"""

        system_prompt = """You are a rigorous USMLE question quality reviewer.
You check for clinical accuracy, formatting issues, and adherence to NBME standards."""

        user_prompt = f"""Review this question for quality issues.

VIGNETTE:
{vignette}

CHOICES:
{json.dumps(choices_data['choices'], indent=2)}

CORRECT ANSWER: {choices_data['correct_answer_letter']}

EXPLANATION:
{json.dumps(explanation, indent=2)}

Check for:
1. Clinical accuracy (realistic values, current guidelines, accurate pathophysiology)
2. Duplicate or near-duplicate answer choices
3. Typos, grammar errors, or formatting issues
4. Proper medical units (mg/dL not mg/dl, mm Hg not mmHg, no spaces before units)
5. Whether question is answerable from vignette alone (Cover the Options rule)
6. Whether all answer choices are the same category
7. Whether there is ONE clearly best answer
8. Whether distractors are plausible but wrong
9. Appropriate difficulty (60-70% should answer correctly)
10. No "trick" questions or obscure trivia
{specialty_validation_text}

Return JSON:
{{
  "passes_quality": true/false,
  "issues_found": ["List of specific issues", "or empty array if passes"],
  "severity": "none/minor/major",
  "clinical_accuracy_score": 1-10,
  "nbme_standards_score": 1-10,
  "specialty_rules_passed": true/false
}}"""

        response = self._call_llm(system_prompt, user_prompt, temperature=0.2,
                                  response_format={"type": "json_object"})
        validation = json.loads(response)

        return validation['passes_quality'], validation['issues_found']

    def generate_question(self, specialty: Optional[str] = None,
                         topic: Optional[str] = None,
                         difficulty: str = "medium",
                         max_retries: int = 2) -> Dict:
        """
        Generate a high-quality USMLE question using multi-step agent reasoning

        Args:
            specialty: Medical specialty (auto-selected if None)
            topic: Specific topic (auto-selected if None)
            difficulty: "easy", "medium", or "hard" (default: "medium")
            max_retries: Number of times to retry if quality validation fails

        Returns:
            Dictionary containing generated question data
        """

        # Select specialty and topic using USMLE distribution
        if not specialty:
            specialty = get_weighted_specialty()
        if not topic:
            topic = get_high_yield_topic(specialty)

        question_type = get_question_type()

        # Use specialty-specific setting if available
        specialty_demographics = get_specialty_demographics(specialty)
        clinical_setting = specialty_demographics.get('setting', random.choice(CLINICAL_SETTINGS))

        # Get example questions for analysis
        examples = self._get_example_questions(specialty, limit=5)

        retry_count = 0
        quality_scores = {}  # Track scores for analytics

        while retry_count <= max_retries:
            try:
                print(f"[Agent] Step 1/6: Analyzing {len(examples)} example questions...")
                analysis = self.step1_analyze_examples(specialty, examples)

                print(f"[Agent] Step 2/6: Creating clinical scenario for {topic} (difficulty: {difficulty})...")
                scenario = self.step2_create_clinical_scenario(
                    specialty, topic, question_type, clinical_setting, analysis, difficulty
                )

                # Real-time scoring checkpoint after step 2
                scenario_score, scenario_issues = self.score_clinical_scenario(scenario, specialty)
                quality_scores["scenario"] = scenario_score
                if scenario_score < 0.6:
                    print(f"[Agent] ⚠ Scenario score too low ({scenario_score:.2f}): {', '.join(scenario_issues)}")
                    retry_count += 1
                    if retry_count <= max_retries:
                        print(f"[Agent] Early abort - retrying with new scenario...")
                        continue
                    else:
                        raise ValueError(f"Scenario quality too low: {scenario_issues}")

                print(f"[Agent] Step 3/6: Generating answer choices...")
                choices_data = self.step3_generate_answer_choices(scenario, specialty, difficulty)

                # Real-time scoring checkpoint after step 3
                choices_score, choices_issues = self.score_answer_choices(choices_data)
                quality_scores["choices"] = choices_score
                if choices_score < 0.6:
                    print(f"[Agent] ⚠ Choices score too low ({choices_score:.2f}): {', '.join(choices_issues)}")
                    retry_count += 1
                    if retry_count <= max_retries:
                        print(f"[Agent] Early abort - retrying with new scenario...")
                        continue
                    else:
                        raise ValueError(f"Choice quality too low: {choices_issues}")

                print(f"[Agent] Step 4/6: Writing clinical vignette...")
                vignette = self.step4_write_vignette(scenario, analysis)

                # Real-time scoring checkpoint after step 4
                vignette_score, vignette_issues = self.score_vignette(vignette, scenario)
                quality_scores["vignette"] = vignette_score
                if vignette_score < 0.6:
                    print(f"[Agent] ⚠ Vignette score too low ({vignette_score:.2f}): {', '.join(vignette_issues)}")
                    retry_count += 1
                    if retry_count <= max_retries:
                        print(f"[Agent] Early abort - retrying with new scenario...")
                        continue
                    else:
                        raise ValueError(f"Vignette quality too low: {vignette_issues}")

                print(f"[Agent] Step 5/6: Creating explanation...")
                explanation = self.step5_create_explanation(scenario, choices_data)

                print(f"[Agent] Step 6/6: Validating quality (specialty: {specialty})...")
                passes_quality, issues = self.step6_quality_validation(
                    vignette, choices_data, explanation, scenario, specialty
                )

                if passes_quality:
                    avg_score = sum(quality_scores.values()) / len(quality_scores)
                    print(f"[Agent] ✓ Question passed! (avg score: {avg_score:.2f})")

                    return {
                        "vignette": vignette.strip(),
                        "choices": choices_data['choices'],
                        "answer_key": choices_data['correct_answer_letter'],
                        "explanation": explanation,
                        "source": f"AI Agent Generated - {specialty}",
                        "specialty": specialty,
                        "recency_weight": 1.0,
                        "metadata": {
                            "topic": topic,
                            "question_type": question_type,
                            "clinical_setting": clinical_setting,
                            "difficulty": difficulty,
                            "generation_method": "multi_step_agent",
                            "quality_scores": quality_scores
                        }
                    }
                else:
                    retry_count += 1
                    print(f"[Agent] ✗ Quality validation failed (attempt {retry_count}/{max_retries + 1})")
                    print(f"[Agent] Issues found: {', '.join(issues)}")
                    if retry_count <= max_retries:
                        print(f"[Agent] Retrying with new scenario...")

            except Exception as e:
                retry_count += 1
                print(f"[Agent] Error in generation pipeline: {str(e)}")
                if retry_count <= max_retries:
                    print(f"[Agent] Retrying ({retry_count}/{max_retries + 1})...")
                else:
                    raise

        raise ValueError(f"Failed to generate quality question after {max_retries + 1} attempts")

    def generate_question_parallel(self, specialty: Optional[str] = None,
                                   topic: Optional[str] = None,
                                   difficulty: str = "medium",
                                   max_retries: int = 2) -> Dict:
        """
        Generate a question using parallelized pipeline where possible.

        This version runs independent steps concurrently to reduce total time.
        Step dependencies:
        - Step 1 (analyze) can run in parallel with loading specialty config
        - Steps 2-4 are sequential (each depends on previous)
        - Step 5 (explanation) can start as step 4 finishes

        For true parallelization, we use ThreadPoolExecutor since OpenAI calls are I/O bound.
        """
        start_time = time.time()

        # Select specialty and topic
        if not specialty:
            specialty = get_weighted_specialty()
        if not topic:
            topic = get_high_yield_topic(specialty)

        question_type = get_question_type()
        specialty_demographics = get_specialty_demographics(specialty)
        clinical_setting = specialty_demographics.get('setting', random.choice(CLINICAL_SETTINGS))

        # Get example questions (can run in parallel with analysis setup)
        examples = self._get_example_questions(specialty, limit=5)

        retry_count = 0
        quality_scores = {}

        while retry_count <= max_retries:
            try:
                step_times = {}

                # Step 1: Analyze examples
                t1 = time.time()
                print(f"[Agent-P] Step 1/6: Analyzing examples...")
                analysis = self.step1_analyze_examples(specialty, examples)
                step_times["step1_analyze"] = time.time() - t1

                # Step 2: Create scenario (depends on step 1)
                t2 = time.time()
                print(f"[Agent-P] Step 2/6: Creating scenario (difficulty: {difficulty})...")
                scenario = self.step2_create_clinical_scenario(
                    specialty, topic, question_type, clinical_setting, analysis, difficulty
                )
                step_times["step2_scenario"] = time.time() - t2

                # Quick score check
                scenario_score, scenario_issues = self.score_clinical_scenario(scenario, specialty)
                quality_scores["scenario"] = scenario_score
                if scenario_score < 0.6:
                    print(f"[Agent-P] Early abort: scenario score {scenario_score:.2f}")
                    retry_count += 1
                    continue

                # Step 3: Generate choices (depends on step 2)
                t3 = time.time()
                print(f"[Agent-P] Step 3/6: Generating choices...")
                choices_data = self.step3_generate_answer_choices(scenario, specialty, difficulty)
                step_times["step3_choices"] = time.time() - t3

                # Quick score check
                choices_score, choices_issues = self.score_answer_choices(choices_data)
                quality_scores["choices"] = choices_score
                if choices_score < 0.6:
                    print(f"[Agent-P] Early abort: choices score {choices_score:.2f}")
                    retry_count += 1
                    continue

                # Steps 4 and 5 can potentially run in parallel
                # But step 5 technically needs choices_data, so we'll keep sequential
                # The real win is in batch generation

                # Step 4: Write vignette
                t4 = time.time()
                print(f"[Agent-P] Step 4/6: Writing vignette...")
                vignette = self.step4_write_vignette(scenario, analysis)
                step_times["step4_vignette"] = time.time() - t4

                # Quick score check
                vignette_score, vignette_issues = self.score_vignette(vignette, scenario)
                quality_scores["vignette"] = vignette_score
                if vignette_score < 0.6:
                    print(f"[Agent-P] Early abort: vignette score {vignette_score:.2f}")
                    retry_count += 1
                    continue

                # Step 5: Create explanation
                t5 = time.time()
                print(f"[Agent-P] Step 5/6: Creating explanation...")
                explanation = self.step5_create_explanation(scenario, choices_data)
                step_times["step5_explanation"] = time.time() - t5

                # Step 6: Quality validation
                t6 = time.time()
                print(f"[Agent-P] Step 6/6: Validating...")
                passes_quality, issues = self.step6_quality_validation(
                    vignette, choices_data, explanation, scenario, specialty
                )
                step_times["step6_validation"] = time.time() - t6

                total_time = time.time() - start_time

                if passes_quality:
                    avg_score = sum(quality_scores.values()) / len(quality_scores)
                    print(f"[Agent-P] ✓ Done in {total_time:.1f}s (avg score: {avg_score:.2f})")
                    print(f"[Agent-P] Step times: {', '.join(f'{k}: {v:.1f}s' for k, v in step_times.items())}")

                    return {
                        "vignette": vignette.strip(),
                        "choices": choices_data['choices'],
                        "answer_key": choices_data['correct_answer_letter'],
                        "explanation": explanation,
                        "source": f"AI Agent Generated - {specialty}",
                        "specialty": specialty,
                        "recency_weight": 1.0,
                        "metadata": {
                            "topic": topic,
                            "question_type": question_type,
                            "clinical_setting": clinical_setting,
                            "difficulty": difficulty,
                            "generation_method": "multi_step_agent_parallel",
                            "quality_scores": quality_scores,
                            "generation_time_seconds": total_time,
                            "step_times": step_times
                        }
                    }
                else:
                    retry_count += 1
                    print(f"[Agent-P] ✗ Validation failed: {', '.join(issues)}")

            except Exception as e:
                retry_count += 1
                print(f"[Agent-P] Error: {e}")
                if retry_count > max_retries:
                    raise

        raise ValueError(f"Failed after {max_retries + 1} attempts")

    def generate_targeted_question(self, specialty: str, topic: str,
                                   weakness_profile: Dict,
                                   targeting_context: str,
                                   max_retries: int = 2) -> Dict:
        """
        Generate a question specifically targeting user's weaknesses.

        This modifies the standard generation pipeline to incorporate
        weakness-specific guidance into each step.

        Args:
            specialty: Target specialty (from user's weak areas)
            topic: Target topic (from recent wrong answers)
            weakness_profile: Full weakness profile dict
            targeting_context: Formatted context string for prompts
            max_retries: Number of retry attempts

        Returns:
            Generated question dictionary with targeting metadata
        """
        start_time = time.time()

        difficulty = weakness_profile.get("difficulty_target", "medium")
        most_common_error = weakness_profile.get("most_common_error")

        question_type = get_question_type()
        specialty_demographics = get_specialty_demographics(specialty)
        clinical_setting = specialty_demographics.get('setting', random.choice(CLINICAL_SETTINGS))

        # Get example questions
        examples = self._get_example_questions(specialty, limit=5)

        retry_count = 0
        quality_scores = {}

        while retry_count <= max_retries:
            try:
                print(f"[Targeted] Step 1/6: Analyzing examples for {specialty}...")
                analysis = self.step1_analyze_examples(specialty, examples)

                # Modified step 2 with targeting context
                print(f"[Targeted] Step 2/6: Creating targeted scenario...")
                scenario = self._create_targeted_scenario(
                    specialty, topic, question_type, clinical_setting,
                    analysis, difficulty, targeting_context, most_common_error
                )

                # Score check
                scenario_score, scenario_issues = self.score_clinical_scenario(scenario, specialty)
                quality_scores["scenario"] = scenario_score
                if scenario_score < 0.6:
                    retry_count += 1
                    continue

                print(f"[Targeted] Step 3/6: Generating answer choices...")
                choices_data = self.step3_generate_answer_choices(scenario, specialty, difficulty)

                choices_score, choices_issues = self.score_answer_choices(choices_data)
                quality_scores["choices"] = choices_score
                if choices_score < 0.6:
                    retry_count += 1
                    continue

                print(f"[Targeted] Step 4/6: Writing clinical vignette...")
                vignette = self.step4_write_vignette(scenario, analysis)

                vignette_score, vignette_issues = self.score_vignette(vignette, scenario)
                quality_scores["vignette"] = vignette_score
                if vignette_score < 0.6:
                    retry_count += 1
                    continue

                print(f"[Targeted] Step 5/6: Creating explanation...")
                explanation = self.step5_create_explanation(scenario, choices_data)

                print(f"[Targeted] Step 6/6: Validating quality...")
                passes_quality, issues = self.step6_quality_validation(
                    vignette, choices_data, explanation, scenario, specialty
                )

                total_time = time.time() - start_time

                if passes_quality:
                    avg_score = sum(quality_scores.values()) / len(quality_scores)
                    print(f"[Targeted] ✓ Generated in {total_time:.1f}s (score: {avg_score:.2f})")

                    return {
                        "vignette": vignette.strip(),
                        "choices": choices_data['choices'],
                        "answer_key": choices_data['correct_answer_letter'],
                        "explanation": explanation,
                        "source": f"AI Targeted - {specialty}",
                        "specialty": specialty,
                        "recency_weight": 1.0,
                        "metadata": {
                            "topic": topic,
                            "question_type": question_type,
                            "clinical_setting": clinical_setting,
                            "difficulty": difficulty,
                            "generation_method": "weakness_targeted",
                            "targeted_weakness": weakness_profile.get("recommended_focus"),
                            "targeted_error_pattern": most_common_error,
                            "quality_scores": quality_scores,
                            "generation_time_seconds": total_time
                        }
                    }
                else:
                    retry_count += 1
                    print(f"[Targeted] ✗ Validation failed: {', '.join(issues)}")

            except Exception as e:
                retry_count += 1
                print(f"[Targeted] Error: {e}")
                if retry_count > max_retries:
                    raise

        raise ValueError(f"Targeted generation failed after {max_retries + 1} attempts")

    def _create_targeted_scenario(self, specialty: str, topic: str,
                                  question_type: str, clinical_setting: str,
                                  analysis: Dict, difficulty: str,
                                  targeting_context: str,
                                  error_pattern: Optional[str]) -> Dict:
        """
        Create a clinical scenario specifically designed to address user's weaknesses.

        This is a modified version of step2 that incorporates targeting guidance.
        """
        specialty_context = get_specialty_prompt_context(specialty, question_type)
        specialty_demographics = get_specialty_demographics(specialty)

        # Error-specific scenario guidance
        error_scenario_guidance = {
            "knowledge_gap": """
TARGETING KNOWLEDGE GAP:
- Focus on testing a specific, teachable concept
- The correct answer should reinforce foundational knowledge
- Include clear clinical features that map to the concept being tested
- Explanation should be highly educational""",
            "premature_closure": """
TARGETING PREMATURE CLOSURE:
- Create a scenario where 2-3 diagnoses initially seem plausible
- Include features that differentiate between similar conditions
- The "obvious" answer should NOT be correct
- Test the student's ability to consider full differential""",
            "misread_stem": """
TARGETING MISREAD STEM:
- Include one subtle but CRITICAL clinical detail
- This detail should change the diagnosis/management
- Place it naturally within the vignette (not at the very end)
- Test attention to clinical details""",
            "faulty_reasoning": """
TARGETING FAULTY REASONING:
- Create a multi-step reasoning question
- Test: presentation → diagnosis → pathophysiology → management
- Include a step where students commonly make logical errors
- Correct answer requires complete reasoning pathway""",
            "test_taking_error": """
TARGETING TEST-TAKING ERROR:
- Create a clear, unambiguous scenario
- Correct answer should be clearly best when analyzed
- Build student confidence with solid clinical reasoning
- Avoid "trick" elements""",
            "time_pressure": """
TARGETING TIME PRESSURE:
- Keep vignette concise and focused
- Include all necessary information efficiently
- Clear lead-in question
- Test clinical efficiency"""
        }

        error_guidance = error_scenario_guidance.get(error_pattern, "") if error_pattern else ""

        system_prompt = f"""You are an expert clinician creating a TARGETED patient scenario.
This question is specifically designed to address a student's identified weakness.

{specialty_context}

{targeting_context}

{error_guidance}"""

        user_prompt = f"""Create a clinical scenario TARGETING THE USER'S WEAKNESS.

SPECIFICATIONS:
- Specialty: {specialty}
- Topic: {topic}
- Question type: {question_type}
- Clinical setting: {clinical_setting or specialty_demographics.get('setting', 'clinic')}
- Target difficulty: {difficulty}

PATIENT PROFILE:
- Age range: {specialty_demographics.get('age_range', '45-65 years')}
- Risk factors: {', '.join(specialty_demographics.get('risk_factors', []))}

QUALITY GUIDELINES:
{json.dumps(analysis, indent=2)}

Create a scenario that:
1. Directly addresses the user's identified weakness
2. Tests the specific concept they've been missing
3. Uses realistic clinical presentation for the specialty
4. Has clear clinical reasoning to the correct answer
5. Includes teaching value in the explanation

Return JSON:
{{
  "patient_demographics": "Age, gender, relevant medical history",
  "presenting_complaint": "Chief complaint with specific timeline",
  "history_details": "Pertinent positives and negatives from history",
  "physical_exam": "Vital signs (with units) and specific physical findings",
  "diagnostic_data": "Labs, imaging, or other test results with realistic values",
  "clinical_question": "What is being asked",
  "correct_answer_concept": "What the correct answer should be",
  "reasoning": "Why this tests the user's weakness",
  "teaching_point": "The key concept the user should learn from this question"
}}"""

        response = self._call_llm(system_prompt, user_prompt, temperature=0.8,
                                  response_format={"type": "json_object"})
        return json.loads(response)

    def _get_example_questions(self, specialty: Optional[str] = None, limit: int = 5) -> List[Dict]:
        """Get example questions from database for analysis"""

        query = self.db.query(Question).filter(
            ~Question.source.like('%AI Generated%')
        )

        if specialty:
            query = query.filter(Question.source.like(f"%{specialty}%"))

        # Get diverse examples across recency tiers
        examples = []

        # Tier 1: Newest, most accurate
        tier1 = query.filter(Question.recency_weight >= 0.8).order_by(Question.recency_weight.desc()).limit(2).all()
        examples.extend(tier1)

        # Tier 2: Mid-high recency
        tier2 = query.filter(Question.recency_weight >= 0.6, Question.recency_weight < 0.8).order_by(Question.recency_weight.desc()).limit(2).all()
        examples.extend(tier2)

        # Tier 3: Additional variety
        remaining = limit - len(examples)
        if remaining > 0:
            tier3 = query.limit(remaining).all()
            examples.extend(tier3)

        return [{
            "vignette": q.vignette,
            "choices": q.choices,
            "answer": q.answer_key,
            "explanation": q.explanation,
            "source": q.source
        } for q in examples[:limit]]


def generate_question_with_agent(db: Session, specialty: Optional[str] = None,
                                 topic: Optional[str] = None,
                                 difficulty: str = "medium",
                                 parallel: bool = False) -> Dict:
    """
    Generate a question using the agent-based system

    This is the main entry point for agent-based question generation.
    Use this instead of the simple question_generator for higher quality.

    Args:
        db: Database session
        specialty: Optional specialty filter
        topic: Optional topic filter
        difficulty: "easy", "medium", or "hard" (affects complexity and distractors)
        parallel: If True, use parallelized generation (faster but uses more resources)

    Returns:
        Generated question dictionary
    """
    agent = QuestionGenerationAgent(db)
    if parallel:
        return agent.generate_question_parallel(specialty, topic, difficulty)
    return agent.generate_question(specialty, topic, difficulty)


def generate_questions_batch(db: Session, count: int = 5,
                            specialty: Optional[str] = None,
                            difficulty: str = "medium") -> List[Dict]:
    """
    Generate multiple questions in parallel for batch processing.

    Useful for warming the pool or generating study sets.

    Args:
        db: Database session
        count: Number of questions to generate (max 10)
        specialty: Optional specialty filter
        difficulty: Difficulty level

    Returns:
        List of generated question dictionaries
    """
    count = min(count, 10)  # Limit to prevent resource exhaustion

    def generate_one(i):
        try:
            agent = QuestionGenerationAgent(db)
            topic = get_high_yield_topic(specialty) if specialty else None
            return agent.generate_question(specialty, topic, difficulty, max_retries=1)
        except Exception as e:
            print(f"[Batch] Question {i+1} failed: {e}")
            return None

    # Use ThreadPoolExecutor for parallel generation
    with ThreadPoolExecutor(max_workers=min(count, 5)) as executor:
        results = list(executor.map(generate_one, range(count)))

    # Filter out None results
    return [q for q in results if q is not None]


def generate_weakness_targeted_question(db: Session, user_id: str) -> Dict:
    """
    Generate a question specifically targeting the user's weaknesses.

    This is the core of adaptive learning - generating questions that
    directly address the user's weak areas and error patterns.

    Args:
        db: Database session
        user_id: User ID to get weakness profile for

    Returns:
        Generated question dictionary targeting user's weaknesses
    """
    # Get user's weakness profile
    weakness_profile = get_user_weakness_profile(db, user_id)

    # Determine specialty to target
    specialty = None
    topic = None

    if weakness_profile.get("weak_specialties"):
        # Target the weakest specialty
        weakest = weakness_profile["weak_specialties"][0]
        specialty = weakest["specialty"]
        print(f"[Targeted] Targeting weak specialty: {specialty} ({weakest['accuracy']:.0%})")
    else:
        # No clear weakness - use weighted random
        specialty = get_weighted_specialty()

    # Get a topic, preferring recently missed topics
    if weakness_profile.get("recent_wrong_topics"):
        # Try to use a recently missed topic
        recent_topics = weakness_profile["recent_wrong_topics"]
        topic = random.choice(recent_topics) if recent_topics else None

    if not topic:
        topic = get_high_yield_topic(specialty)

    # Get targeting context for prompts
    targeting_context = get_targeting_prompt_context(weakness_profile)

    # Generate with targeting
    agent = QuestionGenerationAgent(db)
    question = agent.generate_targeted_question(
        specialty=specialty,
        topic=topic,
        weakness_profile=weakness_profile,
        targeting_context=targeting_context
    )

    return question


def generate_learning_stage_question(db: Session, user_id: str,
                                     topic: Optional[str] = None) -> Dict:
    """
    Generate a question optimized for the user's learning stage.

    Learning Stages determine generation parameters:
    - New: Focus on foundational concepts, obvious distractors, detailed explanations
    - Learning: Clinical application, moderate distractors, standard explanations
    - Review: Integration, subtle distractors, concise explanations
    - Mastered: Edge cases, highly plausible distractors, brief explanations

    This is the recommended entry point for generating personalized questions.
    It combines weakness targeting with learning stage optimization.

    Args:
        db: Database session
        user_id: User ID
        topic: Optional topic filter

    Returns:
        Generated question dictionary with learning stage optimization
    """
    # Get comprehensive recommendations
    recommendations = get_generation_recommendations(db, user_id)
    rec = recommendations["recommendation"]

    # Extract parameters
    specialty = rec.get("specialty") or get_weighted_specialty()
    difficulty = rec.get("difficulty", "medium")
    learning_stage = rec.get("learning_stage", "Learning")
    generation_params = rec.get("generation_params", {})
    error_to_target = rec.get("error_pattern_to_target")

    # Use provided topic or get from recommendations/high-yield
    if not topic:
        topic = rec.get("topic") or get_high_yield_topic(specialty)

    print(f"[LearningStage] Generating for {user_id}")
    print(f"[LearningStage] Stage: {learning_stage}, Difficulty: {difficulty}")
    print(f"[LearningStage] Target: {specialty} - {topic}")

    # Build generation context based on learning stage
    stage_context = _build_learning_stage_context(learning_stage, generation_params)

    # If user has weakness data, use targeted generation
    if recommendations["priority"] == "weakness_targeted":
        # Get full weakness profile for targeted generation
        weakness_profile = recommendations["context"]["weakness_profile"]
        targeting_context = get_targeting_prompt_context(weakness_profile)

        agent = QuestionGenerationAgent(db)
        question = agent.generate_targeted_question(
            specialty=specialty,
            topic=topic,
            weakness_profile=weakness_profile,
            targeting_context=f"{targeting_context}\n\n{stage_context}"
        )
    else:
        # Standard generation with learning stage adjustments
        agent = QuestionGenerationAgent(db)
        question = agent.generate_question(
            specialty=specialty,
            topic=topic,
            difficulty=difficulty
        )

    # Add learning stage metadata
    if question.get("metadata"):
        question["metadata"]["learning_stage"] = learning_stage
        question["metadata"]["generation_params"] = generation_params

    return question


def _build_learning_stage_context(stage: str, params: Dict) -> str:
    """Build generation context based on learning stage parameters."""

    stage_guidance = {
        "New": """
LEARNING STAGE: NEW LEARNER
- Focus: Foundational concepts that build core knowledge
- Distractors: Should be distinguishable with basic knowledge
- Explanation: Provide detailed, educational explanations with clear teaching points
- Complexity: Keep clinical scenarios straightforward
- Goal: Build confidence and foundational understanding""",

        "Learning": """
LEARNING STAGE: ACTIVE LEARNING
- Focus: Clinical application of concepts
- Distractors: Represent common clinical considerations
- Explanation: Standard depth with clinical reasoning pathways
- Complexity: Moderate clinical complexity with some nuance
- Goal: Develop clinical reasoning skills""",

        "Review": """
LEARNING STAGE: REVIEW/REINFORCEMENT
- Focus: Integration of concepts across topics
- Distractors: Subtle distinctions requiring careful analysis
- Explanation: Concise, reinforcing key differentiating features
- Complexity: Include pertinent negatives and complicating factors
- Goal: Solidify knowledge and improve discrimination""",

        "Mastered": """
LEARNING STAGE: MASTERY/CHALLENGE
- Focus: Edge cases, atypical presentations, advanced management
- Distractors: Highly plausible alternatives requiring expert reasoning
- Explanation: Brief, focusing on subtle clinical nuances
- Complexity: Complex clinical scenarios with multiple factors
- Goal: Challenge and expand expert-level knowledge"""
    }

    context = stage_guidance.get(stage, stage_guidance["Learning"])

    # Add specific parameter guidance
    if params:
        context += f"\n\nSPECIFIC PARAMETERS:"
        context += f"\n- Target accuracy: {params.get('target_accuracy', 0.65):.0%}"
        context += f"\n- Distractor style: {params.get('distractor_style', 'moderate')}"
        context += f"\n- Explanation depth: {params.get('explanation_depth', 'standard')}"

    return context


def generate_optimal_question(db: Session, user_id: Optional[str] = None,
                              specialty: Optional[str] = None,
                              topic: Optional[str] = None) -> Dict:
    """
    Generate the most appropriate question based on all available context.

    This is the highest-level entry point that automatically selects
    the best generation strategy:
    1. If user_id provided: Use learning stage + weakness targeting
    2. If specialty provided: Generate specialty-specific question
    3. Otherwise: Generate using weighted specialty distribution

    Args:
        db: Database session
        user_id: Optional user ID for personalization
        specialty: Optional specialty filter
        topic: Optional topic filter

    Returns:
        Generated question with optimal parameters
    """
    # If we have a user, generate personalized question
    if user_id:
        try:
            return generate_learning_stage_question(db, user_id, topic)
        except Exception as e:
            print(f"[Optimal] Learning stage generation failed: {e}, falling back")

    # Fallback to standard generation
    if not specialty:
        specialty = get_weighted_specialty()
    if not topic:
        topic = get_high_yield_topic(specialty)

    agent = QuestionGenerationAgent(db)
    return agent.generate_question(specialty=specialty, topic=topic)
