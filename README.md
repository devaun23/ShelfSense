# ShelfSense

Adaptive shelf exam preparation platform with cognitive pattern recognition.

## Project Overview

ShelfSense is an intelligent medical education platform that helps medical students prepare for NBME shelf exams through adaptive learning and reasoning pattern recognition.

## Features

- Adaptive question delivery based on reasoning pattern mastery
- 30+ cognitive reasoning patterns for medical decision-making
- Question bank extraction from NBME practice exams
- Spaced repetition algorithm
- Progress tracking and analytics

## Repository Contents

- `nbme_extractor.py` - Python script to extract questions from NBME PDFs
- `data/compressed_pdfs/` - Compressed NBME practice exam PDFs
- `data/extracted_questions/` - JSON files with extracted questions

## Usage

1. Install dependencies:
```bash
pip install pdfplumber
```

2. Run the extraction script:
```bash
python3 nbme_extractor.py
```

## Next Steps

- Complete question extraction from all PDFs
- Add correct answers from answer keys
- Integrate with adaptive learning algorithm
- Build frontend interface
