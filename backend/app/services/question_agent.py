"""
Agent-based Question Generation Service for ShelfSense
Uses multi-step reasoning with specialized agents to generate high-quality USMLE questions
"""

import os
import json
import random
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
                                       analysis: Dict) -> Dict:
        """Step 2: Create a realistic clinical scenario with specific patient details"""

        system_prompt = """You are an expert clinician creating realistic patient scenarios.
You understand how diseases actually present in clinical practice, with realistic lab values,
physical exam findings, and patient demographics."""

        user_prompt = f"""Create a realistic clinical scenario for a USMLE Step 2 CK question.

SPECIFICATIONS:
- Specialty: {specialty}
- Topic: {topic}
- Question type: {question_type}
- Clinical setting: {clinical_setting}

QUALITY GUIDELINES FROM ANALYSIS:
{json.dumps(analysis, indent=2)}

Create a patient scenario that:
1. Uses realistic demographics appropriate for the condition
2. Has a classic presentation (not zebra cases)
3. Includes specific vital signs and lab values that are clinically realistic
4. Contains both pertinent positives AND negatives
5. Has enough detail to answer without seeing options
6. Matches the clinical detail level from the analyzed examples

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

    def step3_generate_answer_choices(self, scenario: Dict, specialty: str) -> Dict:
        """Step 3: Generate plausible answer choices with one clearly best answer"""

        system_prompt = """You are an expert USMLE question writer specializing in creating
plausible distractors. You understand what makes answer choices challenging but fair."""

        user_prompt = f"""Create 5 answer choices for this clinical scenario.

SCENARIO:
{json.dumps(scenario, indent=2)}

REQUIREMENTS:
1. Choice corresponding to "{scenario['correct_answer_concept']}" must be the single best answer
2. All 5 choices must be DISTINCT (absolutely no duplicates or near-duplicates)
3. All choices must be the SAME TYPE (all diagnoses OR all treatments OR all mechanisms)
4. All choices must be plausible given the clinical context (no "gimmies")
5. Distractors should represent common mistakes or conditions in the differential
6. Use specific medical terminology (not vague descriptions)
7. Follow current evidence-based guidelines

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

    def step6_quality_validation(self, vignette: str, choices_data: Dict,
                                 explanation: Dict, scenario: Dict) -> Tuple[bool, List[str]]:
        """Step 6: Validate question quality and identify issues"""

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

Return JSON:
{{
  "passes_quality": true/false,
  "issues_found": ["List of specific issues", "or empty array if passes"],
  "severity": "none/minor/major",
  "clinical_accuracy_score": 1-10,
  "nbme_standards_score": 1-10
}}"""

        response = self._call_llm(system_prompt, user_prompt, temperature=0.2,
                                  response_format={"type": "json_object"})
        validation = json.loads(response)

        return validation['passes_quality'], validation['issues_found']

    def generate_question(self, specialty: Optional[str] = None,
                         topic: Optional[str] = None,
                         max_retries: int = 2) -> Dict:
        """
        Generate a high-quality USMLE question using multi-step agent reasoning

        Args:
            specialty: Medical specialty (auto-selected if None)
            topic: Specific topic (auto-selected if None)
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
        clinical_setting = random.choice(CLINICAL_SETTINGS)

        # Get example questions for analysis
        examples = self._get_example_questions(specialty, limit=5)

        retry_count = 0
        while retry_count <= max_retries:
            try:
                print(f"[Agent] Step 1/6: Analyzing {len(examples)} example questions...")
                analysis = self.step1_analyze_examples(specialty, examples)

                print(f"[Agent] Step 2/6: Creating clinical scenario for {topic}...")
                scenario = self.step2_create_clinical_scenario(
                    specialty, topic, question_type, clinical_setting, analysis
                )

                print(f"[Agent] Step 3/6: Generating answer choices...")
                choices_data = self.step3_generate_answer_choices(scenario, specialty)

                print(f"[Agent] Step 4/6: Writing clinical vignette...")
                vignette = self.step4_write_vignette(scenario, analysis)

                print(f"[Agent] Step 5/6: Creating explanation...")
                explanation = self.step5_create_explanation(scenario, choices_data)

                print(f"[Agent] Step 6/6: Validating quality...")
                passes_quality, issues = self.step6_quality_validation(
                    vignette, choices_data, explanation, scenario
                )

                if passes_quality:
                    print(f"[Agent] ✓ Question passed quality validation!")

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
                            "generation_method": "multi_step_agent"
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
                                 topic: Optional[str] = None) -> Dict:
    """
    Generate a question using the agent-based system

    This is the main entry point for agent-based question generation.
    Use this instead of the simple question_generator for higher quality.
    """
    agent = QuestionGenerationAgent(db)
    return agent.generate_question(specialty, topic)
