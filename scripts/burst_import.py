#!/usr/bin/env python3
"""
ONE-TIME BURST IMPORT SCRIPT

Run this ONCE with ~$30 of Claude API credits to:
1. Extract all questions from NBME PDF files
2. Generate 285+ caliber explanations for each
3. Save to the ShelfSense database

After this runs, you never need Claude API again for content.
All ongoing operations use Ollama (free) or rule-based validation.

Usage:
    # Set your API key
    export ANTHROPIC_API_KEY="your-key-here"

    # Run the import
    python scripts/burst_import.py ./pdfs/

    # Or specify output directory
    python scripts/burst_import.py ./pdfs/ --output ./extracted/

    # Dry run (no database writes)
    python scripts/burst_import.py ./pdfs/ --dry-run

Prerequisites:
    1. Get API key from https://console.anthropic.com
    2. Add at least $30 credits
    3. pip install anthropic pymupdf
"""

import os
import sys
import json
import asyncio
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERROR: PyMuPDF not installed. Run: pip install pymupdf")
    sys.exit(1)

try:
    from anthropic import Anthropic
except ImportError:
    print("ERROR: Anthropic not installed. Run: pip install anthropic")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# PROMPTS
# ============================================================================

EXTRACTION_PROMPT = """You are extracting USMLE Step 2 CK questions from a medical education PDF page.

For each complete question found on this page, extract:
1. The full clinical vignette (patient presentation)
2. The question stem (what is being asked)
3. All 5 answer choices (A through E)
4. The correct answer letter (if shown)
5. Any explanation provided

Return a JSON array. For each question:
{{
    "vignette": "Full clinical scenario text...",
    "question_stem": "What is the most appropriate next step?",
    "choices": {{
        "A": "Choice A text",
        "B": "Choice B text",
        "C": "Choice C text",
        "D": "Choice D text",
        "E": "Choice E text"
    }},
    "answer_key": "B",
    "original_explanation": "Any explanation from the PDF (or null)",
    "source_page": {page_num},
    "source_type": "NBME"
}}

If no complete questions are found on this page, return an empty array: []

Important:
- Only extract COMPLETE questions (vignette + all 5 choices)
- Preserve exact wording from the PDF
- If answer key is not shown, set to null
- Combine multi-page questions if the vignette starts on a previous page"""

ELITE_EXPLANATION_PROMPT = """You are a 290-scorer creating a 285+ caliber USMLE Step 2 CK explanation.

QUESTION:
{vignette}

{question_stem}

CHOICES:
A. {choice_a}
B. {choice_b}
C. {choice_c}
D. {choice_d}
E. {choice_e}

CORRECT ANSWER: {answer_key}

Create a comprehensive explanation that teaches 285+ scorer thinking patterns.

Return ONLY valid JSON:
{{
    "quick_answer": "One sentence (<30 words) that a 285+ scorer thinks immediately. Reference the key first-sentence finding.",

    "principle": "The decision rule using arrow notation: 'finding1 + finding2 -> diagnosis -> management'. Include specific thresholds.",

    "clinical_reasoning": "3-4 sentences explaining the mechanism chain. Use -> for causation. Include (normal X-Y) after values.",

    "correct_answer_explanation": "Why {answer_key} is correct for THIS specific patient. Reference specific vignette findings.",

    "distractor_explanations": {{
        "A": "Why A is tempting (what error leads here) but wrong for this patient...",
        "B": "Why B is tempting but wrong...",
        "C": "Why C is tempting but wrong...",
        "D": "Why D is tempting but wrong...",
        "E": "Why E is tempting but wrong..."
    }},

    "deep_dive": {{
        "pathophysiology": "Brief mechanism explanation",
        "clinical_pearls": ["High-yield fact 1", "High-yield fact 2"],
        "common_mistakes": ["Error pattern 1", "Error pattern 2"]
    }},

    "question_type": "One of: TYPE_A_STABILITY, TYPE_B_TIME, TYPE_C_DIAGNOSTIC, TYPE_D_RISK, TYPE_E_TREATMENT, TYPE_F_DIFFERENTIAL"
}}

CRITICAL REQUIREMENTS:
1. quick_answer MUST reference findings from the FIRST sentence of the vignette
2. Use -> for ALL causal chains (risk -> pathology -> finding -> treatment)
3. Every numeric value needs (normal X-Y) context
4. Each distractor MUST explain why it's TEMPTING, not just wrong
5. Be specific to THIS patient, not generic"""


# ============================================================================
# PDF EXTRACTION
# ============================================================================

def extract_text_from_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extract text from each page of a PDF.

    Returns list of {{page_num, text, has_images}} dicts.
    """
    pages = []
    doc = fitz.open(pdf_path)

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        images = page.get_images()

        pages.append({
            "page_num": page_num,
            "text": text,
            "has_images": len(images) > 0,
            "image_count": len(images)
        })

    doc.close()
    logger.info(f"Extracted {len(pages)} pages from {pdf_path.name}")
    return pages


def extract_page_as_image(pdf_path: Path, page_num: int) -> bytes:
    """
    Render a PDF page as a PNG image for vision extraction.
    """
    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]  # 0-indexed

    # Render at 2x resolution for better OCR
    mat = fitz.Matrix(2, 2)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")

    doc.close()
    return img_bytes


# ============================================================================
# CLAUDE API CALLS
# ============================================================================

def extract_questions_from_text(
    client: Anthropic,
    page_text: str,
    page_num: int,
    source_file: str
) -> List[Dict[str, Any]]:
    """
    Use Claude to extract structured questions from page text.
    """
    prompt = EXTRACTION_PROMPT.format(page_num=page_num)

    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",  # Cheapest for extraction
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": f"{prompt}\n\nPDF PAGE TEXT:\n{page_text}"
            }]
        )

        content = response.content[0].text

        # Extract JSON from response
        json_start = content.find("[")
        json_end = content.rfind("]") + 1

        if json_start >= 0 and json_end > json_start:
            questions = json.loads(content[json_start:json_end])
            for q in questions:
                q["source_file"] = source_file
            return questions

        return []

    except Exception as e:
        logger.error(f"Extraction failed for page {page_num}: {e}")
        return []


def extract_questions_from_image(
    client: Anthropic,
    image_bytes: bytes,
    page_num: int,
    source_file: str
) -> List[Dict[str, Any]]:
    """
    Use Claude Vision to extract questions from a PDF page image.
    Use this for complex layouts or scanned PDFs.
    """
    import base64
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    prompt = EXTRACTION_PROMPT.format(page_num=page_num)

    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",  # Vision-capable
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_b64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        )

        content = response.content[0].text

        json_start = content.find("[")
        json_end = content.rfind("]") + 1

        if json_start >= 0 and json_end > json_start:
            questions = json.loads(content[json_start:json_end])
            for q in questions:
                q["source_file"] = source_file
                q["extracted_via"] = "vision"
            return questions

        return []

    except Exception as e:
        logger.error(f"Vision extraction failed for page {page_num}: {e}")
        return []


def generate_elite_explanation(
    client: Anthropic,
    question: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a 285+ caliber explanation for a question.
    Uses Claude Sonnet for best quality.
    """
    choices = question.get("choices", {})

    prompt = ELITE_EXPLANATION_PROMPT.format(
        vignette=question.get("vignette", ""),
        question_stem=question.get("question_stem", ""),
        choice_a=choices.get("A", ""),
        choice_b=choices.get("B", ""),
        choice_c=choices.get("C", ""),
        choice_d=choices.get("D", ""),
        choice_e=choices.get("E", ""),
        answer_key=question.get("answer_key", "?")
    )

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # Best quality for explanations
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        content = response.content[0].text

        # Extract JSON
        json_start = content.find("{")
        json_end = content.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            explanation = json.loads(content[json_start:json_end])
            return explanation

        logger.warning("Could not parse explanation JSON")
        return {"raw_response": content, "parse_error": True}

    except Exception as e:
        logger.error(f"Explanation generation failed: {e}")
        return {"error": str(e)}


# ============================================================================
# MAIN IMPORT LOGIC
# ============================================================================

def process_pdf(
    client: Anthropic,
    pdf_path: Path,
    use_vision: bool = False
) -> List[Dict[str, Any]]:
    """
    Process a single PDF and extract all questions.
    """
    logger.info(f"Processing: {pdf_path.name}")

    pages = extract_text_from_pdf(pdf_path)
    all_questions = []

    for page in pages:
        page_num = page["page_num"]
        text = page["text"]

        # Skip pages with very little text (likely just images or blank)
        if len(text.strip()) < 100:
            if page["has_images"] and use_vision:
                # Try vision extraction for image-heavy pages
                img_bytes = extract_page_as_image(pdf_path, page_num)
                questions = extract_questions_from_image(
                    client, img_bytes, page_num, pdf_path.name
                )
            else:
                continue
        else:
            # Use text extraction
            questions = extract_questions_from_text(
                client, text, page_num, pdf_path.name
            )

        if questions:
            logger.info(f"  Page {page_num}: Found {len(questions)} question(s)")
            all_questions.extend(questions)

    logger.info(f"Total questions from {pdf_path.name}: {len(all_questions)}")
    return all_questions


def enhance_questions(
    client: Anthropic,
    questions: List[Dict[str, Any]],
    output_path: Path,
    progress_callback=None,
    checkpoint_interval: int = 10,
    delay_seconds: float = 1.0
) -> List[Dict[str, Any]]:
    """
    Generate elite explanations for all questions with checkpoint recovery.

    Features:
    - Saves checkpoint every N questions to prevent data loss
    - Rate limiting to avoid API throttling
    - Resume from checkpoint if interrupted
    """
    import time

    enhanced = []
    checkpoint_path = output_path.with_suffix('.checkpoint.json')

    # Check for existing checkpoint to resume from
    start_index = 0
    if checkpoint_path.exists():
        try:
            with open(checkpoint_path, 'r') as f:
                checkpoint_data = json.load(f)
                enhanced = checkpoint_data.get("enhanced", [])
                start_index = checkpoint_data.get("last_index", 0) + 1
                logger.info(f"Resuming from checkpoint at question {start_index}")
                print(f"\nResuming from checkpoint: {start_index}/{len(questions)} questions already done")
        except Exception as e:
            logger.warning(f"Could not load checkpoint: {e}")

    for i in range(start_index, len(questions)):
        q = questions[i]

        if progress_callback:
            progress_callback(i + 1, len(questions))

        logger.info(f"Enhancing question {i+1}/{len(questions)}")

        try:
            explanation = generate_elite_explanation(client, q)
            q["explanation"] = explanation
            q["enhanced_at"] = datetime.utcnow().isoformat()
            enhanced.append(q)

            # Save checkpoint periodically
            if (i + 1) % checkpoint_interval == 0:
                checkpoint_data = {
                    "last_index": i,
                    "enhanced": enhanced,
                    "timestamp": datetime.utcnow().isoformat()
                }
                with open(checkpoint_path, 'w') as f:
                    json.dump(checkpoint_data, f)
                logger.info(f"Checkpoint saved at question {i+1}")

            # Rate limiting to avoid API throttling
            time.sleep(delay_seconds)

        except Exception as e:
            logger.error(f"Failed to enhance question {i+1}: {e}")
            # Save checkpoint before failing
            checkpoint_data = {
                "last_index": i - 1,
                "enhanced": enhanced,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "failed_at_index": i
            }
            with open(checkpoint_path, 'w') as f:
                json.dump(checkpoint_data, f)
            print(f"\nError at question {i+1}. Checkpoint saved. Re-run to resume.")
            raise

    # Clean up checkpoint file on successful completion
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        logger.info("Checkpoint file removed after successful completion")

    return enhanced


def save_to_json(questions: List[Dict[str, Any]], output_path: Path):
    """Save extracted questions to JSON file."""
    with open(output_path, 'w') as f:
        json.dump(questions, f, indent=2)
    logger.info(f"Saved {len(questions)} questions to {output_path}")


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="One-time burst import of NBME PDFs with 285+ explanations"
    )
    parser.add_argument(
        "pdf_folder",
        type=Path,
        help="Folder containing PDF files to import"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./extracted_questions.json"),
        help="Output JSON file (default: extracted_questions.json)"
    )
    parser.add_argument(
        "--use-vision",
        action="store_true",
        help="Use vision extraction for image-heavy pages (costs more)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract only, don't generate explanations"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of questions to enhance (for testing)"
    )

    args = parser.parse_args()

    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("Get your key from https://console.anthropic.com")
        sys.exit(1)

    # Check PDF folder
    if not args.pdf_folder.exists():
        print(f"ERROR: PDF folder not found: {args.pdf_folder}")
        sys.exit(1)

    pdf_files = list(args.pdf_folder.glob("*.pdf"))
    if not pdf_files:
        print(f"ERROR: No PDF files found in {args.pdf_folder}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("SHELFSENSE BURST IMPORT")
    print(f"{'='*60}")
    print(f"PDF folder: {args.pdf_folder}")
    print(f"PDF files found: {len(pdf_files)}")
    print(f"Output: {args.output}")
    print(f"Vision mode: {'ON' if args.use_vision else 'OFF'}")
    print(f"Dry run: {'YES' if args.dry_run else 'NO'}")
    print(f"{'='*60}\n")

    # Initialize client
    client = Anthropic(api_key=api_key)

    # Phase 1: Extract from all PDFs
    print("\n[PHASE 1] Extracting questions from PDFs...")
    all_questions = []

    for pdf_file in pdf_files:
        questions = process_pdf(client, pdf_file, use_vision=args.use_vision)
        all_questions.extend(questions)

    print(f"\nTotal questions extracted: {len(all_questions)}")

    if args.dry_run:
        print("\n[DRY RUN] Skipping explanation generation")
        save_to_json(all_questions, args.output)
        return

    # Phase 2: Generate elite explanations
    print("\n[PHASE 2] Generating 285+ explanations...")

    if args.limit:
        all_questions = all_questions[:args.limit]
        print(f"Limited to {args.limit} questions for testing")

    # Cost estimate before proceeding
    estimated_cost = len(all_questions) * 0.05  # ~$0.05 per explanation with Sonnet
    print(f"\nEstimated cost: ${estimated_cost:.2f}")
    print(f"Questions to enhance: {len(all_questions)}")

    if estimated_cost > 50:
        response = input("\nThis will cost more than $50. Continue? (y/n): ")
        if response.lower() != 'y':
            print("Aborted. Saving extracted questions without enhancement...")
            save_to_json(all_questions, args.output.with_suffix('.extracted.json'))
            sys.exit(0)

    def progress(current, total):
        percentage = current / total * 100
        print(f"  Progress: {current}/{total} ({percentage:.1f}%)", end='\r')

    enhanced = enhance_questions(
        client,
        all_questions,
        output_path=args.output,
        progress_callback=progress,
        checkpoint_interval=10,
        delay_seconds=1.0
    )
    print()  # Newline after progress

    # Save results
    save_to_json(enhanced, args.output)

    print(f"\n{'='*60}")
    print("IMPORT COMPLETE")
    print(f"{'='*60}")
    print(f"Questions extracted: {len(all_questions)}")
    print(f"Questions enhanced: {len(enhanced)}")
    print(f"Output saved to: {args.output}")
    print(f"\nNext steps:")
    print(f"1. Review the extracted questions in {args.output}")
    print(f"2. Import to database: python scripts/import_to_db.py {args.output}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
