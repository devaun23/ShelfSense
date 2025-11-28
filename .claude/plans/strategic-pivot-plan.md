# ShelfSense Strategic Pivot Plan

## The Hard Truth

**AI cannot reliably generate NBME-quality medical questions in real-time.**

After deep analysis of the codebase, here's what's happening:

| Current State | Problem |
|---------------|---------|
| 16k tokens/question (agent mode) | $0.10-0.30 per question, API limits hit |
| Temperature 0.7-0.8 | Inconsistent quality, hallucinations |
| 11+ explanation fields | Bloated, often generic content |
| Real-time generation | Slow (30-60s), unreliable, expensive |
| Inline + tabbed explanations | Information overload |

**What real question banks do:** Human-written questions, peer-reviewed, psychometrically validated, finite curated pools.

---

## The Pivot: Curated Content + AI Tutoring

### Core Philosophy Change

```
BEFORE: AI generates questions in real-time → Users answer
AFTER:  Curated questions exist → AI explains/tutors → Users learn
```

### Three-Part Strategy

1. **Curate a Core Question Bank** (500-1000 questions)
2. **Use AI for Explanations Only** (batch generation, not real-time)
3. **Simplify UI** (clean, scannable, progressive disclosure)

---

## Part 1: Curated Question Bank

### Option A: Open-Source Medical Questions
- **OpenMedQA** - Open-source medical question datasets
- **MedQA** - USMLE-style questions from research datasets
- **WikiDoc Questions** - Community-contributed medical education

### Option B: Content Partnership
- Contact AMBOSS, Firecracker, or similar for licensing
- Many offer API access or bulk licensing

### Option C: Professional Content Creation
- Hire medical students/residents to write questions
- Use AI to assist (not replace) content creation
- Implement review queue (already exists in your schema)

### Database Changes
```sql
-- Mark questions as "curated" vs "ai_generated"
ALTER TABLE questions ADD COLUMN is_curated BOOLEAN DEFAULT FALSE;
ALTER TABLE questions ADD COLUMN curator_id VARCHAR;
ALTER TABLE questions ADD COLUMN curation_date TIMESTAMP;
ALTER TABLE questions ADD COLUMN medical_accuracy_score FLOAT;
```

### Import Process
```python
# backend/scripts/import_curated_questions.py
def import_question(data: dict, curator_id: str) -> Question:
    return Question(
        vignette=data['stem'],
        choices=data['options'],
        answer_key=data['answer'],
        source='Curated - Medical Education',
        source_type='curated',
        is_curated=True,
        curator_id=curator_id,
        content_status='active',
        explanation=None  # AI will generate later
    )
```

---

## Part 2: AI for Explanations Only

### New Explanation Schema (Simplified)

Replace the 11+ field monstrosity with 4 focused fields:

```python
# backend/app/schemas/explanation_v2.py
class ExplanationV2(BaseModel):
    """Simplified, focused explanation"""

    # 1. THE ANSWER (30 words max)
    answer: str  # "The correct answer is C because..."

    # 2. THE CONCEPT (1-2 sentences)
    key_concept: str  # Core medical principle being tested

    # 3. WHY EACH WRONG (one sentence each)
    wrong_answers: dict[str, str]  # {"A": "...", "B": "...", "D": "...", "E": "..."}

    # 4. CLINICAL PEARL (optional, memorable)
    pearl: str | None  # "Remember: X always means Y"
```

### Batch Explanation Generation

Generate explanations offline, not in real-time:

```python
# backend/scripts/batch_generate_explanations.py
async def generate_explanations_batch(db: Session, batch_size: int = 50):
    """Generate explanations for all questions without them"""

    questions = db.query(Question).filter(
        Question.explanation.is_(None),
        Question.is_curated == True
    ).limit(batch_size).all()

    for question in questions:
        explanation = await generate_simple_explanation(question)
        question.explanation = explanation.model_dump()

        # Small delay to avoid rate limits
        await asyncio.sleep(0.5)

    db.commit()
```

### Token Cost Comparison

| Approach | Tokens | Cost/Question | 1000 Questions |
|----------|--------|---------------|----------------|
| Current Agent | 16,000 | $0.107 | $107 |
| Current Simple | 5,500 | $0.029 | $29 |
| **New Explanation-Only** | 1,500 | $0.008 | **$8** |

---

## Part 3: Simplified UI

### Current Problem
- Vignette takes too much space
- Inline explanations + 4 tabs = overwhelming
- Too much text density

### New UI Philosophy
```
1. QUESTION (clean, readable)
2. ANSWER (immediate feedback)
3. EXPLANATION (progressive disclosure)
```

### Mockup: Clean Question View

```
┌─────────────────────────────────────────────────────────┐
│ Internal Medicine • Question 23 of 50                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  A 62-year-old man presents with chest pain...          │
│  [Clinical vignette - properly spaced, serif font]      │
│                                                         │
│  Which is the most appropriate next step?               │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  ○ A. Emergent cardiac catheterization                  │
│  ○ B. Stress echocardiography                           │
│  ○ C. Serial troponins                                  │
│  ○ D. CT angiography                                    │
│  ○ E. Discharge with follow-up                          │
├─────────────────────────────────────────────────────────┤
│                    [ Submit Answer ]                     │
└─────────────────────────────────────────────────────────┘
```

### After Answer: Single Explanation Panel

```
┌─────────────────────────────────────────────────────────┐
│ ✓ Correct! (or ✗ Incorrect)                             │
├─────────────────────────────────────────────────────────┤
│ ANSWER                                                  │
│ C is correct. Serial troponins establish diagnosis      │
│ before intervention in NSTEMI with ongoing symptoms.    │
├─────────────────────────────────────────────────────────┤
│ KEY CONCEPT                                             │
│ NSTEMI = conservative strategy first. STEMI = emergent  │
│ cath. Troponin trend guides timing of intervention.     │
├─────────────────────────────────────────────────────────┤
│ ▸ Why A is wrong (click to expand)                      │
│ ▸ Why B is wrong                                        │
│ ▸ Why D is wrong                                        │
│ ▸ Why E is wrong                                        │
├─────────────────────────────────────────────────────────┤
│ 💡 Pearl: "NSTEMI = can wait, STEMI = can't wait"       │
├─────────────────────────────────────────────────────────┤
│            [ Next Question ]  [ Ask AI Tutor ]          │
└─────────────────────────────────────────────────────────┘
```

### CSS Changes

```css
/* Increase readability, reduce density */
.question-vignette {
  font-size: 1rem;           /* Reduced from 1.125rem */
  line-height: 1.75;         /* Increased from 1.8 */
  max-width: 42rem;          /* Reduced from 48rem (3xl) */
  margin: 0 auto;
}

.answer-choice {
  padding: 0.75rem 1rem;     /* Reduced from py-4 px-5 */
  font-size: 0.9375rem;      /* 15px, slightly smaller */
}

.explanation-section {
  max-width: 38rem;          /* Narrower for readability */
  margin: 1.5rem auto;
}
```

---

## Part 4: Remove Real-Time Generation

### What to Remove

1. `backend/app/services/question_agent.py` - Multi-step agent
2. `backend/app/routers/questions.py:generate_question` endpoint
3. `backend/app/services/question_generator.py:generate_question()` - Real-time function

### What to Keep

1. `question_generator.py:get_fallback_question()` - For serving from DB
2. `question_generator.py:get_example_questions()` - For explanation generation
3. `cache_service.py` - For caching served questions

### New API Flow

```
OLD:  GET /questions/generate → AI generates → returns question
NEW:  GET /questions/next → DB query → returns curated question
```

```python
# backend/app/routers/questions.py
@router.get("/next")
async def get_next_question(
    specialty: str | None = None,
    difficulty: str | None = None,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get next question from curated pool"""

    # Get questions user hasn't seen
    seen = db.query(QuestionAttempt.question_id).filter(
        QuestionAttempt.user_id == user_id
    ).subquery()

    query = db.query(Question).filter(
        Question.is_curated == True,
        Question.content_status == 'active',
        ~Question.id.in_(seen)
    )

    if specialty:
        query = query.filter(Question.specialty == specialty)
    if difficulty:
        query = query.filter(Question.difficulty_level == difficulty)

    # Randomize selection
    question = query.order_by(func.random()).first()

    return question
```

---

## Part 5: Keep AI Tutoring

AI is great for tutoring, just not for question generation:

```python
# backend/app/routers/tutor.py
@router.post("/ask")
async def ask_tutor(
    question_id: str,
    user_question: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI tutor for follow-up questions about a specific question"""

    question = db.query(Question).get(question_id)

    response = await openai_service.chat_completion(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": f"""You are a USMLE Step 2 CK tutor.
                The student just answered a question about: {question.vignette[:200]}...
                Help them understand the concept better."""
            },
            {"role": "user", "content": user_question}
        ],
        max_tokens=500  # Keep responses focused
    )

    return {"answer": response.choices[0].message.content}
```

---

## Implementation Timeline (Phases, Not Dates)

### Phase 1: Database & Content
- [ ] Add `is_curated` column to questions table
- [ ] Create import script for curated questions
- [ ] Source 200-500 initial curated questions
- [ ] Run batch explanation generation

### Phase 2: Backend Simplification
- [ ] Create `/questions/next` endpoint
- [ ] Disable `/questions/generate` endpoint
- [ ] Implement simplified explanation schema
- [ ] Keep AI tutor endpoint

### Phase 3: UI Cleanup
- [ ] Create new `QuestionCard` component
- [ ] Create new `SimpleExplanation` component
- [ ] Remove `TabbedExplanation` (or hide behind "More Details")
- [ ] Clean up CSS for better spacing

### Phase 4: Migration
- [ ] Migrate existing good questions to curated status
- [ ] Archive low-quality AI-generated questions
- [ ] Update frontend to use new endpoints
- [ ] Test full flow

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Token cost per session | $0.50-2.00 | $0.05-0.10 |
| Question load time | 30-60s | <500ms |
| Explanation quality (user rating) | Variable | Consistent 4+/5 |
| UI readability | Cluttered | Clean |
| API failures | Frequent | Rare (cached) |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Less content variety | Quality > quantity; add questions over time |
| Users expect AI generation | Market as "expertly curated" - a feature, not limitation |
| Explanation batch job fails | Retry logic, manual review queue |
| Existing users have AI questions | Grandfather in, but serve curated first |

---

## Decision Required

Before implementing, confirm:

1. **Content Source**: Import open-source, license, or create?
2. **Question Count**: Start with 200, 500, or 1000?
3. **Keep AI Tutor**: Yes/No?
4. **UI Style**: Minimal (like above) or keep some tabs?

---

## Files to Modify

### Backend
- `backend/app/models/models.py` - Add curated fields
- `backend/app/routers/questions.py` - New endpoints
- `backend/app/schemas/explanation.py` - Simplify
- `backend/app/services/question_generator.py` - Remove generation

### Frontend
- `frontend/app/study/page.tsx` - Simplify
- `frontend/components/TabbedExplanation.tsx` - Simplify or remove
- `frontend/components/SimpleExplanation.tsx` - NEW
- `frontend/app/globals.css` - Spacing fixes

### Scripts
- `backend/scripts/import_curated_questions.py` - NEW
- `backend/scripts/batch_generate_explanations.py` - NEW
