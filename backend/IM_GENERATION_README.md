# Internal Medicine Question Generation - Documentation Index

Complete documentation for generating 2,500 NBME-calibrated IM questions.

---

## 📚 Documentation Files

### 1. **IM_GENERATION_SUMMARY.md** ⭐ START HERE
**Purpose**: Executive summary with visual distribution charts
**Best For**: Understanding the overall strategy at a glance
**Contains**:
- Distribution by subspecialty (13 categories)
- Distribution by task type (11 types)
- Distribution by difficulty (4 levels)
- Phased approach (Weeks 1-6)
- Top 50 high-yield topics
- Quality gates overview
- 6-week timeline
- Success metrics

---

### 2. **IM_QUESTION_GENERATION_MANIFEST.md** 📋 FULL SPECIFICATION
**Purpose**: Complete technical specification with all details
**Best For**: Implementation reference, troubleshooting, deep dives
**Contains**:
- Exact question distribution (2,500 questions)
- 3D matrix: subspecialty × task × difficulty
- Generation order priority (Phase 1→2→3)
- High-yield topic list (Top 50 with question counts)
- Quality checkpoints (automated, batch, comprehensive)
- Gap filling strategy
- Batch size recommendations
- Generation configuration (prompts, API settings)
- Success metrics and completion criteria
- Risk mitigation strategies
- Post-generation validation procedures

**Length**: ~8,000 words
**Read Time**: 30 minutes

---

### 3. **GENERATION_QUICKSTART.md** 🚀 DAILY OPERATIONS
**Purpose**: Quick reference for daily use
**Best For**: Running commands, troubleshooting, workflows
**Contains**:
- Quick command reference
- Daily workflow (morning/evening)
- Weekly generation schedule
- Common issues and solutions
- Progress tracking commands
- Quality monitoring procedures
- Expected timeline table
- Success criteria checklist

**Length**: ~3,000 words
**Read Time**: 10 minutes

---

### 4. **IM_3D_MATRIX.csv** 📊 EXACT DISTRIBUTION
**Purpose**: Precise question counts for every combination
**Best For**: Excel analysis, import into tracking tools
**Contains**:
- 13 subspecialties × 11 task types × 4 difficulties
- 143 rows of exact question counts
- Easy to filter, sort, pivot in Excel
- Reference for batch generation targets

**Format**: CSV (open in Excel, Google Sheets, pandas)

---

## 🛠️ Scripts

### 1. **scripts/batch_generate_im.py** - Question Generator
**Purpose**: Generate questions in batches

**Usage**:
```bash
# Phase-based generation (follows manifest)
python scripts/batch_generate_im.py phase --phase 1 --batch 1

# Custom generation (specific subspecialty/task/difficulty)
python scripts/batch_generate_im.py custom \
  --subspecialty Cardiology \
  --count 50 \
  --task pharmacotherapy \
  --difficulty medium
```

**Features**:
- Automated validation (vague terms, testwiseness, distractors)
- Batch size: 50 questions (optimal for checkpoints)
- Rate limiting: 3s between questions (20 Q/min max)
- Task/difficulty distribution matching manifest
- Saves to database with metadata (subspecialty, batch_id, etc.)

---

### 2. **scripts/monitor_generation_progress.py** - Progress Monitor
**Purpose**: Track progress vs manifest targets

**Usage**:
```bash
# Print progress report
python scripts/monitor_generation_progress.py

# Export to JSON
python scripts/monitor_generation_progress.py --export report.json
```

**Output**:
- Overall progress (current / target)
- Subspecialty breakdown with gaps
- Task type breakdown with gaps
- Difficulty breakdown with gaps
- Priority recommendations (HIGH/MEDIUM/LOW)
- Estimated completion time

---

## 📖 How to Use This Documentation

### If you are...

#### **A Medical Educator** (reviewing strategy)
1. Read: `IM_GENERATION_SUMMARY.md` (10 min)
2. Review: Top 50 high-yield topics
3. Check: Quality gates section
4. Validate: Subspecialty distribution matches NBME blueprint

#### **A Developer** (implementing generation)
1. Read: `IM_GENERATION_SUMMARY.md` (overview)
2. Deep dive: `IM_QUESTION_GENERATION_MANIFEST.md` (technical spec)
3. Reference: `GENERATION_QUICKSTART.md` (commands)
4. Run: `python scripts/batch_generate_im.py phase --phase 1 --batch 1`
5. Monitor: `python scripts/monitor_generation_progress.py`

#### **A Project Manager** (tracking progress)
1. Daily: Run `monitor_generation_progress.py`
2. Daily: Check validation pass rate (target: >85%)
3. Weekly: Export progress report to JSON
4. Weekly: Review quality audit results
5. Bi-weekly: Update stakeholders with subspecialty completion %

#### **A QA Engineer** (validating quality)
1. Read: Quality gates section in `IM_QUESTION_GENERATION_MANIFEST.md`
2. Review: Automated validation logic in `scripts/batch_generate_im.py`
3. Sample: 10% of each 250-question batch
4. Check: Validation criteria (NBME patterns, distractor quality, clinical accuracy)
5. Report: Issues with batch_id, error logs

---

## 🎯 Quick Start (5 Minutes)

### Step 1: Understand the Goal
- Generate **2,500 IM questions** to reach 4,000 total
- **6 weeks** @ 60 questions/day
- **NBME-calibrated** quality (elite validation)

### Step 2: Check Current State
```bash
python scripts/monitor_generation_progress.py
```

### Step 3: Start Phase 1
```bash
python scripts/batch_generate_im.py phase --phase 1 --batch 1
```

### Step 4: Review Results
- Check validation pass rate (target: >85%)
- Review generated questions in database
- Export progress: `python scripts/monitor_generation_progress.py --export day1.json`

### Step 5: Continue Daily
- Increment `--batch` number each day
- Monitor progress vs targets
- Adjust if gaps widen

---

## 📊 Distribution Summary

| Dimension | Categories | Distribution |
|-----------|------------|--------------|
| **Subspecialty** | 13 | Cardiology (13%), Pulm/GI/ID (10% each), Renal/Endo/Heme (8% each), Ethics (10%), Biostats (5%), Others |
| **Task Type** | 11 | Diagnosis (18%), Lab/Dx (15%), Mixed Mgmt (14%), Pharmacotherapy (10%), Others |
| **Difficulty** | 4 | Easy (20%), Medium (50%), Hard (25%), Very Hard (5%) |

**Total Combinations**: 13 × 11 × 4 = **572 unique question types**
**Target**: 2,500 questions distributed across these 572 types

---

## ✅ Quality Standards

### Validation Requirements (Every Question)
- ✓ No vague clinical terms (explicit vitals/labs)
- ✓ No testwiseness cues (balanced lengths, no absolutes)
- ✓ 5 distinct, homogeneous distractors
- ✓ Complete explanations (all 5 choices)
- ✓ NBME pattern matching (cover-the-options rule)

### Acceptance Thresholds
- **Automated Validation**: ≥85% pass rate
- **Expert Review**: ≥90% shelf-quality
- **Student Accuracy**: 60-70% on medium questions

---

## 🗓️ Timeline at a Glance

| Week | Phase | Questions | Cumulative | Focus |
|------|-------|-----------|------------|-------|
| 1 | 1 | 420 | 420 | Ethics, Biostats |
| 2 | 1 | 380 | 800 | Endo, Heme/Onc, Renal, Neuro |
| 3 | 2 | 420 | 1,220 | Cardiology |
| 4 | 2 | 480 | 1,700 | Pulm, GI, ID |
| 5 | 3 | 420 | 2,120 | Rheum, Immuno, complete ID |
| 6 | 3 | 380 | 2,500 | Gap filling, multisystem, QA |

---

## 📞 Support & Contact

### Issues or Questions?
1. Check `GENERATION_QUICKSTART.md` for common issues
2. Review `IM_QUESTION_GENERATION_MANIFEST.md` for detailed specs
3. Create GitHub issue with:
   - Batch ID
   - Error logs
   - Expected vs actual behavior

### Documentation Updates
- **Version**: 1.0
- **Last Updated**: 2025-11-29
- **Next Review**: After Phase 1 completion (Week 2)
- **Maintained By**: ShelfSense Medical Education Team

---

## 📁 File Structure

```
backend/
├── IM_GENERATION_README.md          ← YOU ARE HERE (index)
├── IM_GENERATION_SUMMARY.md         ← Executive summary (START HERE)
├── IM_QUESTION_GENERATION_MANIFEST.md  ← Full technical spec
├── GENERATION_QUICKSTART.md         ← Daily operations guide
├── IM_3D_MATRIX.csv                 ← Exact distribution table
└── curriculum_gaps.json             ← Current gap analysis

scripts/
├── batch_generate_im.py             ← Question generator
├── monitor_generation_progress.py   ← Progress tracker
└── analyze_curriculum_gaps.py       ← Gap analyzer (existing)
```

---

## 🚀 Next Steps

1. **Read**: `IM_GENERATION_SUMMARY.md` for overview
2. **Review**: Top 50 high-yield topics
3. **Run**: `python scripts/monitor_generation_progress.py` to check baseline
4. **Generate**: `python scripts/batch_generate_im.py phase --phase 1 --batch 1`
5. **Track**: Daily progress monitoring

**Goal**: 2,500 elite-quality IM questions in 6 weeks!

---

**Happy Generating! 🎓**
