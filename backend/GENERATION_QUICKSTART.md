# Internal Medicine Question Generation Quickstart

Quick reference for generating 2,500 IM questions using the manifest strategy.

---

## Overview

- **Strategy Document**: `IM_QUESTION_GENERATION_MANIFEST.md` (full details)
- **Generation Script**: `scripts/batch_generate_im.py`
- **Progress Monitor**: `scripts/monitor_generation_progress.py`

**Goal**: Generate 2,500 elite-quality IM questions in 6 weeks (42 days)

---

## Quick Commands

### 1. Check Current Progress
```bash
python scripts/monitor_generation_progress.py
```

**Output**: Shows current vs target for subspecialties, task types, and difficulties

---

### 2. Generate Questions (Phase-Based)

#### Phase 1: Critical Gaps (800 Questions)
```bash
# Batch 1 (50 questions)
python scripts/batch_generate_im.py phase --phase 1 --batch 1

# Batch 2 (50 questions)
python scripts/batch_generate_im.py phase --phase 1 --batch 2

# Continue through Batch 16 (800 total)
```

**Phase 1 Focus**: Ethics, Biostatistics, Endocrinology, Hematology/Oncology, Renal, Neurology

#### Phase 2: High-Yield Core (900 Questions)
```bash
# Batch 1
python scripts/batch_generate_im.py phase --phase 2 --batch 1

# Continue through Batch 18 (900 total)
```

**Phase 2 Focus**: Cardiology, Pulmonology, Gastroenterology, Infectious Disease

#### Phase 3: Completion (800 Questions)
```bash
# Batch 1
python scripts/batch_generate_im.py phase --phase 3 --batch 1

# Continue through Batch 16 (800 total)
```

**Phase 3 Focus**: Fill remaining gaps across all subspecialties

---

### 3. Generate Questions (Custom)

```bash
# 50 Cardiology questions (all task types, all difficulties)
python scripts/batch_generate_im.py custom \
  --subspecialty Cardiology \
  --count 50

# 25 Endocrinology pharmacotherapy questions
python scripts/batch_generate_im.py custom \
  --subspecialty Endocrinology \
  --count 25 \
  --task pharmacotherapy

# 40 hard Pulmonology questions
python scripts/batch_generate_im.py custom \
  --subspecialty Pulmonology \
  --count 40 \
  --difficulty hard
```

**Available Subspecialties**:
- Cardiology
- Pulmonology
- Gastroenterology
- Infectious Disease
- Renal
- Endocrinology
- Hematology/Oncology
- Rheumatology
- Neurology
- Immunology/Allergy
- Ethics/Professionalism
- Biostatistics/Epidemiology
- Multisystem

**Available Task Types**:
- diagnosis
- lab_diagnostic
- mixed_management
- pharmacotherapy
- clinical_interventions
- prognosis
- health_maintenance
- professionalism
- systems_practice
- practice_learning
- mechanism

**Available Difficulties**:
- easy (target: 80-90% accuracy)
- medium (target: 60-70% accuracy)
- hard (target: 40-50% accuracy)
- very_hard (target: 20-30% accuracy)

---

### 4. Export Progress Report
```bash
python scripts/monitor_generation_progress.py --export progress_$(date +%Y%m%d).json
```

**Use Case**: Track daily/weekly progress, share with team

---

## Daily Workflow

### Morning (Day Start)
```bash
# 1. Check overnight generation status
python scripts/monitor_generation_progress.py

# 2. Review validation failures from previous day
# Check logs in backend/logs/

# 3. Start daily batch
python scripts/batch_generate_im.py phase --phase 1 --batch <today's batch number>
```

### Evening (Day End)
```bash
# 1. Export daily progress
python scripts/monitor_generation_progress.py --export daily_progress_$(date +%Y%m%d).json

# 2. Review quality metrics
# - Validation pass rate should be >85%
# - Check for systematic issues (e.g., all cardiology questions failing)

# 3. Plan tomorrow's batches
# - If gaps widening, switch to custom generation
# - If validation rate drops, pause and debug
```

---

## Typical Generation Schedule

### Week 1-2: Phase 1 (Critical Gaps)
| Day | Batch | Subspecialty | Questions | Cumulative |
|-----|-------|--------------|-----------|------------|
| 1 | 1 | Ethics/Professionalism | 50 | 50 |
| 2 | 2 | Ethics/Professionalism | 50 | 100 |
| 3 | 3 | Ethics/Professionalism | 50 | 150 |
| 4 | 4 | Ethics/Professionalism | 50 | 200 |
| 5 | 5 | Ethics/Professionalism | 50 | 250 |
| 6 | 6 | Biostatistics/Epi | 50 | 300 |
| 7 | 7 | Biostatistics/Epi | 50 | 350 |
| 8 | 8 | Biostatistics/Epi | 25 | 375 |
| 9 | 9 | Endocrinology | 50 | 425 |
| 10 | 10 | Endocrinology | 50 | 475 |
| 11 | 11 | Endocrinology | 25 | 500 |
| 12 | 12 | Hematology/Oncology | 50 | 550 |
| 13 | 13 | Hematology/Oncology | 50 | 600 |
| 14 | 14 | Hematology/Oncology | 25 | 625 |

**Quality Checkpoint**: Manual review of 62 questions (10% of 625)

---

## Monitoring Quality

### Automated Validation (Every Question)
The batch generator automatically runs these checks:

✓ No vague clinical terms
✓ No testwiseness cues
✓ 5 distinct distractors
✓ Valid answer key (A-E)
✓ Complete explanations
✓ Proper medical units

**Action if <85% pass rate**: Pause generation, review prompt engineering

---

### Manual Audit (Every 250 Questions)
```bash
# Sample 25 random questions (10%)
python scripts/quality_audit.py \
  --batch-id "Phase1_Batch5_Ethics_Professionalism" \
  --sample-size 25 \
  --reviewer your_name
```

**Review Criteria**:
- Medical accuracy: 100%
- NBME fidelity: Indistinguishable from real shelf
- Difficulty calibration: Matches intended level
- Learning value: Educational for both correct and incorrect

**Action if <90% shelf-quality**: Regenerate batch, adjust parameters

---

## Common Issues & Solutions

### Issue: Validation Pass Rate Drops Below 85%
**Symptoms**:
- Batch generation logs show many failures
- Progress monitor shows low question count

**Solution**:
```bash
# 1. Check validation failure patterns
tail -n 100 backend/logs/generation.log | grep "FAILED"

# 2. Common patterns:
#    - Vague terms: Add explicit values to prompt examples
#    - Testwiseness: Regenerate with balanced choice lengths
#    - Duplicate choices: Increase creativity (temperature)

# 3. Regenerate failed batch
python scripts/batch_generate_im.py custom \
  --subspecialty <failed subspecialty> \
  --count <failed count>
```

---

### Issue: Subspecialty Imbalance Growing
**Symptoms**:
- Progress monitor shows >15% deviation in one subspecialty
- Gap analysis shows new HIGH priority gaps

**Solution**:
```bash
# 1. Pause current phase
# 2. Run custom batch for underrepresented subspecialty
python scripts/batch_generate_im.py custom \
  --subspecialty <underrepresented> \
  --count 100

# 3. Resume phase
```

---

### Issue: Circuit Breaker Opens (OpenAI Rate Limit)
**Symptoms**:
- Batch generation hangs
- Logs show "Circuit breaker OPEN"

**Solution**:
```bash
# 1. Wait 120 seconds (automatic cooldown)
# 2. Reduce generation rate
#    Edit batch_generate_im.py:
#    time.sleep(3) → time.sleep(5)  # Slower rate
# 3. Resume batch with same batch number
```

---

### Issue: All Questions Too Easy/Hard
**Symptoms**:
- Student alpha testing shows 85%+ accuracy (too easy)
- Student alpha testing shows <40% accuracy (too hard)

**Solution**:
```bash
# Regenerate with explicit difficulty targets
python scripts/batch_generate_im.py custom \
  --subspecialty <subspecialty> \
  --count 50 \
  --difficulty hard  # or easy, medium
```

---

## Progress Tracking

### Daily Metrics to Track
- Questions generated (cumulative)
- Validation pass rate (%)
- Subspecialty distribution (current vs target %)
- Task type distribution (current vs target %)
- Difficulty distribution (current vs target %)
- Circuit breaker status (CLOSED = good)

### Weekly Metrics to Track
- Expert review approval rate (target: >90%)
- Student alpha test accuracy (target: 60-70%)
- Generation velocity (questions/day)
- Quality drift indicators

---

## Expected Timeline

| Week | Phase | Target Questions | Cumulative | Focus |
|------|-------|------------------|------------|-------|
| 1-2 | 1 | 800 | 800 | Critical gaps (Ethics, Biostats, Endo, Heme/Onc) |
| 3-4 | 2 | 900 | 1,700 | High-yield core (Cards, Pulm, GI, ID) |
| 5-6 | 3 | 800 | 2,500 | Completion (Rheum, Neuro, Multisystem) |

**Total**: 6 weeks (42 days) @ 60 questions/day average

---

## Quality Checkpoints

### After 250 Questions
- ✓ Automated validation: >85% pass
- ✓ Manual review: 25 questions
- ✓ Gap reanalysis: Check for new imbalances

### After 500 Questions
- ✓ Comprehensive audit: 50 questions (10% sample)
- ✓ Student alpha testing: 20 students × 5 questions each
- ✓ Difficulty calibration: Compare intended vs actual accuracy
- ✓ IRT analysis: Check discrimination indices

### After 1,000 Questions
- ✓ External expert review: Medical educator
- ✓ NBME pattern matching: Compare to real shelf questions
- ✓ Systematic issue check: Any AI fingerprints?
- ✓ Update prompts: Based on learnings

---

## Final Validation (After 2,500 Questions)

### Database Checks
```sql
-- Subspecialty distribution
SELECT
  JSON_EXTRACT(extra_data, '$.subspecialty') as subspecialty,
  COUNT(*) as count
FROM questions
WHERE specialty = 'internal_medicine'
  AND source LIKE '%AI Generated%'
GROUP BY subspecialty;

-- Task type distribution
SELECT
  JSON_EXTRACT(extra_data, '$.task_type') as task_type,
  COUNT(*) as count
FROM questions
WHERE specialty = 'internal_medicine'
GROUP BY task_type;

-- Difficulty distribution
SELECT
  difficulty_level,
  COUNT(*) as count
FROM questions
WHERE specialty = 'internal_medicine'
GROUP BY difficulty_level;
```

### Quality Metrics
- ✓ All subspecialties within ±5% of target
- ✓ All task types within ±5% of target
- ✓ Difficulty: 20% easy, 50% medium, 25% hard, 5% very hard (±3%)
- ✓ Expert approval: >95%
- ✓ No duplicates (>85% similarity)
- ✓ Student accuracy: 60-70% on medium questions

---

## Success Criteria

**Phase 1 Complete**:
- ✓ 800 questions generated
- ✓ All HIGH priority gaps <50 questions
- ✓ Ethics: 250 questions
- ✓ Pharmacotherapy: +200 questions
- ✓ Lab/diagnostic: +200 questions

**Phase 2 Complete**:
- ✓ 1,700 questions total
- ✓ Cardiology: 325 questions
- ✓ Pulmonology: 250 questions
- ✓ Gastroenterology: 250 questions
- ✓ No task type <80% of target

**Phase 3 Complete**:
- ✓ 2,500 questions total
- ✓ All 13 subspecialties at 100% ±5%
- ✓ All task types at 100% ±5%
- ✓ Difficulty distribution: 20/50/25/5 achieved
- ✓ Final gap analysis: all gaps <10 questions

---

## Next Steps After Completion

1. **Alpha Testing**: 100 medical students × 25 questions each
2. **IRT Calibration**: Reclassify difficulty based on actual performance
3. **Platform Integration**: Import to production database
4. **Monitoring**: Track student accuracy, flag low-discrimination questions
5. **Continuous Improvement**: Regenerate bottom 5% of questions quarterly

---

## Support

**Issues**: Create GitHub issue with:
- Batch ID
- Error message
- Expected vs actual behavior
- Logs (if applicable)

**Questions**: Contact project lead or check `IM_QUESTION_GENERATION_MANIFEST.md`

---

**Last Updated**: 2025-11-29
**Version**: 1.0
**Author**: ShelfSense Medical Education Team
