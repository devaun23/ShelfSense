# Adaptive Algorithm Integration: Executive Summary

**Date**: 2025-11-29
**Audience**: Product, Engineering, Medical Education Teams
**Purpose**: High-level overview of how 2,500 question generation supports adaptive learning

---

## The Core Question

**"How many questions do we need, and why?"**

**Answer**: **800 minimum (Phase 1), 2,500 optimal (Phase 2)**

This isn't arbitrary. It's mathematically derived from how our adaptive algorithms work.

---

## Current State vs Target

| **Metric** | **Current (223 Q's)** | **Phase 1 (800 Q's)** | **Phase 2 (2,500 Q's)** |
|------------|----------------------|---------------------|----------------------|
| **Algorithm Efficacy** | 22-30% | 75% | 95% |
| **Study Coverage** | 9 days | 33 days | 80+ days |
| **Weak Area Detection** | Not possible | 85% confidence | 95% confidence |
| **User Retention (Week 4)** | 20-30% | 60-70% | 75-85% |
| **Competitive Position** | Non-viable | Entry-level | Mid-tier |

**Bottom Line**: We're currently running the algorithm at 30% capacity. We need 800 questions to reach 75% capacity (competitive), and 2,500 to reach 95% capacity (industry-leading).

---

## Why These Numbers?

### 1. Spaced Repetition Math

**User Study Pattern**:
- 40 questions/day for 42 days (6-week shelf prep)
- 60% new, 40% review
- **Need**: 896 new questions minimum

**With 223 questions**:
- Content exhausted by Day 9
- Days 10-42: Only reviewing same 223 questions
- **Result**: Memorization of specific questions, not concepts

**With 800 questions**:
- Content lasts through Day 33
- Proper spaced repetition without content exhaustion
- **Result**: True concept mastery

### 2. Weak Area Detection

**Statistical Requirement**:
- Need 15+ questions per topic for 85% confidence
- Internal Medicine has 13 major systems
- **Minimum**: 13 × 15 = 195 questions
- **Target**: 13 × 40-80 = 520-1,040 questions

**With 223 questions**:
- ~17 questions per system
- Only 70% confidence (high false positive rate)
- Can't detect subtopic weaknesses

**With 800 questions**:
- ~60 questions per system
- 85% confidence in topic-level weakness
- Can detect subtopic weaknesses (e.g., "weak in ACS but strong in heart failure")

### 3. IRT Difficulty Calibration

**Our algorithm needs 50+ user responses** per question to measure difficulty.

**With 223 questions**:
- Questions get calibrated quickly (good)
- But not enough difficulty range to personalize (bad)

**With 800-2,500 questions**:
- Smooth difficulty curve across all topics
- Can target 65-75% accuracy zone for optimal learning

---

## What Makes a "Good" Question for Our Algorithm?

Not all questions are equal. Our algorithms need specific metadata:

### Required Metadata (Every Question)

```json
{
  "specialty": "internal_medicine",
  "difficulty_level": "medium",
  "extra_data": {
    "topic": "cardiology",                  // Body system
    "subtopic": "acute_coronary_syndrome",  // Specific condition
    "cognitive_level": "application",       // Bloom's taxonomy
    "clinical_task": "next_step",           // NBME task type
    "concepts": [                           // Medical concepts tested
      "stemi_diagnosis",
      "primary_pci",
      "antiplatelet_therapy"
    ],
    "high_yield": true                      // Priority flag
  }
}
```

**Why This Matters**:
- `topic` enables weak area detection
- `subtopic` enables fine-grained targeting
- `concepts` enables concept-based spaced repetition (review concept, not question)
- `cognitive_level` enables reasoning error detection (knowledge gap vs reasoning failure)

### Quality Thresholds (Post-Launch)

After 50+ user attempts, we measure:

| **Metric** | **Target** | **Action if Below** |
|------------|------------|---------------------|
| **Discrimination Index** | >0.20 | Flag for review or retire |
| **p-value (difficulty)** | 0.40-0.85 | Recategorize or revise |
| **Distractor Selection** | 5-30% each | Improve distractors |

**Quality Control**: We automatically retire questions with negative discrimination (strong students do worse than weak students) or extreme difficulty.

---

## Question Distribution Strategy

### Phase 1: 800 Internal Medicine Questions

| **System** | **Questions** | **% of Bank** | **Subtopics** | **Q's per Subtopic** |
|------------|---------------|---------------|---------------|---------------------|
| Cardiology | 120 | 15% | 10 | 12 |
| Infectious Disease | 96 | 12% | 12 | 8 |
| Gastroenterology | 80 | 10% | 10 | 8 |
| Pulmonology | 64 | 8% | 8 | 8 |
| Nephrology | 64 | 8% | 8 | 8 |
| Endocrinology | 64 | 8% | 8 | 8 |
| Neurology | 64 | 8% | 8 | 8 |
| Hematology | 48 | 6% | 6 | 8 |
| Psychiatry | 48 | 6% | 6 | 8 |
| Rheumatology | 40 | 5% | 5 | 8 |
| Oncology | 40 | 5% | 5 | 8 |
| Dermatology | 32 | 4% | 4 | 8 |
| Preventive Medicine | 40 | 5% | 5 | 8 |
| **TOTAL** | **800** | **100%** | **95** | **~8 avg** |

**Difficulty Distribution**:
- 25% easy (200 questions)
- 50% medium (400 questions)
- 25% hard (200 questions)

**Cognitive Distribution**:
- 15% recall (factual knowledge)
- 30% application (apply to scenario)
- 35% analysis (differential diagnosis)
- 20% synthesis (multi-step reasoning)

**Clinical Task Distribution**:
- 40% diagnosis
- 30% next step
- 20% treatment
- 10% mechanism/other

---

## How Algorithms Use This Data

### Algorithm 1: Weak Area Detection

**Input**: User's question attempts grouped by `topic` and `subtopic`
**Output**: Prioritized list of weaknesses

```
User Performance:
  Cardiology (55% accuracy) ← WEAK
    ├─ ACS (40%) ← CRITICAL
    ├─ Heart Failure (65%) ← Developing
    └─ Arrhythmias (70%) ← OK

Algorithm Action:
  Next 5 questions → 3 ACS, 1 Heart Failure, 1 review
```

**Requirements**:
- 15+ questions per topic (85% confidence)
- 8+ questions per subtopic (reliable detection)

### Algorithm 2: Spaced Repetition (SM-2)

**Input**: User's attempt history per question
**Output**: Review schedule based on learning stage

```
Learning Stages:
  NEW (0 attempts) → Review in 0 days (show now)
  LEARNING (1-2 attempts) → Review in 1 day
  YOUNG (2-3 correct) → Review in 3 days
  MATURE (4+ correct) → Review in 7 days
  MASTERED (5+ correct) → Review in 21 days
```

**Enhancement with Concepts**:
- Instead of reviewing question #142, review **concept**: "ACS diagnosis"
- Show different question testing same concept to prevent memorization

**Requirements**:
- 896 new questions for 42-day study period
- 8-15 variations per concept (different clinical presentations)

### Algorithm 3: Difficulty Targeting

**Input**: User's accuracy per difficulty level
**Output**: Questions in 65-75% accuracy zone (optimal learning)

```
User Profile:
  Easy: 90% accuracy → Too easy, skip
  Medium: 70% accuracy → Perfect zone
  Hard: 45% accuracy → Too hard, avoid

Algorithm Action:
  Select medium difficulty questions in weak areas
```

**Requirements**:
- Balanced difficulty distribution (25/50/25)
- IRT calibration after 50 responses
- Enough questions at each difficulty level

### Algorithm 4: Plateau Detection

**Input**: 14-day accuracy trend
**Output**: Is user improving or stuck?

```
Daily Accuracy:
  Day 1-7: 60% → 65% → 68% (improving) ✓
  Day 8-14: 70% → 69% → 70% (plateau) ⚠️

Algorithm Action:
  If plateau: Suggest break, different specialty, or review
```

**Requirements**:
- Continuous new content for 14-day window
- Minimum 5 sessions with 70+ attempts

---

## User Experience Impact

### Current Experience (223 Questions)

**Day 1-9**: "Loving ShelfSense! Questions are great."
**Day 10**: "I've seen all these before..."
**Day 11-42**: "Just reviewing same 223 questions over and over. Feels like I'm memorizing answers, not learning."
**Week 4**: 70-80% of users have churned.

### With 800 Questions (Phase 1)

**Day 1-3**: Baseline assessment (20 questions across all topics)
**Day 4-33**: New content daily + targeted weak area review
**Day 34-42**: Final review phase with spaced repetition
**Week 4**: 60-70% retention (2-3x improvement)

**User Feedback**: "ShelfSense keeps targeting my weak areas. I'm actually improving."

### With 2,500 Questions (Phase 2)

**Day 1-80+**: Continuous personalized learning
**Multiple rotations**: IM, Surgery, Peds all covered
**Week 4**: 75-85% retention (industry-leading)

**User Feedback**: "Better than UWorld. Smarter question selection."

---

## Competitive Benchmarking

| **Platform** | **IM Questions** | **Total Questions** | **Adaptive Algorithm** | **Position** |
|--------------|------------------|---------------------|------------------------|--------------|
| **UWorld** | 800-1,000 | 2,500+ | Yes (proprietary) | Industry Leader |
| **AMBOSS** | 600-800 | 2,000+ | Yes (Bayesian) | Strong Competitor |
| **Kaplan** | 500-700 | 1,500+ | Limited | Mid-Tier |
| **ShelfSense (Current)** | 223 | 223 | Yes (30% efficacy) | Non-Competitive |
| **ShelfSense (Phase 1)** | 800 | 800 | Yes (75% efficacy) | Entry-Level |
| **ShelfSense (Phase 2)** | 1,200 | 2,500 | Yes (95% efficacy) | Competitive |

**Competitive Moat**: Not the questions themselves, but the algorithm that routes students to the right questions at the right time.

---

## Implementation Timeline

### Phase 1: Critical (Next 90 Days)

**Goal**: 800 Internal Medicine questions

**Milestones**:
- Week 1-2: Metadata schema finalized, AI prompts tuned
- Week 3-4: Generate + validate first 200 questions (pilot)
- Week 5-10: Generate remaining 600 questions in batches
- Week 11-12: Expert review, database import, IRT calibration

**Deliverable**: 800 high-quality IM questions enabling 75% algorithm efficacy

**Success Metrics**:
- User retention Week 4: 30% → 60%
- Study coverage: 9 days → 33 days
- Weak area detection: N/A → 85% confidence

### Phase 2: Competitive (6-12 Months)

**Goal**: 2,500 multi-specialty questions

**Distribution**:
- Internal Medicine: 1,200 (35%)
- Surgery: 700 (20%)
- Pediatrics: 600 (17%)
- OBGYN: 450 (13%)
- Psychiatry: 350 (10%)
- Emergency Medicine: 200 (5%)

**Deliverable**: Industry-competitive question bank with 95% algorithm efficacy

**Success Metrics**:
- User retention Week 4: 60% → 75%
- Study coverage: 33 days → 80+ days
- Score prediction: ±15 points → ±10 points

---

## Resource Requirements

### Phase 1 (800 Questions)

**Time Estimate**:
- AI generation: 5 min/question × 800 = 67 hours
- Expert validation: 10 min/question × 800 = 133 hours
- Database import + QA: 20 hours
- **Total**: 220 hours (~6 weeks with 1 FTE)

**Cost Estimate**:
- AI API costs: ~$500 (GPT-4o at $0.60/question)
- Expert validation: ~$6,650 (at $50/hour)
- **Total**: ~$7,150

### Phase 2 (Additional 1,700 Questions)

**Time Estimate**:
- ~467 hours (~12 weeks with 1 FTE)

**Cost Estimate**:
- ~$15,000 total

**Total Investment (Phase 1 + 2)**: ~$22,000 and 18 weeks

---

## Risk Mitigation

### Risk 1: Low-Quality AI-Generated Questions

**Mitigation**:
- Multi-stage validation pipeline
- Expert review before database import
- IRT calibration identifies flawed questions post-launch
- Automated retirement of questions with discrimination <0.20

### Risk 2: Content Exhaustion Still Occurs

**Mitigation**:
- 800 questions covers 33 days (>6-week rotation)
- 2,500 questions covers 80+ days (multiple rotations)
- Monitor user study patterns and adjust targets

### Risk 3: Algorithm Doesn't Improve Outcomes

**Mitigation**:
- Track Week 4 retention as primary KPI
- Correlate ShelfSense accuracy with NBME scores
- A/B test algorithm changes before full rollout

---

## Success Criteria

### Phase 1 Success (After 800 Questions Deployed)

**Quantitative**:
- [ ] Algorithm efficacy: 30% → 75%
- [ ] User retention Week 4: 30% → 60%
- [ ] Study coverage: 9 days → 33 days
- [ ] Weak area detection confidence: N/A → 85%

**Qualitative**:
- [ ] Users report algorithm "feels smart"
- [ ] Reduced complaints about repetitive questions
- [ ] Positive correlation between ShelfSense accuracy and NBME scores

### Phase 2 Success (After 2,500 Questions Deployed)

**Quantitative**:
- [ ] Algorithm efficacy: 75% → 95%
- [ ] User retention Week 4: 60% → 75%
- [ ] Study coverage: 33 days → 80+ days
- [ ] Score prediction CI: ±15 points → ±10 points

**Qualitative**:
- [ ] Users choose ShelfSense over UWorld
- [ ] "Best adaptive algorithm" becomes competitive moat
- [ ] Premium tier conversions driven by algorithm personalization

---

## Frequently Asked Questions

### Q1: Can't we just buy questions from a third-party vendor?

**A**: Possibly, but our value is in the **algorithm**, not the questions. We need:
- Full metadata control (topic, subtopic, concepts)
- Ability to A/B test question formats
- Ownership of IRT calibration data
- Ability to retire/revise based on algorithm feedback

Third-party questions rarely come with this level of metadata.

### Q2: Why not crowdsource questions from users?

**A**: Quality control. We need:
- Consistent difficulty calibration
- NBME-style formatting
- Framework-based explanations
- Expert medical accuracy validation

Crowdsourced questions would require extensive editing to meet these standards.

### Q3: Can we start with fewer than 800 questions?

**A**: Yes, but algorithm efficacy will be proportionally lower:
- 400 questions = ~50% efficacy
- 600 questions = ~65% efficacy
- 800 questions = ~75% efficacy

The ROI inflection point is at 800 questions.

### Q4: What happens after we hit 2,500 questions?

**A**: Continuous quality improvement:
- IRT recalibration quarterly
- Retire underperforming questions (discrimination <0.20)
- Add variations to high-yield concepts
- Update for new NBME guidelines

**Steady State**: 2,500-3,000 active questions with 5-10% annual churn.

---

## Conclusion

**The 2,500 question target is not arbitrary.** It's mathematically derived from how our adaptive algorithms function:

1. **Spaced Repetition**: Need 896 questions for 42-day coverage
2. **Weak Area Detection**: Need 15+ questions per topic for 85% confidence
3. **Difficulty Calibration**: Need balanced distribution across easy/medium/hard
4. **Concept Mastery**: Need 8-15 variations per concept

**Current state (223 questions)**: Algorithms running at 30% capacity, users churning at Week 2-3.

**Phase 1 target (800 questions)**: Algorithms at 75% capacity, competitive with entry-level platforms, users retained through Week 6.

**Phase 2 target (2,500 questions)**: Algorithms at 95% capacity, competitive with industry leaders, users retained 75-85% at Week 4.

**Investment**: ~$22,000 and 18 weeks to reach Phase 2.

**Expected ROI**: 2-3x improvement in user retention, 285+ score outcomes, competitive moat through superior adaptive personalization.

---

## Related Documents

1. **`ADAPTIVE_ALGORITHM_QUESTION_REQUIREMENTS.md`** - Detailed technical requirements
2. **`QUESTION_GENERATION_TECHNICAL_SPEC.md`** - Implementation guide with code examples
3. **`QUESTION_BANK_SUMMARY.md`** - Statistical analysis of bank size requirements

---

**Document Version**: 1.0
**Last Updated**: 2025-11-29
**Next Review**: After Phase 1 completion (800 questions deployed)
**Owner**: Product + Engineering + Medical Education Teams
