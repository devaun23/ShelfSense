# Question Weighting Strategy - Recency-Based Accuracy

## Critical Principle: Newer = More Accurate

**User Guidance:** "The newer NBMEs and shelf exams are the most accurate. The older they get, the less accurate they are for the new exams."

This means our algorithm must weight questions based on their recency to maximize prediction accuracy for current exams.

---

## Weighting Hierarchy (Most → Least Accurate)

### Tier 1: Highest Accuracy (Weight: 1.0)
**Most Recent NBMEs**
- NBME 13 (most recent)
- NBME 12
- NBME 11

**Rationale:** These reflect the current NBME question style, content emphasis, and difficulty calibration.

### Tier 2: High Accuracy (Weight: 0.85)
**Recent NBMEs**
- NBME 10
- NBME 9
- NBME 8

**Shelf Exam Forms 7-8** (most recent)
- Internal Medicine 7-8
- Neurology 7-8
- Pediatrics 7-8
- Surgery 7-8

**Rationale:** Still highly relevant but slightly older question styles.

### Tier 3: Moderate Accuracy (Weight: 0.70)
**Mid-Range NBMEs**
- NBME 7
- NBME 6

**Shelf Exam Forms 5-6**
- Internal Medicine 5-6
- Neurology 5-6
- Pediatrics 5-6
- Surgery 5-6

**Rationale:** Good for pattern recognition but may contain outdated clinical guidelines.

### Tier 4: Lower Accuracy (Weight: 0.55)
**Older NBMEs**
- NBME 4 (if available)
- NBME 3 (if available)

**Shelf Exam Forms 3-4**
- Internal Medicine 3-4
- Neurology 3-4
- Pediatrics 3-4
- Surgery 3-4

**Rationale:** Useful for breadth but may contain outdated treatment protocols and guidelines.

### Tier 5: Baseline Accuracy (Weight: 0.40)
**Oldest Available**
- Shelf Exam Forms 1-2
- Emergency Medicine 1-2 (oldest available)

**Rationale:** Historical value only. Use for topic coverage but down-weight heavily for predictive accuracy.

---

## Algorithm Implementation

### 1. Question Selection Algorithm

```python
def select_next_question(user_weaknesses, question_pool):
    """
    Select next question with recency bias
    """
    scored_questions = []

    for q in question_pool:
        # Base score from user's weakness pattern
        weakness_score = calculate_weakness_match(q, user_weaknesses)

        # Recency weight
        recency_weight = get_recency_weight(q)

        # Combined score: weakness × recency
        final_score = weakness_score * recency_weight

        scored_questions.append((q, final_score))

    # Sort by score, return highest
    return sorted(scored_questions, key=lambda x: -x[1])[0][0]

def get_recency_weight(question):
    """
    Assign weight based on source recency
    """
    source = question['source']

    # NBME weights
    if 'NBME 13' in source or 'NBME 12' in source or 'NBME 11' in source:
        return 1.0
    elif 'NBME 10' in source or 'NBME 9' in source or 'NBME 8' in source:
        return 0.85
    elif 'NBME 7' in source or 'NBME 6' in source:
        return 0.70
    elif 'NBME' in source:  # NBME 4, 5 or older
        return 0.55

    # Shelf exam weights (infer from form number)
    elif 'Form 8' in source or 'Form 7' in source or '8 -' in source or '7 -' in source:
        return 0.85
    elif 'Form 6' in source or 'Form 5' in source or '6 -' in source or '5 -' in source:
        return 0.70
    elif 'Form 4' in source or 'Form 3' in source or '4 -' in source or '3 -' in source:
        return 0.55
    elif 'Form 2' in source or 'Form 1' in source or '2 -' in source or '1 -' in source:
        return 0.40

    # Default for unknown sources
    return 0.60
```

### 2. Explanation Priority

When generating explanations, **prioritize citing newer sources:**

```python
def generate_explanation(question, knowledge_base):
    """
    Build explanation with recency-weighted references
    """
    # Find supporting concepts from knowledge base
    related_concepts = find_related_concepts(question, knowledge_base)

    # Weight concepts by source recency
    weighted_concepts = []
    for concept in related_concepts:
        recency = get_concept_recency_weight(concept)
        weighted_concepts.append((concept, recency))

    # Sort by recency, use most recent first
    weighted_concepts.sort(key=lambda x: -x[1])

    # Build explanation citing newest sources first
    return build_explanation(weighted_concepts)
```

### 3. Performance Prediction

**Use recency-weighted performance to predict exam scores:**

```python
def predict_exam_score(user_performance_history):
    """
    Predict Step 2 CK score using recency-weighted accuracy
    """
    weighted_correct = 0
    total_weight = 0

    for question_attempt in user_performance_history:
        recency_weight = get_recency_weight(question_attempt.question)

        if question_attempt.correct:
            weighted_correct += recency_weight

        total_weight += recency_weight

    weighted_accuracy = weighted_correct / total_weight

    # Convert to predicted score (empirical formula)
    predicted_score = 200 + (weighted_accuracy * 60)  # Scales 0-1 to 200-260

    return predicted_score
```

---

## Metadata Tagging

**Ensure all questions are tagged with recency metadata:**

```json
{
  "id": "nbme_13_001",
  "source": "NBME 13",
  "recency_tier": 1,
  "recency_weight": 1.0,
  "year_approximate": 2023,
  "vignette": "...",
  "correct_answer": "B",
  "explanation": "..."
}
```

---

## UWorld & AMBOSS Integration

**When UWorld and AMBOSS questions are added:**

### UWorld (Weight: 0.95)
- UWorld is continuously updated
- Near-maximal weight (0.95) but slightly below newest NBMEs
- UWorld questions test differently than NBMEs (more granular)

### AMBOSS (Weight: 0.90)
- AMBOSS also continuously updated
- Slightly lower than UWorld due to different question style
- Excellent for high-yield facts, less predictive of NBME style

### Combined Strategy:
```python
def get_recency_weight(question):
    source = question['source']

    # Third-party QBanks
    if 'UWorld' in source:
        return 0.95
    elif 'AMBOSS' in source:
        return 0.90

    # NBME (as above)
    elif 'NBME 13' in source or 'NBME 12' in source or 'NBME 11' in source:
        return 1.0
    # ... rest of NBME tiers
```

---

## Adaptive Learning Integration

### Priority Queue for Question Serving

1. **First**: Identify user's weakest topics
2. **Second**: Filter questions matching those topics
3. **Third**: Sort by recency weight (newest first)
4. **Fourth**: Serve highest-scored question

**Example:**
```
User struggles with "Heart Failure Management"
→ Find all Heart Failure questions
→ Questions available:
   - NBME 13, Q47 (weight: 1.0)
   - NBME 8, Q23 (weight: 0.85)
   - NBME 6, Q102 (weight: 0.70)
   - IM Form 3, Q12 (weight: 0.55)

→ Serve NBME 13, Q47 first (highest recency weight)
```

---

## Decay Function (Optional Advanced Feature)

**As new NBMEs are released, automatically decay older weights:**

```python
import datetime

def calculate_dynamic_recency_weight(question):
    """
    Decay weight based on time since question creation
    """
    base_weight = get_recency_weight(question)

    # Estimate question age (if metadata available)
    question_year = question.get('year_approximate', 2020)
    current_year = datetime.datetime.now().year
    years_old = current_year - question_year

    # Decay: 5% per year
    decay_factor = 0.95 ** years_old

    return base_weight * decay_factor
```

---

## Summary: Implementation Checklist

✅ **Tag all questions with:**
- `recency_tier` (1-5)
- `recency_weight` (0.40-1.0)
- `source` (for inference)
- `year_approximate` (if known)

✅ **Algorithm priorities:**
1. Weakness matching (what user struggles with)
2. Recency weighting (newer = better)
3. Diversity (don't over-serve one source)

✅ **Performance tracking:**
- Weight user's correct/incorrect by recency
- Predict scores using recency-weighted accuracy
- Alert user when struggling on newest content

✅ **Question rotation:**
- Prefer newest questions for active learning
- Use older questions for breadth/coverage
- Never ignore old questions completely (still valuable for topic exposure)

---

## User-Facing Impact

**What the user sees:**

"You're performing at 85% on NBME 11-13 questions (most recent). Based on this, your predicted Step 2 CK score is **245**. Focus on improving performance on the newest NBMEs to maximize your score."

**vs. without recency weighting:**

"You're performing at 78% overall. Predicted score: 238." ← Less accurate because it treats old/new equally

---

**Last Updated:** November 19, 2025
**Status:** Ready for algorithm implementation
**Priority:** HIGH - Critical for accurate score prediction
