# ShelfSense Project Roadmap

## Vision
An adaptive learning platform for USMLE Step 2 CK and shelf exams that learns from student mistakes and continuously improves explanations based on real performance data.

---

## Phase 1: Question Bank Development ⏳ IN PROGRESS

### 1.1 Shelf Exam Questions (Target: 1,300 questions)
**Status:** 760/1,300 extracted

**Sources:**
- Emergency Medicine Forms 1-8 (8 exams × 50Q = 400 questions)
- Internal Medicine Forms 3-8 (6 exams × 50Q = 300 questions)
- Neurology Forms 3-8 (6 exams × 50Q = 300 questions)
- Pediatrics Forms 3-8 (6 exams × 50Q = 300 questions)
- Surgery Forms 3-8 (6 exams × 50Q = 300 questions)

**Extraction Tools:**
- ✅ `nbme_complete_extractor.py` - Text-based PDFs
- ✅ `nbme_ocr_extractor.py` - Image-based PDFs (OCR)
- ✅ `nbme_ultra_extractor.py` - Multi-strategy for stubborn PDFs
- ✅ `fix_explanations.py` - Clean corrupted data

**Current Progress:**
- Emergency Medicine: 99 questions
- Internal Medicine: 167 questions
- Neurology: 195 questions
- Pediatrics: 150 questions
- Surgery: 149 questions

**Remaining:**
- 8 image-based PDFs (OCR in progress)
- Fix/validate existing explanations
- Extract missing questions from text PDFs

### 1.2 NBME Step 2 CK Practice Exams
**Status:** 🔄 Extraction in progress

**Sources:**
- NBME 4, 6, 7, 8, 9, 10, 11, 12, 13, 14 (10 exams)
- Each exam: ~200 questions
- Expected total: ~2,000 questions

**Extraction Tools:**
- ✅ `nbme_comprehensive_extractor.py` - Handles 1-200+ questions per exam

**Current Progress:**
- Extractor running in background
- Processing both text-based "(sp)" versions and image-based PDFs

###  1.3 UWorld Step 2 CK
**Status:** 📥 Awaiting upload

**Expected:**
- ~3,000+ questions
- Full explanations with diagrams
- Clinical vignettes with all answer choices

**Required:**
- Upload PDF versions of UWorld questions
- Create UWorld-specific extractor (different format from NBME)
- Preserve images/diagrams

### 1.4 AMBOSS Step 2 CK
**Status:** 📥 Awaiting upload

**Expected:**
- ~2,500+ questions
- Explanations with learning cards
- Clinical vignettes

**Required:**
- Upload PDF versions of AMBOSS questions
- Create AMBOSS-specific extractor
- Link to learning cards/concept anchors

### 1.5 First Aid for Step 2 CK
**Status:** 📥 Awaiting upload

**Purpose:**
- Knowledge base for explanation enhancement
- Concept mapping for questions
- High-yield facts integration

**Required:**
- Upload PDF of First Aid Step 2 CK
- Extract high-yield concepts
- Create knowledge graph
- Link concepts to question topics

---

## Phase 2: Explanation System ✅ DESIGNED

### 2.1 Explanation Framework
**Status:** ✅ Complete

**Components:**
- `EXPLANATION_FRAMEWORK.md` - 6 adaptive question types
  - TYPE A: Stable/Unstable Bifurcation
  - TYPE B: Time-Sensitive Decisions
  - TYPE C: Diagnostic Sequence
  - TYPE D: Risk Stratification
  - TYPE E: Treatment Hierarchy
  - TYPE F: Differential Narrowing

**Quality Standards:**
- Explicit thresholds (not "hypotensive", but "BP <90")
- Complete decision trees
- Under 200 words
- Pattern-based teaching

### 2.2 Behavioral Tracking
**Status:** ✅ Designed, ⏳ Implementation pending

**Document:** `BEHAVIORAL_TRACKING.md`

**Metrics:**
- Mouse hover time
- Scroll behavior
- Re-reading patterns
- Next question timing
- 24-48hr retention testing

**Privacy:**
- No PII collected
- Only interaction patterns
- Anonymized data

### 2.3 Adaptive Improvement
**Status:** ✅ Designed, ⏳ Implementation pending

**Document:** `ADAPTIVE_IMPROVEMENT.md`

**Features:**
- Retention rate tracking per explanation
- A/B testing framework
- Automatic promotion of better versions
- Error pattern analysis
- Continuous optimization pipeline

**Database Schema:**
- `explanation_performance` table
- `explanation_versions` table
- Weekly analytics and promotion

---

## Phase 3: Tips, Tricks & Common Mistakes 📥 AWAITING CONTENT

### 3.1 Test-Taking Strategies
**Status:** 📥 Awaiting upload

**Content Needed:**
- Shelf exam-specific strategies
- Step 2 CK test-taking tips
- Time management approaches
- Common traps to avoid

### 3.2 Common Mistake Patterns
**Status:** 📥 Awaiting upload

**Integration Points:**
- Map to reasoning patterns in questions
- Link mistakes to explanation types
- Create targeted interventions
- Build prediction models

**Examples:**
- Students rush on stable/unstable questions
- Timeline confusion in acute vs chronic
- Missed contraindications
- Anchoring on first differential

### 3.3 Reasoning Pattern Library
**Status:** ⏳ To be developed

**Current Patterns (30+):**
- urgency_assessment
- treatment_prioritization
- severity_misjudgment
- timeline_errors
- test_sequence_errors
- contraindication_missed
- anchoring_bias
- missed_qualifiers

**Enhancement Needed:**
- Define each pattern with examples
- Link to explanation types
- Create pattern-specific practice sets
- Track student performance by pattern

---

## Phase 4: Platform Development 📋 PLANNED

### 4.1 Backend API
**Status:** 📋 Design phase

**Tech Stack (Proposed):**
- Python/FastAPI or Node.js/Express
- PostgreSQL database
- Redis for caching
- JWT authentication

**Endpoints:**
- Question delivery system
- Explanation serving with A/B testing
- Metrics collection
- User progress tracking
- Analytics dashboard

### 4.2 Frontend Application
**Status:** 📋 Design phase

**Tech Stack (Proposed):**
- React/Next.js
- TypeScript
- Tailwind CSS
- Chart.js for analytics

**Features:**
- Question interface (NBME-style)
- Explanation display with progressive disclosure
- Performance dashboard
- Progress tracking
- Study mode vs exam mode

### 4.3 Adaptive Learning Engine
**Status:** 📋 Algorithm design phase

**Components:**
- Spaced repetition algorithm
- Weakness identification
- Question selection based on performance
- Pattern-based recommendations
- Retention prediction

---

## Phase 5: Content Enhancement 🔄 CONTINUOUS

### 5.1 Explanation Quality Improvement
**Process:**
1. Launch with initial explanations
2. Collect behavioral data (Weeks 1-2)
3. Identify failing explanations (Weeks 3-4)
4. A/B test improvements (Weeks 5-6)
5. Promote winners (Week 7+)
6. Repeat continuously

### 5.2 Question Curation
**Tasks:**
- Review extracted questions for accuracy
- Fix corrupted explanations
- Enhance vignettes with structured data
- Classify by reasoning pattern
- Assign difficulty and tier
- Tag with topics and concepts

### 5.3 Knowledge Graph Development
**Purpose:**
- Link questions to First Aid concepts
- Connect related questions
- Build concept dependencies
- Enable targeted study paths

---

## Current Priorities (Next Steps)

1. ✅ **Complete shelf exam extraction** (760 → 1,300 questions)
   - Finish OCR on 8 image PDFs
   - Fix corrupted explanations
   - Validate all extractions

2. 🔄 **Complete NBME Step 2 CK extraction** (~2,000 questions)
   - Running in background
   - Validate outputs
   - Merge into question bank

3. 📥 **Prepare for next uploads:**
   - First Aid for Step 2 CK PDF
   - UWorld Step 2 CK questions
   - AMBOSS Step 2 CK questions
   - Tips & tricks document

4. 📋 **Begin platform development:**
   - Design database schema
   - Create API architecture
   - Prototype frontend interface
   - Implement tracking infrastructure

---

## Success Metrics

### Short-term (3 months):
- ✅ 1,300+ shelf exam questions extracted
- ✅ 2,000+ NBME Step 2 CK questions extracted
- ✅ Explanation framework implemented
- ⏳ 3,000+ UWorld questions integrated
- ⏳ 2,500+ AMBOSS questions integrated

### Medium-term (6 months):
- Platform MVP launched
- 100+ beta users
- Behavioral tracking active
- First A/B test results
- 75%+ retention rate on explanations

### Long-term (12 months):
- 1,000+ active users
- 85%+ explanation retention rate
- Fully automated explanation improvement
- Proven score improvement data
- Expansion to Step 1 and Step 3

---

## Repository Structure (Current)

```
ShelfSense/
├── README.md
├── PROJECT_ROADMAP.md              ← This file
├── EXPLANATION_FRAMEWORK.md
├── BEHAVIORAL_TRACKING.md
├── ADAPTIVE_IMPROVEMENT.md
├── data/
│   └── extracted_questions/
│       ├── all_nbme_questions.json (760 shelf questions)
│       ├── emergency_medicine_questions.json
│       ├── internal_medicine_questions.json
│       ├── neurology_questions.json
│       ├── pediatrics_questions.json
│       ├── surgery_questions.json
│       ├── extraction_summary.json
│       └── [NBME Step 2 CK files - in progress]
├── nbme_complete_extractor.py
├── nbme_ocr_extractor.py
├── nbme_ultra_extractor.py
├── nbme_comprehensive_extractor.py
├── fix_explanations.py
└── run_all_ocr.py
```

---

## Notes

- All extraction tools continuously improved until 100% capture rate
- PDF formats vary significantly - flexible patterns required
- OCR quality varies - may need manual review
- Explanation quality critical - continuous improvement essential
- Privacy-first design - no PII collection
- Evidence-based approach - all improvements data-driven
