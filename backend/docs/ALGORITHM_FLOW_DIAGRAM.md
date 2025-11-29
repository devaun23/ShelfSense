# Adaptive Learning Algorithm: System Flow Diagram

**Date**: 2025-11-29
**Purpose**: Visual representation of how question metadata flows through adaptive algorithms

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        QUESTION GENERATION PIPELINE                       │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 1: AI Generation (GPT-4o)                                         │
│  ────────────────────────────────────────────────────────────────────   │
│  Input:  topic, subtopic, difficulty, clinical_task                     │
│  Output: vignette, choices, answer_key, explanation, metadata           │
│                                                                          │
│  Generated Metadata:                                                     │
│    ✓ topic: "cardiology"                                                │
│    ✓ subtopic: "acute_coronary_syndrome"                                │
│    ✓ cognitive_level: "application"                                     │
│    ✓ clinical_task: "next_step"                                         │
│    ✓ concepts: ["stemi_diagnosis", "primary_pci"]                       │
│    ✓ high_yield: true                                                   │
│    ✓ estimated_p_value: 0.65                                            │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 2: Quality Validation                                             │
│  ────────────────────────────────────────────────────────────────────   │
│  Checks:                                                                 │
│    ✓ Schema validation (all required metadata present)                  │
│    ✓ Content quality (Elite Quality Validator)                          │
│    ✓ Medical accuracy (Fact Checker)                                    │
│    ✓ Distractor quality (plausibility, explanations)                    │
│    ✓ Explanation quality (framework-based reasoning)                    │
│                                                                          │
│  Quality Score: 0-100                                                    │
│    ≥60 → Approved for database                                          │
│    40-59 → Needs expert review                                          │
│    <40 → Rejected                                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 3: Database Import                                                │
│  ────────────────────────────────────────────────────────────────────   │
│  Table: questions                                                        │
│    id, specialty, difficulty_level, source_type, content_status         │
│    vignette, choices, answer_key, explanation                           │
│    extra_data: {topic, subtopic, concepts, cognitive_level, ...}        │
│                                                                          │
│  Status: content_status = "active"                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ADAPTIVE ALGORITHM ECOSYSTEM                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## User Study Session Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│  USER STARTS STUDY SESSION                                              │
│  Request: GET /api/questions/next?specialty=internal_medicine           │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ADAPTIVE ENGINE: select_next_question()                                │
│  (backend/app/services/adaptive_engine.py)                              │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ Step 1: Identify User Weaknesses                           │         │
│  │ ─────────────────────────────────────────────────────────  │         │
│  │ Query: GROUP BY extra_data['topic']                        │         │
│  │ Filter: attempts ≥ 3 AND accuracy < 70%                    │         │
│  │                                                             │         │
│  │ Output:                                                     │         │
│  │   - Cardiology: 55% (WEAK)                                 │         │
│  │   - Gastro: 62% (WEAK)                                     │         │
│  │   - Pulmonary: 75% (OK)                                    │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                     │                                    │
│                                     ▼                                    │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ Step 2: Get Candidate Questions                            │         │
│  │ ─────────────────────────────────────────────────────────  │         │
│  │ Query: SELECT questions WHERE                              │         │
│  │   - specialty = "internal_medicine"                        │         │
│  │   - content_status = "active"                              │         │
│  │   - NOT IN exclude_ids (current session)                   │         │
│  │ JOIN attempts ON user_id for performance data              │         │
│  │                                                             │         │
│  │ Candidate Pool: 200 questions                              │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                     │                                    │
│                                     ▼                                    │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ Step 3: Score Each Candidate                               │         │
│  │ ─────────────────────────────────────────────────────────  │         │
│  │ For each question, calculate priority score:               │         │
│  │                                                             │         │
│  │ • Weak Area Bonus:                                         │         │
│  │   IF topic IN weaknesses:                                  │         │
│  │     score += 3.0 * severity_multiplier                     │         │
│  │     (critical: 1.5x, weak: 1.0x, developing: 0.7x)         │         │
│  │                                                             │         │
│  │ • Due Review Bonus:                                        │         │
│  │   IF last_attempt + interval ≤ now:                        │         │
│  │     score += 2.5                                           │         │
│  │                                                             │         │
│  │ • Difficulty Match Bonus:                                  │         │
│  │   IF user_accuracy on this Q ≈ 0.70:                       │         │
│  │     score += 1.5                                           │         │
│  │                                                             │         │
│  │ • Coverage Bonus:                                          │         │
│  │   IF attempts_count == 0 (new question):                   │         │
│  │     score += 1.0                                           │         │
│  │                                                             │         │
│  │ • Randomness: score += random(0, 0.3)                      │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                     │                                    │
│                                     ▼                                    │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ Step 4: Select Question                                    │         │
│  │ ─────────────────────────────────────────────────────────  │         │
│  │ Top 3 Candidates:                                          │         │
│  │   1. Q#1427 (cardiology/ACS, score: 6.2) ← 60% chance     │         │
│  │   2. Q#0834 (gastro/IBD, score: 5.8) ← 30% chance         │         │
│  │   3. Q#2103 (cardio/HF, score: 5.1) ← 10% chance          │         │
│  │                                                             │         │
│  │ Selection: Weighted random from top 3                      │         │
│  │ Prevents predictability while prioritizing weaknesses      │         │
│  └────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  RETURN QUESTION TO USER                                                │
│  Response: Question #1427 (cardiology/ACS, medium difficulty)           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Question Attempt Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│  USER SUBMITS ANSWER                                                    │
│  POST /api/questions/1427/attempt                                       │
│  Body: {user_answer: "B", time_spent: 85, confidence: 4}                │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  SAVE ATTEMPT TO DATABASE                                               │
│  (backend/app/models/models.py: QuestionAttempt)                        │
│                                                                          │
│  Table: question_attempts                                               │
│    user_id, question_id, user_answer, is_correct                        │
│    time_spent_seconds, confidence_level                                 │
│    interaction_data: {answer_changes, hover_events, ...}                │
│    attempted_at                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  UPDATE SPACED REPETITION SCHEDULE                                      │
│  (backend/app/services/adaptive_engine.py)                              │
│                                                                          │
│  Learning Stage Progression:                                            │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ Current Stage: LEARNING (1 previous attempt, incorrect)    │         │
│  │ Current Attempt: CORRECT                                   │         │
│  │                                                             │         │
│  │ → New Stage: YOUNG                                         │         │
│  │ → Next Review: 3 days from now                             │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                          │
│  Table: scheduled_reviews                                               │
│    user_id, question_id, scheduled_for: now + 3 days                    │
│    review_interval: "3d", learning_stage: "young"                       │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  UPDATE CONCEPT RETENTION                                               │
│  (backend/app/models/models.py: ConceptRetention)                       │
│                                                                          │
│  For each concept in question.extra_data['concepts']:                   │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ Concept: "stemi_diagnosis"                                 │         │
│  │                                                             │         │
│  │ Previous:                                                   │         │
│  │   memory_strength: 0.7                                     │         │
│  │   stability: 2.0 days                                      │         │
│  │   consecutive_correct: 1                                   │         │
│  │                                                             │         │
│  │ After Correct Answer:                                      │         │
│  │   memory_strength: 1.0 (refreshed)                         │         │
│  │   stability: 3.5 days (increased)                          │         │
│  │   consecutive_correct: 2                                   │         │
│  │   next_optimal_review: now + 3.5 days                      │         │
│  └────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  INVALIDATE LEARNING METRICS CACHE                                      │
│  (backend/app/models/models.py: LearningMetricsCache)                   │
│                                                                          │
│  Mark user's cached metrics as stale:                                   │
│    is_stale = True                                                      │
│                                                                          │
│  Next analytics request will trigger recalculation:                     │
│    - Weak areas                                                         │
│    - Predicted score                                                    │
│    - Velocity score                                                     │
│    - Calibration score                                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## IRT Calibration Flow (Post-Launch)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  WEEKLY BATCH JOB: IRT Calibration                                      │
│  (backend/app/services/item_response_theory.py)                         │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 1: Identify Calibration Candidates                                │
│  ────────────────────────────────────────────────────────────────────   │
│  Query: SELECT question_id, COUNT(attempts)                             │
│         FROM question_attempts                                          │
│         GROUP BY question_id                                            │
│         HAVING COUNT(*) ≥ 50                                            │
│         AND (question NOT calibrated OR calibrated >30 days ago)        │
│                                                                          │
│  Found: 127 questions ready for calibration                             │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 2: Calculate IRT Parameters (Per Question)                        │
│  ────────────────────────────────────────────────────────────────────   │
│  Question #1427 (ACS question, 127 attempts)                            │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ Difficulty (p-value):                                      │         │
│  │   Proportion correct = 83/127 = 0.65                       │         │
│  │   Classification: MEDIUM (0.55 < p < 0.70)                 │         │
│  │   Confidence Interval: [0.56, 0.73] (Wilson score)         │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ Discrimination Index:                                       │         │
│  │   Top 27% students: 32/34 = 94% correct                    │         │
│  │   Bottom 27% students: 18/34 = 53% correct                 │         │
│  │   Discrimination = 0.94 - 0.53 = 0.41 (EXCELLENT)          │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ Distractor Analysis:                                        │         │
│  │   A (distractor): 15% selected (good)                      │         │
│  │   B (CORRECT): 65% selected ✓                              │         │
│  │   C (distractor): 12% selected (good)                      │         │
│  │   D (distractor): 6% selected (acceptable)                 │         │
│  │   E (distractor): 2% selected (too obvious - FLAG)         │         │
│  └────────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 3: Update Question Metadata                                       │
│  ────────────────────────────────────────────────────────────────────   │
│  UPDATE questions                                                        │
│  SET                                                                     │
│    difficulty_level = "medium" (was "medium" - confirmed)               │
│    extra_data = extra_data || {                                         │
│      "irt_calibration": {                                               │
│        "p_value": 0.65,                                                 │
│        "discrimination": 0.41,                                          │
│        "response_count": 127,                                           │
│        "confidence_interval": [0.56, 0.73],                             │
│        "calibrated_at": "2025-11-29T10:00:00Z"                          │
│      },                                                                 │
│      "quality_flags": ["DISTRACTOR_E_TOO_OBVIOUS"]                      │
│    }                                                                    │
│  WHERE id = "1427"                                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 4: Quality Action (If Needed)                                     │
│  ────────────────────────────────────────────────────────────────────   │
│  IF discrimination < 0.0 (negative):                                    │
│    → content_status = "retired"                                         │
│    → Reason: Strong students do worse (flawed question)                 │
│                                                                          │
│  ELSE IF discrimination < 0.20:                                         │
│    → content_status = "needs_review"                                    │
│    → Reason: Poor discrimination                                        │
│                                                                          │
│  ELSE IF p_value < 0.30 OR p_value > 0.90:                              │
│    → Flag for revision (too easy/hard)                                  │
│                                                                          │
│  ELSE:                                                                  │
│    → Keep active (good quality)                                         │
│                                                                          │
│  Question #1427: KEEP ACTIVE (discrimination 0.41, p-value 0.65)        │
│  Minor issue: Distractor E could be improved                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Metadata Flow Through System

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           QUESTION METADATA                               │
└───────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────┐            ┌───────────────┐            ┌───────────────┐
│ TOPIC         │            │ SUBTOPIC      │            │ CONCEPTS      │
│ (System-Level)│            │ (Disease)     │            │ (Knowledge)   │
├───────────────┤            ├───────────────┤            ├───────────────┤
│ "cardiology"  │            │ "acs"         │            │ ["stemi_      │
│               │            │               │            │  diagnosis",  │
│ Used by:      │            │ Used by:      │            │  "primary_    │
│ • Weak area   │            │ • Fine-grained│            │  pci"]        │
│   detection   │            │   targeting   │            │               │
│ • Topic       │            │ • Sub-topic   │            │ Used by:      │
│   coverage    │            │   weakness    │            │ • Concept     │
│   analysis    │            │ • User        │            │   retention   │
│               │            │   feedback    │            │ • Spaced rep  │
│               │            │               │            │   scheduling  │
└───────────────┘            └───────────────┘            └───────────────┘


┌───────────────┐            ┌───────────────┐            ┌───────────────┐
│ COGNITIVE     │            │ CLINICAL      │            │ DIFFICULTY    │
│ LEVEL         │            │ TASK          │            │ LEVEL         │
├───────────────┤            ├───────────────┤            ├───────────────┤
│ "application" │            │ "next_step"   │            │ "medium"      │
│               │            │               │            │               │
│ Used by:      │            │ Used by:      │            │ Used by:      │
│ • Reasoning   │            │ • Task-       │            │ • Difficulty  │
│   error       │            │   specific    │            │   targeting   │
│   detection   │            │   training    │            │ • IRT         │
│ • Knowledge   │            │ • Format      │            │   calibration │
│   gap vs      │            │   error       │            │ • User        │
│   reasoning   │            │   detection   │            │   performance │
│   failure     │            │               │            │   zone        │
└───────────────┘            └───────────────┘            └───────────────┘


                         ┌───────────────┐
                         │ HIGH_YIELD    │
                         │ FLAG          │
                         ├───────────────┤
                         │ true/false    │
                         │               │
                         │ Used by:      │
                         │ • Priority    │
                         │   weighting   │
                         │ • Question    │
                         │   selection   │
                         │   bonus       │
                         └───────────────┘
```

---

## Algorithm Synergy: How Components Work Together

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    USER LEARNING JOURNEY (Day 1-42)                       │
└───────────────────────────────────────────────────────────────────────────┘

DAY 1-3: BASELINE ASSESSMENT
│
├─ Algorithm: Baseline Question Pool
│  • Pre-selected 20 questions covering all 13 IM systems
│  • Balanced difficulty (30% easy, 50% medium, 20% hard)
│  • Goal: Establish baseline performance across topics
│
└─ Metadata Used: topic, difficulty_level
   Output: Initial weak area estimates


DAY 4-10: EXPLORATION PHASE
│
├─ Algorithm: Topic Coverage + Early Weak Area Targeting
│  • Ensure at least 5 attempts per major topic
│  • Start prioritizing topics with <60% accuracy
│  • Mix new content (70%) with early reviews (30%)
│
└─ Metadata Used: topic, subtopic, difficulty_level
   Output: Refined weak area detection (60% confidence)


DAY 11-20: TARGETED LEARNING
│
├─ Algorithm: Full Adaptive Mode (75% efficacy)
│  • Weak area detection: 85% confidence (≥10 attempts per topic)
│  • Subtopic targeting: Focus on specific conditions
│  • Difficulty calibration: 65-75% accuracy zone
│  • Spaced repetition: Reviews start appearing
│
└─ Metadata Used: ALL
   • topic + subtopic → Precise weak area targeting
   • concepts → Concept-based review scheduling
   • cognitive_level → Reasoning error detection
   • clinical_task → Task-specific training
   • difficulty_level (IRT-calibrated) → Optimal challenge


DAY 21-33: MASTERY PHASE
│
├─ Algorithm: Maximum Personalization (85% efficacy)
│  • Weak areas continuously refined
│  • Spaced reviews dominate (40% of session)
│  • Concept retention tracking active
│  • Plateau detection monitoring
│
└─ Metadata Used: ALL + IRT data
   • IRT p-value → Empirical difficulty
   • IRT discrimination → Question quality filtering
   • Concept retention → Forgetting curve predictions


DAY 34-42: FINAL REVIEW
│
├─ Algorithm: Review Optimization
│  • Prioritize weak concepts for final reinforcement
│  • High-yield topics get extra coverage
│  • Spaced reviews of mastered content
│  • Simulate exam conditions
│
└─ Metadata Used: ALL + Performance history
   • high_yield flag → Priority weighting
   • Retention metrics → Optimal review timing
   • Weakness severity → Final push on critical areas
```

---

## Data Flow Summary

```
GENERATION → VALIDATION → DATABASE → USER STUDY → ALGORITHM → CALIBRATION → IMPROVEMENT

1. AI generates question with full metadata
   ↓
2. Quality validator checks content and metadata
   ↓
3. Question imported to database (content_status: "active")
   ↓
4. User starts study session
   ↓
5. Adaptive engine scores all candidates using metadata
   ↓
6. Question selected based on:
   • Topic weakness (from extra_data.topic)
   • Subtopic precision (from extra_data.subtopic)
   • Difficulty match (from difficulty_level)
   • Review schedule (from learning_stage)
   • Concepts tested (from extra_data.concepts)
   ↓
7. User answers question
   ↓
8. Attempt saved with interaction data
   ↓
9. Spaced repetition schedule updated
   ↓
10. Concept retention updated for all concepts
   ↓
11. (After 50 attempts) IRT calibrates difficulty
   ↓
12. Question quality assessed (discrimination, p-value)
   ↓
13. Low-quality questions retired or revised
   ↓
14. Cycle continues with improved question pool
```

---

## Key Insight: Why Metadata Matters

**Without proper metadata**, the adaptive algorithm becomes a **random question generator**.

**With proper metadata**, the adaptive algorithm becomes a **personalized tutor** that:
- Identifies weaknesses at topic AND subtopic level
- Targets questions in the optimal difficulty zone
- Schedules reviews at scientifically-proven intervals
- Tracks concept mastery across multiple question variations
- Detects reasoning errors vs knowledge gaps
- Provides task-specific training (diagnosis vs next step vs treatment)
- Prioritizes high-yield topics for maximum ROI

**The metadata is the algorithm's "eyes."** Without it, we're blind.

---

## Related Documents

1. **`ALGORITHM_INTEGRATION_SUMMARY.md`** - Executive summary
2. **`ADAPTIVE_ALGORITHM_QUESTION_REQUIREMENTS.md`** - Technical requirements
3. **`QUESTION_GENERATION_TECHNICAL_SPEC.md`** - Implementation guide

---

**Document Version**: 1.0
**Last Updated**: 2025-11-29
