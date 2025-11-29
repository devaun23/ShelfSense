"""
Originality Checker for AI-Generated Questions

Ensures generated questions are novel and don't plagiarize existing content.
Uses multiple detection methods:
1. Fuzzy text matching (fast, no API cost)
2. N-gram overlap detection
3. Semantic similarity via embeddings (optional, uses API)

Usage:
    from app.services.originality_checker import OriginalityChecker

    checker = OriginalityChecker(db)
    await checker.load_corpus()

    result = await checker.check_originality(question_dict)
    if result.is_original:
        # Safe to use
    else:
        # Too similar to existing question
"""

import re
import logging
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass
from datetime import datetime
from collections import Counter

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class OriginalityResult:
    """Result of originality check."""
    is_original: bool  # True if question is sufficiently novel
    similarity_score: float  # 0-1, higher = more similar to existing
    matched_question_id: Optional[str]  # ID of most similar existing question
    matched_text: Optional[str]  # Preview of matched content
    method_used: str  # Which detection method found the match
    check_time_ms: float
    details: Dict[str, Any]


class OriginalityChecker:
    """
    Checks AI-generated questions for originality.

    Uses a multi-tiered approach:
    1. Exact phrase matching (catches direct copies)
    2. N-gram overlap (catches paraphrased copies)
    3. Semantic similarity (catches conceptual copies) - optional

    Default threshold: 0.7 similarity = flagged as duplicate
    """

    def __init__(
        self,
        db: Session,
        similarity_threshold: float = 0.7,
        ngram_size: int = 4,
        min_phrase_length: int = 8
    ):
        """
        Initialize the checker.

        Args:
            db: Database session for loading existing questions
            similarity_threshold: 0-1, questions above this are flagged
            ngram_size: Size of n-grams for overlap detection
            min_phrase_length: Minimum words for phrase matching
        """
        self.db = db
        self.similarity_threshold = similarity_threshold
        self.ngram_size = ngram_size
        self.min_phrase_length = min_phrase_length

        # Corpus data (loaded lazily)
        self._corpus_loaded = False
        self._question_texts: Dict[str, str] = {}  # id -> normalized text
        self._question_ngrams: Dict[str, Set[str]] = {}  # id -> set of ngrams
        self._all_ngrams: Set[str] = set()  # All ngrams across corpus

        # Stats
        self._checks_performed = 0
        self._duplicates_found = 0

    async def load_corpus(self, force_reload: bool = False) -> int:
        """
        Load existing questions into memory for comparison.

        Args:
            force_reload: If True, reload even if already loaded

        Returns:
            Number of questions loaded
        """
        if self._corpus_loaded and not force_reload:
            return len(self._question_texts)

        from app.models.models import Question

        logger.info("Loading question corpus for originality checking...")

        try:
            questions = self.db.query(Question).filter(
                Question.vignette.isnot(None)
            ).all()

            for q in questions:
                q_id = str(q.id)
                text = self._normalize_text(q.vignette or "")

                if len(text) > 50:  # Skip very short questions
                    self._question_texts[q_id] = text
                    ngrams = self._extract_ngrams(text)
                    self._question_ngrams[q_id] = ngrams
                    self._all_ngrams.update(ngrams)

            self._corpus_loaded = True
            logger.info(f"Loaded {len(self._question_texts)} questions into corpus")

            return len(self._question_texts)

        except Exception as e:
            logger.error(f"Failed to load corpus: {e}")
            return 0

    async def check_originality(
        self,
        question: Dict[str, Any],
        use_semantic: bool = False
    ) -> OriginalityResult:
        """
        Check if a question is original.

        Args:
            question: Question dict with vignette
            use_semantic: If True, also use embedding similarity (costs API calls)

        Returns:
            OriginalityResult with similarity info
        """
        start_time = datetime.utcnow()
        self._checks_performed += 1

        # Ensure corpus is loaded
        if not self._corpus_loaded:
            await self.load_corpus()

        vignette = question.get("vignette", "")
        normalized_text = self._normalize_text(vignette)

        if len(normalized_text) < 50:
            return OriginalityResult(
                is_original=True,
                similarity_score=0,
                matched_question_id=None,
                matched_text=None,
                method_used="skip_short",
                check_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                details={"reason": "Question too short to check"}
            )

        # Method 1: Exact phrase matching
        phrase_result = self._check_exact_phrases(normalized_text)
        if phrase_result[0] >= self.similarity_threshold:
            self._duplicates_found += 1
            return OriginalityResult(
                is_original=False,
                similarity_score=phrase_result[0],
                matched_question_id=phrase_result[1],
                matched_text=phrase_result[2],
                method_used="exact_phrase",
                check_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                details={"matched_phrases": phrase_result[3]}
            )

        # Method 2: N-gram overlap
        ngram_result = self._check_ngram_overlap(normalized_text)
        if ngram_result[0] >= self.similarity_threshold:
            self._duplicates_found += 1
            return OriginalityResult(
                is_original=False,
                similarity_score=ngram_result[0],
                matched_question_id=ngram_result[1],
                matched_text=ngram_result[2],
                method_used="ngram_overlap",
                check_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                details={"overlap_ratio": ngram_result[0]}
            )

        # Method 3: Semantic similarity (optional)
        if use_semantic:
            semantic_result = await self._check_semantic_similarity(normalized_text)
            if semantic_result[0] >= self.similarity_threshold:
                self._duplicates_found += 1
                return OriginalityResult(
                    is_original=False,
                    similarity_score=semantic_result[0],
                    matched_question_id=semantic_result[1],
                    matched_text=semantic_result[2],
                    method_used="semantic",
                    check_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                    details={"cosine_similarity": semantic_result[0]}
                )

        # Passed all checks - question is original
        max_similarity = max(phrase_result[0], ngram_result[0])

        return OriginalityResult(
            is_original=True,
            similarity_score=max_similarity,
            matched_question_id=phrase_result[1] if phrase_result[0] > ngram_result[0] else ngram_result[1],
            matched_text=None,
            method_used="all_passed",
            check_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            details={
                "phrase_similarity": phrase_result[0],
                "ngram_similarity": ngram_result[0]
            }
        )

    async def check_batch(
        self,
        questions: List[Dict[str, Any]],
        use_semantic: bool = False
    ) -> Tuple[List[Dict[str, Any]], List[OriginalityResult]]:
        """
        Check a batch of questions, returning only original ones.

        Args:
            questions: List of question dicts
            use_semantic: If True, also use embedding similarity

        Returns:
            Tuple of (original_questions, all_results)
        """
        original_questions = []
        all_results = []

        for i, question in enumerate(questions):
            logger.info(f"Checking originality {i+1}/{len(questions)}")

            result = await self.check_originality(question, use_semantic)
            all_results.append(result)

            if result.is_original:
                original_questions.append(question)
            else:
                logger.warning(
                    f"Duplicate detected: {result.similarity_score:.2%} similar to {result.matched_question_id}"
                )

        logger.info(
            f"Originality check: {len(original_questions)}/{len(questions)} passed "
            f"({len(questions) - len(original_questions)} duplicates filtered)"
        )

        return original_questions, all_results

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Lowercase
        text = text.lower()

        # Remove extra whitespace
        text = " ".join(text.split())

        # Remove common medical abbreviations variations
        # (e.g., "y/o" -> "year old")
        replacements = {
            r"\by/o\b": "year old",
            r"\byo\b": "year old",
            r"\bh/o\b": "history of",
            r"\bc/o\b": "complaining of",
            r"\bs/p\b": "status post",
            r"\bw/\b": "with",
            r"\bpt\b": "patient",
            r"\bdx\b": "diagnosis",
            r"\btx\b": "treatment",
            r"\brx\b": "prescription",
        }

        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)

        # Remove punctuation except essential ones
        text = re.sub(r"[^\w\s\-\.]", " ", text)
        text = " ".join(text.split())

        return text

    def _extract_ngrams(self, text: str) -> Set[str]:
        """Extract n-grams from text."""
        words = text.split()
        ngrams = set()

        for i in range(len(words) - self.ngram_size + 1):
            ngram = " ".join(words[i:i + self.ngram_size])
            ngrams.add(ngram)

        return ngrams

    def _check_exact_phrases(self, text: str) -> Tuple[float, Optional[str], Optional[str], List[str]]:
        """
        Check for exact phrase matches using indexed lookups.

        Returns:
            Tuple of (similarity_score, matched_id, matched_preview, matched_phrases)
        """
        words = text.split()
        if len(words) < self.min_phrase_length:
            return (0.0, None, None, [])

        # Extract candidate phrases from input
        phrases = []
        for i in range(len(words) - self.min_phrase_length + 1):
            phrase = " ".join(words[i:i + self.min_phrase_length])
            phrases.append(phrase)

        if not phrases:
            return (0.0, None, None, [])

        # Count matches per question using indexed lookup
        match_counts: Dict[str, int] = {}
        matched_phrases_by_q: Dict[str, List[str]] = {}

        for phrase in phrases:
            # O(n) search - consider building an inverted index if performance is critical
            for q_id, corpus_text in self._question_texts.items():
                if phrase in corpus_text:
                    match_counts[q_id] = match_counts.get(q_id, 0) + 1
                    if q_id not in matched_phrases_by_q:
                        matched_phrases_by_q[q_id] = []
                    if len(matched_phrases_by_q[q_id]) < 5:  # Limit stored phrases
                        matched_phrases_by_q[q_id].append(phrase)

        if not match_counts:
            return (0.0, None, None, [])

        # Find best match
        best_match_id = max(match_counts.items(), key=lambda x: x[1])[0]
        best_match_score = match_counts[best_match_id] / len(phrases)
        best_match_preview = self._question_texts.get(best_match_id, "")[:200] + "..."
        matched_phrases = matched_phrases_by_q.get(best_match_id, [])

        return (best_match_score, best_match_id, best_match_preview, matched_phrases)

    def _check_ngram_overlap(self, text: str) -> Tuple[float, Optional[str], Optional[str]]:
        """
        Check for n-gram overlap with corpus.

        Returns:
            Tuple of (similarity_score, matched_id, matched_preview)
        """
        text_ngrams = self._extract_ngrams(text)

        if not text_ngrams:
            return (0.0, None, None)

        best_match_id = None
        best_match_score = 0.0
        best_match_preview = None

        for q_id, corpus_ngrams in self._question_ngrams.items():
            if not corpus_ngrams:
                continue

            # Jaccard similarity
            intersection = len(text_ngrams & corpus_ngrams)
            union = len(text_ngrams | corpus_ngrams)

            if union > 0:
                similarity = intersection / union

                if similarity > best_match_score:
                    best_match_score = similarity
                    best_match_id = q_id
                    best_match_preview = self._question_texts.get(q_id, "")[:200] + "..."

        return (best_match_score, best_match_id, best_match_preview)

    async def _check_semantic_similarity(
        self,
        text: str
    ) -> Tuple[float, Optional[str], Optional[str]]:
        """
        Check semantic similarity using embeddings.

        Note: This method uses API calls and costs money.
        Only use when high-confidence originality is needed.

        Returns:
            Tuple of (similarity_score, matched_id, matched_preview)
        """
        # For now, return 0 similarity (not implemented)
        # Can be extended to use OpenAI embeddings or sentence-transformers
        logger.info("Semantic similarity check not yet implemented - skipping")
        return (0.0, None, None)

    def add_to_corpus(self, question_id: str, vignette: str) -> None:
        """
        Add a new question to the corpus (call after accepting a question).

        Args:
            question_id: Unique ID of the question
            vignette: Question vignette text
        """
        text = self._normalize_text(vignette)

        if len(text) > 50:
            self._question_texts[question_id] = text
            ngrams = self._extract_ngrams(text)
            self._question_ngrams[question_id] = ngrams
            self._all_ngrams.update(ngrams)

            logger.debug(f"Added question {question_id} to originality corpus")

    def get_stats(self) -> Dict[str, Any]:
        """Get checker statistics."""
        return {
            "corpus_size": len(self._question_texts),
            "corpus_loaded": self._corpus_loaded,
            "checks_performed": self._checks_performed,
            "duplicates_found": self._duplicates_found,
            "duplicate_rate": (
                f"{(self._duplicates_found / self._checks_performed * 100):.1f}%"
                if self._checks_performed > 0 else "N/A"
            ),
            "config": {
                "similarity_threshold": self.similarity_threshold,
                "ngram_size": self.ngram_size,
                "min_phrase_length": self.min_phrase_length
            }
        }


# Convenience function
async def check_question_originality(
    db: Session,
    question: Dict[str, Any]
) -> OriginalityResult:
    """Quick originality check using default settings."""
    checker = OriginalityChecker(db)
    await checker.load_corpus()
    return await checker.check_originality(question)
