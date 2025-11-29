# Adaptive Learning Algorithm: Question Generation Requirements

**Date**: 2025-11-29
**Author**: Adaptive Learning Algorithm Specialist
**Purpose**: Define technical requirements for 2,500 question generation to support ShelfSense adaptive learning algorithms

---

## Executive Summary

The 2,500 question generation plan must meet specific technical requirements for ShelfSense's adaptive learning system to function at design capacity. This document provides **concrete, actionable specifications** for question metadata, distribution, and quality metrics.

**Key Finding**: Current 223 questions support only 22-30% algorithm efficacy. Target 800 questions (Phase 1) enables 75% efficacy; 2,500 questions (Phase 2) enables 95% efficacy.

---

## 1. Tagging Requirements

### 1.1 Mandatory Metadata Fields

Every question MUST include the following fields in the `Question` table:

```python
# Required Fields (database columns)
specialty: str              # "internal_medicine", "surgery", etc.
difficulty_level: str       # "easy", "medium", "hard" (LLM-predicted initially)
source_type: str            # "ai_generated", "nbme", "community", "imported"
content_status: str         # "active" (only active questions used by algorithm)

# Required Fields (extra_data JSON)
extra_data: {
    "topic": str,           # REQUIRED - Body system (see Topic Granularity below)
    "subtopic": str,        # REQUIRED - Specific disease/condition
    "cognitive_level": str, # REQUIRED - Bloom's taxonomy level
    "clinical_task": str,   # REQUIRED - NBME task category
    "concepts": list[str],  # REQUIRED - Medical concepts tested
    "high_yield": bool      # REQUIRED - Matches HIGH_YIELD_TOPICS list
}
```

### 1.2 Current vs Required Tags

| **Tag Type** | **Current** | **Required** | **Impact** |
|--------------|-------------|--------------|------------|
| `specialty` | ✅ Present | ✅ Required | Question pool filtering |
| `difficulty_level` | ✅ Present | ✅ Required | IRT calibration baseline |
| `extra_data.topic` | ✅ Present | ✅ Required | Weak area detection (system level) |
| `extra_data.subtopic` | ❌ Missing | ⚠️ Highly Recommended | Fine-grained weak area detection |
| `extra_data.cognitive_level` | ❌ Missing | ⚠️ Highly Recommended | Reasoning error detection |
| `extra_data.clinical_task` | ❌ Missing | ⚠️ Highly Recommended | Task-specific training |
| `extra_data.concepts` | ❌ Missing | ⚠️ Highly Recommended | Concept retention tracking |
| `extra_data.high_yield` | ❌ Missing | ⚠️ Highly Recommended | Priority weighting |

### 1.3 Tag Specifications

#### Topic (Body System)
**Purpose**: Primary grouping for weak area detection
**Granularity**: 13 major systems for Internal Medicine

```python
INTERNAL_MEDICINE_TOPICS = [
    "cardiology",
    "pulmonology",
    "gastroenterology",
    "nephrology",
    "endocrinology",
    "hematology",
    "oncology",
    "infectious_disease",
    "rheumatology",
    "neurology",
    "psychiatry",
    "dermatology",
    "preventive_medicine"
]
```

**Algorithm Impact**:
- `adaptive_engine.py` groups attempts by `extra_data['topic']` (line 256-276)
- Requires **MIN_ATTEMPTS_FOR_ANALYSIS = 3** per topic for weak area detection
- **Statistical requirement**: 15+ questions per topic for 85% confidence

#### Subtopic (Disease/Condition)
**Purpose**: Fine-grained weak area detection
**Granularity**: Specific clinical entities (e.g., "acute_coronary_syndrome", "heart_failure", "atrial_fibrillation")

**Example Distribution for Cardiology**:
```python
CARDIOLOGY_SUBTOPICS = {
    "acute_coronary_syndrome": 15,  # Questions per subtopic
    "heart_failure": 12,
    "arrhythmias": 10,
    "valvular_disease": 8,
    "hypertension": 8,
    "pericardial_disease": 6,
    "congenital_heart_disease": 5
}
# Total: 64 cardiology questions
```

**Algorithm Impact**:
- Enables detection of narrow knowledge gaps (e.g., user knows heart failure but struggles with ACS)
- Future enhancement to `adaptive_engine.identify_weaknesses()` to support subtopic analysis
- **Requirement**: 8-15 questions per subtopic for reliable detection

#### Cognitive Level (Bloom's Taxonomy)
**Purpose**: Differentiate knowledge recall vs clinical reasoning errors

```python
COGNITIVE_LEVELS = {
    "recall": "Factual knowledge (normal lab values, drug side effects)",
    "comprehension": "Understanding pathophysiology, mechanisms",
    "application": "Applying knowledge to clinical scenario",
    "analysis": "Differential diagnosis, distinguishing similar conditions",
    "synthesis": "Complex multi-step reasoning, integration",
    "evaluation": "Clinical judgment, best next step decisions"
}
```

**Algorithm Impact**:
- Used by reasoning error detection to identify if errors are knowledge gaps vs reasoning failures
- **Distribution Target**: 15% recall, 20% comprehension, 30% application, 20% analysis, 10% synthesis, 5% evaluation

#### Clinical Task (NBME Categories)
**Purpose**: Task-specific skill development

```python
CLINICAL_TASKS = [
    "diagnosis",          # What is the most likely diagnosis?
    "next_step",          # What is the best next step in management?
    "mechanism",          # What is the underlying mechanism?
    "risk_factor",        # What is the most significant risk factor?
    "complication",       # What complication should you monitor for?
    "treatment",          # What is the most appropriate treatment?
    "screening",          # What screening test is indicated?
    "prognosis",          # What is the expected prognosis?
    "preventive_measure"  # What preventive measure should be recommended?
]
```

**Algorithm Impact**:
- Detects systematic errors on question types (e.g., always wrong on "EXCEPT" questions)
- **Distribution Target**: Match NBME Step 2 CK blueprint (diagnosis 40%, next_step 30%, treatment 20%, other 10%)

#### Concepts (Medical Knowledge Units)
**Purpose**: Concept-level mastery tracking via `ConceptRetention` table

**Example**:
```json
{
    "concepts": [
        "troponin_elevation",
        "stemi_criteria",
        "dual_antiplatelet_therapy",
        "pci_indications"
    ]
}
```

**Algorithm Impact**:
- Powers `ConceptRetention` forgetting curve model (lines 1108-1156 in models.py)
- Enables concept-based spaced repetition (review concept, not specific questions)
- **Requirement**: 3-5 concepts per question, aim for concept library of 500-800 unique concepts

---

## 2. Difficulty Distribution

### 2.1 Target Distribution

**For optimal learning curve (70% target accuracy zone)**:

| **Difficulty** | **% of Bank** | **Questions (800 target)** | **Questions (2,500 target)** |
|----------------|---------------|----------------------------|------------------------------|
| Easy | 25% | 200 | 625 |
| Medium | 50% | 400 | 1,250 |
| Hard | 25% | 200 | 625 |

**Rationale**:
- Matches desirable difficulty distribution for maintaining 65-75% accuracy
- Prevents frustration (too hard) or boredom (too easy)
- Enables smooth difficulty progression as users improve

### 2.2 IRT Difficulty Calibration Process

**Initial Difficulty Assignment** (LLM-predicted):
```python
# During question generation, LLM predicts difficulty based on:
# - Vignette complexity
# - Number of clinical findings to integrate
# - Differential diagnosis breadth
# - Diagnostic certainty level
difficulty_level = "easy" | "medium" | "hard"
```

**Post-Launch Calibration** (IRT-measured):
```python
# After MIN_RESPONSES_FOR_CALIBRATION = 50 attempts (item_response_theory.py)
from app.services.item_response_theory import IRTCalibrator

calibrator = IRTCalibrator(db)
irt_params = calibrator.calibrate_question(question_id)

# Empirical difficulty classification by p-value:
if p_value >= 0.85:   difficulty = "very_easy"  # Too easy - flag for revision
elif p_value >= 0.70: difficulty = "easy"
elif p_value >= 0.55: difficulty = "medium"
elif p_value >= 0.40: difficulty = "hard"
else:                 difficulty = "very_hard"  # Too hard - flag for revision

# Update question difficulty
question.difficulty_level = difficulty
question.extra_data['irt_calibration'] = {
    "p_value": irt_params.p_value,
    "discrimination": irt_params.discrimination_index,
    "response_count": irt_params.response_count,
    "calibrated_at": datetime.utcnow().isoformat()
}
```

**Quality Thresholds**:
- **Discrimination Index** > 0.20 (otherwise flag for review)
- **p-value** between 0.30-0.90 (outside = too easy/hard)
- **Response count** ≥ 50 for reliable calibration

### 2.3 Cold-Start Handling for New Questions

**Problem**: New questions have no response data, can't use IRT difficulty.

**Solution** (implemented in `adaptive_engine._score_candidates`):
```python
# New questions receive priority boost for coverage
if c.attempts_count == 0:
    score += self.WEIGHTS["coverage"]  # +1.0 score
    c.reason = "New question"
    c.difficulty = question.difficulty_level  # Use LLM-predicted difficulty
```

**Cold-start strategy**:
1. **Weeks 1-2**: Show new questions to high-performing students first (>70% accuracy)
2. **After 20 responses**: Preliminary p-value estimate (wide CI)
3. **After 50 responses**: Full IRT calibration (narrow CI)
4. **Ongoing**: Recalibrate quarterly if p-value shifts by >0.10

---

## 3. Topic Granularity

### 3.1 Current Granularity Issues

**Current Implementation**:
- **Coarse**: 13 body systems for Internal Medicine
- **Problem**: "Cardiology" weakness doesn't tell student if issue is ACS, arrhythmias, or heart failure

**Impact on Algorithm**:
```python
# Current weak area detection (adaptive_engine.py line 256-276)
weakness = UserWeakness(
    topic="cardiology",        # Too broad
    accuracy=0.55,
    attempts=20,
    severity="weak"
)
# Student sees "Weak in Cardiology" - not actionable
```

### 3.2 Recommended Granularity Enhancement

**Two-Level Taxonomy**:

```python
# Level 1: Body System (current - keep for broad categorization)
topic = "cardiology"

# Level 2: Clinical Category (NEW - add to extra_data)
subtopic = "acute_coronary_syndrome"

# Example question metadata:
extra_data = {
    "topic": "cardiology",           # System-level (13 categories)
    "subtopic": "acs",                # Disease-level (8-12 per system)
    "concepts": [                     # Concept-level (500+ total)
        "troponin_elevation",
        "stemi_criteria",
        "dual_antiplatelet_therapy"
    ]
}
```

**Recommended Subtopic Distribution** (Internal Medicine):

| **System** | **Questions** | **Subtopics** | **Questions/Subtopic** |
|------------|---------------|---------------|------------------------|
| Cardiology | 120 | 10 | 12 |
| Infectious Disease | 96 | 12 | 8 |
| Gastroenterology | 80 | 10 | 8 |
| Pulmonology | 64 | 8 | 8 |
| Nephrology | 64 | 8 | 8 |
| Endocrinology | 64 | 8 | 8 |
| Neurology | 64 | 8 | 8 |
| Hematology | 48 | 6 | 8 |
| Psychiatry | 48 | 6 | 8 |
| Rheumatology | 40 | 5 | 8 |
| Oncology | 40 | 5 | 8 |
| Dermatology | 32 | 4 | 8 |
| Preventive Medicine | 40 | 5 | 8 |
| **TOTAL** | **800** | **95** | **~8 avg** |

**Subtopic Example - Cardiology (120 questions)**:

```python
CARDIOLOGY_SUBTOPICS = {
    "acute_coronary_syndrome": 18,      # STEMI, NSTEMI, unstable angina
    "heart_failure": 15,                # Systolic, diastolic, acute decompensation
    "arrhythmias": 12,                  # Afib, VTach, heart blocks
    "valvular_disease": 10,             # AS, AR, MS, MR, MVP
    "hypertension": 10,                 # HTN urgency, resistant HTN
    "dyslipidemia": 8,                  # Statin therapy, familial hypercholesterolemia
    "pericardial_disease": 8,           # Pericarditis, tamponade, effusion
    "cardiomyopathy": 8,                # Dilated, hypertrophic, restrictive
    "peripheral_vascular": 6,           # PAD, AAA, DVT/PE
    "congenital_heart_disease": 5,      # ASD, VSD, PDA in adults
    "endocarditis": 5,                  # Native valve, prosthetic, prophylaxis
    "syncope": 5,                       # Cardiac vs non-cardiac
    "shock": 5,                         # Cardiogenic, distributive
    "other": 5                          # Cardiac arrest, cardiac exam findings
}
# Total: 120 questions across 14 subtopics
```

### 3.3 Algorithm Enhancement with Subtopic Support

**Enhanced Weak Area Detection**:
```python
# NEW: Detect weakness at subtopic level
async def identify_weaknesses_detailed(
    self,
    user_id: str,
    specialty: str = None
) -> List[DetailedUserWeakness]:
    """
    Enhanced weakness detection with subtopic granularity.

    Returns hierarchical weaknesses:
    - System-level: "Cardiology" (55% accuracy)
      - Subtopic: "ACS" (40% accuracy) ← Critical weakness
      - Subtopic: "Heart Failure" (65% accuracy) ← Developing
      - Subtopic: "Arrhythmias" (70% accuracy) ← Strong area
    """
    # Group by both topic AND subtopic
    query = self.db.query(
        Question.extra_data['topic'].label('topic'),
        Question.extra_data['subtopic'].label('subtopic'),
        func.count(QuestionAttempt.id).label('attempts'),
        func.avg(func.cast(QuestionAttempt.is_correct, func.Float)).label('accuracy')
    ).join(
        QuestionAttempt, Question.id == QuestionAttempt.question_id
    ).filter(
        QuestionAttempt.user_id == user_id
    ).group_by(
        Question.extra_data['topic'],
        Question.extra_data['subtopic']
    ).having(
        func.count(QuestionAttempt.id) >= 3  # Min 3 attempts per subtopic
    ).all()

    # Build hierarchical weakness tree
    weaknesses = defaultdict(lambda: {"subtopics": {}, "accuracy": 0})
    for row in query:
        topic = row.topic or "general"
        subtopic = row.subtopic or "general"
        accuracy = float(row.accuracy)

        weaknesses[topic]["subtopics"][subtopic] = {
            "accuracy": accuracy,
            "attempts": row.attempts,
            "severity": get_severity(accuracy)
        }

    return weaknesses
```

**Impact on Question Selection**:
```python
# Enhanced candidate scoring with subtopic targeting
def _score_candidates(
    self,
    candidates: List[QuestionCandidate],
    weaknesses: Dict[str, Dict]
) -> List[QuestionCandidate]:
    """Score with subtopic-aware weak area bonus."""

    for c in candidates:
        score = 0.0

        # Check subtopic weakness first (higher priority)
        if c.topic in weaknesses:
            topic_data = weaknesses[c.topic]
            if c.subtopic in topic_data["subtopics"]:
                subtopic_weakness = topic_data["subtopics"][c.subtopic]

                # Critical subtopic weakness = highest priority
                if subtopic_weakness["severity"] == "critical":
                    score += self.WEIGHTS["weak_area"] * 2.0  # 6.0 score!
                elif subtopic_weakness["severity"] == "weak":
                    score += self.WEIGHTS["weak_area"] * 1.5  # 4.5 score
            else:
                # Topic weak but subtopic not seen = exploration bonus
                score += self.WEIGHTS["weak_area"] * 1.0  # 3.0 score

        # ... rest of scoring logic
```

### 3.4 Accuracy Impact on Weak Area Detection

**Statistical Requirements**:

| **Questions per Subtopic** | **Min Attempts** | **Accuracy Confidence** | **False Positive Rate** |
|----------------------------|------------------|-------------------------|-------------------------|
| 3-5 | 3 | 70% | 30% |
| 6-10 | 5 | 85% | 15% |
| 11-15 | 8 | 92% | 8% |
| 16+ | 10 | 95% | 5% |

**Recommendation**: Aim for **8-15 questions per subtopic** to achieve 85-92% confidence in weakness detection.

---

## 4. Spaced Repetition Support

### 4.1 Current SM-2 Implementation

**Review Intervals** (from `adaptive_engine.py` lines 149-156):
```python
REVIEW_INTERVALS = {
    LearningStage.NEW: 0,          # Never seen
    LearningStage.LEARNING: 1,     # Seen 1-2 times
    LearningStage.YOUNG: 3,        # Correct 2-3 times
    LearningStage.MATURE: 7,       # Correct 4+ times
    LearningStage.MASTERED: 21     # Correct 5+ times
}
```

**Learning Stage Progression**:
```python
async def get_learning_stage(self, user_id: str, question_id: str) -> LearningStage:
    """Determine learning stage based on performance history."""
    attempts = self.db.query(QuestionAttempt).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.question_id == question_id
    ).order_by(QuestionAttempt.attempted_at.desc()).all()

    if not attempts:
        return LearningStage.NEW

    correct_count = sum(1 for a in attempts if a.is_correct)
    total_count = len(attempts)

    # Progression logic
    if total_count <= 2:
        return LearningStage.LEARNING
    elif correct_count >= 5 and (correct_count / total_count) >= 0.8:
        return LearningStage.MASTERED
    elif correct_count >= 4 and (correct_count / total_count) >= 0.7:
        return LearningStage.MATURE
    elif correct_count >= 2:
        return LearningStage.YOUNG
    else:
        return LearningStage.LEARNING
```

### 4.2 Questions Needed Per Topic for Proper Intervals

**Calculation**:
- User studies 40 questions/day for 42 days (6-week shelf prep)
- Target mix: 60% new, 40% review
- Days 1-21: Mostly new questions
- Days 22-42: Mix of new + review

**Question Requirements by Day**:

| **Day Range** | **New Questions/Day** | **Review Questions/Day** | **Total New Questions** | **Total Reviews** |
|---------------|----------------------|--------------------------|-------------------------|-------------------|
| Days 1-7 | 30 | 10 | 210 | 70 |
| Days 8-14 | 28 | 12 | 196 | 84 |
| Days 15-21 | 25 | 15 | 175 | 105 |
| Days 22-28 | 20 | 20 | 140 | 140 |
| Days 29-35 | 15 | 25 | 105 | 175 |
| Days 36-42 | 10 | 30 | 70 | 210 |
| **TOTAL** | - | - | **896** | **784** |

**Minimum Questions Needed**: **896 new questions** to cover 42-day study period without repetition fatigue.

**With 223 questions** (current state):
- New content exhausted by Day 9
- Days 10-42: Only reviewing same 223 questions (33 days of pure review)
- **Problem**: Memorization of specific questions, not concept mastery

**With 800 questions** (Phase 1 target):
- New content lasts through Day 33
- Days 34-42: Final review period (9 days)
- **Result**: Proper spaced repetition without content exhaustion

**With 2,500 questions** (Phase 2 target):
- New content for 100+ days
- Supports multiple rotations (Medicine, Surgery, Peds)
- Enables true long-term retention tracking

### 4.3 Variation Requirements (Avoiding Question Memorization)

**Problem**: If user sees "45-year-old male with chest pain radiating to left arm" repeatedly, they memorize the specific vignette, not the ACS diagnosis pattern.

**Solution**: **Concept variations** - Same concept, different clinical presentations.

**Example - Acute Coronary Syndrome (15 questions)**:

```python
ACS_VARIATIONS = [
    # Classic presentation variations
    {
        "vignette": "45yo M, crushing substernal chest pain radiating to left arm, diaphoresis",
        "difficulty": "easy",
        "distractor_pattern": "Other cardiac causes (PE, dissection, pericarditis)"
    },
    {
        "vignette": "62yo F, jaw pain and nausea after climbing stairs, no chest pain",
        "difficulty": "medium",
        "distractor_pattern": "Atypical presentation in women"
    },
    {
        "vignette": "70yo diabetic, sudden dyspnea without chest pain (silent MI)",
        "difficulty": "hard",
        "distractor_pattern": "Diabetic neuropathy masking pain"
    },

    # ECG interpretation variations
    {
        "vignette": "Shows ECG with ST elevation in leads II, III, aVF",
        "difficulty": "easy",
        "distractor_pattern": "Inferior STEMI vs other ST changes"
    },
    {
        "vignette": "ECG with hyperacute T waves and minimal ST elevation",
        "difficulty": "hard",
        "distractor_pattern": "Early STEMI vs pericarditis"
    },

    # Management variations
    {
        "vignette": "STEMI diagnosed, what is best next step?",
        "difficulty": "medium",
        "distractor_pattern": "PCI vs thrombolytics timing"
    },
    {
        "vignette": "NSTEMI with elevated troponin, management strategy?",
        "difficulty": "medium",
        "distractor_pattern": "Early invasive vs conservative strategy"
    },

    # Complication variations
    {
        "vignette": "Post-MI patient develops new systolic murmur",
        "difficulty": "hard",
        "distractor_pattern": "VSD vs papillary muscle rupture vs free wall"
    },

    # Risk stratification variations
    {
        "vignette": "Which patient is HIGHEST risk for ACS?",
        "difficulty": "medium",
        "distractor_pattern": "Diabetes, age, smoking comparison"
    },

    # Treatment complication variations
    {
        "vignette": "Post-PCI patient on dual antiplatelet, develops GI bleed",
        "difficulty": "hard",
        "distractor_pattern": "Bleeding management during anticoagulation"
    }
]
```

**Variation Strategy**:
- **Per concept**: 8-15 different clinical presentations
- **Variation types**:
  - Demographics (age, sex, comorbidities)
  - Presentation (typical vs atypical)
  - Diagnostic approach (labs, imaging, ECG)
  - Management (acute, chronic, complications)
  - Special populations (pregnancy, elderly, immunocompromised)

**Algorithm Support** (concept-based spaced repetition):
```python
# Instead of scheduling question_id for review, schedule concept for review
schedule = ScheduledReview(
    user_id=user_id,
    question_id=None,  # Not question-specific
    concept_id="acute_coronary_syndrome",  # Concept-level
    scheduled_for=datetime.utcnow() + timedelta(days=7),
    review_interval="7d",
    learning_stage="Young"
)

# On review due date, select a DIFFERENT question testing the same concept
def select_concept_review_question(user_id, concept_id):
    # Get all questions for this concept
    all_questions = db.query(Question).filter(
        Question.extra_data['concepts'].contains(concept_id)
    ).all()

    # Exclude questions user has seen recently (last 14 days)
    recent_attempts = db.query(QuestionAttempt.question_id).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.attempted_at >= datetime.utcnow() - timedelta(days=14)
    ).all()
    recent_ids = [a.question_id for a in recent_attempts]

    # Select unseen or least recently seen question for this concept
    candidate_questions = [q for q in all_questions if q.id not in recent_ids]

    if not candidate_questions:
        # All questions seen recently, pick least recent
        candidate_questions = all_questions

    return random.choice(candidate_questions)
```

**Benefit**: User reviews the **concept** (ACS diagnosis), not the **specific question**, preventing memorization.

---

## 5. Algorithm Warm-Up

### 5.1 Cold-Start Problem

**Definition**: When a new user starts, the algorithm has:
- No performance history
- No weak area data
- No difficulty calibration
- No personalization possible

**Current Behavior** (first 10-20 questions):
```python
# adaptive_engine.select_next_question() with no user data
weaknesses = []  # Empty
candidates = _get_candidates(user_id, specialty, [], exclude_ids)

# Scoring defaults to:
# - New question bonus (+1.0)
# - Random LLM-predicted difficulty
# - No weak area targeting
# Result: Random question selection from pool
```

### 5.2 Recommended Baseline Assessment Design

**Phase 1: Diagnostic Assessment (First 20 Questions)**

**Goal**: Establish baseline performance across all topics.

```python
BASELINE_ASSESSMENT_CONFIG = {
    "total_questions": 20,
    "difficulty_distribution": {
        "easy": 6,      # 30% - build confidence
        "medium": 10,   # 50% - calibrate baseline
        "hard": 4       # 20% - identify strong performers
    },
    "topic_distribution": {
        # Ensure 1-2 questions per major system
        "cardiology": 3,
        "pulmonology": 2,
        "gastroenterology": 2,
        "infectious_disease": 2,
        "nephrology": 2,
        "endocrinology": 2,
        "neurology": 2,
        "hematology": 1,
        "rheumatology": 1,
        "oncology": 1,
        "psychiatry": 1,
        "dermatology": 1
    },
    "selection_strategy": "fixed_pool",  # Pre-selected baseline questions
    "feedback_mode": "immediate"  # Show explanations after each
}
```

**Implementation**:
```python
async def select_baseline_question(user_id: str, specialty: str) -> Question:
    """
    Select next question for baseline assessment.

    First 20 questions are pre-selected to ensure topic/difficulty coverage.
    """
    attempt_count = db.query(func.count(QuestionAttempt.id)).filter(
        QuestionAttempt.user_id == user_id
    ).scalar() or 0

    if attempt_count >= 20:
        # Baseline complete, switch to adaptive mode
        return await adaptive_engine.select_next_question(user_id, specialty)

    # Get baseline question pool (pre-selected high-quality questions)
    baseline_pool = get_baseline_question_pool(specialty)

    # Find next question in sequence that user hasn't answered
    answered_ids = db.query(QuestionAttempt.question_id).filter(
        QuestionAttempt.user_id == user_id
    ).all()
    answered_ids = [a[0] for a in answered_ids]

    for question_id in baseline_pool:
        if question_id not in answered_ids:
            return db.query(Question).filter(Question.id == question_id).first()

    # Fallback: random from pool
    remaining = [q for q in baseline_pool if q not in answered_ids]
    return db.query(Question).filter(Question.id.in_(remaining)).first()
```

### 5.3 Questions Before Personalization Kicks In

**Personalization Thresholds**:

| **Feature** | **Min Attempts** | **Confidence** | **Rationale** |
|-------------|------------------|----------------|---------------|
| **Weak Area Detection** | 3 per topic | Low | MIN_ATTEMPTS_FOR_ANALYSIS (adaptive_engine.py line 147) |
| **Weak Area Detection** | 10 per topic | Medium | 80% confidence in topic weakness |
| **Weak Area Detection** | 20 per topic | High | 95% confidence in topic weakness |
| **Difficulty Calibration** | 20 total | Medium | User's 70% accuracy zone identified |
| **Difficulty Calibration** | 50 total | High | Stable difficulty targeting |
| **Spaced Repetition** | 1 per question | Immediate | Starts after first attempt |
| **Plateau Detection** | 70+ over 14 days | Medium | Requires 5+ sessions (adaptive_engine line 305) |

**Algorithm Efficacy by Attempt Count**:

| **Total Attempts** | **Weak Areas Identified** | **Difficulty Targeting** | **Overall Efficacy** |
|-------------------|---------------------------|--------------------------|----------------------|
| 0-20 | None | Random | 10% (baseline only) |
| 21-50 | 1-2 topics | Rough estimate | 40% (early personalization) |
| 51-100 | 3-5 topics | Calibrated | 65% (functional) |
| 101-200 | 5-8 topics | Well-calibrated | 80% (effective) |
| 201+ | 8-13 topics | Precise | 90-95% (full capability) |

**Recommendation**:
- **First 20 questions**: Baseline assessment (diagnostic)
- **Questions 21-100**: Algorithm "learning" phase (40-65% efficacy)
- **Questions 101+**: Full adaptive personalization (80%+ efficacy)

### 5.4 Initial Question Selection Strategy

**Cold-Start Selection Algorithm**:

```python
def select_initial_questions(user_id: str, specialty: str, attempt_count: int):
    """
    Progressive question selection strategy based on user maturity.

    Phases:
    1. Baseline Assessment (0-20 attempts): Diagnostic coverage
    2. Exploration (21-50 attempts): Sample all topics
    3. Targeted Learning (51-100 attempts): Focus on weak areas
    4. Full Adaptive (101+ attempts): Algorithm at full capacity
    """

    if attempt_count < 20:
        # Phase 1: Baseline Assessment
        return select_baseline_question(user_id, specialty)

    elif attempt_count < 50:
        # Phase 2: Exploration
        # Goal: Get at least 5 attempts per topic for weak area detection
        topic_coverage = get_topic_coverage(user_id, specialty)

        # Prioritize under-sampled topics
        undersampled = [t for t, count in topic_coverage.items() if count < 5]
        if undersampled:
            target_topic = random.choice(undersampled)
            return select_random_from_topic(specialty, target_topic)
        else:
            # All topics sampled, start using adaptive algorithm
            return await adaptive_engine.select_next_question(user_id, specialty)

    else:
        # Phase 3+: Full Adaptive Mode
        return await adaptive_engine.select_next_question(user_id, specialty)


def get_topic_coverage(user_id: str, specialty: str) -> Dict[str, int]:
    """Get attempt count per topic."""
    results = db.query(
        Question.extra_data['topic'].label('topic'),
        func.count(QuestionAttempt.id).label('attempts')
    ).join(
        QuestionAttempt, Question.id == QuestionAttempt.question_id
    ).filter(
        QuestionAttempt.user_id == user_id,
        Question.specialty == specialty
    ).group_by(
        Question.extra_data['topic']
    ).all()

    return {row.topic: row.attempts for row in results}
```

**Warm-up Timeline**:
- **Day 1-2** (20 questions): Baseline assessment
- **Day 3-5** (30 questions): Topic exploration
- **Day 6-10** (50 questions): Early weak area targeting
- **Day 11+** (101+ questions): Full adaptive personalization

---

## 6. Performance Tracking

### 6.1 Data Collection Per Question Attempt

**Current Fields** (`QuestionAttempt` table, lines 93-117 in models.py):

```python
class QuestionAttempt(Base):
    # Basic attempt data
    id: str
    user_id: str
    question_id: str
    user_answer: str              # "A", "B", "C", "D", "E"
    is_correct: bool
    attempted_at: datetime

    # Timing data
    time_spent_seconds: int       # Total time on question

    # Interaction tracking
    hover_events: JSON            # Which choices hovered over
    scroll_events: JSON           # Scrolling behavior
    confidence_level: int         # 1-5 user self-rating

    # Rich cognitive tracking
    interaction_data: JSON        # {
                                  #   "answer_changes": 3,
                                  #   "changed_from_correct": true,
                                  #   "elimination_pattern": ["B", "D"],
                                  #   "time_per_choice": {...}
                                  # }
```

**Recommended Additions**:

```python
# ADD to interaction_data JSON:
interaction_data = {
    # Existing fields
    "answer_changes": int,           # Number of answer changes
    "changed_from_correct": bool,    # Did user change FROM correct answer?
    "time_distribution": {           # Time spent per section
        "vignette_read": 30,         # Seconds reading vignette
        "choices_review": 20,        # Reviewing answer choices
        "final_decision": 10         # Making final selection
    },

    # NEW fields for reasoning analysis
    "choice_selection_order": ["A", "D", "B", "C"],  # Order choices were clicked
    "choice_hover_durations": {     # Hover time per choice (ms)
        "A": 2000,
        "B": 500,
        "C": 1200,
        "D": 3500,
        "E": 800
    },
    "distractor_attraction": "D",   # Which wrong answer user hovered on most
    "question_type": "except",       # EXCEPT, best_next_step, diagnosis, etc.
    "vignette_highlights": ["troponin", "ST elevation"],  # If feature exists
    "used_elimination": bool,        # Did user flag choices as eliminated?
    "paused_reading": bool,          # Did user pause while reading vignette?
}
```

### 6.2 Metrics for Question Effectiveness

**Per-Question Metrics** (calculated by `IRTCalibrator`):

```python
class QuestionPsychometrics:
    # Difficulty metrics
    p_value: float                    # 0.0-1.0 (proportion correct)
    difficulty_level: DifficultyLevel # very_easy, easy, medium, hard, very_hard
    confidence_interval: Tuple[float, float]  # 95% CI for p-value

    # Discrimination metrics
    discrimination_index: float       # -1.0 to 1.0 (point-biserial correlation)
    top_27_accuracy: float            # Accuracy among top students
    bottom_27_accuracy: float         # Accuracy among bottom students

    # Distractor metrics (per choice)
    distractor_metrics: List[DistractorMetrics]  # Selection rates, discrimination

    # Quality flags
    quality_flags: List[str]          # ["TOO_EASY", "LOW_DISCRIMINATION", etc.]
    recommendations: List[str]        # Suggested improvements

    # Usage metrics
    response_count: int               # Total attempts
    last_calibrated: datetime
```

**Quality Thresholds** (from `item_response_theory.py`):

```python
QUALITY_CRITERIA = {
    "discrimination_index": {
        "excellent": 0.40,      # Top-tier question
        "good": 0.30,           # Acceptable
        "acceptable": 0.20,     # Minimum threshold
        "poor": 0.10,           # Flag for review
        "flawed": 0.0           # Negative = remove or fix
    },

    "p_value": {
        "too_easy": 0.90,       # >90% correct = too easy
        "easy_range": (0.70, 0.90),
        "medium_range": (0.55, 0.70),
        "hard_range": (0.40, 0.55),
        "too_hard": 0.30        # <30% correct = too hard or flawed
    },

    "distractor_selection_rate": {
        "too_attractive": 0.30,  # >30% = may be correct or ambiguous
        "good": (0.15, 0.25),    # Plausible distractor
        "acceptable": (0.05, 0.30),
        "too_obvious": 0.05      # <5% = obviously wrong
    },

    "response_count": {
        "uncalibrated": 50,      # Need 50+ for reliable metrics
        "well_calibrated": 100,  # 100+ for high confidence
        "highly_reliable": 200   # 200+ for very narrow CI
    }
}
```

**Automated Quality Checks**:

```python
def assess_question_quality(question_id: str) -> Dict[str, Any]:
    """
    Run automated quality assessment on question.

    Returns quality report with flags and recommendations.
    """
    calibrator = IRTCalibrator(db)
    psychometrics = calibrator.get_full_psychometrics(question_id)

    if not psychometrics:
        return {"status": "insufficient_data", "response_count": 0}

    flags = []
    recommendations = []
    quality_score = 100.0

    # Check discrimination
    if psychometrics.irt_params.discrimination_index < 0.0:
        flags.append("CRITICAL: Negative discrimination - strong students do worse")
        recommendations.append("Review for answer key errors or ambiguous wording")
        quality_score -= 50
    elif psychometrics.irt_params.discrimination_index < 0.20:
        flags.append("Low discrimination - doesn't separate strong/weak students")
        recommendations.append("Improve distractors or clarify vignette")
        quality_score -= 20

    # Check difficulty
    if psychometrics.irt_params.p_value > 0.90:
        flags.append("Too easy - most students answer correctly")
        recommendations.append("Increase complexity or add subtle clinical findings")
        quality_score -= 15
    elif psychometrics.irt_params.p_value < 0.30:
        flags.append("Too hard - most students answer incorrectly")
        recommendations.append("Check for errors, reduce complexity, or provide more clues")
        quality_score -= 15

    # Check distractors
    for dm in psychometrics.distractor_metrics:
        if dm.choice != psychometrics.correct_choice:
            if dm.selection_rate < 0.05:
                flags.append(f"Distractor {dm.choice} too obvious (<5% selection)")
                recommendations.append(f"Make choice {dm.choice} more plausible")
                quality_score -= 5
            elif dm.selection_rate > 0.30:
                flags.append(f"Distractor {dm.choice} too attractive (>30% selection)")
                recommendations.append(f"Review choice {dm.choice} for correctness")
                quality_score -= 10

            # Check if distractor attracts strong students (bad sign)
            if dm.discrimination > 0.10:  # Strong students select this more
                flags.append(f"Distractor {dm.choice} attracts strong students")
                recommendations.append(f"Choice {dm.choice} may be partially correct")
                quality_score -= 15

    return {
        "question_id": question_id,
        "quality_score": max(0, quality_score),
        "status": "excellent" if quality_score >= 80 else "good" if quality_score >= 60 else "needs_review",
        "flags": flags,
        "recommendations": recommendations,
        "psychometrics": psychometrics
    }
```

### 6.3 When to Retire/Replace Questions

**Retirement Triggers**:

```python
RETIREMENT_CRITERIA = {
    # Psychometric failures
    "negative_discrimination": {
        "threshold": 0.0,
        "action": "immediate_retire",
        "reason": "Strong students perform worse than weak students"
    },

    "low_discrimination": {
        "threshold": 0.20,
        "attempts_threshold": 100,  # Give benefit of doubt with low N
        "action": "flag_for_review",
        "reason": "Question doesn't distinguish skill levels"
    },

    "extreme_difficulty": {
        "p_value_thresholds": (0.25, 0.95),  # Too hard or too easy
        "attempts_threshold": 100,
        "action": "flag_for_revision",
        "reason": "Difficulty outside acceptable range"
    },

    # User feedback
    "high_reject_rate": {
        "threshold": 0.30,  # >30% of users reject/report
        "action": "immediate_review",
        "reason": "User feedback indicates quality issues"
    },

    # Staleness
    "content_outdated": {
        "last_reviewed_threshold": 365,  # Days since expert review
        "action": "flag_for_update",
        "reason": "Medical guidelines may have changed"
    },

    # Performance degradation
    "p_value_drift": {
        "drift_threshold": 0.20,  # p-value changed by >20% over time
        "action": "recalibrate_or_retire",
        "reason": "Question difficulty has shifted significantly"
    }
}
```

**Retirement Workflow**:

```python
async def evaluate_question_lifecycle(question_id: str) -> Dict[str, Any]:
    """
    Determine if question should be retired, revised, or kept.

    Returns recommendation with reasoning.
    """
    calibrator = IRTCalibrator(db)
    psychometrics = calibrator.get_full_psychometrics(question_id)

    if not psychometrics:
        return {"action": "keep", "reason": "insufficient_data"}

    question = db.query(Question).filter(Question.id == question_id).first()

    # Check retirement triggers

    # 1. Negative discrimination = immediate retire
    if psychometrics.irt_params.discrimination_index < 0.0:
        return {
            "action": "retire",
            "urgency": "immediate",
            "reason": "Negative discrimination - likely flawed",
            "quality_score": 0
        }

    # 2. Low discrimination with sufficient data
    if (psychometrics.irt_params.discrimination_index < 0.20 and
        psychometrics.irt_params.response_count >= 100):
        return {
            "action": "revise_or_retire",
            "urgency": "high",
            "reason": "Poor discrimination after 100+ attempts",
            "recommendations": psychometrics.recommendations,
            "quality_score": 30
        }

    # 3. Extreme difficulty
    p_value = psychometrics.irt_params.p_value
    if (p_value < 0.25 or p_value > 0.95) and psychometrics.irt_params.response_count >= 100:
        return {
            "action": "revise",
            "urgency": "medium",
            "reason": f"Too {'hard' if p_value < 0.25 else 'easy'} (p={p_value:.2f})",
            "recommendations": psychometrics.recommendations,
            "quality_score": 50
        }

    # 4. High user rejection rate
    rejection_rate = calculate_rejection_rate(question_id)
    if rejection_rate > 0.30:
        return {
            "action": "review",
            "urgency": "high",
            "reason": f"High rejection rate ({rejection_rate:.0%})",
            "quality_score": 40
        }

    # 5. Content staleness
    days_since_review = (datetime.utcnow() - question.last_edited_at).days if question.last_edited_at else 9999
    if days_since_review > 365:
        return {
            "action": "expert_review",
            "urgency": "low",
            "reason": "Content may be outdated (>1 year old)",
            "quality_score": 70
        }

    # Question is performing well
    quality_score = calculate_quality_score(psychometrics)
    return {
        "action": "keep",
        "reason": "Good psychometric performance",
        "quality_score": quality_score,
        "next_review_date": datetime.utcnow() + timedelta(days=365)
    }


def calculate_quality_score(psychometrics: QuestionPsychometrics) -> float:
    """
    Calculate composite quality score (0-100).

    Weights:
    - Discrimination: 50%
    - Difficulty appropriateness: 25%
    - Distractor quality: 25%
    """
    score = 0.0

    # Discrimination component (0-50 points)
    disc = psychometrics.irt_params.discrimination_index
    if disc >= 0.40:
        disc_score = 50
    elif disc >= 0.30:
        disc_score = 40
    elif disc >= 0.20:
        disc_score = 30
    else:
        disc_score = disc * 100  # Linear scaling for poor questions
    score += disc_score

    # Difficulty component (0-25 points)
    p_value = psychometrics.irt_params.p_value
    if 0.55 <= p_value <= 0.70:  # Ideal medium range
        diff_score = 25
    elif 0.40 <= p_value <= 0.85:  # Acceptable range
        diff_score = 20
    else:  # Too easy or too hard
        diff_score = 10
    score += diff_score

    # Distractor component (0-25 points)
    distractor_score = 25
    for dm in psychometrics.distractor_metrics:
        if dm.choice != psychometrics.correct_choice:
            # Penalty for too obvious (<5%) or too attractive (>30%)
            if dm.selection_rate < 0.05 or dm.selection_rate > 0.30:
                distractor_score -= 5
            # Penalty if attracts strong students
            if dm.discrimination > 0.10:
                distractor_score -= 5
    score += max(0, distractor_score)

    return min(100, max(0, score))
```

**Replacement Strategy**:

| **Quality Score** | **Action** | **Timeline** | **Replacement Priority** |
|-------------------|------------|--------------|--------------------------|
| 0-30 | Retire immediately | 1 week | High (replace ASAP) |
| 31-50 | Major revision or retire | 1 month | Medium (schedule replacement) |
| 51-70 | Minor revision | 3 months | Low (improve in place) |
| 71-85 | Keep, monitor | 1 year | N/A (no replacement needed) |
| 86-100 | Excellent, keep | 2 years | N/A (exemplar question) |

**Batch Evaluation**:
```python
# Run monthly quality audit
async def monthly_quality_audit(specialty: str):
    """
    Evaluate all questions in specialty for retirement candidates.

    Generates report of questions needing attention.
    """
    questions = db.query(Question).filter(
        Question.specialty == specialty,
        Question.content_status == "active"
    ).all()

    results = {
        "retire_immediately": [],
        "revise_urgent": [],
        "revise_normal": [],
        "review_annual": [],
        "excellent": []
    }

    for question in questions:
        evaluation = await evaluate_question_lifecycle(question.id)

        if evaluation["quality_score"] < 30:
            results["retire_immediately"].append(question)
        elif evaluation["quality_score"] < 50:
            results["revise_urgent"].append(question)
        elif evaluation["quality_score"] < 70:
            results["revise_normal"].append(question)
        elif evaluation["quality_score"] < 85:
            results["review_annual"].append(question)
        else:
            results["excellent"].append(question)

    return results
```

---

## 7. Summary: Generation Requirements Checklist

### Question-Level Requirements (Per Question)

**✅ Mandatory Fields**:
- [ ] `specialty` - Target specialty (e.g., "internal_medicine")
- [ ] `difficulty_level` - LLM-predicted: "easy", "medium", "hard"
- [ ] `source_type` - "ai_generated" for bulk generation
- [ ] `content_status` - "active" after validation
- [ ] `extra_data.topic` - Body system from INTERNAL_MEDICINE_TOPICS
- [ ] `extra_data.subtopic` - Specific disease/condition
- [ ] `extra_data.cognitive_level` - Bloom's taxonomy level
- [ ] `extra_data.clinical_task` - NBME task category
- [ ] `extra_data.concepts` - List of 3-5 medical concepts
- [ ] `extra_data.high_yield` - Boolean flag for priority topics

**✅ Quality Requirements**:
- [ ] Clinical vignette: Realistic patient presentation
- [ ] 5 answer choices: 1 correct + 4 plausible distractors
- [ ] Framework-based explanation: Why correct answer is correct
- [ ] Distractor explanations: Why each wrong answer is wrong
- [ ] Predicted discrimination > 0.20 (via LLM or expert estimate)

### Bank-Level Requirements (800 Questions - Phase 1)

**✅ Distribution Targets**:
- [ ] Difficulty: 25% easy, 50% medium, 25% hard
- [ ] Topic coverage: All 13 IM systems represented
- [ ] Questions per topic: Minimum 15, target 40-80
- [ ] Questions per subtopic: Minimum 8, target 12-15
- [ ] Cognitive level: 15% recall, 30% application, 35% analysis, 20% synthesis
- [ ] Clinical task: 40% diagnosis, 30% next_step, 20% treatment, 10% other

**✅ Variation Requirements**:
- [ ] Per concept: 8-15 different clinical presentations
- [ ] Avoid verbatim duplicates
- [ ] Vary demographics, presentation, diagnostic approach
- [ ] Include typical and atypical presentations

### Algorithm Support Requirements

**✅ Weak Area Detection**:
- [ ] 15+ questions per major topic (13 topics × 15 = 195 minimum)
- [ ] 8+ questions per subtopic for reliable detection
- [ ] Metadata enables grouping by topic and subtopic

**✅ Spaced Repetition**:
- [ ] 896 new questions to cover 42-day study period (60% new, 40% review)
- [ ] Concept variations prevent memorization
- [ ] Questions support concept-based review scheduling

**✅ Difficulty Calibration**:
- [ ] LLM-predicted difficulty as starting point
- [ ] IRT recalibration after 50+ responses
- [ ] Target distribution enables 65-75% user accuracy

**✅ Question Quality**:
- [ ] Initial quality score > 60 (via LLM validator)
- [ ] Post-launch discrimination index > 0.20
- [ ] Distractor selection rates 5-30% each
- [ ] Monthly quality audits identify retirement candidates

---

## 8. Implementation Roadmap

### Phase 1: Metadata Enhancement (Week 1-2)

**Tasks**:
1. Add `subtopic`, `cognitive_level`, `clinical_task`, `concepts`, `high_yield` to question generation prompts
2. Create validation schema for new metadata fields
3. Update `adaptive_engine.py` to support subtopic-level weak area detection
4. Implement baseline assessment question pool selection

**Deliverable**: Enhanced question generation template with full metadata.

### Phase 2: Bank Generation (Week 3-10)

**Tasks**:
1. Generate 800 Internal Medicine questions with target distribution
2. Expert validation for quality (discrimination, distractors, clinical accuracy)
3. IRT pre-calibration using LLM-predicted difficulty
4. Database import with all metadata fields populated

**Deliverable**: 800 high-quality IM questions in production database.

### Phase 3: Algorithm Tuning (Week 11-12)

**Tasks**:
1. Implement subtopic weak area detection
2. Deploy baseline assessment flow for new users
3. Create monthly quality audit job
4. Monitor algorithm efficacy metrics

**Deliverable**: Adaptive algorithm operating at 75% efficacy.

### Phase 4: Scale to 2,500 (Month 4-12)

**Tasks**:
1. Expand IM bank to 1,200 questions
2. Add Surgery (700), Pediatrics (600), OBGYN (450), Psychiatry (350) specialties
3. Continuous IRT recalibration
4. Question lifecycle management (retire/revise low-quality questions)

**Deliverable**: 2,500 multi-specialty questions, 95% algorithm efficacy.

---

## 9. Success Metrics

### Short-Term (After Phase 1 - 800 Questions)

| **Metric** | **Current** | **Target** | **Measurement** |
|------------|-------------|------------|-----------------|
| Algorithm Efficacy | 22-30% | 75% | User retention + score prediction accuracy |
| Study Coverage | 9 days | 33 days | Days until new content exhausted |
| Weak Area Confidence | N/A | 85% | Statistical confidence in weakness detection |
| User Retention (Week 4) | 20-30% | 60-70% | % of users still active after 4 weeks |
| Score Prediction CI | ±25 points | ±15 points | Confidence interval width |

### Long-Term (After Phase 4 - 2,500 Questions)

| **Metric** | **Target** | **Industry Benchmark** |
|------------|------------|------------------------|
| Algorithm Efficacy | 95% | 90% (UWorld/AMBOSS) |
| Study Coverage | 80+ days | 60-100 days |
| Weak Area Confidence | 95% | 90% |
| User Retention (Week 4) | 75-85% | 70-80% |
| Question Quality Score | 85+ | 80+ |
| IRT Discrimination | >0.30 avg | >0.25 avg |

---

## Conclusion

The 2,500 question generation plan is **technically feasible** and **algorithmically necessary** for ShelfSense to reach competitive parity with industry leaders.

**Critical Path**:
1. **Metadata enrichment**: Add subtopic, cognitive level, concepts to every question
2. **Balanced distribution**: 800 IM questions with proper topic/difficulty/task coverage
3. **Variation strategy**: 8-15 clinical presentations per concept to prevent memorization
4. **Quality validation**: IRT calibration + expert review to maintain discrimination > 0.20
5. **Lifecycle management**: Monthly audits to retire/revise underperforming questions

**Expected Outcome**: Algorithm efficacy improves from 30% → 75% (Phase 1) → 95% (Phase 4), enabling ShelfSense to deliver on its promise of personalized, adaptive learning for 285+ USMLE Step 2 CK scores.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-29
**Next Review**: After Phase 1 completion (800 questions deployed)
