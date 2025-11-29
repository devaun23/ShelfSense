#!/usr/bin/env python3
"""
Test PDF Extraction Script

Tests PDF extraction on a single file before running the full burst import.
Validates that:
1. PyMuPDF can read the PDF
2. Text extraction works (or vision is needed)
3. Claude can parse questions from the content
4. Output structure is valid

Usage:
    export ANTHROPIC_API_KEY="your-key"
    python scripts/test_pdf_extract.py path/to/sample.pdf

    # Test without API (just check PDF readability)
    python scripts/test_pdf_extract.py path/to/sample.pdf --offline
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("WARNING: PyMuPDF not installed. Run: pip install pymupdf")

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


def check_pdf_readability(pdf_path: Path) -> Dict[str, Any]:
    """
    Check if PDF can be read and extract basic info.
    """
    if not PYMUPDF_AVAILABLE:
        return {"error": "PyMuPDF not installed"}

    try:
        doc = fitz.open(pdf_path)

        result = {
            "readable": True,
            "page_count": len(doc),
            "pages": []
        }

        for i, page in enumerate(doc):
            text = page.get_text()
            images = page.get_images()

            page_info = {
                "page_num": i + 1,
                "text_length": len(text),
                "has_text": len(text.strip()) > 50,
                "image_count": len(images),
                "text_preview": text[:200].strip() if text else ""
            }
            result["pages"].append(page_info)

        doc.close()

        # Analyze
        pages_with_text = sum(1 for p in result["pages"] if p["has_text"])
        pages_with_images = sum(1 for p in result["pages"] if p["image_count"] > 0)

        result["analysis"] = {
            "pages_with_text": pages_with_text,
            "pages_with_images": pages_with_images,
            "needs_vision": pages_with_images > pages_with_text,
            "recommendation": (
                "Use --use-vision flag" if pages_with_images > pages_with_text
                else "Text extraction should work"
            )
        }

        return result

    except Exception as e:
        return {"readable": False, "error": str(e)}


def test_extraction_with_claude(pdf_path: Path, page_num: int = 1) -> Dict[str, Any]:
    """
    Test question extraction on a single page using Claude.
    """
    if not ANTHROPIC_AVAILABLE:
        return {"error": "Anthropic not installed"}

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not set"}

    try:
        # Extract text from specified page
        doc = fitz.open(pdf_path)
        if page_num > len(doc):
            return {"error": f"Page {page_num} not found (PDF has {len(doc)} pages)"}

        page = doc[page_num - 1]
        text = page.get_text()
        doc.close()

        if len(text.strip()) < 50:
            return {
                "warning": "Page has very little text",
                "text_length": len(text),
                "suggestion": "Try a different page or use --use-vision"
            }

        # Call Claude for extraction
        client = Anthropic(api_key=api_key)

        prompt = f"""Extract any USMLE-style medical questions from this text.

For each question found, return JSON:
{{
    "vignette": "Clinical scenario",
    "question_stem": "What is asked",
    "choices": {{"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."}},
    "answer_key": "A/B/C/D/E or null",
    "source": "NBME/UWorld/Unknown"
}}

If no complete questions found, return: []

TEXT:
{text[:3000]}"""

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text

        # Parse response
        json_start = content.find("[")
        json_end = content.rfind("]") + 1

        if json_start >= 0 and json_end > json_start:
            questions = json.loads(content[json_start:json_end])
            return {
                "success": True,
                "questions_found": len(questions),
                "questions": questions,
                "api_cost_estimate": "$0.002"
            }

        return {
            "success": True,
            "questions_found": 0,
            "message": "No questions detected on this page",
            "raw_response": content[:500]
        }

    except Exception as e:
        return {"error": str(e)}


def validate_question_structure(question: Dict[str, Any]) -> List[str]:
    """
    Validate that a question has the required structure.
    """
    issues = []

    if not question.get("vignette"):
        issues.append("Missing vignette")

    choices = question.get("choices", {})
    if not choices:
        issues.append("Missing choices")
    else:
        expected = ["A", "B", "C", "D", "E"]
        missing = [c for c in expected if c not in choices]
        if missing:
            issues.append(f"Missing choices: {missing}")

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Test PDF extraction before full import"
    )
    parser.add_argument(
        "pdf_path",
        type=Path,
        help="Path to PDF file to test"
    )
    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="Page number to test extraction on (default: 1)"
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Only check PDF readability, don't call Claude API"
    )
    parser.add_argument(
        "--all-pages",
        action="store_true",
        help="Analyze all pages (offline mode only)"
    )

    args = parser.parse_args()

    # Check file exists
    if not args.pdf_path.exists():
        print(f"ERROR: File not found: {args.pdf_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("SHELFSENSE PDF EXTRACTION TEST")
    print(f"{'='*60}")
    print(f"File: {args.pdf_path}")
    print(f"Size: {args.pdf_path.stat().st_size / 1024:.1f} KB")
    print(f"{'='*60}\n")

    # Step 1: Check readability
    print("[1/3] Checking PDF readability...")
    read_result = check_pdf_readability(args.pdf_path)

    if not read_result.get("readable"):
        print(f"  ERROR: {read_result.get('error')}")
        sys.exit(1)

    print(f"  Pages: {read_result['page_count']}")
    print(f"  Pages with text: {read_result['analysis']['pages_with_text']}")
    print(f"  Pages with images: {read_result['analysis']['pages_with_images']}")
    print(f"  Recommendation: {read_result['analysis']['recommendation']}")

    if args.all_pages:
        print("\n  Per-page analysis:")
        for page in read_result["pages"]:
            status = "TEXT" if page["has_text"] else "IMG" if page["image_count"] > 0 else "EMPTY"
            print(f"    Page {page['page_num']}: [{status}] {page['text_length']} chars")

    if args.offline:
        print("\n[OFFLINE MODE] Skipping API test")
        print(f"\n{'='*60}")
        print("RESULT: PDF is readable")
        if read_result['analysis']['needs_vision']:
            print("NOTE: This PDF may need --use-vision flag for best results")
        print(f"{'='*60}\n")
        return

    # Step 2: Test Claude extraction
    print(f"\n[2/3] Testing Claude extraction on page {args.page}...")

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("  SKIP: ANTHROPIC_API_KEY not set")
        print("  Set it to test extraction: export ANTHROPIC_API_KEY='your-key'")
    else:
        extract_result = test_extraction_with_claude(args.pdf_path, args.page)

        if extract_result.get("error"):
            print(f"  ERROR: {extract_result['error']}")
        elif extract_result.get("warning"):
            print(f"  WARNING: {extract_result['warning']}")
            print(f"  Suggestion: {extract_result.get('suggestion')}")
        else:
            print(f"  Questions found: {extract_result['questions_found']}")
            print(f"  API cost: {extract_result.get('api_cost_estimate', 'N/A')}")

            if extract_result['questions_found'] > 0:
                print("\n  Sample question structure:")
                q = extract_result['questions'][0]
                print(f"    Vignette length: {len(q.get('vignette', ''))} chars")
                print(f"    Choices: {list(q.get('choices', {}).keys())}")
                print(f"    Answer: {q.get('answer_key', 'N/A')}")

                # Validate structure
                issues = validate_question_structure(q)
                if issues:
                    print(f"    Issues: {issues}")
                else:
                    print("    Structure: VALID")

    # Step 3: Summary
    print(f"\n{'='*60}")
    print("TEST COMPLETE")
    print(f"{'='*60}")

    if read_result.get("readable"):
        print("PDF Status: READABLE")
        print(f"Estimated questions: ~{read_result['page_count'] * 2} (rough estimate)")
        print(f"Estimated cost: ~${read_result['page_count'] * 0.05:.2f}")

        print("\nReady to run full import:")
        cmd = f"python scripts/burst_import.py {args.pdf_path.parent}/"
        if read_result['analysis']['needs_vision']:
            cmd += " --use-vision"
        print(f"  {cmd}")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
