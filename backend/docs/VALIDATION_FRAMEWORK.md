# Elite Quality Validation Framework

Comprehensive validation pipeline for 2,500+ AI-generated USMLE Step 2 CK questions, ensuring 285+ scorer quality.

## Overview

This framework implements a **6-stage validation pipeline** combining automated checks, AI validation, statistical analysis, and human sampling to achieve:

- **85%+ acceptance rate** (currently 75%)
- **Minimum quality score**: 85/100 (elite threshold)
- **Zero dangerous misinformation**
- **NBME-style conformance**
- **Cost efficiency**: ~$0.56 for 2,500 questions

---

## Pipeline Stages

### Stage 1: Automated Pre-Flight Checks (Zero Cost)

**Goal**: Filter structurally broken questions before expensive AI validation

**Tools**: `question_validators.py`

**Checks**:
- Vague clinical terms (e.g., "hypotensive" without BP value)
- Testwiseness cues (length, absolute terms, grammatical errors)
- Distractor homogeneity (all same type)
- Duplicate/near-duplicate choices
- Structural completeness (all 5 choices, valid answer key)
- Explanation fields (10 required fields)

**Auto-Reject Criteria**:
- Missing answer choices
- Invalid answer key (not A-E)
- Duplicate choices (>85% similarity)
- Missing explanation fields
- >3 vague clinical terms
- Critical testwiseness errors

**Expected Rejection**: 5-10% (125-250 questions)

**Time**: <1 second per question

---

### Stage 2: AI Medical Validation (Low Cost)

**Goal**: Validate medical accuracy and NBME style

**Tools**: `multi_model_validator.py` (Claude Haiku)

**Validation Dimensions** (0-100 each):
- Medical accuracy (factual correctness)
- Distractor quality (plausibility)
- Vignette quality (clinical realism)
- NBME style conformance
- Explanation completeness

**Auto-Reject Criteria**:
- `medical_accuracy < 80`
- `overall_score < 70`
- `dangerous_misinformation == true`

**Expected Pass Rate**: 75-80%

**Cost**: $0.25 per 1,000 questions

**Time**: ~2 seconds per question

---

### Stage 3: Elite Explanation Validation (Zero Cost)

**Goal**: Ensure 285+ scorer level explanations

**Tools**: `elite_quality_validator.py`

**Elite Quality Dimensions**:
- **Pattern Recognition** (20%): First-sentence diagnosis teaching
- **Mechanism Depth** (25%): Explicit causal chains with arrows
- **Distractor Coverage** (20%): All 5 choices explained
- **Distractor Psychology** (15%): WHY wrong answers are tempting
- **Threshold Explicitness** (10%): Numbers with normal ranges
- **Brevity** (10%): Quick answer ≤30 words

**Elite Requirements**:
```python
elite_requirements = {
    "pattern_recognition": 0.7,
    "mechanism_depth": 0.7,
    "distractor_psychology": 0.7,
    "threshold_explicitness": 0.6,
    "distractor_coverage": 1.0,  # Must explain ALL 5
    "brevity": 0.7,
}
```

**Elite Threshold**: 85/100

**Auto-Reject Criteria**:
- Score <70
- Missing explanations for any choice
- No mechanism arrows
- Quick answer >50 words

**Expected Pass Rate**: 60-70%

**Time**: <1 second per question

---

### Stage 4: Statistical IRT Validation (Post-Deployment)

**Goal**: Empirically validate difficulty and discrimination

**Tools**: `item_response_theory.py`

**Metrics** (requires 50+ attempts):
- **P-value** (difficulty): 0.40-0.85 target
- **Discrimination index**: >0.20 target
- **Distractor selection**: Each 5-30%

**Auto-Flag for Review**:
- P-value <0.30 (too hard) or >0.90 (too easy)
- Discrimination <0.20 (poor item)
- Discrimination <0 (CRITICAL - flawed question)
- Any distractor selected >30% (too attractive)

**This stage runs AFTER deployment** as questions accumulate attempts.

---

### Stage 5: Medical Fact-Checking (Sample-Based)

**Goal**: Expert validation of medical accuracy

**Coverage**: 10% stratified sample (~250 questions for 2,500)

**Stratified Sampling Strategy**:
```python
strata_sampling = {
    "high_confidence": 0.05,    # 5% of 90-100 score
    "medium_confidence": 0.10,  # 10% of 75-89 score
    "borderline": 0.50,          # 50% of 65-74 score
    "complex_topics": 0.20       # 20% of high-risk specialties
}

high_risk_specialties = [
    "endocrinology",
    "rheumatology",
    "hematology",
    "nephrology"
]
```

**Expert Review Checklist**:
- [ ] Correct answer is definitively correct per current guidelines
- [ ] Distractors are plausible but incorrect
- [ ] Vignette is clinically realistic
- [ ] No dangerous misinformation
- [ ] Explanation teaches clinical reasoning
- [ ] Appropriate difficulty for Step 2 CK

**Sample Size Calculation**:
- For 2,500 questions
- 95% confidence level
- 5% margin of error
- **Result: ~333 questions**

**Time**: 2-3 minutes per question = 10-15 hours total

---

### Stage 6: Plagiarism Detection (Zero Cost)

**Goal**: Ensure originality, avoid copyright issues

**Method**: Fuzzy string matching against known question banks

**Thresholds**:
- **>85% similarity**: CRITICAL - auto-reject (likely plagiarism)
- **>70% similarity**: WARNING - manual review
- **<70% similarity**: OK

**Expected Rejection**: <1% (AI-generated should be original)

**Time**: <1 second per question

---

## Quality Metrics Tracked

### Per-Question Metrics

```python
question_metrics = {
    # Overall
    "validation_score": float,          # 0-100 composite
    "elite_score": float,               # 0-100 elite quality
    "is_elite": bool,                   # >= 85

    # Medical Accuracy
    "medical_accuracy_score": float,    # 0-100
    "dangerous_misinformation": bool,
    "guideline_alignment": float,

    # Explanation Quality
    "pattern_recognition": float,       # 0-1
    "mechanism_depth": float,
    "distractor_psychology": float,
    "threshold_explicitness": float,
    "brevity": float,

    # Post-Deployment
    "p_value": float,                   # IRT difficulty
    "discrimination_index": float,      # IRT discrimination
}
```

### Batch-Level Metrics

```python
batch_metrics = {
    "total_questions": int,
    "accepted": int,
    "rejected": int,
    "acceptance_rate": float,           # Target: 85%+
    "elite_count": int,
    "elite_rate": float,                # Target: 60%+
    "avg_validation_score": float,
    "critical_issues": int,
}
```

---

## Red Flags (Auto-Reject)

### Critical Red Flags

1. **Dangerous Misinformation**
   - Contraindicated drug as first-line
   - Inverted normal ranges
   - Surgery for stable patient
   - Pregnancy contraindications listed as correct

2. **Ambiguous Correct Answer**
   - Multiple distractors selected >25% by strong students
   - Two or more "correct" answers

3. **Plagiarism**
   - >85% similarity to known question

4. **Missing Critical Information**
   - Diagnosis question without vital signs
   - Management question without diagnosis

5. **Structural Errors**
   - Not exactly 5 choices
   - Invalid answer key
   - Empty vignette

### High-Severity Red Flags (Manual Review)

1. **Outdated Guidelines**
   - Old diabetes thresholds (HbA1c <6.5)
   - Deprecated screening guidelines
   - Superseded treatment protocols

2. **Negative Discrimination** (IRT)
   - Strong students perform worse than weak students
   - Indicates flawed question

3. **Low Discrimination** (IRT)
   - Doesn't separate strong from weak students
   - <0.15 discrimination index

4. **Extreme Difficulty**
   - >92% correct (too easy)
   - <28% correct (too hard)

---

## Quality Gates

Progressive gates that pause/stop processing on quality issues:

### Gate Thresholds

```python
QUALITY_GATES = {
    "stage1_pass_rate": 0.90,           # 90% must pass automated checks
    "stage2_pass_rate": 0.75,           # 75% must pass AI validation
    "stage3_elite_rate": 0.60,          # 60% should be elite
    "overall_accept_rate": 0.85,        # 85% final acceptance

    "max_critical_issues": 10,          # Stop if >10 critical issues
    "max_reject_streak": 20,            # Pause if 20 consecutive rejects
}
```

### Gate Actions

- **PAUSE_FOR_INVESTIGATION**: Flag for review, continue processing
- **INVESTIGATE_GENERATOR**: Pause to check generation prompts
- **STOP_GENERATION**: Critical issue, stop immediately

---

## Usage

### Command-Line Validation

```bash
# Validate batch of questions
python scripts/validate_2500_questions.py \
    --input questions.json \
    --output validation_report.json \
    --sample-size 333 \
    --check-plagiarism known_questions.json

# Disable quality gates (process all questions)
python scripts/validate_2500_questions.py \
    --input questions.json \
    --disable-gates
```

### Programmatic Usage

```python
from app.database import SessionLocal
from app.services.batch_validation_pipeline import BatchValidationPipeline

# Initialize
db = SessionLocal()
pipeline = BatchValidationPipeline(db)

# Load questions
questions = load_questions("questions.json")

# Validate
report = await pipeline.validate_batch(
    questions=questions,
    enable_gates=True,
    human_review_sample_size=333
)

# Results
print(f"Accepted: {report.accepted}/{report.total_questions}")
print(f"Elite: {report.elite_count} ({report.elite_rate:.1%})")
print(f"Cost: ${report.estimated_cost:.2f}")
```

---

## Testing Strategy for 2,500 Questions

### Phased Approach

**Phase 1: Automated Pre-Flight (1 day)**
- Run all 2,500 through Stage 1
- Cost: $0
- Time: ~1 hour
- Expected: 2,250 pass (90%)

**Phase 2: AI Validation (1 day)**
- Run 2,250 through Stage 2
- Cost: ~$0.56
- Time: ~2 hours
- Expected: 1,800 pass (80%)

**Phase 3: Elite Validation (immediate)**
- Run 1,800 through Stage 3
- Cost: $0
- Time: ~30 minutes
- Expected: 1,400 elite (78%)

**Phase 4: Human Sample (1 day)**
- Review 333 stratified sample
- Cost: Expert time
- Time: 10-15 hours
- Expected: 95% accuracy

**Phase 5: Statistical Confidence**
- Calculate population estimate from sample
- If sample shows 95% accuracy → estimate 92-98% (95% CI)

**Phase 6: Post-Deployment IRT (ongoing)**
- Monitor first 50 attempts per question
- Flag for review based on IRT metrics

### Total Estimates

- **Total Cost**: $0.56 (AI validation only)
- **Total Time**: ~5 days (including human review)
- **Final Quality Estimate**: 92-98% high quality (95% CI)

---

## Statistical Confidence

### Sample Size Calculation

For population of 2,500 questions:
- **Confidence Level**: 95%
- **Margin of Error**: 5%
- **Required Sample**: 333 questions

### Population Estimate

If 315 out of 333 sampled questions pass (94.6%):
- **95% Confidence Interval**: 91.8% - 96.7%
- **Estimated Passing**: 2,296-2,418 out of 2,500 questions

### Sampling Method

**Stratified random sampling** ensures representation across:
- Validation scores (high/medium/borderline)
- Subspecialties (cardiology, pulmonology, etc.)
- Complexity (high-risk topics oversampled)

---

## Continuous Improvement

### Feedback Loop from User Performance

Questions are continuously monitored post-deployment:

1. **IRT Analysis** (after 50+ attempts)
   - Recalibrate difficulty
   - Flag discrimination issues
   - Identify problematic distractors

2. **User Reports** (>3 "unclear" reports)
   - Regenerate explanation with GPT-4
   - Re-validate with elite validator

3. **Automatic Enhancement**
   - Low discrimination → regenerate distractors
   - Too easy/hard → adjust difficulty
   - Negative discrimination → expert review

---

## File Reference

### Core Files

- **Pipeline**: `/backend/app/services/batch_validation_pipeline.py`
- **Stage 1**: `/backend/app/services/question_validators.py`
- **Stage 2**: `/backend/app/services/multi_model_validator.py`
- **Stage 3**: `/backend/app/services/elite_quality_validator.py`
- **Stage 4**: `/backend/app/services/item_response_theory.py`

### Scripts

- **Validation Script**: `/scripts/validate_2500_questions.py`
- **Tests**: `/backend/tests/test_batch_validation.py`

### Documentation

- **This File**: `/backend/docs/VALIDATION_FRAMEWORK.md`

---

## Key Performance Indicators

### Target Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Acceptance Rate | 85%+ | 75% |
| Elite Rate | 60%+ | TBD |
| Medical Accuracy | 100% (no misinformation) | TBD |
| NBME Style Conformance | 90%+ | TBD |
| Cost per 1,000 Questions | <$1.00 | $0.25 |
| Validation Throughput | 500/day | TBD |

### Success Criteria

- [ ] 85%+ acceptance rate
- [ ] 60%+ elite quality explanations
- [ ] Zero critical misinformation detected
- [ ] <10 quality gate failures
- [ ] 95% confidence in population estimate

---

## Troubleshooting

### Low Acceptance Rate (<75%)

**Investigation Steps**:
1. Check Stage 1 pass rate - are automated checks too strict?
2. Review Stage 2 rejections - are there consistent issues?
3. Inspect generation prompts - are they producing low-quality questions?
4. Run sample through GPT-4 instead of Ollama

### High Critical Issues Count (>10)

**Immediate Actions**:
1. STOP question generation
2. Review critical issues for patterns
3. Update generation prompts to avoid misinformation
4. Re-validate existing questions for similar issues

### Quality Gate Failures

**Pause Actions**:
1. Analyze failure reason (pass rate, reject streak, etc.)
2. Sample 20 recent questions for manual review
3. Identify systematic issues in generation
4. Adjust prompts/parameters before continuing

---

## Best Practices

### Before Validation

1. **Verify Input Format**: Ensure all questions have required fields
2. **Set Sample Size**: Calculate based on confidence needs
3. **Enable Quality Gates**: Don't disable unless testing
4. **Prepare Known Questions**: For plagiarism checking

### During Validation

1. **Monitor Progress**: Check logs every 100 questions
2. **Watch for Gate Failures**: Investigate immediately
3. **Track Costs**: Ensure within budget
4. **Save Intermediate Results**: In case of failures

### After Validation

1. **Review Report**: Check acceptance rate and elite rate
2. **Analyze Rejections**: Identify improvement areas
3. **Conduct Human Review**: Sample validation
4. **Calculate Confidence**: Population estimate
5. **Deploy Accepted Questions**: To production
6. **Monitor IRT Metrics**: After 50+ attempts per question

---

## Future Enhancements

### Planned Features

1. **Multi-Expert Review**: Consensus from 2+ reviewers
2. **AI-Powered Explanation Enhancement**: Automatic regeneration
3. **Real-Time IRT Dashboard**: Live monitoring of deployed questions
4. **Guideline Version Tracking**: Auto-flag when guidelines update
5. **Student Feedback Integration**: Incorporate user reports

### Research Directions

1. **Adaptive Difficulty Calibration**: Machine learning for p-value prediction
2. **Cognitive Bias Detection**: Identify reasoning pitfalls
3. **Explanation Quality NLP**: Automated readability and completeness
4. **Cross-Validation with NBME**: Correlate with official assessment performance

---

## Contact

For questions or issues with the validation framework:

- **GitHub Issues**: [Create an issue](https://github.com/yourusername/shelfsense/issues)
- **Documentation**: `/backend/docs/VALIDATION_FRAMEWORK.md`
- **Tests**: `/backend/tests/test_batch_validation.py`

---

## Appendix: Validation Report Example

```json
{
  "validated_at": "2025-11-29T12:00:00Z",
  "input_file": "internal_medicine_2500.json",
  "total_questions": 2500,
  "accepted": 2125,
  "rejected": 375,
  "needs_review": 0,
  "acceptance_rate": 0.85,
  "elite_count": 1275,
  "elite_rate": 0.60,
  "avg_score": 82.3,
  "median_score": 84.0,
  "critical_issues_count": 3,
  "quality_gate_failures": [],
  "stage_breakdown": {
    "stage1_passed": 2250,
    "stage2_passed": 1900,
    "stage3_elite": 1275
  },
  "issue_breakdown": {
    "vague_clinical_terms": 45,
    "low_elite_score": 200,
    "medical_accuracy_low": 30
  },
  "estimated_cost": 0.56,
  "total_time_seconds": 3600,
  "human_review_sample": {
    "sample_size": 333,
    "confidence_level": 0.95,
    "margin_of_error": 0.05
  },
  "population_estimate": {
    "sample_pass_rate": 0.946,
    "ci_lower": 0.918,
    "ci_upper": 0.967,
    "estimated_passing_questions": 2365,
    "estimated_range": [2295, 2418]
  }
}
```

---

**Last Updated**: 2025-11-29
**Version**: 1.0
**Maintainer**: ShelfSense Engineering Team
