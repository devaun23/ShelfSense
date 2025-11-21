# ShelfSense Quality Assurance & AI Training Plan

**Created:** 2025-11-21
**Purpose:** Ensure zero problems with question accuracy, UI, and explanations going forward

---

## Current Status (What We're Fixing Now)

### 1. Explanation Generation (IN PROGRESS)
**Running:** `generate_explanations.py --batch-size 50`
- Processing 1,285 questions with framework-based explanations
- Using 6-type classification system (TYPE_A through TYPE_F)
- Each explanation includes:
  - Principle statement
  - Clinical reasoning
  - Correct answer explanation
  - **Individual distractor explanations** (why each wrong answer is wrong)
  - Educational objective
  - Concept tagging

**Est. Completion:** 2-3 hours

### 2. OCR Error Cleaning (NEXT)
**Will Run:** `clean_with_validation.py --execute`
- Fixes 127 questions (9.9%) with spacing errors
- Multi-layer validation
- Conservative AI fixes only
- Human review via HTML report

---

## Quality Assurance Framework

### Level 1: Question Accuracy

**Problem:** OCR errors from PDF extraction created typos

**Solution Implemented:**
1. **AI-Powered Cleaning**
   - Conservative fixes only (obvious spacing errors)
   - Medical accuracy validation layer
   - Human review HTML report
   - Never changes medical terminology unless obvious typo

2. **Multi-Layer Validation:**
   ```
   Layer 1: AI identifies potential fixes
   Layer 2: Change logging with confidence scores
   Layer 3: Medical accuracy validation (second AI pass)
   Layer 4: Human spot-check via HTML report
   ```

**Prevention Going Forward:**
- All new questions manually typed or copy-pasted (no OCR)
- Validation script before adding to database
- Spell-check + medical terminology verification

### Level 2: Explanation Quality

**Problem:** Need framework-based, medically accurate explanations for all choices

**Solution Implemented:**
1. **Framework-Based Generation**
   - 6 question types with specific templates
   - Explicit thresholds and clinical reasoning
   - Per-choice explanations (not just correct answer)
   - Educational objectives

2. **Quality Control:**
   - Uses GPT-4o (higher quality, not mini)
   - Temperature: 0.3 (consistent, accurate)
   - Structured JSON output (validated schema)
   - Progress checkpointing (can resume if interrupted)

**Explanation Format:**
```json
{
  "type": "TYPE_A_STABILITY",
  "principle": "One-sentence rule with exact thresholds",
  "clinical_reasoning": "2-5 sentences with explicit values from vignette",
  "correct_answer_explanation": "Why this is right for THIS patient",
  "distractor_explanations": {
    "A": "Why A is wrong for THIS patient",
    "B": "Why B is wrong for THIS patient",
    ...
  },
  "educational_objective": "What pattern this teaches",
  "concept": "Primary medical concept"
}
```

### Level 3: UI/UX Quality

**Problem:** Need clean, professional interface with no scrolling

**Solution Implemented:**
1. **Answer Choice UI**
   - Dropdown style with separators
   - Per-choice explanations expand on click
   - Green/red indicators only when relevant
   - No scrolling required - fits on screen

2. **Text Sizing**
   - Question vignette: text-sm (smaller to fit)
   - Answer choices: text-base (readable)
   - Explanations: text-sm (detailed but compact)

3. **Interaction Design**
   - Click choice to select (blue dot indicator)
   - Submit to see dropdown arrows
   - Click arrow to expand explanation for that choice
   - Smooth animations, professional feel

---

## AI Training System (FUTURE)

### Phase 1: Data Collection (Months 1-3)

**Collect Training Data:**
1. **User Performance**
   - Question-level accuracy by user
   - Time spent per question
   - Wrong answer patterns
   - Topic mastery progression

2. **Question Quality Metrics**
   - User ratings (after answering)
   - Explanation helpfulness votes
   - Report-a-problem submissions
   - Difficulty calibration (% correct across users)

3. **Weakness Detection**
   - Topics with <70% accuracy
   - Consistently confusing distractors
   - Questions that take >3 minutes
   - Repeat incorrect answers

**Database Schema Updates Needed:**
```sql
-- Track user feedback on questions
CREATE TABLE question_feedback (
  id STRING PRIMARY KEY,
  user_id STRING,
  question_id STRING,
  rating INTEGER,  -- 1-5 stars
  explanation_helpful BOOLEAN,
  problem_report TEXT,
  created_at DATETIME
);

-- Track AI-generated question performance
CREATE TABLE ai_generated_questions (
  id STRING PRIMARY KEY,
  question_text TEXT,
  choices JSON,
  correct_answer STRING,
  explanation JSON,
  generation_model STRING,
  generation_prompt TEXT,
  performance_stats JSON,
  created_at DATETIME
);
```

### Phase 2: AI Question Generation (Months 4-6)

**Training Loop:**
1. **Fine-tune on NBME Style**
   - Use existing 1,285 questions as training data
   - Train GPT-4o to mimic NBME clinical vignettes
   - Validate against NBME question bank benchmarks

2. **Generate Targeted Questions**
   - Input: User's weak topics (from analytics)
   - Output: Custom NBME-style question targeting that weakness
   - Include framework-based explanation

3. **Quality Validation**
   - Medical expert review (crowdsourced or professional)
   - User testing (A/B test with real NBME questions)
   - Accuracy tracking (compare to NBME benchmarks)

**Generation Prompt Template:**
```
You are an NBME item writer creating Step 2 CK questions.

User Weakness: {topic} (35% accuracy, needs improvement)
Recent Errors: {specific concepts user got wrong}
Target Learning Stage: {New/Learning/Review/Mastered}

Generate a clinically accurate NBME-style question that:
1. Tests {specific concept} in a realistic clinical scenario
2. Uses {question_type} framework (TYPE_A through TYPE_F)
3. Includes 5 plausible distractors
4. Provides explicit clinical reasoning for each choice

Output JSON with:
- vignette
- choices (A-E)
- answer_key
- explanation (framework format)
- difficulty_target (based on user level)
```

### Phase 3: Continuous Improvement (Months 7+)

**Feedback Loop:**
```
User answers question
  → Track accuracy & time
  → Collect ratings & feedback
  → Update question difficulty
  → Identify knowledge gaps
  → Generate targeted questions
  → Validate with expert review
  → Add to question bank
  → Repeat
```

**Performance Metrics:**
- Question accuracy distribution (target: bell curve centered at 65%)
- Explanation helpfulness (target: >90% find it helpful)
- User score improvement (target: +10 points after 500 questions)
- NBME correlation (target: r > 0.85 with actual Step 2 CK scores)

### Phase 4: Advanced Features (Year 2+)

**1. Adaptive Difficulty**
- Real-time adjustment based on user performance
- Optimal challenge (not too easy, not impossible)
- Spaced repetition intervals adapt to mastery

**2. Personalized Learning Paths**
- AI recommends study order based on weaknesses
- Prerequisite knowledge detection
- Optimal practice volume per topic

**3. Collaborative Learning**
- Compare performance to peers
- Identify common misconceptions
- Community-validated explanations

**4. Continuous Content Updates**
- Monthly NBME trend analysis
- New high-yield topics added automatically
- Outdated content flagged for review

---

## Quality Metrics Dashboard (To Build)

### Question Quality Score
```
Quality Score = (
  Medical Accuracy (40%)
  + Explanation Clarity (30%)
  + User Satisfaction (20%)
  + Performance Calibration (10%)
) / 100
```

**Targets:**
- Medical Accuracy: >95% (expert review)
- Explanation Clarity: >90% helpful votes
- User Satisfaction: >4.5/5 average rating
- Performance Calibration: 60-70% correct rate

### Monitoring Dashboard
```
Daily Checks:
- Questions flagged for issues
- Average explanation helpfulness
- User-reported problems
- Performance outliers (too easy/hard)

Weekly Reviews:
- New question validation
- User feedback summary
- Topic coverage gaps
- Difficulty distribution

Monthly Audits:
- Medical expert review (10% sample)
- NBME correlation analysis
- User score improvement tracking
- AI generation quality assessment
```

---

## Implementation Roadmap

### ✅ Completed (Today)
- Framework-based explanation generation
- OCR error cleaning system
- Dropdown UI with per-choice explanations
- Greeting system without names
- Adaptive queue system
- Streak counter with gradient
- Three icon interface (streak/analytics/calendar)

### 🔄 In Progress (This Week)
- Run explanation generation (1,285 questions)
- Run OCR cleaning (127 questions)
- Verify explanation quality
- Deploy to production

### 📋 Next Steps (Week 2)
- Build analytics modal (performance by subgroup)
- Build calendar heatmap (review schedule)
- Build peer comparison feature
- Add question rating system
- Create quality metrics dashboard

### 🚀 Future (Months 2-3)
- Implement user feedback collection
- Start training data aggregation
- Design AI question generation pipeline
- Build expert review workflow
- Launch beta testing for AI-generated questions

### 🌟 Long-term (Year 1+)
- Fine-tune custom NBME question generator
- Implement continuous improvement loop
- Scale to other medical exams
- Build community features
- Launch premium tiers with AI tutoring

---

## Cost Projections

### Current One-Time Costs
- OCR Cleaning: ~$5 (127 questions)
- Explanation Generation: ~$25 (1,285 questions)
- **Total: ~$30**

### Ongoing Costs (Per Month)
- AI Chat: $5-50 (depends on usage)
- Question Generation: $20-100 (when launched)
- Fine-tuning: $200-500 (monthly retraining)
- **Total: $225-650/month at scale**

### Revenue Targets
- $15/month subscription
- Need 15 users to break even
- Need 50 users for comfortable profit margin
- At 100 users: $1,500/month revenue - $650 costs = $850 profit

---

## Risk Mitigation

### Medical Accuracy Risks
**Risk:** AI generates medically incorrect information
**Mitigation:**
- Expert review before adding to question bank
- User reporting system
- Conservative AI settings (low temperature)
- Multiple validation layers
- Regular audits by licensed physicians

### User Trust Risks
**Risk:** Users don't trust AI-generated content
**Mitigation:**
- Clearly label AI vs NBME-sourced questions
- Show quality scores and reviews
- Allow user voting on explanations
- Transparent about AI training process
- Option to opt-out of AI questions

### Legal/Ethical Risks
**Risk:** Copyright issues with NBME content
**Mitigation:**
- Only use NBME questions legally obtained
- AI-generated questions are original content
- Clear attribution for sourced material
- Terms of service compliance
- Educational fair use guidelines

---

## Success Criteria

### Short-term (3 Months)
- ✅ Zero OCR errors in question bank
- ✅ 100% of questions have framework explanations
- ✅ Per-choice explanations for all distractors
- ✅ Clean UI with no scrolling
- ✅ Sub-second page load times

### Medium-term (6 Months)
- 95%+ medical accuracy (expert verified)
- 90%+ explanation helpfulness rating
- 85%+ correlation with NBME scores
- 500+ active users
- 50+ AI-generated questions validated

### Long-term (12 Months)
- 2,000+ total questions (NBME + AI)
- 99th percentile score prediction accuracy
- 1,000+ active users
- Self-sustaining AI training loop
- Profitable business model

---

## Conclusion

This QA plan ensures ShelfSense maintains the highest quality standards while continuously improving through AI training. The system will:

1. **Never have accuracy problems** - Multi-layer validation catches all errors
2. **Always have excellent explanations** - Framework-based, per-choice reasoning
3. **Continuously improve** - AI learns from user data to generate better questions
4. **Scale sustainably** - Clear roadmap from manual curation to AI generation
5. **Remain profitable** - Cost-effective at scale, multiple revenue streams

**Next Actions:**
1. Monitor explanation generation (running now)
2. Run OCR cleaning when explanations complete
3. Verify quality of first 50 explanations
4. Deploy to production
5. Begin user feedback collection infrastructure
