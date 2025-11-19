# ShelfSense Explanation Framework

## Core Structure

Every explanation follows this 3-part format:

1. **Line 1: Principle Statement** - The exact decision rule
2. **Lines 2-5: Clinical Reasoning Section** - Why this rule applies here
3. **Lines 6+: Answer Dissection** - Why each wrong answer fails

## Question Type Classification

ShelfSense uses 6 adaptive frameworks to match NBME reasoning patterns:

### TYPE A: STABLE/UNSTABLE BIFURCATION
**Identify:** Vital sign thresholds (BP <90, HR >120, O2 <92)
**Principle:** `[Finding] with [instability marker] requires [immediate action]`
**Clinical reasoning:** Focus on why instability changes the entire pathway

**Example:**
```
Acute cholecystitis with hemodynamic instability requires source control.

Clinical reasoning: BP 82/48 (systolic <90) indicates septic shock from cholecystitis.
Stable cholecystitis gets antibiotics and elective surgery within 72 hours. Unstable
cholecystitis needs antibiotics and urgent surgery. The hypotension changes this from
elective to urgent. Source control takes priority over additional imaging or medical
optimization when septic.
```

### TYPE B: TIME-SENSITIVE DECISIONS
**Identify:** Time windows (<3 hrs, <4.5 hrs, <24 hrs, >48 hrs)
**Principle:** `[Condition] within [time window] indicates [intervention]`
**Clinical reasoning:** Explain what happens before/after the window

**Example:**
```
Suspected subarachnoid hemorrhage requires immediate non-contrast CT.

Clinical reasoning: Thunderclap headache suggests SAH. CT sensitivity is >95% within
6 hours of onset but drops to 50% by day 5. At 2 hours, CT is the fastest and most
sensitive test. If CT is negative but suspicion remains high, LP would follow. If
presentation were >6 hours, would need both CT and LP. MRI takes too long for
unstable SAH.
```

### TYPE C: DIAGNOSTIC SEQUENCE
**Identify:** Test ordering (screening → confirmatory → definitive)
**Principle:** `[Clinical picture] requires [test sequence]`
**Clinical reasoning:** Show why you can't skip steps or reverse order

### TYPE D: RISK STRATIFICATION
**Identify:** Scoring systems (Wells, CHADS-VASc, CURB-65)
**Principle:** `[Score threshold] determines [disposition/treatment]`
**Clinical reasoning:** Explain the threshold and what changes above/below it

### TYPE E: TREATMENT HIERARCHY
**Identify:** First-line vs second-line, contraindications
**Principle:** `[Condition] treated with [agent] when [criteria met]`
**Clinical reasoning:** Explain when you move to next option

### TYPE F: DIFFERENTIAL NARROWING
**Identify:** Key distinguishing features
**Principle:** `[Specific finding] differentiates [diagnosis] from alternatives`
**Clinical reasoning:** Show what finding makes other diagnoses impossible

## Writing Process

### 1. Classify the Question Type
Which decision pattern does NBME want you to recognize?

### 2. Extract the Critical Values
- Don't say "hypotensive" - say "BP 80/50 (systolic <90)"
- Don't say "elevated" - say "troponin 0.8 (normal <0.04)"

### 3. Write the Principle
One sentence containing the exact decision rule

### 4. Write Clinical Reasoning Section
- Define all thresholds explicitly
- Show both/all pathways without assuming knowledge
- Connect this patient's specific values to the decision
- Keep it neutral and factual

### 5. Dissect Wrong Answers
Explain why each fails for THIS specific patient
Don't just say "incorrect" - show what would need to be different

## Quality Control Checklist

- [ ] Every number is defined (what makes it abnormal)
- [ ] Decision tree is complete but implicit
- [ ] No assumed knowledge
- [ ] Medically accurate for NBME standards
- [ ] Under 200 words total
- [ ] No statistics unless NBME tests them
- [ ] Pattern is teachable across similar questions

## Data Structure

```json
{
  "explanation": {
    "type": "TYPE_A_STABILITY",
    "principle": "Acute cholecystitis with hemodynamic instability requires source control.",
    "clinical_reasoning": "BP 82/48 (systolic <90) indicates septic shock...",
    "correct_answer_explanation": "[Full explanation]",
    "distractor_explanations": {
      "A": "Why A is wrong for THIS patient",
      "B": "Why B is wrong for THIS patient",
      "C": "Why C is wrong for THIS patient"
    },
    "educational_objective": "Recognize that hemodynamic instability in cholecystitis requires urgent source control, not just antibiotics.",
    "concept": "Acute Care Surgery"
  }
}
```

## Integration with Reasoning Patterns

Each explanation type maps to specific reasoning patterns:

- **TYPE A (Stability)** → urgency_assessment, severity_misjudgment
- **TYPE B (Time-Sensitive)** → timeline_errors, treatment_timing
- **TYPE C (Diagnostic)** → test_sequence_errors, premature_closure
- **TYPE D (Risk Stratification)** → threshold_confusion, severity_misjudgment
- **TYPE E (Treatment Hierarchy)** → treatment_prioritization, contraindication_missed
- **TYPE F (Differential)** → anchoring_bias, missed_qualifiers

## Adaptive Learning Integration

The explanation framework supports ShelfSense's adaptive learning by:

1. **Pattern Recognition Training** - Students learn to classify question types
2. **Threshold Internalization** - Explicit values help memorize decision points
3. **Decision Tree Building** - Clinical reasoning section shows complete pathways
4. **Error Prevention** - Distractor dissection shows common mistakes

## Implementation Notes

- Explanations auto-classify based on keywords and structure
- AI can generate explanations following this framework
- Human review ensures medical accuracy
- Students can filter questions by explanation type
- Performance tracking by explanation type guides adaptive learning
