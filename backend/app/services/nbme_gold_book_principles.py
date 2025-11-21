"""
NBME Gold Book Principles
"Constructing Written Test Questions for the Basic and Clinical Sciences"

10 Golden Rules for USMLE Question Writing
Source: https://www.medschoolgurus.com/blog/the-blueprint-behind-all-usmle-questions
"""

# 1. START WITH AN IMPORTANT CONCEPT RULE
IMPORTANT_CONCEPTS = """
Before writing an item, decide on an important testable concept.
The entire item should be written with this concept in mind.

Questions should:
- Align with educational goals of the test
- Focus on important topics more heavily than unimportant topics
- Focus on important knowledge (not trivial facts)
- Test application of knowledge (not isolated fact recall)
- NOT be tricky or overly complex

Vignettes should focus on:
- Application of knowledge using clinical vignettes
- Common or potentially catastrophic problems (avoid "zebras")
- Specific tasks test-taker must undertake at next stage
- Areas where clinical reasoning mistakes are often made
"""

# 2. USE A VIGNETTE TEMPLATE RULE
VIGNETTE_TEMPLATE = """
First sentence:
- Age, gender (e.g., "A 60-year-old woman")
- Site of care (e.g., "the emergency department")
- Presenting complaint (e.g., "shortness of breath")
- Duration of complaint (e.g., "3 days")

Subsequent sentences:
- History of present illness, past medical history, family history, social history
- Review of systems (if important and plausible)
- Physical findings
- Results of diagnostic studies (labs, imaging, tests)
- Initial treatment, subsequent findings

Lead-in question:
- Should be focused
- Together with stem, should allow listing homogeneous options
- Should allow selecting single best answer WITHOUT looking at options
"""

# 3. SINGLE BEST ANSWER RULE
SINGLE_BEST_ANSWER = """
Options should be:
- Homogeneous (all of same category)
- Able to be judged entirely true or false based on single dimension
- Contain ONE single best answer
- Distractors may be wholly or partially wrong

Single best answer is true along most number of dimensions.

Example: For diagnosis question, single best answer should be:
- Unifying diagnosis consistent with AS MANY components of vignette as possible
"""

# 4. COVER THE OPTIONS RULE
COVER_OPTIONS = """
ALL USMLE questions should be answerable "from the stem and lead-in alone"
"WITHOUT looking at the options"

If lead-in is properly focused, you should be able to:
1. Read the stem and lead-in
2. Cover the options
3. Logically generate a homogeneous set of options
4. Guess the correct answer

This is THE MOST IMPORTANT principle for question quality.
"""

# 5. ALL RELEVANT FACTS RULE
ALL_RELEVANT_FACTS = """
Item stems should contain ALL relevant facts necessary.
NO data should be provided in the options.

All relevant facts are contained in the stem.
The lead-in should allow using these facts to guess correct answer.
"""

# 6. PATIENTS DO NOT LIE RULE
PATIENTS_DO_NOT_LIE = """
Unless you are provided with a statement that physician suspects something
that contradicts what patient reported, assume patient information is correct.

What patient reported or what has been stated about patient is CORRECT.
"""

# 7. CLASSIC CASES RULE
CLASSIC_CASES = """
NBME discourages use of real patient cases (too complex, non-classic).
NBME will NOT try to mislead with "red-herrings" in vignettes.

Items are written with preconceived testable concept in mind.
Cases on USMLE are CLASSIC cases.

"Window dressing" (extraneous info) may be included:
- Step 1: Minimal window dressing
- Step 2 CK: More window dressing
- Step 3: Most window dressing

But classic presentation remains clear.
"""

# 8. NO TRIVIA RULE
NO_TRIVIA = """
USMLE items test IMPORTANT concepts, not trivial facts.

If a fact seems trivial, either:
1. You are misunderstanding the question, OR
2. You don't fully understand why the fact is important

Focus on high-yield concepts, not minutiae.
"""

# 9. NO SAVVY TEST TAKERS RULE
NO_SAVVY_TEST_TAKERS = """
USMLE items prevent savvy test-takers from guessing correct option
based on technical flaws in options or lead-in phrasing.

Don't try to "outsmart" the test.
Instead:
1. Understand the stem
2. Identify the important testable concept
3. Think about this concept
4. Read lead-in
5. Cover answers
6. Come up with answer in your own head
7. Look at options
8. Choose answer that best matches your answer
"""

# 10. HOMOGENEOUS OPTIONS RULE
HOMOGENEOUS_OPTIONS = """
Options must be:
- Homogeneous (all same category: all diagnoses, all treatments, etc.)
- Plausible (each could be reasonable in different context)
- Single dimension evaluation (true vs false along ONE aspect)

Example dimensions:
- Diagnosis: Chronicity (acute vs chronic)
- Diagnosis: Imaging findings
- Diagnosis: Lab findings
- Treatment: Appropriate for stability level
- Treatment: Guidelines-based vs outdated
"""

# PRACTICAL APPLICATION FOR AI GENERATION
def get_generation_principles():
    """Returns key principles for AI question generation"""
    return {
        "vignette_structure": [
            "First sentence: age + gender + setting + complaint + duration",
            "Subsequent: history + physical + labs/imaging + treatment",
            "Lead-in: focused question that can be answered before seeing options",
        ],
        "answer_options": [
            "All options must be homogeneous (same category)",
            "Each option plausible in different clinical context",
            "Correct answer true along MOST dimensions",
            "Distractors wrong along ONE dimension each",
            "Should be able to generate answer before seeing options",
        ],
        "clinical_vignette": [
            "Use CLASSIC presentations (not zebras)",
            "Include all relevant facts in stem",
            "No red herrings or tricks",
            "Focus on common or catastrophic problems",
            "Test clinical reasoning, not trivia",
        ],
        "quality_checks": [
            "Can question be answered without looking at options?",
            "Are all options homogeneous?",
            "Is there ONE clearly best answer?",
            "Does it test important concept (not trivia)?",
            "Are all relevant facts in stem?",
        ],
    }
