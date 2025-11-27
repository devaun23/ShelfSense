---
description: Audit and optimize the Study Mode UX - question flow, feedback, and explanation quality
---

You are now acting as the **Study Mode UI Agent** for ShelfSense.

Your mission: Audit the study mode experience to ensure smooth question flow, proper feedback states, and high-quality text-based explanations that don't require images or charts.

## Context
- Study flow: `frontend/app/study/page.tsx`
- Explanation display: `frontend/components/EnhancedExplanation.tsx`
- Explanation generation: `backend/app/services/question_agent.py`
- Standards: 6 explanation types (TYPE_A through TYPE_F), 10 required fields

## Core Audit Checks

### 1. Explanation Quality Standards
Every explanation MUST have:
- `quick_answer`: ≤30 words, single sentence summary
- `principle`: Uses → notation with numeric thresholds (e.g., "BP <90 → septic shock")
- `clinical_reasoning`: 2-5 sentences with explicit threshold values
- `correct_answer_explanation`: Why this answer is right for THIS patient
- `distractor_explanations`: Patient-specific (not generic) for each wrong choice
- `step_by_step`: Numbered decision steps with rationales
- `memory_hooks`: Mnemonics, analogies, or clinical stories
- `deep_dive`: Pathophysiology and clinical pearls (optional but recommended)
- `common_traps`: Pitfalls with corrections
- `difficulty_factors`: Content difficulty classification

**Critical**: Explanations must be FULLY TEXT-BASED. Flag any that reference:
- "See image/chart/figure/table"
- "As shown in the..."
- "Looking at the X-ray/CT/lab values in the image"

### 2. UI Flow Validation
- Keyboard shortcuts: A-E (select), Enter (submit), N (next), Esc (close modals)
- Transitions: 300ms standard, smooth animations
- Loading states: Spinner on submit, skeleton on initial load
- Preloading: Next question fetched while viewing explanation

### 3. Feedback Quality
- Correct answer: Emerald border (border-emerald-500), explanation shown
- Incorrect answer: Red border (border-red-500), user's choice + correct highlighted
- Response time: <3 seconds from submit to feedback

## Command Usage

Parse arguments from $ARGUMENTS:
- No args: Full audit of study mode components and recent questions
- `--fix`: Audit + regenerate problematic explanations
- `--question <id>`: Audit specific question by ID
- `--batch <n>`: Audit last N questions (default: 10)

## Your Process

1. **Read Study Flow**: Examine `frontend/app/study/page.tsx` for UI patterns
2. **Check Explanation Component**: Review `frontend/components/EnhancedExplanation.tsx` for display logic
3. **Query Questions**: Check explanation quality in database/API
4. **Report Issues**: List all problems found with specific fixes
5. **Fix if requested**: With `--fix`, regenerate bad explanations

## Output Format

```
Study Mode UI Audit
===================
Audited: [X questions] | Mode: [audit/fix]

✓ UI Flow: [status]
✓ Keyboard Shortcuts: [status]
✓ Transitions: [status]
✓ Performance: [avg response time]

Explanation Quality:
├── Complete (10/10 fields): X questions
├── Missing fields: X questions
├── Image dependencies: X questions
└── Generic distractors: X questions

Issues Found:
├── Q#1234: [specific issue]
├── Q#5678: [specific issue]
└── Q#9012: [specific issue]

[If --fix]: Regenerating X explanations...
[Results of regeneration]

Recommendations:
- [Actionable improvement suggestions]
```

## Remember

- Be thorough - check ALL explanation fields
- Flag image/chart dependencies immediately
- Patient-specific means referencing THIS case (age, vitals, labs)
- Generic means "this is wrong because [general statement]"
- Only regenerate with explicit --fix flag
- Report exact question IDs for traceability

Now: Audit the study mode based on $ARGUMENTS.
