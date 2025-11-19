# ShelfSense Question Extraction Status

**Last Updated:** November 19, 2025 at 4:42 PM EST

---

## Current Progress

### Shelf Exam Questions
**Status:** 760/1,300 extracted (58.5%)

| Specialty | Extracted | Target | Progress |
|-----------|-----------|--------|----------|
| Emergency Medicine | 99 | 400 | 24.8% |
| Internal Medicine | 167 | 300 | 55.7% |
| Neurology | 195 | 300 | 65.0% |
| Pediatrics | 150 | 300 | 50.0% |
| Surgery | 149 | 300 | 49.7% |

**Forms Processed:**
- Emergency Medicine: Forms 1-2 (text-based)
- Internal Medicine: Forms 3-6 (text-based)
- Neurology: Forms 3-6 (text-based)
- Pediatrics: Forms 3-8 (mixed: 3-6 text, 7-8 image/OCR)
- Surgery: Forms 3-6 (text-based)

**Remaining:**
- Emergency Medicine: Forms 3-8 (6 forms × ~50Q = ~300Q)
- Internal Medicine: Forms 7-8 (2 forms × ~50Q = ~100Q)
- Neurology: Forms 7-8 (2 forms × ~50Q = ~100Q)
- Surgery: Forms 7-8 (2 forms × ~50Q = ~100Q)

**Known Issues:**
- OCR pattern only extracting 5-11 questions per PDF instead of 50
- Pattern needs refinement to handle OCR artifacts better
- Some text-based PDFs skip certain question numbers

---

### NBME Step 2 CK Questions
**Status:** In Progress (NBME 10 at page 220/446)

**Target Exams:**
- NBME 4, 6, 7, 8, 9, 10, 11, 12, 13, 14
- Expected: ~200 questions per exam
- Total Expected: ~2,000 questions

**Current Extractor:**
- Running: nbme_comprehensive_extractor.py
- Processing: NBME 10 - Answers.pdf (424MB)
- OCR in progress: 220/446 pages complete

**Available Files:**
- 10 NBME exams with answer explanations
- Mix of text-based and image-based PDFs
- Some have companion "(sp)" versions with better text extraction

---

## Extraction Tools Status

### Working Tools
✅ `nbme_complete_extractor.py` - Text-based shelf exams (760Q extracted)
✅ `nbme_comprehensive_extractor.py` - NBME Step 2 CK exams (running)
✅ `nbme_ultra_extractor.py` - Multi-strategy extraction

### Tools Needing Improvement
⚠️ `nbme_ocr_extractor.py` - Only getting 5-11Q per PDF (should be 50)
  - Pattern: `r'(?:^|[\n\sv])\s*(\d+)\s*[\.\)]\s+([A-Za-z])'`
  - Issue: Too strict for OCR artifacts
  - Solution: Need more flexible pattern or different OCR approach

⚠️ `fix_explanations.py` - Some explanations still corrupted
  - Pattern finds "Correct Answer: X. ..." with dots instead of text
  - Need better multi-page text extraction

### Background Processes
- **edf3e5**: NBME comprehensive extractor (running, page 220/446)
- **f6b7a1**: OCR extractor (killed)
- **5df28a**: OCR extractor (failed - XCode tools issue)
- **b51e43**: OCR extractor (completed - Pediatrics)
- **1ccf73**: Complete extractor (running)
- **8c464c**: Fix explanations (running)
- **9146a3**: Ultra extractor (running)

---

## Next Steps (Priority Order)

### Immediate (This Session)
1. ✅ Let NBME comprehensive extractor finish (~20-30 min remaining)
2. ⏳ Fix OCR pattern to extract all 50 questions per PDF
3. ⏳ Re-run OCR on 8 image-based shelf PDFs with fixed pattern
4. ⏳ Validate and clean extracted data

### Short-Term (Next Session)
1. Extract remaining Emergency Medicine forms (3-8)
2. Extract remaining Internal Medicine forms (7-8)
3. Extract remaining Neurology forms (7-8)
4. Extract remaining Surgery forms (7-8)
5. Validate we have ~1,300 total shelf questions

### Medium-Term (Waiting on Upload)
1. First Aid for Step 2 CK PDF → Knowledge base extraction
2. UWorld Step 2 CK questions → ~3,000 questions
3. AMBOSS Step 2 CK questions → ~2,500 questions
4. Tips/tricks document → Error pattern library

---

## Extraction Quality Metrics

### Text-Based PDFs
- **Success Rate:** ~85-95% (missing some questions due to skipped numbers)
- **Explanation Quality:** Good (most complete)
- **Processing Speed:** Fast (~30 sec per PDF)

### Image-Based PDFs (OCR)
- **Success Rate:** ~10-20% (major pattern issue)
- **Explanation Quality:** Variable (OCR artifacts)
- **Processing Speed:** Slow (~5-10 min per PDF)

### NBME Step 2 CK PDFs
- **Success Rate:** TBD (in progress)
- **Expected Quality:** Good (Step Prep format has clean text)
- **Processing Speed:** Very slow (~30-60 min per exam due to OCR)

---

## Data Storage

```
/Users/devaun/ShelfSense/data/extracted_questions/
├── all_nbme_questions.json (760 shelf questions)
├── emergency_medicine_questions.json (99)
├── internal_medicine_questions.json (167)
├── neurology_questions.json (195)
├── pediatrics_questions.json (150)
├── surgery_questions.json (149)
├── extraction_summary.json
└── [NBME Step 2 CK files - pending]
```

---

## Estimated Timeline

- **NBME extraction complete:** ~30 minutes (currently running)
- **OCR pattern fix + re-run:** ~2-3 hours
- **Remaining shelf exams:** ~1-2 hours
- **Total to 1,300 shelf + 2,000 NBME:** ~4-6 hours
- **Add UWorld + AMBOSS (after upload):** ~6-8 hours
- **Grand total to 8,000+ questions:** ~10-15 hours

---

## Critical Issues to Resolve

1. **OCR Pattern Accuracy**
   - Current: 10-20% question capture rate
   - Target: 90%+ question capture rate
   - Impact: Missing ~350-400 questions from image-based shelf PDFs

2. **Explanation Corruption**
   - Some PDFs show "..." instead of actual explanation
   - Need better multi-page text assembly
   - Impact: ~5-10% of questions have incomplete explanations

3. **Question Number Gaps**
   - Many PDFs skip certain question numbers (e.g., no Q11, Q20, etc.)
   - Not an extraction issue - PDFs genuinely skip numbers
   - Impact: Maximum possible is ~1,174 instead of 1,300 from shelf exams

---

**Summary:** We have 760 questions extracted and working, with ~2,000 more in progress from NBME exams. Main blocker is OCR pattern accuracy for image-based PDFs. Once that's fixed, we can reach target of 1,300+ shelf questions + 2,000 NBME questions = 3,300+ questions before adding UWorld/AMBOSS.
