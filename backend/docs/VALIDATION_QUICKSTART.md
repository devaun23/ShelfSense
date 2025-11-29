# Validation Framework Quick Start

5-minute guide to validating 2,500 AI-generated questions.

## Prerequisites

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Ensure environment variables are set
export ANTHROPIC_API_KEY="your_key"  # For Claude Haiku validation
export DATABASE_URL="your_db_url"
```

## Quick Validation

### 1. Prepare Your Questions

Questions must be in JSON format with this structure:

```json
{
  "questions": [
    {
      "id": "q1",
      "vignette": "A 65-year-old man with hypertension (BP 180/110 mmHg) presents with chest pain...",
      "choices": [
        "A. Aspirin 325 mg PO",
        "B. Nitroglycerin sublingual",
        "C. Emergent cardiac catheterization",
        "D. IV beta-blocker",
        "E. Morphine for pain control"
      ],
      "answer_key": "C",
      "explanation": {
        "quick_answer": "Anterior STEMI requires emergent reperfusion.",
        "clinical_reasoning": "ST elevations indicate acute MI...",
        "correct_answer_explanation": "...",
        "distractor_explanations": {
          "A": "...",
          "B": "...",
          "D": "...",
          "E": "..."
        },
        "principle": "...",
        "deep_dive": "..."
      },
      "specialty": "internal_medicine",
      "subsystem": "cardiology"
    }
  ]
}
```

### 2. Run Validation

```bash
python scripts/validate_2500_questions.py \
    --input your_questions.json \
    --output validation_report.json
```

### 3. Review Results

The script outputs:
- Console summary with acceptance rate, elite rate, issues
- `validation_report.json` with detailed results
- List of questions needing human review

## Interpreting Results

### Good Validation Run

```
VALIDATION SUMMARY
==================
Total Questions: 2500
Accepted: 2125 (85.0%)
Elite Questions: 1275 (60.0%)
Average Score: 82.3/100
Critical Issues: 0
Quality Gate Failures: 0

✅ Validation complete - all quality gates passed!
```

### Problematic Run

```
VALIDATION SUMMARY
==================
Total Questions: 2500
Accepted: 1500 (60.0%)  ⚠️ Below 85% threshold
Elite Questions: 500 (33.3%)  ⚠️ Below 60% threshold
Critical Issues: 15  ⚠️ Above 10 threshold

Quality Gate Failures: 3
  - stage2_pass_rate at question 500: PAUSE_FOR_INVESTIGATION
  - max_critical_issues at question 1200: STOP_GENERATION
```

**Action**: Review generation prompts, check for systematic issues.

## Common Issues & Fixes

### Issue: Low Stage 1 Pass Rate (<90%)

**Symptoms**:
```
stage1_passed: 1800/2500 (72%)
```

**Causes**:
- Vague clinical terms (no specific values)
- Missing vital signs in vignettes
- Incomplete explanations

**Fix**:
Update generation prompt to require:
```python
REQUIRED_IN_VIGNETTE = [
    "Age and sex (e.g., 65-year-old man)",
    "Chief complaint",
    "Vital signs with numeric values (BP 120/80, HR 72, Temp 37.2C)",
    "Physical exam findings",
    "Relevant lab values with units"
]

REQUIRED_IN_EXPLANATION = [
    "quick_answer (≤30 words)",
    "clinical_reasoning",
    "correct_answer_explanation",
    "distractor_explanations (all 5 choices A-E)",
    "principle",
    "deep_dive (mechanism with arrows →)"
]
```

### Issue: Low Stage 2 Pass Rate (<75%)

**Symptoms**:
```
stage2_passed: 1500/2250 (67%)
medical_accuracy issues: 200
```

**Causes**:
- Incorrect medical facts
- Outdated guidelines
- Ambiguous correct answers

**Fix**:
- Switch from Ollama to GPT-4 for generation
- Add guideline version to prompts: "Use 2024 USPSTF/ACC/AHA guidelines"
- Include specific clinical scenarios from UpToDate

### Issue: Low Elite Rate (<60%)

**Symptoms**:
```
elite_count: 800/2000 (40%)
Common issues:
  - Missing mechanism arrows: 400
  - No distractor psychology: 350
  - Vague quick answers: 250
```

**Causes**:
- Explanations lack depth
- No "why wrong answers tempting" analysis
- Missing causal chains

**Fix**:
Update explanation generation prompt:
```python
ELITE_EXPLANATION_TEMPLATE = """
quick_answer: [In ≤30 words, what first-sentence pattern points to diagnosis]

clinical_reasoning: [Step-by-step clinical reasoning with mechanism arrows]
Example: "Hypertension → LV hypertrophy → diastolic dysfunction → SOB"

correct_answer_explanation: [Why this answer is correct]

distractor_explanations:
  A: "This is TEMPTING because [common misconception], but WRONG because [specific reason]"
  B: "Students often choose this if they [forgot/missed/overlooked X], but..."
  ...

principle: [High-yield clinical pearl]

deep_dive: [Mechanism with arrows: risk factor → pathology → finding → management]
"""
```

### Issue: Critical Misinformation Detected

**Symptoms**:
```
CRITICAL: Dangerous misinformation detected in question 247
Issue: Contraindicated drug listed as correct answer
```

**Immediate Actions**:
1. **Stop generation immediately**
2. **Review all similar questions** for the same error
3. **Update prompts** to explicitly check contraindications
4. **Re-validate** existing questions

**Prevention**:
Add to generation prompt:
```python
SAFETY_CHECKS = [
    "Verify drug contraindications (pregnancy, renal failure, etc.)",
    "Check age-appropriate dosing",
    "Confirm no harmful treatment delays",
    "Validate against current black box warnings"
]
```

## Advanced Options

### Human Review Sample

Generate sample for expert review:

```bash
python scripts/validate_2500_questions.py \
    --input questions.json \
    --sample-size 333 \
    --output report.json
```

This creates `report.json` with `human_review_sample.question_ids` - questions to review manually.

### Plagiarism Check

Check against existing question banks:

```bash
python scripts/validate_2500_questions.py \
    --input new_questions.json \
    --check-plagiarism existing_questions.json \
    --output report.json
```

Flags questions >70% similar to known questions.

### Disable Quality Gates

Process all questions without stopping (not recommended):

```bash
python scripts/validate_2500_questions.py \
    --input questions.json \
    --disable-gates \
    --output report.json
```

Use this only for testing or final cleanup batches.

## Next Steps

After validation:

1. **Review Report**: Check `validation_report.json`
2. **Human Sample**: Review the sampled questions
3. **Calculate Confidence**: Use population estimate
4. **Deploy Questions**: Import accepted questions to database
5. **Monitor IRT**: Track performance after 50+ attempts

## Programmatic Usage

For integration into your pipeline:

```python
import asyncio
from app.database import SessionLocal
from app.services.batch_validation_pipeline import BatchValidationPipeline

async def validate_batch():
    db = SessionLocal()
    pipeline = BatchValidationPipeline(db)

    # Load questions
    with open("questions.json") as f:
        data = json.load(f)
    questions = data["questions"]

    # Validate
    report = await pipeline.validate_batch(
        questions=questions,
        enable_gates=True
    )

    # Check results
    if report.acceptance_rate >= 0.85:
        print(f"✅ Passed: {report.accepted}/{report.total_questions}")
        return True
    else:
        print(f"❌ Failed: {report.acceptance_rate:.1%} acceptance rate")
        return False

# Run
asyncio.run(validate_batch())
```

## Cost Estimation

For 2,500 questions:

| Stage | Tool | Cost per 1k | Total Cost |
|-------|------|-------------|------------|
| Stage 1 | Python regex | $0 | $0 |
| Stage 2 | Claude Haiku | $0.25 | $0.56 |
| Stage 3 | Python rules | $0 | $0 |
| Stage 6 | String matching | $0 | $0 |
| **Total** | | | **$0.56** |

Human review (Stage 5) requires expert time, not API costs.

## Time Estimation

| Phase | Time |
|-------|------|
| Stage 1 (automated) | 1 hour |
| Stage 2 (AI validation) | 2 hours |
| Stage 3 (elite validation) | 30 min |
| Human sample (333 questions) | 10-15 hours |
| **Total** | **~1-2 days** |

## Troubleshooting

### ModuleNotFoundError

```bash
# Ensure you're in backend directory
cd backend
pip install -r requirements.txt
```

### Database Connection Error

```bash
# Check DATABASE_URL is set
echo $DATABASE_URL

# For local SQLite
export DATABASE_URL="sqlite:///./shelfsense.db"
```

### Out of Memory

For very large batches (>5,000 questions):

```python
# Process in chunks
for i in range(0, len(questions), 1000):
    chunk = questions[i:i+1000]
    report = await pipeline.validate_batch(chunk)
    # Save intermediate results
```

## Support

- **Full Documentation**: `/backend/docs/VALIDATION_FRAMEWORK.md`
- **Tests**: Run `pytest backend/tests/test_batch_validation.py`
- **Issues**: Check logs in `backend/logs/validation.log`

---

**Quick Reference Card**:

```bash
# Validate questions
python scripts/validate_2500_questions.py --input questions.json

# With plagiarism check
python scripts/validate_2500_questions.py \
    --input new.json \
    --check-plagiarism old.json

# Run tests
pytest backend/tests/test_batch_validation.py -v

# Check logs
tail -f backend/logs/validation.log
```
