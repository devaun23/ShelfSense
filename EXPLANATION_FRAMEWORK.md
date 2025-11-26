# ShelfSense Explanation Framework

## Overview

This framework defines how ShelfSense generates and displays explanations for USMLE Step 2 CK and shelf exam questions. The goal is to create explanations that help students understand concepts deeply through clear pedagogy, step-by-step breakdowns, memorable analogies, and visual representation suggestions.

---

## Core Principles

### 1. Progressive Disclosure
Explanations reveal information in layers, allowing students to choose their depth of engagement:
- **Quick Answer** (30 words) - For rapid review
- **Core Explanation** (200 words) - Standard learning
- **Deep Dive** - Advanced understanding with pathophysiology and differentials

### 2. Explicit Thresholds
Never use vague terms. Always provide exact values:
- ❌ "hypotensive" → ✅ "BP 82/48 (systolic <90)"
- ❌ "elevated troponin" → ✅ "troponin 0.8 ng/mL (normal <0.04)"
- ❌ "tachycardic" → ✅ "HR 124 bpm (>100)"

### 3. Decision Tree Thinking
Every explanation implicitly teaches a decision pathway that applies to similar questions.

### 4. Error Prevention
Proactively address common mistakes and cognitive traps.

---

## Question Type Classification

ShelfSense uses 6 adaptive frameworks matching NBME reasoning patterns:

### TYPE A: STABLE/UNSTABLE BIFURCATION
**Identify:** Vital sign thresholds (BP <90, HR >120, O2 <92, altered mental status)

**Principle Template:** `[Finding] with [instability marker] requires [immediate action]`

**Clinical Reasoning Focus:** Why instability changes the entire management pathway

**Example:**
```
QUICK: Septic shock from cholecystitis needs urgent surgery, not just antibiotics.

CORE: Acute cholecystitis with hemodynamic instability requires source control.
BP 82/48 (systolic <90) indicates septic shock. Stable cholecystitis gets
antibiotics and elective surgery within 72 hours. Unstable cholecystitis needs
antibiotics AND urgent surgery. The hypotension changes this from elective to
emergent because the source of infection must be removed.

MEMORY HOOK: "You can't put out a fire while fuel is still burning" - antibiotics
alone can't overcome an infected gallbladder that's actively seeding bacteria.
```

---

### TYPE B: TIME-SENSITIVE DECISIONS
**Identify:** Time windows (<3 hrs, <4.5 hrs, <24 hrs, >48 hrs)

**Principle Template:** `[Condition] within [time window] indicates [intervention]`

**Clinical Reasoning Focus:** What changes before/after the time threshold

**Example:**
```
QUICK: SAH within 6 hours = CT first (>95% sensitive). After 6 hours = need LP too.

CORE: Thunderclap headache at 2 hours post-onset requires immediate non-contrast CT.
CT sensitivity for SAH is >95% within 6 hours but drops to 50% by day 5. At 2 hours,
CT is fastest and most sensitive. If negative but suspicion high, LP follows.
MRI takes too long for potentially unstable SAH.

STEP-BY-STEP:
1. Recognize thunderclap headache pattern (worst headache, maximal at onset)
2. Check time since onset (<6 hrs vs >6 hrs changes approach)
3. Order non-contrast CT head immediately
4. If CT negative + high suspicion → LP for xanthochromia
```

---

### TYPE C: DIAGNOSTIC SEQUENCE
**Identify:** Test ordering questions (screening → confirmatory → definitive)

**Principle Template:** `[Clinical picture] requires [test sequence]`

**Clinical Reasoning Focus:** Why you cannot skip steps or reverse order

**Example:**
```
QUICK: Screen with sensitive test, confirm with specific test, then treat.

CORE: Suspected PE with intermediate pretest probability requires D-dimer first.
D-dimer is sensitive (rules out if negative) but not specific. Wells score
determines pretest probability. Low/intermediate probability + negative D-dimer
= PE ruled out. High probability or positive D-dimer = CT angiography needed.

VISUAL AID: Flowchart
┌─────────────────┐
│ Calculate Wells │
└────────┬────────┘
         ▼
    ┌─────────┐
    │ Score?  │
    └────┬────┘
   Low/Int│    High
      ▼       ▼
  D-dimer   CT-PA
      │
  Neg │ Pos
   ▼     ▼
 Stop  CT-PA
```

---

### TYPE D: RISK STRATIFICATION
**Identify:** Scoring systems (Wells, CHADS₂-VASc, CURB-65, HEART)

**Principle Template:** `[Score threshold] determines [disposition/treatment]`

**Clinical Reasoning Focus:** What changes above vs below the threshold

**Example:**
```
QUICK: CURB-65 ≥2 = hospitalize. <2 = outpatient treatment is safe.

CORE: CURB-65 score of 2 requires hospital admission for pneumonia.
C = Confusion, U = Urea >7 mmol/L, R = RR ≥30, B = BP <90/60, 65 = age ≥65.
Score 0-1: outpatient (mortality <3%), Score 2: hospital admission (mortality 9%),
Score 3+: consider ICU (mortality 15-40%). This patient has confusion (1 point)
and age 72 (1 point) = score 2, so admission is warranted.

COMMON TRAP: Don't anchor on "looks well" - the scoring system exists because
clinical gestalt underestimates pneumonia severity in elderly patients.
```

---

### TYPE E: TREATMENT HIERARCHY
**Identify:** First-line vs second-line, contraindications, stepped therapy

**Principle Template:** `[Condition] treated with [agent] when [criteria met]`

**Clinical Reasoning Focus:** When to move to next-line therapy

**Example:**
```
QUICK: Beta-blockers first for stable angina unless asthma/COPD (use CCB instead).

CORE: Stable angina in a patient with asthma requires calcium channel blocker.
Beta-blockers are first-line for stable angina (reduce myocardial oxygen demand,
mortality benefit). However, non-selective beta-blockers cause bronchospasm.
Cardioselective beta-blockers (metoprolol, atenolol) are safer but still
relatively contraindicated in moderate-severe asthma. CCBs (amlodipine, diltiazem)
provide antianginal benefit without respiratory effects.

TREATMENT LADDER:
1st line: Beta-blocker (metoprolol, atenolol)
   ↓ if contraindicated (asthma, severe bradycardia, decompensated HF)
2nd line: CCB (amlodipine for HTN, diltiazem for rate control)
   ↓ if still symptomatic
Add: Long-acting nitrate
```

---

### TYPE F: DIFFERENTIAL NARROWING
**Identify:** Key distinguishing features, "what makes this diagnosis vs that"

**Principle Template:** `[Specific finding] differentiates [diagnosis] from alternatives`

**Clinical Reasoning Focus:** The one finding that makes other diagnoses impossible

**Example:**
```
QUICK: Migratory arthritis + heart murmur = rheumatic fever, not septic arthritis.

CORE: Migratory polyarthritis differentiates acute rheumatic fever from septic arthritis.
Septic arthritis is monoarticular (one hot, swollen joint) and non-migratory.
ARF causes migratory polyarthritis (moves from joint to joint over days).
Additional Jones criteria in this patient: new heart murmur (carditis),
recent strep pharyngitis, elevated ASO titer.

COMPARISON TABLE:
| Feature          | Rheumatic Fever    | Septic Arthritis |
|------------------|--------------------| -----------------|
| Joint pattern    | Migratory, poly    | Single joint     |
| Fever course     | Fluctuating        | Persistent high  |
| Response to NSAIDs| Dramatic           | Minimal          |
| Joint fluid      | Inflammatory       | Purulent, WBC>50K|
```

---

## Enhanced Data Structure

```json
{
  "explanation": {
    "type": "TYPE_A_STABILITY",

    "quick_answer": "30-word maximum summary for rapid review",

    "principle": "One-sentence principle with exact decision rule",

    "clinical_reasoning": "2-5 sentences explaining why this rule applies, with explicit thresholds",

    "correct_answer_explanation": "Why the correct answer is right for THIS patient",

    "distractor_explanations": {
      "A": "Why wrong for THIS patient (15-20 words)",
      "B": "Why wrong for THIS patient",
      "C": "Why wrong for THIS patient",
      "D": "Why wrong for THIS patient"
    },

    "deep_dive": {
      "pathophysiology": "Why this happens at a biological/mechanistic level",
      "differential_comparison": "How to distinguish from similar conditions",
      "clinical_pearls": ["High-yield facts", "Board-relevant details"]
    },

    "step_by_step": [
      {"step": 1, "action": "What to do", "rationale": "Why"},
      {"step": 2, "action": "Next step", "rationale": "Why"}
    ],

    "visual_aid": {
      "type": "decision_tree | flowchart | comparison_table | timeline",
      "description": "What the visual should show",
      "key_elements": ["Branch point 1", "Branch point 2"]
    },

    "memory_hooks": {
      "analogy": "Relatable comparison to help remember",
      "mnemonic": "If applicable (e.g., MUDPILES for anion gap)",
      "clinical_story": "Brief memorable case pattern"
    },

    "common_traps": [
      {
        "trap": "What students commonly do wrong",
        "why_wrong": "Why this thinking fails",
        "correct_thinking": "The right approach"
      }
    ],

    "educational_objective": "What decision-making pattern this question teaches",

    "concept": "Primary medical concept",

    "related_topics": ["Topic 1", "Topic 2"],

    "difficulty_factors": {
      "content_difficulty": "basic | intermediate | advanced",
      "reasoning_complexity": "single_step | multi_step | integration",
      "common_error_rate": 0.35
    }
  }
}
```

---

## Quality Control Checklist

### Required Elements
- [ ] Every number is defined with normal range
- [ ] Decision pathway is complete but implicit
- [ ] No assumed prior knowledge
- [ ] Medically accurate for NBME standards
- [ ] Under 200 words for core explanation
- [ ] Quick answer ≤30 words
- [ ] Distractor explanations are specific to THIS patient

### Enhanced Elements (When Applicable)
- [ ] Step-by-step breakdown for procedural questions
- [ ] Comparison table for differential diagnosis
- [ ] Memory hook for high-yield concepts
- [ ] Common trap addressed if error rate >30%
- [ ] Visual aid suggestion for complex pathways

---

## Integration with Adaptive Learning

### Pattern Recognition Training
Each explanation type maps to reasoning patterns tracked in analytics:
- **TYPE A (Stability)** → urgency_assessment, severity_misjudgment
- **TYPE B (Time-Sensitive)** → timeline_errors, treatment_timing
- **TYPE C (Diagnostic)** → test_sequence_errors, premature_closure
- **TYPE D (Risk Stratification)** → threshold_confusion, score_misapplication
- **TYPE E (Treatment Hierarchy)** → treatment_prioritization, contraindication_missed
- **TYPE F (Differential)** → anchoring_bias, missed_qualifiers

### Error Analysis Integration
When a student answers incorrectly, the ErrorAnalysis component:
1. Identifies the error pattern (knowledge_gap, premature_closure, etc.)
2. Provides targeted coaching based on explanation type
3. Suggests related questions for remediation
4. Tracks acknowledgment for spaced repetition scheduling

### Progressive Difficulty
Explanations adapt based on student performance:
- **Struggling students**: Show step-by-step breakdowns, memory hooks, analogies
- **Proficient students**: Show quick answer, highlight nuances and edge cases
- **Advanced students**: Deep dive with pathophysiology and rare presentations

---

## Implementation Notes

1. **AI Generation**: GPT-4 generates explanations following this framework
2. **Human Review**: Medical accuracy verified for high-stakes content
3. **Version Control**: Explanations versioned for A/B testing improvements
4. **Performance Tracking**: Retention rates tracked per explanation to identify weak explanations
5. **Continuous Improvement**: Low-performing explanations flagged for revision

---

## Frontend Display Guidelines

### Default View
Show: Quick answer + Core explanation + Correct/Wrong answer highlights

### Expanded View (Click to reveal)
Show: Deep dive + Step-by-step + Visual aid + Memory hooks

### Error State
Show: ErrorAnalysis component with coaching question + Common traps

### Review Mode
Show: Quick answer only (for rapid spaced repetition review)
