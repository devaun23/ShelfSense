# Adaptive Explanation Improvement System

## Overview

A self-improving system where explanations evolve based on actual student errors, not assumptions about what's clear.

## Feedback Collection

### 1. Immediate Binary Feedback

After each explanation, single click tracking:
- **[Clicked]** = Understood instantly
- **[Not clicked]** = Needed re-reading
- Track comprehension rate per explanation

### 2. Retention Testing

24-48 hours later, serve similar question:
- Same concept, different vignette
- **If correct** → explanation worked
- **If wrong** → explanation failed
- **If wrong same way** → explanation didn't address the error
- **If wrong new way** → explanation created new confusion

### 3. Error Pattern Tracking

If user gets question wrong AFTER seeing explanation:
- Log exact wrong answer chosen
- Log time spent on question
- Log confidence level
- Pattern emerges: "Explanation X leads to error Y"

## Improvement Algorithm

```python
def improve_explanation(question_id, user_outcomes):
    current_explanation = get_explanation(question_id)

    if retention_rate < 0.7:
        # Explanation not sticking
        if users_still_choosing_B:
            # Need better differentiation of B
            enhance_wrong_answer_explanation('B')
        elif users_taking_too_long:
            # Decision tree not clear
            simplify_decision_pathway()
        elif users_overconfident_and_wrong:
            # Missing a key distinction
            add_threshold_clarification()

    if specific_demographic_failing:
        # e.g., weak foundation students
        add_prerequisite_knowledge()

    return revised_explanation
```

## Continuous Improvement Process

### WEEK 1-2: BASELINE
- Deploy initial explanations
- Track all metrics
- No changes yet (need data)

### WEEK 3-4: IDENTIFY PATTERNS
Failing explanations share:
- Missing explicit thresholds?
- Assuming knowledge?
- Wrong decision tree?

### WEEK 5-6: A/B TESTING
For worst-performing explanations:
- **Version A:** Original
- **Version B:** Revised based on error patterns
- 50/50 split test

### WEEK 7-8: IMPLEMENT WINNERS
Replace explanations where Version B > Version A by >10%

## Specific Tracking Metrics

### Per Explanation:
- First-read comprehension rate
- 24hr retention rate
- Common wrong answer after reading
- Average time to understand
- Confidence calibration change

### Pattern Analysis:
- Which explanations work for strong vs weak students
- Which decision trees are hardest to convey
- Which thresholds get forgotten most

## Example Evolution

### Version 1 (60% retention):
```
"Positive FAST with hemodynamic instability indicates immediate surgery."
```

**Analysis:** Students still choosing CT (40% error rate)
**Problem:** Not understanding what defines "instability"

### Version 2 (75% retention):
```
"Positive FAST with hemodynamic instability indicates immediate surgery.
Clinical reasoning: BP 80/50 (systolic <90) defines instability..."
```

**Analysis:** Students now choosing serial exams (25% error rate)
**Problem:** Not understanding positive FAST is definitive

### Version 3 (88% retention):
```
"Positive FAST with hemodynamic instability indicates immediate surgery.
Clinical reasoning: BP 80/50 (systolic <90) defines instability. Positive FAST
confirms blood requiring surgery; negative FAST would need CT..."
```

## Automation Pipeline

1. Every explanation gets unique ID
2. Track every user interaction
3. Weekly analysis of worst performers
4. AI generates revised version based on error patterns
5. Auto-deploy A/B test
6. Auto-promote winners

## Database Schema

### explanation_performance table

```sql
CREATE TABLE explanation_performance (
    explanation_id TEXT,
    version INTEGER,
    user_id TEXT,
    understood_immediately BOOLEAN,
    time_to_comprehend REAL,
    retention_test_correct BOOLEAN,
    retention_test_wrong_answer TEXT,
    user_baseline_score INTEGER,
    timestamp DATETIME
);
```

### explanation_versions table

```sql
CREATE TABLE explanation_versions (
    explanation_id TEXT,
    version INTEGER,
    content TEXT,
    deployment_date DATETIME,
    retention_rate REAL,
    comprehension_rate REAL,
    common_error_after TEXT
);
```

## Feedback Loop to Question Generation

If explanation for concept X consistently fails:
- Generate more questions testing concept X differently
- Approach from different angles
- Build understanding gradually

This creates a self-improving system where explanations evolve based on actual student errors, not our assumptions about what's clear.

## Implementation Notes

### Backend API Endpoints

```
POST /api/explanation-metrics
- Record user interaction with explanation
- Store timing, hover, scroll data

GET /api/explanation-performance/{id}
- Retrieve performance metrics for specific explanation
- Return retention rate, comprehension rate, common errors

POST /api/retention-test
- Log result of similar question served 24hrs later
- Update explanation effectiveness score

GET /api/explanations/worst-performers
- Return explanations with retention < 70%
- Trigger revision workflow
```

### A/B Testing Implementation

```python
def serve_explanation(question_id, user_id):
    # Get all versions of this explanation
    versions = get_explanation_versions(question_id)

    if len(versions) == 1:
        return versions[0]

    # A/B test: 50/50 split
    user_hash = hash(user_id) % 100
    if user_hash < 50:
        return versions[0]  # Version A
    else:
        return versions[1]  # Version B
```

### Automatic Promotion

```python
def promote_winning_version():
    # Run weekly
    tests = get_active_ab_tests()

    for test in tests:
        version_a = test.versions[0]
        version_b = test.versions[1]

        retention_a = get_retention_rate(version_a.id)
        retention_b = get_retention_rate(version_b.id)

        # If Version B is 10%+ better, promote it
        if retention_b > retention_a * 1.10:
            promote_to_production(version_b)
            deprecate_version(version_a)
```
