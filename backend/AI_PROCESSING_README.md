# ShelfSense AI Processing Guide

## Overview

This document explains how to run the AI-powered enhancement scripts when OpenAI API quota is available.

## Prerequisites

1. **OpenAI API Key** with available quota
2. **Python environment** with all dependencies installed
3. **Database backup** (always backup before running!)

## Scripts

### 1. OCR Error Cleaning (`clean_with_validation.py`)

Fixes OCR spacing errors in question text using AI with multi-layer quality control.

**What it does:**
- Identifies 127 questions with OCR errors (9.9% of database)
- Uses GPT-4o-mini to conservatively fix spacing issues
- Validates medical accuracy with second AI pass
- Generates HTML report for human review
- Only applies changes after approval

**Usage:**
```bash
cd backend
source venv/bin/activate

# Step 1: Preview changes (generates HTML report)
python clean_with_validation.py --dry-run

# Step 2: Review the HTML report in your browser
# (Check file path shown in output)

# Step 3: If changes look good, apply them
python clean_with_validation.py --execute
```

**Cost:** ~$5 for 127 questions
**Time:** ~5-10 minutes

**What gets fixed:**
- "year-o ld" → "year-old"
- "clopidog rel" → "clopidogrel"
- "construct ion" → "construction"
- "mg/d L" → "mg/dL"
- And other OCR spacing patterns

---

### 2. Framework Explanation Generation (`generate_explanations.py`)

Generates structured, high-quality explanations for all questions using the 6-type ShelfSense framework.

**What it does:**
- Processes all 1,285 questions
- Classifies each into one of 6 question types (A-F)
- Generates structured JSON explanations with:
  - Principle statement (exact decision rule)
  - Clinical reasoning (with explicit thresholds)
  - Distractor explanations (why each wrong answer fails)
  - Educational objective
- Saves progress every 50 questions (can resume if interrupted)

**Usage:**
```bash
cd backend
source venv/bin/activate

# Run from start
python generate_explanations.py --batch-size 50

# Or resume from last checkpoint (if interrupted)
python generate_explanations.py --continue
```

**Cost:** ~$20-25 for 1,285 questions
**Time:** ~2-3 hours

**Explanation Types:**
- **TYPE_A**: Stable/Unstable Bifurcation (vital sign thresholds)
- **TYPE_B**: Time-Sensitive Decisions (time windows)
- **TYPE_C**: Diagnostic Sequence (test ordering)
- **TYPE_D**: Risk Stratification (scoring systems)
- **TYPE_E**: Treatment Hierarchy (first-line vs second-line)
- **TYPE_F**: Differential Narrowing (distinguishing features)

---

## Recommended Workflow

### When API Quota Available:

1. **Backup database first!**
   ```bash
   cp shelfsense.db shelfsense_backup_$(date +%Y%m%d).db
   ```

2. **Run OCR cleaning** (quick, $5, 10 min)
   ```bash
   python clean_with_validation.py --dry-run
   # Review HTML report
   python clean_with_validation.py --execute
   ```

3. **Run explanation generation** (long, $25, 2-3 hrs)
   ```bash
   # Start in background so you can close terminal
   nohup python generate_explanations.py --batch-size 50 > explanation.log 2>&1 &

   # Monitor progress
   tail -f explanation.log
   ```

4. **Commit and deploy**
   ```bash
   git add backend/shelfsense.db
   git commit -m "AI-enhanced questions: cleaned OCR errors and added framework explanations"
   git push
   ```

---

## Troubleshooting

### Error: "insufficient_quota"
- **Cause:** OpenAI API quota exceeded
- **Solution:** Add credits at https://platform.openai.com/account/billing or wait for quota reset

### Error: "JSONDecodeError"
- **Cause:** Some questions have invalid explanation format
- **Solution:** Already fixed in database (NULL'd out invalid explanations)

### Script interrupted mid-run
- **For OCR cleaning:** Just re-run, dry-run is safe
- **For explanations:** Use `--continue` flag to resume from checkpoint

### Need to revert changes
- **Restore from backup:**
  ```bash
  cp shelfsense_backup_YYYYMMDD.db shelfsense.db
  ```

---

## Current Status

**As of 2025-11-20:**
- ❌ OCR Cleaning: NOT RUN (quota exceeded)
  - 127 questions still have OCR errors
  - Ready to run when quota available

- ❌ Explanations: NOT RUN (quota exceeded)
  - 0 questions have framework explanations
  - All explanations set to NULL, ready for generation

**Backend Features (Deployed):**
- ✅ Spaced repetition system (works without explanations)
- ✅ Review scheduling (SM-2 algorithm)
- ✅ AI chat endpoint (works with any explanation format)
- ✅ All APIs deployed to Railway

---

## Cost Summary

| Task | Questions | Cost | Time | Priority |
|------|-----------|------|------|----------|
| OCR Cleaning | 127 | ~$5 | 10 min | HIGH (fixes typos) |
| Explanations | 1,285 | ~$25 | 2-3 hrs | MEDIUM (quality of life) |
| **Total** | | **~$30** | **3 hrs** | |

---

## Questions?

Check the main ShelfSense README or the script source code for more details.
Both scripts have extensive documentation and error handling.
